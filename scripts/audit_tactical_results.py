"""Independent raw-record cross-check of the first completed tactical study.

Does not call the main analysis loader or summarizer, change labels or tune.
"""

import hashlib
import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import chess


def main() -> None:
    run = Path("artifacts/tactical-test-v1")
    report = Path("reports/tactical-study-v1")
    positions = json.loads((run / "positions.json").read_text())
    expected = {p["name"]: p for p in positions}
    for position in positions:
        row = position["source_row"]
        board = chess.Board(row["FEN"])
        moves = row["Moves"].split()
        for index, uci in enumerate(moves):
            board.push_uci(uci)
            if index == 0:
                solver = board.copy(stack=False)
        assert solver.fen(en_passant="fen") == position["fen"]
        mates = []
        for move in solver.legal_moves:
            child = solver.copy()
            child.push(move)
            if child.is_checkmate():
                mates.append(move.uci())
        accepted = set(mates) if mates else {moves[1]}
        assert set(position["expected_moves"]) == accepted
    cells = defaultdict(list)
    total_nodes = 0
    elapsed_by_pass = [0.0, 0.0, 0.0]
    for index in range(7200):
        raw = json.loads((run / "cases" / f"{index:06d}.json").read_text())
        case = raw["cases"][0]
        spec = raw["spec"]
        assert case["status"] == "completed"
        position = expected[case["name"]]
        decision = case["decision"]
        assert case["fen"] == position["fen"]
        assert (
            chess.Move.from_uci(decision["action"])
            in chess.Board(case["fen"]).legal_moves
        )
        assert case["expected_move_match"] == (
            decision["action"] in position["expected_moves"]
        )
        assert decision["nodes"] == spec["budget"]["value"]
        total_nodes += decision["nodes"]
        pass_index = index // 2400
        elapsed_by_pass[pass_index] += case["elapsed_seconds"]
        cells[(spec["name"], spec["budget"]["value"], case["name"])].append(case)
    assert len(cells) == 2400
    for trials in cells.values():
        assert len(trials) == 3
        decisions = [dict(c["decision"]) for c in trials]
        for decision in decisions:
            decision.pop("search_elapsed_seconds", None)
        assert decisions[0] == decisions[1] == decisions[2]
    summary = json.loads((report / "analysis.json").read_text())
    repeated = Path("artifacts/tactical-audit-reanalysis-20261017/analysis.json")
    assert repeated.read_bytes() == (report / "analysis.json").read_bytes()
    for row in summary["variants"]:
        trials = [cells[(row["variant"], row["budget"], name)] for name in expected]
        successes = sum(c[0]["expected_move_match"] for c in trials)
        times = [statistics.median(t["elapsed_seconds"] for t in c) for c in trials]
        assert successes == row["first_successes"]
        assert statistics.median(times) == row["median_case_seconds"]
    primary = []
    for variant in ("capture-ordering", "transposition-table", "quiescence-1"):
        only_candidate = only_plain = 0
        pass_ratios = [[], [], []]
        for name in expected:
            candidate = cells[(variant, 5000, name)]
            plain = cells[("plain", 5000, name)]
            a, b = candidate[0]["expected_move_match"], plain[0]["expected_move_match"]
            only_candidate += a and not b
            only_plain += b and not a
            for index in range(3):
                pass_ratios[index].append(
                    candidate[index]["elapsed_seconds"]
                    / plain[index]["elapsed_seconds"]
                )
        primary.append(
            {
                "variant": variant,
                "candidate_only": only_candidate,
                "plain_only": only_plain,
                "paired_delta_pp": (only_candidate - only_plain) / 2,
                "median_paired_runtime_ratio_by_pass": [
                    statistics.median(v) for v in pass_ratios
                ],
            }
        )
    examples = []
    for item in summary["failure_examples"]:
        board = chess.Board(item["fen"])
        examples.append(
            {
                "position": item["position"],
                "accepted_SAN": [
                    board.san(chess.Move.from_uci(m)) for m in item["expected_moves"]
                ],
                "selected_SAN": {
                    v: board.san(chess.Move.from_uci(d["action"]))
                    for v, d in item["decisions"].items()
                },
                "source_themes": item["source_row"]["Themes"],
            }
        )
    audit = {
        "audited_at": datetime.now(UTC).isoformat(),
        "status": "passed",
        "raw_searches": 7200,
        "independent_puzzles": 200,
        "total_visited_nodes": total_nodes,
        "source_setup_and_labels_rechecked": 200,
        "reanalysis_summary_byte_identical": True,
        "repeated_decision_statistic_disagreements": 0,
        "total_case_seconds_by_pass": elapsed_by_pass,
        "primary_contrasts": primary,
        "illustrative_examples_SAN": examples,
        "timing_note": "Per-pass ratios are post-hoc robustness diagnostics, "
        "not replacement primary estimates. No trials were removed.",
        "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (report / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
