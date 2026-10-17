"""Bounded grouped rollout data and UCI labels for the first learned evaluator."""

import argparse
import asyncio
import json
import random
import shutil
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import cast

import chess
import chess.engine

from chesslab.agents.external_uci import ExternalUciAgent, UciConfig, file_sha256
from chesslab.config import json_object, reject_unknown_fields
from chesslab.engine.evaluation.linear import FEATURE_SCHEMA, board_features
from chesslab.engine.evaluation.material import PIECE_VALUES, material_score
from chesslab.eval.artifacts import (
    capture_run_metadata,
    configuration_digest,
    write_artifact_json,
)
from chesslab.games.chess import ChessState

SPLITS = ("train", "validation", "test")


def position_identity(board: chess.Board) -> str:
    """Treat colour mirrors as one identity; exclude counters and prior history."""
    return min(
        " ".join(b.fen(en_passant="legal").split()[:4]) for b in (board, board.mirror())
    )


def rollout(seed: int, max_plies: int) -> list[chess.Move]:
    """Seeded epsilon-greedy material policy; no teacher or evaluator tuning."""
    rng = random.Random(seed)
    board = chess.Board()
    moves = []
    for _ in range(max_plies):
        if board.is_game_over(claim_draw=False):
            break
        legal = list(board.legal_moves)
        if rng.random() < 0.5:
            move = rng.choice(legal)
        else:
            values = []
            perspective = board.turn
            for action in legal:
                board.push(action)
                outcome = board.outcome(claim_draw=False)
                if outcome is not None:
                    value = (
                        0
                        if outcome.winner is None
                        else (
                            1_000_000 if outcome.winner == perspective else -1_000_000
                        )
                    )
                else:
                    value = sum(
                        PIECE_VALUES[p.piece_type]
                        * (1 if p.color == perspective else -1)
                        for p in board.piece_map().values()
                    )
                values.append(value)
                board.pop()
            best = max(values)
            move = rng.choice(
                [m for m, v in zip(legal, values, strict=True) if v == best]
            )
        board.push(move)
        moves.append(move)
    return moves


@dataclass(frozen=True, slots=True)
class PilotConfig:
    seed: int
    groups: tuple[int, int, int]
    sample_plies: tuple[int, ...]
    max_plies: int
    max_attempts: int
    label_nodes: int
    clip_cp: int
    max_label_seconds: int
    teacher: UciConfig
    exclusions: tuple[tuple[str, str], ...]
    lambdas: tuple[float, ...]

    @classmethod
    def from_dict(cls, value: object) -> "PilotConfig":
        data = json_object(value, "pilot")
        reject_unknown_fields(
            data,
            {
                "schema_version",
                "seed",
                "groups",
                "sample_plies",
                "max_plies",
                "max_attempts",
                "label_nodes",
                "clip_cp",
                "max_label_seconds",
                "teacher",
                "exclusions",
                "lambdas",
            },
            "pilot",
        )
        if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            raise ValueError("schema_version must be 1")
        fields = {}
        for name in (
            "seed",
            "max_plies",
            "max_attempts",
            "label_nodes",
            "clip_cp",
            "max_label_seconds",
        ):
            value = data.get(name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
            fields[name] = value
        if fields["clip_cp"] > 10000:
            raise ValueError("clip_cp cannot exceed 10000")
        groups = json_object(data.get("groups"), "groups")
        if set(groups) != set(SPLITS) or any(
            type(n) is not int or n <= 0 for n in groups.values()
        ):
            raise ValueError("positive train/validation/test group counts required")
        counts = []
        for split in SPLITS:
            number = groups[split]
            assert isinstance(number, int)
            counts.append(number)
        plies = data.get("sample_plies")
        if (
            not isinstance(plies, list)
            or not plies
            or any(
                type(p) is not int or p <= 0 or p > fields["max_plies"] for p in plies
            )
        ):
            raise ValueError("valid positive sample_plies required")
        if plies != sorted(set(plies)) or fields["max_attempts"] < sum(counts):
            raise ValueError(
                "sample plies must be sorted/unique and attempts cover groups"
            )
        raw_exclusions = data.get("exclusions")
        if not isinstance(raw_exclusions, list):
            raise ValueError("exclusions must be an array")
        exclusions = []
        for entry in raw_exclusions:
            item = json_object(entry, "exclusion")
            reject_unknown_fields(item, {"path", "sha256"}, "exclusion")
            path, digest = item.get("path"), item.get("sha256")
            if (
                not isinstance(path, str)
                or not path
                or not isinstance(digest, str)
                or len(digest) != 64
            ):
                raise ValueError("exclusion requires path and SHA-256")
            exclusions.append((path, digest))
        lambdas = data.get("lambdas")
        if (
            not isinstance(lambdas, list)
            or not lambdas
            or any(
                type(a) not in (int, float) or not 0 < a < float("inf") for a in lambdas
            )
        ):
            raise ValueError("positive finite lambdas required")
        if len(set(lambdas)) != len(lambdas):
            raise ValueError("lambdas must be unique")
        return cls(
            fields["seed"],
            (counts[0], counts[1], counts[2]),
            tuple(plies),
            fields["max_plies"],
            fields["max_attempts"],
            fields["label_nodes"],
            fields["clip_cp"],
            fields["max_label_seconds"],
            UciConfig.from_dict(data.get("teacher")),
            tuple(exclusions),
            tuple(float(a) for a in lambdas),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "seed": self.seed,
            "groups": dict(zip(SPLITS, self.groups, strict=True)),
            "sample_plies": list(self.sample_plies),
            "max_plies": self.max_plies,
            "max_attempts": self.max_attempts,
            "label_nodes": self.label_nodes,
            "clip_cp": self.clip_cp,
            "max_label_seconds": self.max_label_seconds,
            "teacher": self.teacher.to_dict(),
            "lambdas": list(self.lambdas),
            "exclusions": [{"path": p, "sha256": h} for p, h in self.exclusions],
        }


def excluded_positions(config: PilotConfig) -> set[str]:
    """Read FEN identities only; historical labels are never learning targets."""
    keys = set()
    for filename, digest in config.exclusions:
        path = Path(filename)
        if file_sha256(path) != digest:
            raise ValueError("exclusion file SHA-256 mismatch")
        raw = json.loads(path.read_text())
        rows = raw if isinstance(raw, list) else raw["dataset"]["positions"]
        for row in rows:
            keys.add(position_identity(chess.Board(row["fen"])))
    return keys


def generate_positions(
    config: PilotConfig, excluded: set[str]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Assign source groups first, reject cross-split collisions before labelling."""
    rng = random.Random(config.seed)
    reserved: dict[str, str] = {}
    rows: list[dict[str, object]] = []
    trajectories: list[dict[str, object]] = []
    attempt = 0
    for split, count in zip(SPLITS, config.groups, strict=True):
        accepted = 0
        while accepted < count:
            if attempt >= config.max_attempts:
                raise ValueError(
                    "generation cap reached before group counts were filled"
                )
            seed = rng.getrandbits(128)
            moves = rollout(seed, config.max_plies)
            attempt += 1
            board = chess.Board()
            samples: list[tuple[int, str, str]] = []
            for ply, move in enumerate(moves, start=1):
                board.push(move)
                if ply in config.sample_plies and not board.is_game_over(
                    claim_draw=False
                ):
                    samples.append((ply, board.fen(), position_identity(board)))
            if len(samples) != len(config.sample_plies):
                continue
            if any(
                key in excluded or (key in reserved and reserved[key] != split)
                for _, _, key in samples
            ):
                continue
            if all(key in reserved for _, _, key in samples):
                continue
            group = f"{split}-{accepted:03d}"
            trajectories.append(
                {
                    "group": group,
                    "split": split,
                    "seed": seed,
                    "attempt": attempt,
                    "moves": [m.uci() for m in moves],
                }
            )
            for ply, fen, key in samples:
                if key not in reserved:
                    rows.append(
                        {
                            "group": group,
                            "split": split,
                            "seed": seed,
                            "ply": ply,
                            "fen": fen,
                            "identity": key,
                            "history": [m.uci() for m in moves[:ply]],
                        }
                    )
                reserved[key] = split
            accepted += 1
    return rows, trajectories


@dataclass(frozen=True, slots=True)
class TeacherLabel:
    white_cp: int | None
    white_mate: int | None
    target_cp: int
    nodes: int | None
    depth: int | None
    score_nodes: int | None = None
    final_depth: int | None = None
    final_bound: bool = False


def teacher_label(info: chess.engine.InfoDict, clip_cp: int) -> TeacherLabel:
    """Preserve raw score and map mates using python-chess's signed mate score."""
    if info.get("lowerbound") or info.get("upperbound"):
        raise ValueError(
            "teacher returned a score bound instead of an exact search score"
        )
    score = info.get("score")
    if score is None:
        raise ValueError("teacher returned no score")
    white = score.white()
    value = (
        (clip_cp if white > chess.engine.Cp(0) else -clip_cp)
        if white.is_mate()
        else white.score()
    )
    if value is None:
        raise ValueError("teacher score cannot be converted")
    return TeacherLabel(
        white.score(),
        white.mate(),
        max(-clip_cp, min(clip_cp, value)),
        info.get("nodes"),
        info.get("depth"),
    )


def analyse_label(
    agent: ExternalUciAgent, board: chess.Board, config: PilotConfig
) -> TeacherLabel:
    """Analyse with a hard response watchdog even for fixed-node labels."""
    engine = agent.engine
    if engine is None:
        raise RuntimeError("teacher must be prepared")

    async def analyse() -> tuple[chess.engine.InfoDict, chess.engine.InfoDict]:
        analysis = await engine.protocol.analysis(
            board,
            chess.engine.Limit(nodes=config.label_nodes),
            game=object(),
            info=chess.engine.INFO_SCORE | chess.engine.INFO_BASIC,
        )
        return await completed_score(analysis)

    info, final = asyncio.run_coroutine_threadsafe(
        asyncio.wait_for(analyse(), config.teacher.timeout_seconds),
        engine.protocol.loop,
    ).result()
    return replace(
        teacher_label(info, config.clip_cp),
        nodes=final.get("nodes"),
        score_nodes=info.get("nodes"),
        final_depth=final.get("depth"),
        final_bound=bool(final.get("lowerbound") or final.get("upperbound")),
    )


async def completed_score(
    analysis: chess.engine.AnalysisResult,
) -> tuple[chess.engine.InfoDict, chess.engine.InfoDict]:
    """Keep latest complete UCI score, rather than an unfinished iteration's bound."""
    latest: dict[str, object] = {}
    exact: dict[str, object] | None = None
    try:
        async for info in analysis:
            if "score" in info:
                for bound in ("lowerbound", "upperbound"):
                    latest.pop(bound, None)
            latest.update(info)
            if (
                "score" in info
                and not info.get("lowerbound")
                and not info.get("upperbound")
            ):
                exact = latest.copy()
        await analysis.wait()
    finally:
        analysis.stop()
    if exact is None:
        raise ValueError("teacher returned no completed unbounded score")
    return cast(chess.engine.InfoDict, exact), cast(chess.engine.InfoDict, latest)


def run_pilot(
    config: PilotConfig,
    output: Path,
    repository: Path,
    labeler: Callable[[chess.Board], TeacherLabel] | None = None,
) -> dict[str, object]:
    """Freeze splits before labels; persist failures without retry."""
    output.mkdir(parents=True, exist_ok=False)
    plan = config.to_dict()
    plan["feature_schema"] = FEATURE_SCHEMA
    plan["label_policy"] = "latest-completed-uci-score-v2"
    metadata = capture_run_metadata(
        repository, output.name, configuration_digest(plan), 0
    )
    write_artifact_json(output / "plan.json", plan)
    write_artifact_json(output / "metadata.json", metadata)
    teacher = ExternalUciAgent(config.teacher) if labeler is None else None
    exported: dict[str, list[dict[str, object]]] = {split: [] for split in SPLITS}
    try:
        source_hashes = {}
        paths = list((repository / "src").rglob("*.py")) + [
            repository / "uv.lock",
            repository / "pyproject.toml",
            repository / "docs/research/linear-evaluator-pilot-v1.md",
        ]
        for path in paths:
            relative = path.relative_to(repository)
            copy = output / "source" / relative
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, copy)
            source_hashes[relative.as_posix()] = file_sha256(copy)
        metadata["source_sha256"] = source_hashes
        rows, trajectories = generate_positions(config, excluded_positions(config))
        write_artifact_json(output / "positions.json", rows)
        write_artifact_json(output / "trajectories.json", trajectories)
        metadata.update(
            positions_sha256=file_sha256(output / "positions.json"),
            trajectories_sha256=file_sha256(output / "trajectories.json"),
            runs_planned=len(rows),
        )
        (output / "cases").mkdir()
        if teacher is not None:
            teacher.prepare()
        started = perf_counter()
        failures = 0
        for index, row in enumerate(rows):
            if perf_counter() - started >= config.max_label_seconds:
                raise TimeoutError("labelling invocation cap reached")
            metadata["active_case"] = index
            write_artifact_json(output / "metadata.json", metadata, replace=True)
            record = dict(row)
            before = perf_counter()
            try:
                board = chess.Board()
                history = row["history"]
                assert isinstance(history, list)
                for move in history:
                    assert isinstance(move, str)
                    board.push_uci(move)
                if board.fen() != row["fen"]:
                    raise ValueError("trajectory replay differs from frozen FEN")
                if labeler is not None:
                    label = labeler(board)
                else:
                    assert teacher is not None
                    label = analyse_label(teacher, board, config)
                record.update(asdict(label), error=None)
                state = ChessState.from_fen(board.fen())
                record["features"] = list(board_features(state))
                record["material_cp"] = material_score(state, 0)
                split = row["split"]
                assert isinstance(split, str)
                exported[split].append(record)
            except Exception as error:
                failures += 1
                record["error"] = f"{type(error).__name__}: {error}"
            record["elapsed_seconds"] = perf_counter() - before
            write_artifact_json(output / "cases" / f"{index:04d}.json", record)
            metadata["runs_written"] = index + 1
        metadata.update(
            status="failed" if failures else "completed",
            failed=failures,
            active_case=None,
        )
    except BaseException as error:
        metadata.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            error=f"{type(error).__name__}: {error}",
        )
        raise
    finally:
        if teacher is not None:
            teacher.close()
            metadata["teacher"] = teacher.metadata
            if teacher.metadata.get("cleanup_error"):
                metadata["status"] = "failed"
        split_hashes = {}
        for split, data in exported.items():
            path = output / f"{split}.json"
            write_artifact_json(path, data)
            split_hashes[split] = file_sha256(path)
        metadata["split_sha256"] = split_hashes
        write_artifact_json(output / "metadata.json", metadata, replace=True)
    return metadata


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    config = PilotConfig.from_dict(json.loads(args.config.read_text()))
    metadata = run_pilot(config, args.output, Path.cwd())
    return 0 if metadata["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
