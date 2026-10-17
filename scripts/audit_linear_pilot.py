"""Recompute the pilot's data, label-fidelity and playing diagnostics offline."""

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

import chess

from chesslab.agents.external_uci import file_sha256
from chesslab.compare_tactics import (
    TacticalCase,
    comparison_spec_from_dict,
    summarize_comparison,
)
from chesslab.engine.evaluation.linear import LinearEvaluator, board_features
from chesslab.engine.evaluation.material import material_score
from chesslab.eval.artifacts import configuration_digest, write_artifact_json
from chesslab.eval.matches import (
    FailureKind,
    MatchFailure,
    MatchMetadata,
    MatchResult,
    MatchStatus,
    MoveRecord,
)
from chesslab.games.chess import ChessState
from chesslab.learning import position_identity
from chesslab.match_suite import (
    SuiteGame,
    match_suite_spec_from_dict,
    summarize_match_suite,
)


def checked_sources(directory, metadata, folder):
    for name, expected in metadata["source_sha256"].items():
        assert file_sha256(directory / folder / name) == expected, name


def audit_matches(directory):
    match_manifest = json.loads((directory / "manifest.json").read_text())
    match_spec = match_suite_spec_from_dict(match_manifest)
    games = []
    raw_games = []
    scheduled_seeds = []
    for seed in match_spec.seeds:
        rng = random.Random(seed)
        scheduled_seeds.extend(rng.getrandbits(128) for _ in match_spec.positions)
    for path in sorted((directory / "games").glob("*.json")):
        game = json.loads(path.read_text())
        result = game["result"]
        raw_games.append(game)
        assert result["metadata"]["root_seed"] == scheduled_seeds[game["pair_index"]]
        assert (
            game["initial_fen"]
            == match_spec.positions[game["pair_index"] % len(match_spec.positions)].fen
        )
        board = chess.Board(game["initial_fen"])
        for move in result["moves"]:
            assert move["player"] == (0 if board.turn else 1)
            board.push_uci(move["action"])
        if result["status"] == "completed":
            outcome = board.outcome(claim_draw=False)
            assert outcome is not None
            expected = (
                [0.0, 0.0]
                if outcome.winner is None
                else [1.0, -1.0]
                if outcome.winner
                else [-1.0, 1.0]
            )
            assert result["terminal_returns"] == expected
            termination = outcome.termination.name
        else:
            assert (
                result["failure"]["kind"] == "ply_limit"
                and len(board.move_stack) == match_spec.max_plies
            )
            termination = "PLY_LIMIT"
        games.append(
            {
                key: game[key]
                for key in (
                    "pair_index",
                    "root_seed",
                    "white_agent",
                    "black_agent",
                    "position_name",
                )
            }
            | {
                "match_metadata": result["metadata"],
                "status": result["status"],
                "returns": result["terminal_returns"],
                "plies": result["plies"],
                "termination": termination,
                "raw_sha256": file_sha256(path),
            }
        )
    metadata = json.loads((directory / "metadata.json").read_text())
    checked_sources(directory, metadata, "source")
    assert metadata["manifest_digest"] == match_spec.digest
    decoded = []
    for game in raw_games:
        raw = game["result"]
        failure = raw["failure"]
        result = MatchResult(
            MatchStatus(raw["status"]),
            MatchMetadata(
                **{
                    **raw["metadata"],
                    "player_seeds": tuple(raw["metadata"]["player_seeds"]),
                }
            ),
            tuple(MoveRecord(**move) for move in raw["moves"]),
            tuple(raw["terminal_returns"])
            if raw["terminal_returns"] is not None
            else None,
            MatchFailure(**{**failure, "kind": FailureKind(failure["kind"])})
            if failure
            else None,
        )
        assert result.plies == raw["plies"]
        decoded.append(
            SuiteGame(
                game["pair_index"],
                game["root_seed"],
                game["position_name"],
                game["initial_fen"],
                game["white_agent"],
                game["black_agent"],
                result,
                game.get("engines", {}),
            )
        )
    summary = summarize_match_suite(match_spec, decoded)
    assert summary == json.loads((directory / "summary.json").read_text())
    return {
        "manifest": match_manifest,
        "metadata": metadata,
        "summary": summary,
        "games": games,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--first-attempt", type=Path, required=True)
    parser.add_argument("--tactics", type=Path, nargs="+", required=True)
    parser.add_argument("--matches", type=Path, nargs="+", required=True)
    parser.add_argument("--hardware", type=Path, required=True)
    args = parser.parse_args()
    data = args.data
    metadata = json.loads((data / "metadata.json").read_text())
    plan = json.loads((data / "plan.json").read_text())
    assert metadata["status"] == "completed" and metadata["failed"] == 0
    assert configuration_digest(plan) == metadata["manifest_digest"]
    checked_sources(data, metadata, "source")
    assert file_sha256(data / "positions.json") == metadata["positions_sha256"]
    assert file_sha256(data / "trajectories.json") == metadata["trajectories_sha256"]
    rows = json.loads((data / "positions.json").read_text())
    assert len({r["identity"] for r in rows}) == len(rows)
    groups = {}
    excluded = set()
    for source in plan["exclusions"]:
        path = Path(source["path"])
        assert file_sha256(path) == source["sha256"]
        original = json.loads(path.read_text())
        inputs = (
            original if isinstance(original, list) else original["dataset"]["positions"]
        )
        excluded.update(position_identity(chess.Board(r["fen"])) for r in inputs)
    for row in rows:
        groups.setdefault(row["group"], set()).add(row["split"])
        assert row["identity"] not in excluded
        board = chess.Board()
        for move in row["history"]:
            board.push_uci(move)
        assert board.fen() == row["fen"] and not board.is_game_over()
        assert position_identity(board) == row["identity"]
    assert all(len(splits) == 1 for splits in groups.values())
    selection = json.loads((args.model / "selection.json").read_text())
    assessment = json.loads((args.model / "test-assessment.json").read_text())
    model = LinearEvaluator.load(args.model / "model.json", selection["model_sha256"])
    assert file_sha256(data / "metadata.json") == selection["dataset_metadata_sha256"]
    assert file_sha256(args.model / "train-script.py") == selection["script_sha256"]
    assert file_sha256(args.model / "selection.json") == assessment["selection_sha256"]
    label_counts = {}
    total_nodes = 0
    for split in ("train", "validation", "test"):
        path = data / f"{split}.json"
        assert file_sha256(path) == metadata["split_sha256"][split]
        labelled = json.loads(path.read_text())
        assert len(labelled) == sum(r["split"] == split for r in rows)
        errors, baseline = [], []
        for row in labelled:
            state = ChessState.from_fen(row["fen"])
            assert row["features"] == list(board_features(state))
            assert row["material_cp"] == material_score(state, 0)
            assert row["error"] is None and abs(row["target_cp"]) <= model.clip_cp
            assert (
                json.loads(
                    (
                        data
                        / "cases"
                        / f"{rows.index({k: row[k] for k in rows[0]}):04d}.json"
                    ).read_text()
                )
                == row
            )
            errors.append(model.evaluate(state, 0) - row["target_cp"])
            baseline.append(
                max(-model.clip_cp, min(model.clip_cp, row["material_cp"]))
                - row["target_cp"]
            )
            total_nodes += row["nodes"] or 0

        def metric(values):
            return {
                "rmse_cp": math.sqrt(sum(e * e for e in values) / len(values)),
                "mae_cp": sum(abs(e) for e in values) / len(values),
            }

        observed = metric(errors)
        expected = (
            selection["selected"][split] if split != "test" else assessment["learned"]
        )
        for key, value in observed.items():
            assert math.isclose(value, expected[key], rel_tol=1e-12)
        expected_baseline = (
            selection[f"{split}_material"]
            if split != "test"
            else assessment["material"]
        )
        for key, value in metric(baseline).items():
            assert math.isclose(value, expected_baseline[key], rel_tol=1e-12)
        label_counts[split] = {
            "positions": len(labelled),
            "groups": len({r["group"] for r in labelled}),
            "mate_targets": sum(r["white_mate"] is not None for r in labelled),
            "final_iteration_bound": sum(r["final_bound"] for r in labelled),
            "saturated_targets": sum(
                abs(r["target_cp"]) == model.clip_cp for r in labelled
            ),
        }
    tactics = []
    for directory in args.tactics:
        manifest = json.loads((directory / "manifest.json").read_text())
        spec = comparison_spec_from_dict(manifest)
        raw = [
            TacticalCase(**json.loads(p.read_text()))
            for p in sorted((directory / "cases").glob("*.json"))
        ]
        summary = summarize_comparison(spec, raw)
        assert summary == json.loads((directory / "summary.json").read_text())
        meta = json.loads((directory / "metadata.json").read_text())
        checked_sources(directory, meta, "source")
        assert any(
            a.learned and a.learned.sha256 == selection["model_sha256"]
            for a in spec.agents
        )
        tactics.append({"manifest": manifest, "metadata": meta, "summary": summary})
    matches = [audit_matches(directory) for directory in args.matches]
    previous = args.first_attempt
    first = json.loads((previous / "metadata.json").read_text())
    failures = Counter(
        json.loads(p.read_text()).get("error")
        for p in (previous / "cases").glob("*.json")
    )
    assert file_sha256(previous / "positions.json") == metadata["positions_sha256"]
    write_artifact_json(
        args.output,
        {
            "dataset": {
                "plan": plan,
                "metadata": metadata,
                "counts": label_counts,
                "total_reported_nodes": total_nodes,
            },
            "selection": selection,
            "assessment": assessment,
            "tactics": tactics,
            "matches": matches,
            "first_attempt": {
                "metadata": first,
                "errors": {str(k): v for k, v in failures.items()},
            },
            "hardware": json.loads(args.hardware.read_text()),
            "audit": {
                "status": "passed",
                "script_sha256": file_sha256(Path(__file__)),
                "checks": "source/data/model pins, split identities, replay, "
                "exclusions, "
                "features, label metrics, tactical summary and game outcomes",
            },
        },
    )


if __name__ == "__main__":
    main()
