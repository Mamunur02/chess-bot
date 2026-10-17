"""Learned-evaluator semantics and leakage guards without NumPy or engines."""

import json
import random
import runpy
import sys
from collections.abc import AsyncIterator
from dataclasses import replace
from io import StringIO
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import chess
import chess.engine
import pytest

import chesslab.learning as learning
from chesslab.agents.external_uci import UciConfig, file_sha256
from chesslab.agents.linear_alpha_beta import LinearAlphaBetaAgent
from chesslab.engine.evaluation.linear import (
    FEATURE_COUNT,
    LinearEvaluator,
    board_features,
)
from chesslab.engine.evaluation.material import material_score
from chesslab.games.chess import ChessState
from chesslab.learning import (
    PilotConfig,
    TeacherLabel,
    completed_score,
    generate_positions,
    run_pilot,
    teacher_label,
)
from chesslab.match_suite import match_agent_config_from_dict
from chesslab.search import DepthBudget
from chesslab.search.classical import MATE_SCORE
from chesslab.uci import main as uci_main

TRAINER = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/train_linear_evaluator.py")
)


def config() -> PilotConfig:
    return PilotConfig(
        17,
        (1, 1, 1),
        (4, 6),
        8,
        50,
        100,
        2000,
        60,
        UciConfig("not-used", "0" * 64, {}),
        (),
        (0.1, 1.0),
    )


def test_features_sparse_dense_and_mirror_perspectives() -> None:
    state = ChessState().apply(chess.Move.from_uci("e2e4"))
    mirror = ChessState.from_fen(state.to_board().mirror().fen())
    weights = tuple((i % 13 - 6) * 3.1 for i in range(FEATURE_COUNT))
    model = LinearEvaluator(weights)
    dense = material_score(state, 0) + sum(
        a * b for a, b in zip(board_features(state), weights, strict=True)
    )
    assert model.evaluate(state, 0) == round(dense)
    assert model.evaluate(state, 1) == -model.evaluate(state, 0)
    assert model.evaluate(mirror, 0) == -model.evaluate(state, 0)
    assert board_features(mirror) == tuple(-x for x in board_features(state))
    assert LinearEvaluator((0.0,) * FEATURE_COUNT).evaluate(state, 0) == material_score(
        state, 0
    )


@pytest.mark.parametrize(
    "weights,clip",
    [
        ([0.0], 2000),
        ([float("nan")] * FEATURE_COUNT, 2000),
        ([True] * FEATURE_COUNT, 2000),
        ([0.0] * FEATURE_COUNT, True),
        ([0.0] * FEATURE_COUNT, 10001),
    ],
)
def test_reject_invalid_checkpoints(weights: list[float], clip: int) -> None:
    with pytest.raises(ValueError):
        LinearEvaluator(tuple(weights), clip)


def test_model_json_pin_bounds_and_mate_override(tmp_path: Path) -> None:
    model = LinearEvaluator((9000.0,) * FEATURE_COUNT)
    assert abs(model.evaluate(ChessState(), 0)) <= 2000
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model.to_dict()))
    settings = {
        "name": "learned",
        "agent": {
            "kind": "linear_alpha_beta",
            "path": str(path),
            "sha256": file_sha256(path),
        },
    }
    agent = match_agent_config_from_dict(settings).build()
    assert isinstance(agent, LinearAlphaBetaAgent)
    state = ChessState.from_fen("7k/8/5KQ1/8/8/8/8/1r6 w - - 0 1")
    result = agent.select_action(state, DepthBudget(1), random.Random(0))
    assert result.value == MATE_SCORE and state.apply(result.action).is_terminal()
    path.write_text("{}")
    with pytest.raises(ValueError, match="SHA-256"):
        match_agent_config_from_dict(settings).build()


def test_model_schema_and_training_switches_strict() -> None:
    model = LinearEvaluator((0.0,) * FEATURE_COUNT).to_dict()
    model["perspective"] = "side-to-move"
    with pytest.raises(ValueError, match="schema"):
        LinearEvaluator.from_dict(model)
    with pytest.raises(ValueError, match="unknown"):
        match_agent_config_from_dict(
            {
                "name": "learned",
                "agent": {
                    "kind": "linear_alpha_beta",
                    "path": "model",
                    "sha256": "0" * 64,
                    "capture_ordering": True,
                },
            }
        )


def test_learned_uci_entry_and_required_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.json"
    model.write_text(json.dumps(LinearEvaluator((0.0,) * FEATURE_COUNT).to_dict()))
    output = StringIO()
    monkeypatch.setattr(
        sys, "stdin", StringIO("uci\nposition startpos\ngo depth 1\nquit\n")
    )
    monkeypatch.setattr(sys, "stdout", output)
    uci_main(["--model", str(model), "--model-sha256", file_sha256(model)])
    assert "uciok" in output.getvalue() and "bestmove " in output.getvalue()
    with pytest.raises(SystemExit):
        uci_main(["--model", str(model)])


@pytest.mark.parametrize(
    "score,pov,target",
    [
        (chess.engine.Cp(3000), chess.WHITE, 2000),
        (chess.engine.Cp(125), chess.BLACK, -125),
        (chess.engine.Mate(3), chess.BLACK, -2000),
        (chess.engine.Mate(-2), chess.BLACK, 2000),
        (chess.engine.Mate(0), chess.WHITE, -2000),
    ],
)
def test_teacher_score_perspective_clipping_and_mates(
    score: chess.engine.Score,
    pov: chess.Color,
    target: int,
) -> None:
    result = teacher_label({"score": chess.engine.PovScore(score, pov)}, 2000)
    assert result.target_cp == target


def test_teacher_missing_or_bound_scores_fail() -> None:
    with pytest.raises(ValueError, match="no score"):
        teacher_label({}, 2000)
    with pytest.raises(ValueError, match="bound"):
        teacher_label(
            cast(
                chess.engine.InfoDict,
                {
                    "score": chess.engine.PovScore(chess.engine.Cp(5), chess.WHITE),
                    "lowerbound": True,
                },
            ),
            2000,
        )


@pytest.mark.parametrize("end_exact", [True, False])
def test_completed_iteration_labels_ignore_stale_or_final_bounds(
    end_exact: bool,
) -> None:
    class Stream:
        stopped = False

        async def __aiter__(self) -> AsyncIterator[chess.engine.InfoDict]:
            yield {
                "score": chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE),
                "nodes": 100,
                "depth": 2,
            }
            yield cast(
                chess.engine.InfoDict,
                {
                    "score": chess.engine.PovScore(chess.engine.Cp(200), chess.WHITE),
                    "nodes": 2000,
                    "depth": 3,
                    "lowerbound": True,
                },
            )
            if end_exact:
                yield {
                    "score": chess.engine.PovScore(chess.engine.Cp(250), chess.WHITE),
                    "nodes": 2001,
                    "depth": 3,
                }

        async def wait(self) -> None:
            return None

        def stop(self) -> None:
            self.stopped = True

    stream = Stream()
    coro = completed_score(cast(chess.engine.AnalysisResult, stream))
    # All fake awaits complete immediately, requiring no OS event loop/socket.
    with pytest.raises(StopIteration) as finished:
        coro.send(None)
    exact, final = finished.value.value
    assert teacher_label(exact, 2000).target_cp == (250 if end_exact else 100)
    assert bool(final.get("lowerbound")) is not end_exact
    assert stream.stopped


def test_label_stream_without_a_completed_score_fails() -> None:
    class Stream:
        stopped = False

        async def __aiter__(self) -> AsyncIterator[chess.engine.InfoDict]:
            yield cast(
                chess.engine.InfoDict,
                {
                    "score": chess.engine.PovScore(chess.engine.Cp(200), chess.WHITE),
                    "nodes": 20,
                    "lowerbound": True,
                },
            )

        async def wait(self) -> None:
            return None

        def stop(self) -> None:
            self.stopped = True

    stream = Stream()
    coro = completed_score(cast(chess.engine.AnalysisResult, stream))
    with pytest.raises(ValueError, match="no completed"):
        coro.send(None)
    assert stream.stopped


def test_group_assignment_determinism_and_exclusions() -> None:
    first = generate_positions(config(), set())
    assert first == generate_positions(config(), set())
    rows, trajectories = first
    assert len(trajectories) == 3
    identities = [row["identity"] for row in rows]
    assert len(set(identities)) == len(identities)
    blocked = rows[0]["identity"]
    assert isinstance(blocked, str)
    excluded, _ = generate_positions(config(), {blocked})
    assert all(row["identity"] != blocked for row in excluded)
    for split in ("train", "validation", "test"):
        assert {row["group"] for row in rows if row["split"] == split} == {
            f"{split}-000"
        }


def test_cross_split_collisions_reject_whole_trajectory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    moves = [
        chess.Move.from_uci(m) for m in ("e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5")
    ]
    monkeypatch.setattr(learning, "rollout", lambda *args: moves)
    with pytest.raises(ValueError, match="generation cap"):
        generate_positions(replace(config(), max_attempts=3), set())


def test_label_failures_export_and_hashes(tmp_path: Path) -> None:
    def label(board: chess.Board) -> TeacherLabel:
        if not board.turn:
            raise TimeoutError("offline teacher failure")
        return TeacherLabel(100, None, 100, 100, 2)

    output = tmp_path / "dataset"
    metadata = run_pilot(config(), output, Path.cwd(), label)
    assert metadata["status"] == "completed"  # sampled even plies: White to move
    hashes = metadata["split_sha256"]
    assert isinstance(hashes, dict)
    for split, digest in hashes.items():
        assert file_sha256(output / f"{split}.json") == digest
    raw = json.loads((output / "train.json").read_text())
    assert raw[0]["features"] == list(
        board_features(ChessState.from_fen(raw[0]["fen"]))
    )
    assert metadata["positions_sha256"] == file_sha256(output / "positions.json")
    before = (output / "metadata.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_pilot(config(), output, Path.cwd(), label)
    assert (output / "metadata.json").read_bytes() == before

    def fail(board: chess.Board) -> TeacherLabel:
        raise TimeoutError("offline teacher failure")

    failed = tmp_path / "failed"
    result = run_pilot(config(), failed, Path.cwd(), fail)
    assert result["status"] == "failed" and result["failed"] == 6
    with pytest.raises(ValueError, match="completed"):
        TRAINER["load_split"](failed, "train")


def test_pilot_config_round_trip_and_reject_bad_counts() -> None:
    assert PilotConfig.from_dict(config().to_dict()) == config()
    data = config().to_dict()
    data["groups"] = {"train": True, "validation": 1, "test": 1}
    with pytest.raises(ValueError, match="group"):
        PilotConfig.from_dict(data)


def test_frozen_training_plan_rejects_tampering(tmp_path: Path) -> None:
    dataset = tmp_path / "data"
    run_pilot(config(), dataset, Path.cwd(), lambda b: TeacherLabel(0, None, 0, 100, 1))
    plan = json.loads((dataset / "plan.json").read_text())
    plan["lambdas"] = [0.001]
    (dataset / "plan.json").write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="frozen digest"):
        TRAINER["load_plan"](dataset)


def test_validation_selection_ties_and_split_leakage() -> None:
    row = {
        "features": [1.0] + [0.0] * (FEATURE_COUNT - 1),
        "target_cp": 100,
        "material_cp": 0,
        "group": "train",
        "identity": "a",
    }
    validation = dict(row, group="validation", identity="b")

    def fitter(rows: object, regularization: float) -> list[float]:
        return [100.0] + [0.0] * (FEATURE_COUNT - 1)

    weights, chosen, _ = TRAINER["select_model"](
        [row], [validation], [0.1, 1.0], 2000, fitter
    )
    assert chosen["lambda"] == 1.0 and weights[0] == 100.0
    with pytest.raises(ValueError, match="group overlap"):
        TRAINER["select_model"]([row], [row], [1.0], 2000, fitter)


def test_training_never_opens_test_split(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = tmp_path / "dataset"
    run_pilot(
        config(), dataset, Path.cwd(), lambda board: TeacherLabel(0, None, 0, 100, 1)
    )
    fake_numpy = ModuleType("numpy")
    fake_numpy.__version__ = "offline-test"  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    select = TRAINER["select_model"]
    monkeypatch.setattr(
        select, "__defaults__", (lambda rows, a: [0.0] * FEATURE_COUNT,)
    )
    original_text, original_bytes = Path.read_text, Path.read_bytes

    def text(path: Path, *args: Any, **kwargs: Any) -> str:
        assert path.name != "test.json", "training attempted to read test data"
        return original_text(path, *args, **kwargs)

    def binary(path: Path) -> bytes:
        assert path.name != "test.json", "training attempted to hash/read test data"
        return original_bytes(path)

    monkeypatch.setattr(Path, "read_text", text)
    monkeypatch.setattr(Path, "read_bytes", binary)
    output = tmp_path / "model"
    TRAINER["train"](dataset, output)
    assert (output / "model.json").exists() and (output / "selection.json").exists()
