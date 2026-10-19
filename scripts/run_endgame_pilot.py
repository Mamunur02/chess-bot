"""Run the bounded, development-only neural endgame pilot.

Usage: ``python scripts/run_endgame_pilot.py --development-dir ...``. The
runner deliberately reads only the KRvKR development partition.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import time
import tracemalloc
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

import chess
import chess.syzygy

from chesslab.endgames.acquisition import _utc_now
from chesslab.endgames.dataset import verify_acquisition_manifest
from chesslab.endgames.encoding import encode_board
from chesslab.endgames.identity import canonical_position, make_rng, ownership_bucket
from chesslab.endgames.interaction import run_interaction
from chesslab.endgames.reference import evaluate

MAX_DECISIONS = 512
REPLAY_WARMUP = 256
UPDATE_INTERVAL = 8
REPLAY_BATCH_SIZE = 32
BETAS = (0.0, 0.5, 1.0)
DEV_SEED = 1101
PILOT_SEED = 9001
SOURCE_FILES = (
    "scripts/run_endgame_pilot.py",
    "src/chesslab/endgames/acquisition.py",
    "src/chesslab/endgames/dataset.py",
    "src/chesslab/endgames/encoding.py",
    "src/chesslab/endgames/identity.py",
    "src/chesslab/endgames/interaction.py",
    "src/chesslab/endgames/neural.py",
    "src/chesslab/endgames/opponent.py",
    "src/chesslab/endgames/reference.py",
    "src/chesslab/endgames/replay.py",
    "src/chesslab/endgames/rules.py",
    "src/chesslab/endgames/targets.py",
)


def update_is_eligible(transition_count: int, replay_size: int) -> bool:
    """Return whether the protocol warmup/interval schedule allows an update."""
    return (
        transition_count >= REPLAY_WARMUP
        and transition_count % UPDATE_INTERVAL == 0
        and replay_size >= REPLAY_BATCH_SIZE
    )


def validate_decisions(decisions: int) -> None:
    """Enforce the prespecified pilot's bounded decision count."""
    if isinstance(decisions, bool) or not 1 <= decisions <= MAX_DECISIONS:
        raise ValueError(f"decisions must be between 1 and {MAX_DECISIONS}")


def create_fresh_output(path: Path) -> None:
    """Create a new output directory and refuse to overwrite prior results."""
    path.mkdir(parents=True, exist_ok=False)


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_state(root: Path) -> dict[str, object]:
    state: dict[str, object] = {}
    safe_directory = root.resolve().as_posix()
    for name, arguments in (
        ("head", ["rev-parse", "HEAD"]),
        ("status", ["status", "--porcelain"]),
        ("diff_sha256", ["diff", "--binary"]),
    ):
        try:
            result = subprocess.run(
                ["git", "-c", f"safe.directory={safe_directory}", *arguments],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            state[name] = (
                _sha256(result.stdout.encode())
                if name == "diff_sha256"
                else result.stdout.strip()
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            state[name] = {"error": str(exc)}
    return state


def _source_snapshot(root: Path, output: Path) -> dict[str, str]:
    destination = output / "source"
    hashes: dict[str, str] = {}
    for relative in SOURCE_FILES:
        source = root / relative
        data = source.read_bytes()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[relative] = _sha256(data)
    return hashes


def _load_development(directory: Path) -> tuple[list[dict[str, Any]], str]:
    """Verify and load only the complete KRvKR development JSONL partition."""
    data_path = directory / "krvkr-development.jsonl"
    manifest_path = directory / "krvkr-development.manifest.json"
    raw = data_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("family") != "KRvKR"
        or manifest.get("partition") != "development"
        or manifest.get("seed") != DEV_SEED
        or manifest.get("complete") is not True
        or manifest.get("status") != "complete"
        or manifest.get("row_count") != 2000
        or manifest.get("jsonl_sha256") != _sha256(raw)
    ):
        raise ValueError("KRvKR development manifest/hash/seed is invalid")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    if len(rows) != 2000:
        raise ValueError("KRvKR development JSONL must contain exactly 2000 rows")
    indexed: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for row in rows:
        if row.get("family") != "KRvKR" or row.get("ownership_split") != "development":
            raise ValueError(
                "development row has incorrect family or ownership partition"
            )
        try:
            board = chess.Board(str(row["fen"]))
        except (KeyError, ValueError) as exc:
            raise ValueError("development row contains an invalid FEN") from exc
        if not board.is_valid() or board.chess960:
            raise ValueError("development row contains an invalid standard board")
        key = canonical_position(board)
        if row.get("canonical_position") != key:
            raise ValueError("development row canonical key mismatch")
        bucket = ownership_bucket("KRvKR", key)
        if (
            bucket >= 10
            or row.get("ownership_bucket") != bucket
            or row.get("ownership_split") != "development"
        ):
            raise ValueError("development row is not owned by the development split")
        if key in seen:
            raise ValueError("development rows contain duplicate canonical keys")
        seen.add(key)
        indexed.append((key, row))
    indexed.sort(
        key=lambda item: hashlib.sha256(f"pilot-v1|KRvKR|{item[0]}".encode()).digest()
    )
    return [row for _, row in indexed], _sha256(raw)


class _Predictor(Protocol):
    def predict(
        self, positions: Sequence[tuple[chess.Board, chess.Color]]
    ) -> Sequence[float]: ...


def _mse(
    predictor: _Predictor, boards: list[chess.Board], labels: list[float]
) -> float:
    learners = [not board.turn for board in boards]
    values = predictor.predict(list(zip(boards, learners, strict=True)))
    if not values:
        raise ValueError("validation subset must not be empty")
    return math.fsum(
        (value - label) ** 2 for value, label in zip(values, labels, strict=True)
    ) / len(values)


class _CountingProbe:
    """Count tablebase queries while forwarding the python-chess interface."""

    def __init__(self, table: Any) -> None:
        self.table = table
        self.probes = 0
        self.probe_seconds = 0.0

    def probe_wdl(self, board: chess.Board) -> int:
        self.probes += 1
        started = time.perf_counter()
        try:
            return int(self.table.probe_wdl(board))
        finally:
            self.probe_seconds += time.perf_counter() - started

    def probe_dtz(self, board: chess.Board) -> int:
        self.probes += 1
        started = time.perf_counter()
        try:
            return int(self.table.probe_dtz(board))
        finally:
            self.probe_seconds += time.perf_counter() - started

    def close(self) -> None:
        """Close the wrapped tablebase handle."""
        self.table.close()


def _peak_memory() -> dict[str, object]:
    """Report process-lifetime Windows peak or pilot-scoped Python heap peak."""
    if os.name == "nt":

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        get_process = ctypes.windll.kernel32.GetCurrentProcess
        get_process.restype = ctypes.c_void_p
        get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        get_memory.restype = ctypes.c_int
        process = get_process()
        if get_memory(
            process, ctypes.byref(counters), counters.cb
        ):
            return {
                "kind": "process_lifetime_peak_working_set",
                "bytes": int(counters.PeakWorkingSetSize),
            }
        return {"kind": "process_lifetime_peak_working_set_unavailable"}
    current, peak = tracemalloc.get_traced_memory()
    return {
        "kind": "pilot_python_heap_peak",
        "current_bytes": current,
        "peak_bytes": peak,
    }


def _package_versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for package in ("python-chess", "torch", "numpy"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = None
    return result


def _save_checkpoint(torch: Any, model: Any, path: Path) -> str:
    torch.save(model.state_dict(), path)
    return _sha256(path.read_bytes())


def _record_method_failure(
    method: dict[str, object],
    result_path: Path,
    *,
    status: str,
    error: str,
    elapsed_seconds: float,
) -> None:
    """Persist partial method progress when its run fails or is interrupted."""
    if status not in {"failed", "interrupted"}:
        raise ValueError("method failure status must be failed or interrupted")
    method.update(
        {
            "status": status,
            "error": error,
            "elapsed_seconds": max(0.0, elapsed_seconds),
            "memory_sample": _peak_memory(),
        }
    )
    _atomic_json(result_path, method)


def run_pilot(args: argparse.Namespace) -> dict[str, object]:
    validate_decisions(args.decisions)
    if args.threads <= 0:
        raise ValueError("threads must be positive")
    output = args.output_dir
    create_fresh_output(output)
    manifest: dict[str, object] = {
        "protocol": "opponent-dependence-protocol-v1",
        "status": "running",
        "cost_accounting": {
            "simulator_and_online_inference_seconds": (
                "Residual wall time after separately timed target construction and "
                "optimizer work; includes simulation, online inference, encoding, "
                "replay, logging, opponent selection, reference queries, and runtime "
                "overhead. Reference query seconds are a nested diagnostic and must "
                "not be added again."
            ),
            "target_forward_leaves": (
                "Counts nonterminal network leaves evaluated during target building; "
                "terminal branches require no network forward."
            ),
        },
        "started_at_utc": _utc_now(),
        "arguments": {"decisions": args.decisions, "threads": args.threads},
        "pilot_seed": PILOT_SEED,
        "development_seed": DEV_SEED,
        "methods": [],
    }
    _atomic_json(output / "pilot.json", manifest)
    if os.name != "nt":
        tracemalloc.start()
    overall_start = time.perf_counter()
    neural_import_start = time.perf_counter()
    active_method: dict[str, object] | None = None
    active_result_path: Path | None = None
    active_method_start: float | None = None
    try:
        # Keep the lightweight scheduling/output helpers importable without
        # the optional neural dependency installed.
        from chesslab.endgames.neural import (
            BatchPredictor,
            PretrainingConfig,
            RLValueTrainer,
            ValueNetwork,
            pretrain,
        )
        from chesslab.endgames.replay import ReplayBuffer
        from chesslab.endgames.targets import build_targets

        neural_import_seconds = time.perf_counter() - neural_import_start
        root = Path(__file__).resolve().parents[1]
        manifest["git"] = _git_state(root)
        manifest["source_sha256"] = _source_snapshot(root, output)
        manifest["platform"] = {
            "python": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
        }
        manifest["dependencies"] = _package_versions()
        manifest["thread_request"] = args.threads

        ordered_rows, dev_hash = _load_development(args.development_dir)
        manifest["development"] = {
            "partition": "KRvKR-development",
            "manifest": str(args.development_dir / "krvkr-development.manifest.json"),
            "jsonl_sha256": dev_hash,
            "verified_seed": DEV_SEED,
            "deterministic_selection": "sha256(pilot-v1|KRvKR|canonical_position)",
            "training_count": 1600,
            "validation_count": 400,
        }
        acquisition = verify_acquisition_manifest(
            args.acquisition_manifest, args.tablebase_dir
        )
        manifest["acquisition_manifest_sha256"] = _sha256(
            args.acquisition_manifest.read_bytes()
        )
        manifest["table_hashes"] = acquisition["table_sha256"]
        _atomic_json(output / "pilot.json", manifest)

        labels_start = time.perf_counter()
        table = _CountingProbe(chess.syzygy.open_tablebase(str(args.tablebase_dir)))
        try:
            labels: list[float] = []
            wdl_counts: Counter[str] = Counter()
            for row in ordered_rows:
                board = chess.Board(str(row["fen"]))
                reference = evaluate(board, table)
                labels.append(-float(reference.value))
                wdl_counts[str(reference.raw_wdl)] += 1
            label_seconds = time.perf_counter() - labels_start
            if len(labels) != 2000:
                raise RuntimeError(
                    "reference labeling did not cover all development rows"
                )

            train_rows, validation_rows = ordered_rows[:1600], ordered_rows[1600:]
            train_boards = [chess.Board(str(row["fen"])) for row in train_rows]
            validation_boards = [
                chess.Board(str(row["fen"])) for row in validation_rows
            ]
            train_labels, validation_labels = labels[:1600], labels[1600:]
            import torch  # type: ignore[import-not-found]

            model_loading_seconds = 0.0
            torch.set_num_threads(args.threads)
            try:
                torch.set_num_interop_threads(args.threads)
            except RuntimeError:
                pass
            actual_threads = {
                "intraop": torch.get_num_threads(),
                "interop": torch.get_num_interop_threads(),
            }
            torch.use_deterministic_algorithms(True)
            manifest["threads"] = actual_threads
            manifest["compute"] = {
                "device": "cpu",
                "deterministic_algorithms": (
                    torch.are_deterministic_algorithms_enabled()
                ),
            }

            pretrain_start = time.perf_counter()
            initial = ValueNetwork(root_seed=PILOT_SEED)
            initial.eval()
            initial_path = output / "initial-checkpoint.pt"
            initial_hash = _save_checkpoint(torch, initial, initial_path)
            initial_predictor = BatchPredictor(initial)
            initial_mse = _mse(initial_predictor, validation_boards, validation_labels)
            train_learners = [not board.turn for board in train_boards]
            validation_learners = [not board.turn for board in validation_boards]
            config = PretrainingConfig()
            pretraining = pretrain(
                initial,
                [
                    encode_board(board, learner)
                    for board, learner in zip(train_boards, train_learners, strict=True)
                ],
                train_labels,
                [
                    encode_board(board, learner)
                    for board, learner in zip(
                        validation_boards, validation_learners, strict=True
                    )
                ],
                validation_labels,
                seed=PILOT_SEED,
                config=config,
            )
            pretrained = ValueNetwork(root_seed=PILOT_SEED)
            pretrained.load_state_dict(pretraining.best_state_dict)
            pretrained.eval()
            pretrained_path = output / "pretrained-checkpoint.pt"
            pretrained_hash = _save_checkpoint(torch, pretrained, pretrained_path)
            frozen_predictor = BatchPredictor(pretrained)
            frozen_mse = _mse(frozen_predictor, validation_boards, validation_labels)
            pretraining_seconds = time.perf_counter() - pretrain_start
            manifest["labeling"] = {
                "seconds": label_seconds,
                "tablebase_probe_calls": table.probes,
                "tablebase_probe_seconds": table.probe_seconds,
                "raw_wdl_counts": dict(sorted(wdl_counts.items())),
                "label_counts": dict(
                    sorted(Counter(str(value) for value in labels).items())
                ),
            }
            pretraining_config: dict[str, object] = {
                "learning_rate": config.learning_rate,
                "batch_size": config.batch_size,
                "max_epochs": config.max_epochs,
                "patience": config.patience,
                "min_delta": config.min_delta,
                "seed": PILOT_SEED,
            }
            manifest["pretraining"] = {
                "config": pretraining_config,
                "epochs": [
                    {
                        "epoch": record.epoch,
                        "training_mse": record.training_mse,
                        "validation_mse": record.validation_mse,
                    }
                    for record in pretraining.epochs
                ],
                "best_epoch": pretraining.best_epoch,
                "stop_reason": pretraining.stop_reason,
                "untrained_validation_mse": initial_mse,
                "frozen_validation_mse": frozen_mse,
                "untrained_validation_forward_boards": (
                    initial_predictor.boards_evaluated
                ),
                "initial_checkpoint_sha256": initial_hash,
                "pretrained_checkpoint_sha256": pretrained_hash,
                "seconds": pretraining_seconds,
                "frozen_validation_forward_boards": frozen_predictor.boards_evaluated,
                "training_forward_boards": len(train_boards)
                * len(pretraining.epochs),
                "validation_forward_boards": len(validation_boards)
                * len(pretraining.epochs),
            }
            _atomic_json(
                output / "resolved-config.json",
                {
                    "protocol": "opponent-dependence-protocol-v1",
                    "family": "KRvKR",
                    "decision_budget": args.decisions,
                    "betas": list(BETAS),
                    "epsilon": 0.1,
                    "opponent_p": 0.5,
                    "rl_seed": PILOT_SEED,
                    "replay_capacity": 10_000,
                    "replay_warmup": REPLAY_WARMUP,
                    "update_interval": UPDATE_INTERVAL,
                    "batch_size": REPLAY_BATCH_SIZE,
                    "pretraining": pretraining_config,
                    "initialization_seed": PILOT_SEED,
                    "torch_device": "cpu",
                },
            )
            _atomic_json(output / "pilot.json", manifest)

            method_results: list[dict[str, object]] = []
            for beta in BETAS:
                result_path = output / f"beta-{beta:.1f}.json"
                method: dict[str, object] = {"beta": beta, "status": "running"}
                method_results.append(method)
                active_method = method
                active_result_path = result_path
                active_method_start = time.perf_counter()
                manifest["methods"] = method_results
                _atomic_json(result_path, method)
                _atomic_json(output / "pilot.json", manifest)
                load_start = time.perf_counter()
                online = ValueNetwork(root_seed=PILOT_SEED)
                online.load_state_dict(pretraining.best_state_dict)
                trainer = RLValueTrainer(online)
                model_loading_seconds += time.perf_counter() - load_start
                online_before = [
                    parameter.detach().clone()
                    for parameter in trainer.online.parameters()
                ]
                target_predictor = BatchPredictor(trainer.target)
                online_predictor = BatchPredictor(trainer.online)
                replay = ReplayBuffer()
                replay_rng = make_rng(PILOT_SEED, "replay")
                target_seconds = update_seconds = 0.0
                target_leaves = 0
                update_records: list[dict[str, object]] = []
                transition_count = 0
                method_start = time.perf_counter()

                def on_transition(transition: Any) -> None:
                    nonlocal \
                        transition_count, \
                        target_seconds, \
                        update_seconds, \
                        target_leaves
                    replay.append(
                        transition.afterstate,
                        transition.learner,
                        transition.observed_reply,
                    )
                    transition_count += 1
                    if update_is_eligible(transition_count, len(replay)):
                        batch = replay.sample(REPLAY_BATCH_SIZE, replay_rng)
                        started = time.perf_counter()
                        target_batch = build_targets(batch, beta, target_predictor)
                        target_seconds += time.perf_counter() - started
                        target_leaves += target_batch.forward_leaf_count
                        features = torch.tensor(
                            [
                                encode_board(item.afterstate, item.learner)
                                for item in batch
                            ],
                            dtype=torch.float32,
                        )
                        started = time.perf_counter()
                        update = trainer.update_batch(features, target_batch.targets)
                        update_seconds += time.perf_counter() - started
                        update_records.append(
                            {
                                "update": update.update_number,
                                "loss": update.loss,
                                "gradient_norm": update.gradient_norm_before_clipping,
                                "target_updated": update.target_updated,
                                "transition_count": transition_count,
                            }
                        )
                        method["updates"] = len(update_records)
                        method["update_records"] = update_records
                        _atomic_json(result_path, method)

                simulator_start = time.perf_counter()
                method_probe_start = table.probes
                method_probe_seconds_start = table.probe_seconds
                try:
                    interaction = run_interaction(
                        [str(row["fen"]) for row in ordered_rows],
                        args.decisions,
                        online_predictor,
                        table,
                        make_rng(PILOT_SEED, "starts"),
                        make_rng(PILOT_SEED, "exploration"),
                        make_rng(PILOT_SEED, "opponent"),
                        chess.WHITE,
                        0.1,
                        0.5,
                        on_transition,
                    )
                finally:
                    simulator_seconds = time.perf_counter() - simulator_start
                    method.update(
                        {
                            "partial_transitions": transition_count,
                            "partial_updates": len(update_records),
                            "partial_target_building_seconds": target_seconds,
                            "partial_optimizer_seconds": update_seconds,
                            "partial_online_forward_boards": (
                                online_predictor.boards_evaluated
                            ),
                            "partial_target_forward_boards": (
                                target_predictor.boards_evaluated
                            ),
                            "partial_target_forward_leaves": target_leaves,
                            "interaction_tablebase_probe_calls": (
                                table.probes - method_probe_start
                            ),
                            "interaction_tablebase_probe_seconds": (
                                table.probe_seconds - method_probe_seconds_start
                            ),
                            "elapsed_seconds": time.perf_counter()
                            - active_method_start,
                        }
                    )
                method_seconds = time.perf_counter() - method_start
                changed = any(
                    not torch.equal(before, after)
                    for before, after in zip(
                        online_before, trainer.online.parameters(), strict=True
                    )
                )
                if trainer.updates and not changed:
                    raise RuntimeError(
                        "optimizer updates did not change online parameters"
                    )
                if any(
                    parameter.grad is not None
                    for parameter in trainer.target.parameters()
                ):
                    raise RuntimeError("frozen target accumulated gradients")
                checkpoint_hash = _save_checkpoint(
                    torch, trainer.online, output / f"beta-{beta:.1f}-checkpoint.pt"
                )
                method.update(
                    {
                        "status": "complete",
                        "decisions": interaction.decisions,
                        "transitions": interaction.transitions,
                        "unrecorded_decisions": interaction.unrecorded_decisions,
                        "episodes": [
                            {
                                "start_fen": episode.start_fen,
                                "learner": "white" if episode.learner else "black",
                                "reward": episode.reward,
                                "truncated": episode.truncated,
                                "truncation_reason": episode.truncation_reason,
                                "plies": episode.plies,
                                "learner_decisions": episode.learner_decisions,
                                "recorded_transitions": episode.recorded_transitions,
                            }
                            for episode in interaction.episodes
                        ],
                        "encountered_keys": list(interaction.encountered_keys),
                        "truncated_episodes": interaction.truncated_episodes,
                        "interaction_predictor_calls": interaction.predictor_calls,
                        "interaction_forward_evaluations": (
                            interaction.forward_evaluations
                        ),
                        "opponent_opportunities": interaction.opponent_opportunities,
                        "opponent_worsenings": interaction.opponent_worsenings,
                        "opponent_category_loss": interaction.opponent_category_loss,
                        "learner_wins": interaction.learner_wins,
                        "learner_draws": interaction.learner_draws,
                        "learner_losses": interaction.learner_losses,
                        "online_forward_boards": online_predictor.boards_evaluated,
                        "target_forward_boards": target_predictor.boards_evaluated,
                        "target_forward_leaves": target_leaves,
                        "interaction_tablebase_probe_calls": table.probes
                        - method_probe_start,
                        "interaction_tablebase_probe_seconds": table.probe_seconds
                        - method_probe_seconds_start,
                        "updates": trainer.updates,
                        "optimizer_forward_boards": (
                            trainer.updates * REPLAY_BATCH_SIZE
                        ),
                        "update_records": update_records,
                        "simulator_and_online_inference_seconds": max(
                            0.0, simulator_seconds - target_seconds - update_seconds
                        ),
                        "target_building_seconds": target_seconds,
                        "optimizer_seconds": update_seconds,
                        "method_training_seconds": method_seconds,
                        "elapsed_seconds": time.perf_counter() - method_start,
                        "decisions_per_second": (
                            interaction.decisions / method_seconds
                            if method_seconds > 0
                            else None
                        ),
                        "updates_per_second": (
                            trainer.updates / method_seconds
                            if method_seconds > 0
                            else None
                        ),
                        "memory_sample": _peak_memory(),
                        "final_checkpoint_sha256": checkpoint_hash,
                        "parameters_changed": changed,
                    }
                )
                method.pop("error", None)
                _atomic_json(result_path, method)
                _atomic_json(output / "pilot.json", manifest)
                active_method = None
                active_result_path = None
                active_method_start = None

            manifest.update(
                {
                    "status": "complete",
                    "completed_at_utc": _utc_now(),
                    "methods": method_results,
                    "model_loading_seconds": model_loading_seconds,
                    "neural_import_seconds": neural_import_seconds,
                    "pilot_elapsed_seconds": time.perf_counter() - overall_start,
                    "peak_memory": _peak_memory(),
                }
            )
            _atomic_json(output / "pilot.json", manifest)
            return manifest
        finally:
            table.close()
    except KeyboardInterrupt:
        if (
            active_method is not None
            and active_result_path is not None
            and active_method_start is not None
        ):
            _record_method_failure(
                active_method,
                active_result_path,
                status="interrupted",
                error="KeyboardInterrupt",
                elapsed_seconds=time.perf_counter() - active_method_start,
            )
        manifest.update(
            {
                "status": "interrupted",
                "completed_at_utc": _utc_now(),
                "error": "KeyboardInterrupt",
                "peak_memory": _peak_memory(),
                "pilot_elapsed_seconds": time.perf_counter() - overall_start,
            }
        )
        _atomic_json(output / "pilot.json", manifest)
        raise
    except Exception as exc:
        if (
            active_method is not None
            and active_result_path is not None
            and active_method_start is not None
        ):
            _record_method_failure(
                active_method,
                active_result_path,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                elapsed_seconds=time.perf_counter() - active_method_start,
            )
        manifest.update(
            {
                "status": "failed",
                "completed_at_utc": _utc_now(),
                "error": f"{type(exc).__name__}: {exc}",
                "peak_memory": _peak_memory(),
                "pilot_elapsed_seconds": time.perf_counter() - overall_start,
            }
        )
        _atomic_json(output / "pilot.json", manifest)
        raise
    finally:
        if tracemalloc.is_tracing():
            tracemalloc.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-dir", required=True, type=Path)
    parser.add_argument("--tablebase-dir", required=True, type=Path)
    parser.add_argument("--acquisition-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--decisions", type=int, default=512)
    parser.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()
    try:
        run_pilot(args)
    except Exception as exc:
        parser.exit(1, f"pilot failed: {exc}\n")


if __name__ == "__main__":
    main()
