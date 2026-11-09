"""Bounded, development-only runtime calibration for endgame neural baselines."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import random
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import chess
import chess.syzygy

from chesslab.endgames import evaluation
from chesslab.endgames.encoding import encode_board
from chesslab.endgames.identity import make_rng
from chesslab.endgames.interaction import select_learner_move
from chesslab.endgames.reference import evaluate as evaluate_reference

BETAS = (0.0, 0.5, 1.0)
P_VALUES = (0.0, 0.25, 0.5)
CALIBRATION_SEED = 1401
MAX_SECONDS = 3600
MAX_SAMPLES = 100
TRAINING_COUNT = 20000
VALIDATION_COUNT = 2500
PRETRAIN_MAX_EPOCHS = 30
PRETRAIN_PATIENCE = 31


def _pilot_module() -> Any:
    path = Path(__file__).with_name("run_endgame_pilot.py")
    spec = importlib.util.spec_from_file_location("run_endgame_pilot", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pilot helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _deadline(start: float, seconds: float) -> Callable[[], bool]:
    return lambda: time.perf_counter() - start >= seconds


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _persist_or_attach(
    path: Path, value: dict[str, Any], active: BaseException | None
) -> None:
    """Persist a manifest, preserving an active failure and exposing its snapshot.

    If persistence fails, ``partial_manifest`` exposes the latest in-memory state.
    An active original exception also receives the secondary ``persistence_error``.
    """
    try:
        _atomic_json(path, value)
    except BaseException as persistence_error:
        value.setdefault("persistence_errors", []).append(
            f"{type(persistence_error).__name__}: {persistence_error}"
        )
        if active is not None:
            setattr(active, "partial_manifest", value)
            setattr(active, "persistence_error", persistence_error)
            active.add_note(f"manifest persistence failed: {persistence_error}")
            return
        if value.get("status") in {"running", "complete"}:
            value["status"] = "failed"
        setattr(persistence_error, "partial_manifest", value)
        raise


def _models(
    pilot_dir: Path, torch: Any, neural: Any, manifest: dict[str, Any]
) -> list[tuple[str, Any]]:
    expected = manifest.get("pretraining", {})
    entries = [
        (
            "pretrained",
            "pretrained-checkpoint.pt",
            expected.get("pretrained_checkpoint_sha256"),
        )
    ]
    for beta in BETAS:
        name = f"beta-{beta:.1f}"
        entries.append(
            (
                name,
                f"{name}-checkpoint.pt",
                next(
                    (
                        m.get("final_checkpoint_sha256")
                        for m in manifest.get("methods", [])
                        if m.get("beta") == beta
                    ),
                    None,
                ),
            )
        )
    loaded = []
    for name, filename, digest in entries:
        path = pilot_dir / filename
        if not isinstance(digest, str) or _sha256(path.read_bytes()) != digest:
            raise ValueError(f"checkpoint hash mismatch for {filename}")
        model = neural.ValueNetwork(root_seed=9001)
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        model.eval()
        loaded.append((name, model))
    return loaded


class _TimedPredictor:
    """Time attempted predictor work, retaining totals across local resets."""

    def __init__(self, predictor: Any, totals: dict[str, Any] | None = None) -> None:
        self.predictor = predictor
        self.calls = 0
        self.boards = 0
        self.seconds = 0.0
        self.failures = 0
        self.totals = (
            totals
            if totals is not None
            else {"calls": 0, "boards": 0, "seconds": 0.0, "failures": 0}
        )

    def __call__(self, boards: Any, learner: chess.Color) -> Any:
        self.calls += 1
        self.boards += len(boards)
        self.totals["calls"] += 1
        self.totals["boards"] += len(boards)
        started = time.perf_counter()
        try:
            return self.predictor(boards, learner)
        except BaseException:
            self.failures += 1
            self.totals["failures"] += 1
            raise
        finally:
            elapsed = time.perf_counter() - started
            self.seconds += elapsed
            self.totals["seconds"] += elapsed


class _TimedTablebase:
    """Measure attempted WDL/DTZ probes while preserving tablebase behavior."""

    def __init__(self, table: Any) -> None:
        self.table = table
        self.probes = {"probe_wdl": 0, "probe_dtz": 0}
        self.seconds = {"probe_wdl": 0.0, "probe_dtz": 0.0}
        self.failures = {"probe_wdl": 0, "probe_dtz": 0}
        self.errors: dict[str, list[str]] = {"probe_wdl": [], "probe_dtz": []}

    def _probe(self, name: str, *args: Any, **kwargs: Any) -> Any:
        self.probes[name] += 1
        started = time.perf_counter()
        try:
            return getattr(self.table, name)(*args, **kwargs)
        except BaseException as exc:
            self.failures[name] += 1
            self.errors[name].append(f"{type(exc).__name__}: {exc}")
            raise
        finally:
            self.seconds[name] += time.perf_counter() - started

    def probe_wdl(self, *args: Any, **kwargs: Any) -> Any:
        return self._probe("probe_wdl", *args, **kwargs)

    def probe_dtz(self, *args: Any, **kwargs: Any) -> Any:
        return self._probe("probe_dtz", *args, **kwargs)


def _game_progress(snapshot: Any) -> dict[str, Any]:
    return {
        "start_fen": snapshot.start_fen,
        "learner": snapshot.learner,
        "p": snapshot.p,
        "plies": snapshot.plies,
        "moves": list(snapshot.moves),
        "reward": snapshot.reward,
        "truncated": snapshot.truncated,
        "truncation_reason": snapshot.truncation_reason,
        "failure": snapshot.failure,
        "learner_decisions": snapshot.learner_decisions,
        "reference_evaluated_decisions": snapshot.reference_evaluated_decisions,
        "predictor_calls": snapshot.predictor_calls,
        "forward_evaluations": snapshot.forward_evaluations,
        "learner_reference_errors": snapshot.learner_reference_errors,
        "reference_failures": snapshot.reference_failures,
        "neural_work": snapshot.neural_work,
        "encountered_keys": list(snapshot.encountered_keys),
        "choice_records": [asdict(choice) for choice in snapshot.choice_records],
    }


def _record_game(path: Path, record: dict[str, Any], snapshot: Any) -> None:
    record["progress"] = _game_progress(snapshot)
    _atomic_json(path, record)


def _finalize(
    path: Path, value: dict[str, Any], table: Any, original: BaseException | None
) -> None:
    """Keep the first work error authoritative through cleanup and final writes."""
    cleanup_error = None
    try:
        if table is not None:
            table.close()
    except BaseException as exc:
        cleanup_error = exc
        value["cleanup_error"] = f"{type(exc).__name__}: {exc}"
        if value["status"] in {"running", "complete"}:
            value["status"] = (
                "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
            )
        if original is not None:
            setattr(original, "cleanup_error", exc)
            original.add_note(f"table cleanup failed: {exc}")
    preferred = original if original is not None else cleanup_error
    before = len(value.get("persistence_errors", []))
    _persist_or_attach(path, value, preferred)
    if cleanup_error is not None or len(value.get("persistence_errors", [])) > before:
        assert preferred is not None
        setattr(preferred, "partial_manifest", value)
        raise preferred


def _provenance(root: Path, output_dir: Path) -> dict[str, Any]:
    source_names = (
        "scripts/run_endgame_pilot.py",
        "scripts/run_endgame_calibration.py",
        "src/chesslab/endgames/evaluation.py",
        "src/chesslab/endgames/interaction.py",
        "src/chesslab/endgames/opponent.py",
        "src/chesslab/endgames/neural.py",
        "src/chesslab/endgames/encoding.py",
        "src/chesslab/endgames/identity.py",
        "src/chesslab/endgames/rules.py",
        "src/chesslab/endgames/reference.py",
        "src/chesslab/endgames/targets.py",
        "src/chesslab/endgames/dataset.py",
    )
    hashes: dict[str, str] = {}
    for name in source_names:
        data = (root / name).read_bytes()
        destination = output_dir / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        hashes[name] = _sha256(data)
    git: dict[str, str] = {}
    for key, command in (
        ("head", ["rev-parse", "HEAD"]),
        ("status", ["status", "--porcelain"]),
        ("diff_sha256", ["diff", "--binary"]),
    ):
        try:
            value = subprocess.run(
                ["git", *command], cwd=root, check=True, capture_output=True, text=True
            ).stdout
            git[key] = (
                _sha256(value.encode()) if key == "diff_sha256" else value.strip()
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            git[key] = f"unavailable: {exc}"
    packages: dict[str, str | None] = {}
    for package in ("python-chess", "torch", "numpy"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    return {
        "source_sha256": hashes,
        "git": git,
        "packages": packages,
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
    }


def _configure_torch(torch: Any) -> dict[str, int]:
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        # PyTorch freezes interop configuration after parallel work starts.
        if torch.get_num_interop_threads() != 1:
            raise RuntimeError("cannot set PyTorch interop threads to 1")
    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
        raise RuntimeError("PyTorch thread configuration did not take effect")
    torch.use_deterministic_algorithms(True)
    return {
        "torch_intraop": torch.get_num_threads(),
        "torch_interop": torch.get_num_interop_threads(),
    }


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    deadline = _deadline(started, args.deadline_seconds)
    output: dict[str, Any] = {"mode": "evaluation", "status": "running", "items": []}
    out_path = args.output_dir / "calibration.json"
    table = None
    original_table = None
    table_work = None
    predictor_totals: dict[str, dict[str, Any]] = {}
    original_error: BaseException | None = None
    try:
        _persist_or_attach(out_path, output, None)
        pilot = _pilot_module()
        pilot_path = args.pilot_dir / "pilot.json"
        pilot_manifest = json.loads(pilot_path.read_text(encoding="utf-8"))
        if pilot_manifest.get("status") != "complete":
            raise ValueError("pilot manifest is not complete")
        rows, data_hash = pilot._load_development(args.development_dir)
        dev = pilot_manifest.get("development", {})
        if (
            dev.get("jsonl_sha256") != data_hash
            or dev.get("verified_seed") != pilot.DEV_SEED
        ):
            raise ValueError(
                "development data does not match the verified pilot partition"
            )
        import torch  # type: ignore[import-not-found]

        from chesslab.endgames.neural import BatchPredictor

        output["threads"] = _configure_torch(torch)
        models = _models(
            args.pilot_dir,
            torch,
            __import__("chesslab.endgames.neural", fromlist=["ValueNetwork"]),
            pilot_manifest,
        )
        if deadline():
            raise TimeoutError(
                "calibration deadline exceeded while loading checkpoints"
            )
        provenance = _provenance(Path(__file__).resolve().parents[1], args.output_dir)
        acquisition = pilot.verify_acquisition_manifest(
            args.acquisition_manifest, args.tablebase_dir
        )
        acquisition_hash = _sha256(args.acquisition_manifest.read_bytes())
        if pilot_manifest.get(
            "acquisition_manifest_sha256"
        ) != acquisition_hash or pilot_manifest.get("table_hashes") != acquisition.get(
            "table_sha256"
        ):
            raise ValueError(
                "tablebase acquisition provenance does not match the pilot"
            )
        original_table = chess.syzygy.open_tablebase(str(args.tablebase_dir))
        table_work = _TimedTablebase(original_table)
        table = table_work
        selected_rows = rows[: args.samples]
        boards = [chess.Board(str(row["fen"])) for row in selected_rows]
        output.update(
            {
                "mode": "evaluation",
                "status": "running",
                "data_sha256": data_hash,
                "pilot_manifest_sha256": _sha256(pilot_path.read_bytes()),
                "seed": CALIBRATION_SEED,
                "sample_count": len(boards),
                "items": [],
                "cost_accounting": (
                    "Predictor and tablebase times are nested within caller wall time; "
                    "do not add them."
                ),
                "started_at": time.time(),
                "provenance": provenance,
                "acquisition_manifest_sha256": acquisition_hash,
                "table_hashes": acquisition.get("table_sha256"),
            }
        )
        _atomic_json(out_path, output)
        predictor_totals = {
            name: {"calls": 0, "boards": 0, "seconds": 0.0, "failures": 0}
            for name, _ in models
        }
        predictors = {
            name: _TimedPredictor(BatchPredictor(model), predictor_totals[name])
            for name, model in models
        }
        output["latency"] = {}
        output["latency_attempts"] = {name: [] for name, _ in models}
        latency_samples_by_model: dict[str, list[float]] = {
            name: [] for name, _ in models
        }
        latency_inputs = boards[:30]

        def persist_attempted_work() -> None:
            output["attempted_work"] = {
                "predictors": predictor_totals,
                "tablebase": {
                    "probes": table_work.probes,
                    "seconds": table_work.seconds,
                    "failures": table_work.failures,
                    "errors": table_work.errors,
                },
                "cost_accounting": (
                    "Nested operation times; do not add to elapsed_seconds."
                ),
            }
            _persist_or_attach(out_path, output, sys.exception())

        def record_latency(
            name: str, phase: str, board: Any, seed: int, pass_index: int, index: int
        ) -> None:
            attempt: dict[str, Any] = {
                "phase": phase,
                "status": "attempted",
                "fen": board.fen(),
                "pass_index": pass_index,
                "index": index,
                "seconds": None,
            }
            output["latency_attempts"][name].append(attempt)
            started_attempt = time.perf_counter()
            try:
                select_learner_move(
                    board,
                    board.turn,
                    predictors[name],
                    random.Random(seed),
                    0.0,
                )
            except BaseException as exc:
                attempt["status"] = (
                    "interrupted"
                    if isinstance(exc, KeyboardInterrupt)
                    else "deadline"
                    if isinstance(exc, TimeoutError)
                    else "failed"
                )
                attempt["error"] = f"{type(exc).__name__}: {exc}"
                raise
            else:
                attempt["status"] = "complete"
            finally:
                attempt["seconds"] = time.perf_counter() - started_attempt
                if phase == "sample" and attempt["status"] == "complete":
                    latency_samples_by_model[name].append(attempt["seconds"])
                output["latency"][name] = {
                    "warmup_count": sum(
                        a["phase"] == "warmup" and a["status"] == "complete"
                        for a in output["latency_attempts"][name]
                    ),
                    "sample_count": len(latency_samples_by_model[name]),
                    "seconds": list(latency_samples_by_model[name]),
                    "mean_seconds": (
                        sum(latency_samples_by_model[name])
                        / len(latency_samples_by_model[name])
                        if latency_samples_by_model[name]
                        else None
                    ),
                    "predictor_calls": predictors[name].calls,
                    "predictor_seconds": predictors[name].seconds,
                    "predictor_failures": predictors[name].failures,
                }
                persist_attempted_work()

        for name, _ in models:
            for warmup_index, board in enumerate(latency_inputs[:10]):
                if deadline():
                    raise TimeoutError("calibration deadline exceeded during warmup")
                record_latency(name, "warmup", board, 0, -1, warmup_index)
        for pass_index in range(3):
            ordered = [
                models[(offset + pass_index) % len(models)][0]
                for offset in range(len(models))
            ]
            for name in ordered:
                for index, board in enumerate(latency_inputs):
                    if deadline():
                        raise TimeoutError(
                            "calibration deadline exceeded during latency samples"
                        )
                    record_latency(
                        name,
                        "sample",
                        board,
                        pass_index * 30 + index,
                        pass_index,
                        index,
                    )
        for name, _ in models:
            samples = latency_samples_by_model[name]
            output["latency"][name] = {
                "warmup_count": sum(
                    a["phase"] == "warmup" and a["status"] == "complete"
                    for a in output["latency_attempts"][name]
                ),
                "sample_count": len(samples),
                "seconds": samples,
                "mean_seconds": sum(samples) / len(samples) if samples else None,
                "predictor_calls": predictors[name].calls,
                "predictor_seconds": predictors[name].seconds,
                "predictor_failures": predictors[name].failures,
            }
            predictors[name].calls = predictors[name].boards = predictors[
                name
            ].failures = 0
            predictors[name].seconds = 0.0
        failed_games = False
        for name, model in models:
            if deadline():
                raise TimeoutError("calibration deadline exceeded")
            predictor = predictors[name]
            predictor.calls = predictor.boards = predictor.failures = 0
            predictor.seconds = 0.0
            for index, board in enumerate(boards):
                if deadline():
                    raise TimeoutError("calibration deadline exceeded")
                item = {
                    "model": name,
                    "index": index,
                    "fen": board.fen(),
                    "prediction_status": "not_started",
                    "choice_status": "not_started",
                    "prediction_seconds": None,
                    "choice_seconds": None,
                }
                output["items"].append(item)
                for phase in ("prediction", "choice"):
                    if phase == "choice" and deadline():
                        raise TimeoutError(
                            "calibration deadline exceeded before choice"
                        )
                    item[f"{phase}_status"] = "attempted"
                    phase_started = time.perf_counter()
                    try:
                        if phase == "prediction":
                            prediction = evaluation.evaluate_predictions(
                                [board], predictor, table
                            )
                            item["prediction_mse"] = prediction.mse
                        else:
                            choice = evaluation.evaluate_choices(
                                [board], predictor, table
                            )
                            item["choice_loss_rate"] = choice.loss_rate
                        item[f"{phase}_status"] = "complete"
                    except BaseException as exc:
                        item[f"{phase}_status"] = (
                            "interrupted"
                            if isinstance(exc, KeyboardInterrupt)
                            else "deadline"
                            if isinstance(exc, TimeoutError)
                            else "failed"
                        )
                        item[f"{phase}_error"] = f"{type(exc).__name__}: {exc}"
                        raise
                    finally:
                        item[f"{phase}_seconds"] = time.perf_counter() - phase_started
                        persist_attempted_work()
            output.setdefault("static", {})[name] = {
                "prediction_seconds": sum(
                    i["prediction_seconds"]
                    for i in output["items"]
                    if i["model"] == name
                ),
                "choice_seconds": sum(
                    i["choice_seconds"] for i in output["items"] if i["model"] == name
                ),
                "predictor_calls": predictor.calls,
                "predictor_boards": predictor.boards,
                "predictor_seconds": predictor.seconds,
                "predictor_failures": predictor.failures,
            }
            _atomic_json(out_path, output)
            # SHA-derived fixed starts are shared across methods and p values.
            starts = sorted(
                rows,
                key=lambda row: hashlib.sha256(
                    f"calibration-v1|{row['canonical_position']}".encode()
                ).digest(),
            )[:10]
            for p_value in P_VALUES:
                for start_index, row in enumerate(starts):
                    color = chess.WHITE if start_index % 2 == 0 else chess.BLACK
                    if deadline():
                        raise TimeoutError("calibration deadline exceeded")
                    record = {
                        "model": name,
                        "p": p_value,
                        "start_index": start_index,
                        "start_fen": str(row["fen"]),
                        "learner": "white" if color else "black",
                        "status": "running",
                    }
                    path = (
                        args.output_dir
                        / "games"
                        / f"{name}-p{p_value:.2f}-s{start_index:02d}.json"
                    )
                    output["active_game"] = record

                    def persist_progress(game_snapshot: Any) -> None:
                        active = sys.exception()
                        # _record_game installs the complete snapshot before I/O.
                        try:
                            _record_game(path, record, game_snapshot)
                        except BaseException as write_error:
                            output.setdefault("persistence_errors", []).append(
                                f"{type(write_error).__name__}: {write_error}"
                            )
                            preferred = active if active is not None else write_error
                            setattr(preferred, "partial_manifest", output)
                            if active is not None:
                                setattr(active, "persistence_error", write_error)
                                active.add_note(
                                    f"game persistence failed: {write_error}"
                                )
                            raise preferred

                    try:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        _atomic_json(path, record)
                        snap = evaluation.play_fixed_game(
                            chess.Board(str(row["fen"])),
                            color,
                            predictor,
                            table,
                            make_rng(
                                CALIBRATION_SEED, f"explore|{p_value}|{start_index}"
                            ),
                            make_rng(
                                CALIBRATION_SEED, f"opponent|{p_value}|{start_index}"
                            ),
                            p_value,
                            deadline_check=deadline,
                            progress_callback=persist_progress,
                        )
                        record["status"] = (
                            "failed"
                            if snap.failure
                            else (snap.truncation_reason or "completed")
                        )
                        failed_games |= (
                            snap.failure is not None
                            or snap.truncation_reason is not None
                        )
                        _record_game(path, record, snap)
                    except BaseException as exc:
                        record.update(
                            status="interrupted"
                            if isinstance(exc, KeyboardInterrupt)
                            else "failed",
                            error=f"{type(exc).__name__}: {exc}",
                        )
                        setattr(exc, "partial_manifest", output)
                        raise
                _atomic_json(out_path, output)
        output["status"] = "failed" if failed_games else "complete"
    except KeyboardInterrupt as exc:
        original_error = exc
        output["status"] = "interrupted"
        raise
    except TimeoutError as exc:
        original_error = exc
        output["status"] = "deadline"
        output["error"] = str(exc)
    except BaseException as exc:
        original_error = exc
        output["status"] = "failed"
        output["error"] = f"{type(exc).__name__}: {exc}"
        setattr(exc, "partial_manifest", output)
        raise
    finally:
        output["elapsed_seconds"] = time.perf_counter() - started
        output["attempted_work"] = {
            "predictors": predictor_totals,
            "tablebase": (
                {
                    "probes": table_work.probes,
                    "seconds": table_work.seconds,
                    "failures": table_work.failures,
                    "errors": table_work.errors,
                }
                if table_work is not None
                else {"probes": {}, "seconds": {}, "failures": {}}
            ),
            "cost_accounting": "Nested operation times; do not add to elapsed_seconds.",
        }
        _finalize(out_path, output, original_table, original_error)
    return output


def run_pretraining(args: argparse.Namespace) -> dict[str, Any]:
    """Time fitting on development data without changing scientific patience."""
    started = time.perf_counter()
    deadline = _deadline(started, args.deadline_seconds)
    result: dict[str, Any] = {"mode": "pretraining", "status": "running", "scales": []}
    out_path = args.output_dir / "calibration.json"
    table = None
    original_table = None
    table_work = None
    original_error: BaseException | None = None
    try:
        _persist_or_attach(out_path, result, None)
        pilot = _pilot_module()
        rows, data_hash = pilot._load_development(args.development_dir)
        pilot_manifest = json.loads(
            (args.pilot_dir / "pilot.json").read_text(encoding="utf-8")
        )
        dev = pilot_manifest.get("development", {})
        if (
            dev.get("jsonl_sha256") != data_hash
            or dev.get("verified_seed") != pilot.DEV_SEED
        ):
            raise ValueError(
                "development data does not match the verified pilot partition"
            )
        import torch

        from chesslab.endgames.neural import PretrainingConfig, ValueNetwork, pretrain

        acquisition = pilot.verify_acquisition_manifest(
            args.acquisition_manifest, args.tablebase_dir
        )
        acquisition_hash = _sha256(args.acquisition_manifest.read_bytes())
        if pilot_manifest.get(
            "acquisition_manifest_sha256"
        ) != acquisition_hash or pilot_manifest.get("table_hashes") != acquisition.get(
            "table_sha256"
        ):
            raise ValueError(
                "tablebase acquisition provenance does not match the pilot"
            )
        original_table = chess.syzygy.open_tablebase(str(args.tablebase_dir))
        table_work = _TimedTablebase(original_table)
        table = table_work
        result.update(
            {
                "data_sha256": data_hash,
                "seed": CALIBRATION_SEED,
                "training_count": TRAINING_COUNT,
                "validation_count": VALIDATION_COUNT,
                "acquisition_manifest_sha256": acquisition_hash,
                "table_hashes": acquisition.get("table_sha256"),
                "provenance": _provenance(
                    Path(__file__).resolve().parents[1], args.output_dir
                ),
                "started_at": time.time(),
            }
        )
        boards = [chess.Board(str(row["fen"])) for row in rows]
        labels = []
        for board in boards:
            if deadline():
                raise TimeoutError("calibration deadline exceeded while labeling")
            labels.append(-float(evaluate_reference(board, table).value))
        training = list(zip(boards[:1600], labels[:1600], strict=True))
        validation = list(zip(boards[1600:], labels[1600:], strict=True))
        result["threads"] = _configure_torch(torch)
        train_count, validation_count = TRAINING_COUNT, VALIDATION_COUNT
        if deadline():
            raise TimeoutError("calibration deadline exceeded")
        train_pairs = [training[i % len(training)] for i in range(train_count)]
        validation_pairs = [
            validation[i % len(validation)] for i in range(validation_count)
        ]
        t = time.perf_counter()
        train_x = [encode_board(board, not board.turn) for board, _ in train_pairs]
        validation_x = [
            encode_board(board, not board.turn) for board, _ in validation_pairs
        ]
        encoding_seconds = time.perf_counter() - t
        train_y = [label for _, label in train_pairs]
        validation_y = [label for _, label in validation_pairs]
        model = ValueNetwork(root_seed=CALIBRATION_SEED)
        epochs: list[int] = []

        def progress(record: Any) -> None:
            epochs.append(record.epoch)
            result["current"] = {
                "training_count": train_count,
                "validation_count": validation_count,
                "completed_epochs": list(epochs),
            }
            _atomic_json(out_path, result)

        t = time.perf_counter()
        training_result = pretrain(
            model,
            train_x,
            train_y,
            validation_x,
            validation_y,
            seed=CALIBRATION_SEED,
            config=PretrainingConfig(
                max_epochs=PRETRAIN_MAX_EPOCHS, patience=PRETRAIN_PATIENCE
            ),
            deadline_check=deadline,
            progress_callback=progress,
        )
        training_seconds = time.perf_counter() - t
        result["scales"].append(
            {
                "training_count": train_count,
                "validation_count": validation_count,
                "encoding_seconds": encoding_seconds,
                "training_seconds": training_seconds,
                "epochs": len(training_result.epochs),
                "status": "completed",
            }
        )
        _atomic_json(out_path, result)
        result["status"] = "complete"
    except TimeoutError as exc:
        original_error = exc
        result["status"] = "deadline"
        result["error"] = str(exc)
    except KeyboardInterrupt as exc:
        original_error = exc
        result["status"] = "interrupted"
        raise
    except BaseException as exc:
        original_error = exc
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        result["elapsed_seconds"] = time.perf_counter() - started
        result["attempted_work"] = {
            "tablebase": (
                {
                    "probes": table_work.probes,
                    "seconds": table_work.seconds,
                    "failures": table_work.failures,
                    "errors": table_work.errors,
                }
                if table_work is not None
                else {"probes": {}, "seconds": {}, "failures": {}}
            ),
            "cost_accounting": "Nested operation times; do not add to elapsed_seconds.",
        }
        _finalize(out_path, result, original_table, original_error)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("evaluation", "pretraining"))
    parser.add_argument("--development-dir", type=Path, required=True)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--deadline-seconds", type=float, default=1800)
    args = parser.parse_args()
    if (
        not 1 <= args.samples <= MAX_SAMPLES
        or not 1 <= args.deadline_seconds <= MAX_SECONDS
    ):
        parser.error(
            f"samples must be 1..{MAX_SAMPLES} and deadline 1..{MAX_SECONDS} seconds"
        )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    try:
        result = (run_evaluation if args.mode == "evaluation" else run_pretraining)(
            args
        )
        if result.get("status") in {"failed", "deadline", "interrupted"}:
            parser.exit(
                1, f"calibration {result['status']}: {result.get('error', '')}\n"
            )
    except Exception as exc:
        parser.exit(1, f"calibration failed: {exc}\n")


if __name__ == "__main__":
    main()
