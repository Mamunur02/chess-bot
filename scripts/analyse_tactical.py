"""Validate and analyse a completed tactical run without tuning the agents.

Uses only existing project dependencies. Optional figures run in a separate
Matplotlib environment; the frozen agent environment and lock remain unchanged.
"""

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chess

from chesslab.eval.artifacts import configuration_digest, write_artifact_json
from chesslab.tactical import VARIANTS, tactical_specs

JSON = dict[str, Any]
Cell = tuple[str, int, str]


def load_logging_amendment(directory: Path, plan: JSON) -> JSON | None:
    """Verify the disclosed operational writer fix separately from frozen search."""
    recovery = directory / "recovery-v2"
    if not recovery.exists():
        return None
    amendment = json.loads((recovery / "amendment.json").read_text())
    old_hash = plan["code_sha256"].get("src/chesslab/eval/artifacts.py")
    if amendment["old_writer_sha256"] != old_hash:
        raise ValueError("logging amendment original-source mismatch")
    for name, field in (
        ("logging-writer.py", "new_writer_sha256"),
        ("launcher.py", "launcher_sha256"),
    ):
        actual = hashlib.sha256((recovery / name).read_bytes()).hexdigest()
        if actual != amendment[field]:
            raise ValueError("logging amendment source digest mismatch")
    if amendment["original_plan_digest"] != configuration_digest(plan):
        raise ValueError("logging amendment plan mismatch")
    return amendment


def percentile(values: list[float], probability: float) -> float:
    """Linearly interpolate sorted values at (n-1)*p, including endpoints."""
    if not values or not 0 <= probability <= 1:
        raise ValueError("nonempty values and probability in [0, 1] required")
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def paired_intervals(
    vectors: list[list[int | None]], *, seed: int, replicates: int
) -> list[tuple[float, float] | None]:
    """Resample shared puzzle indices, retaining all contrasts together.

    Missing pairs contribute no observed outcome; coverage and worst-case bounds
    are reported separately. Intervals describe the observed complete pairs.
    """
    if replicates <= 0 or not vectors or not vectors[0]:
        raise ValueError("positive replicates and nonempty vectors required")
    size = len(vectors[0])
    if any(len(v) != size for v in vectors):
        raise ValueError("paired vectors must share source indices")
    samples: list[list[float]] = [[] for _ in vectors]
    rng = random.Random(seed)
    for _ in range(replicates):
        indices = [rng.randrange(size) for _ in range(size)]
        for vector, estimates in zip(vectors, samples, strict=True):
            observed = [vector[i] for i in indices if vector[i] is not None]
            if observed:
                estimates.append(100 * sum(observed) / len(observed))
    return [
        (percentile(v, 0.025), percentile(v, 0.975)) if v else None for v in samples
    ]


def load_run(directory: Path) -> tuple[JSON, JSON, list[JSON], dict[Cell, list[Any]]]:
    """Check frozen identities, schedule, chess decisions and case coverage."""
    plan = json.loads((directory / "plan.json").read_text())
    metadata = json.loads((directory / "metadata.json").read_text())
    if metadata["status"] != "completed":
        raise ValueError("formal analysis requires a completed run")
    if metadata["manifest_digest"] != configuration_digest(plan):
        raise ValueError("run plan digest mismatch")
    load_logging_amendment(directory, plan)
    if plan["protocol_sha256"] is not None:
        protocol_hash = hashlib.sha256(
            (directory / "protocol.md").read_bytes()
        ).hexdigest()
        if protocol_hash != plan["protocol_sha256"]:
            raise ValueError("copied protocol digest mismatch")
    for name, digest in plan["code_sha256"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("invalid source snapshot path")
        if (
            hashlib.sha256((directory / "sources" / path).read_bytes()).hexdigest()
            != digest
        ):
            raise ValueError("source snapshot digest mismatch")
    payload = (directory / "positions.json").read_bytes()
    if hashlib.sha256(payload).hexdigest() != plan["split_sha256"]:
        raise ValueError("copied positions digest mismatch")
    positions = json.loads(payload)
    groups = [p.get("game_id", p["name"]) for p in positions]
    if len(groups) != len(set(groups)):
        raise ValueError("bootstrap expects one retained puzzle per source-game group")
    inputs = [
        {key: p[key] for key in ("name", "fen", "expected_moves")} for p in positions
    ]
    specs = tactical_specs(inputs, tuple(plan["budgets"]), plan["repeats"])
    if [s.digest for s in specs] != plan["case_digests"]:
        raise ValueError("schedule digest mismatch")
    if metadata["runs_planned"] != len(specs):
        raise ValueError("planned-case count mismatch")
    expected_files = {f"{i:06d}.json" for i in range(len(specs))}
    if any(p.name not in expected_files for p in (directory / "cases").glob("*.json")):
        raise ValueError("unexpected case artifact")
    cells: dict[Cell, list[Any]] = defaultdict(list)
    for index, spec in enumerate(specs):
        path = directory / "cases" / f"{index:06d}.json"
        position = spec.positions[0]
        budget = spec.to_dict()["budget"]
        assert isinstance(budget, dict)
        key = (spec.name, int(budget["value"]), position.name)
        if not path.exists():
            cells[key].append(None)
            continue
        raw = json.loads(path.read_text())
        if raw["spec"] != spec.to_dict() or len(raw["cases"]) != 1:
            raise ValueError("case spec/count differs from schedule")
        if raw["provenance"]["config_digest"] != spec.digest:
            raise ValueError("case provenance digest mismatch")
        case = raw["cases"][0]
        if case["name"] != position.name or case["fen"] != position.fen:
            raise ValueError("case identity differs from schedule")
        if case["status"] not in {"completed", "failed"}:
            raise ValueError("invalid case status")
        elapsed = case["elapsed_seconds"]
        if (
            not isinstance(elapsed, (int, float))
            or not math.isfinite(elapsed)
            or elapsed < 0
        ):
            raise ValueError("invalid measured case duration")
        decision = case["decision"]
        if case["status"] == "completed":
            if decision is None or case["error"] is not None:
                raise ValueError("inconsistent completed-case status")
            board = chess.Board(position.fen)
            move = chess.Move.from_uci(decision["action"])
            if move not in board.legal_moves:
                raise ValueError("illegal recorded decision")
            if case["expected_move_match"] is not (
                decision["action"] in position.expected_moves
            ):
                raise ValueError("recorded agreement differs from frozen labels")
            if (
                type(decision["nodes"]) is not int
                or not 0 <= decision["nodes"] <= key[1]
            ):
                raise ValueError("invalid recorded node budget")
            if not 0 <= decision["quiescence_nodes"] <= decision["nodes"]:
                raise ValueError("quiescence nodes are not a subset of total nodes")
        elif decision is not None or case["expected_move_match"] is not None:
            raise ValueError("failed case must not contain a successful decision")
        cells[key].append(case)
    if any(len(cases) != plan["repeats"] for cases in cells.values()):
        raise ValueError("repeat coverage does not match plan")
    return plan, metadata, positions, cells


def successful(case: Any) -> bool:
    return case is not None and case["status"] == "completed"


def outcome(case: Any) -> int | None:
    return int(case["expected_move_match"]) if successful(case) else None


def summarize(
    plan: JSON,
    positions: list[JSON],
    cells: dict[Cell, list[Any]],
    *,
    replicates: int = 10000,
    seed: int = 20261018,
) -> JSON:
    """Compute prespecified first-pass quality and complete-repeat median times."""
    names = [p["name"] for p in positions]
    variants = [name for name, _ in VARIANTS]
    n = len(names)
    rows, contrasts, vectors = [], [], []
    medians: dict[Cell, float] = {}
    nondeterminism: list[JSON] = []
    for budget in plan["budgets"]:
        for variant in variants:
            first = [cells[(variant, budget, name)][0] for name in names]
            for name in names:
                trials = cells[(variant, budget, name)]
                fingerprints = {
                    json.dumps(
                        {
                            k: v
                            for k, v in c["decision"].items()
                            if k != "search_elapsed_seconds"
                        },
                        sort_keys=True,
                    )
                    for c in trials
                    if successful(c)
                }
                if len(fingerprints) > 1:
                    nondeterminism.append(
                        {"variant": variant, "budget": budget, "position": name}
                    )
                if all(successful(c) for c in trials):
                    medians[(variant, budget, name)] = statistics.median(
                        c["elapsed_seconds"] for c in trials
                    )
            times = [
                medians[(variant, budget, name)]
                for name in names
                if (variant, budget, name) in medians
            ]
            completed = [c for c in first if successful(c)]
            row = {
                "variant": variant,
                "budget": budget,
                "planned_positions": n,
                "first_completed": len(completed),
                "first_failed": sum(c is not None and not successful(c) for c in first),
                "first_missing": sum(c is None for c in first),
                "first_successes": sum(outcome(c) == 1 for c in first),
                "first_agreement_percent": 100
                * sum(outcome(c) == 1 for c in first)
                / n,
                "first_runtime_seconds": sum(c["elapsed_seconds"] for c in first if c),
                "complete_timing_positions": len(times),
                "median_case_seconds": statistics.median(times) if times else None,
                "timing_q1_seconds": percentile(times, 0.25) if times else None,
                "timing_q3_seconds": percentile(times, 0.75) if times else None,
                "depth_zero": sum(c["decision"]["depth"] == 0 for c in completed),
            }
            for field in (
                "nodes",
                "depth",
                "cutoffs",
                "transposition_hits",
                "quiescence_nodes",
            ):
                row[f"first_total_{field}"] = sum(
                    c["decision"][field] for c in completed
                )
            rows.append(row)
        for variant in variants[1:]:
            vector: list[int | None] = []
            lower, upper, ratios = [], [], []
            wins = losses = 0
            for name in names:
                a = outcome(cells[(variant, budget, name)][0])
                b = outcome(cells[("plain", budget, name)][0])
                vector.append(a - b if a is not None and b is not None else None)
                lower.append((a if a is not None else 0) - (b if b is not None else 1))
                upper.append((a if a is not None else 1) - (b if b is not None else 0))
                wins += a == 1 and b == 0
                losses += a == 0 and b == 1
                left, right = (variant, budget, name), ("plain", budget, name)
                if left in medians and right in medians and medians[right] > 0:
                    ratios.append(medians[left] / medians[right])
            observed = [d for d in vector if d is not None]
            contrasts.append(
                {
                    "variant": variant,
                    "reference": "plain",
                    "budget": budget,
                    "planned_positions": n,
                    "complete_pairs": len(observed),
                    "complete_pair_delta_pp": 100 * sum(observed) / len(observed)
                    if observed
                    else None,
                    "candidate_only_success": wins,
                    "reference_only_success": losses,
                    "missing_outcome_lower_pp": 100 * sum(lower) / n,
                    "missing_outcome_upper_pp": 100 * sum(upper) / n,
                    "timing_pairs": len(ratios),
                    "median_paired_runtime_ratio": statistics.median(ratios)
                    if ratios
                    else None,
                    "runtime_ratio_q1": percentile(ratios, 0.25) if ratios else None,
                    "runtime_ratio_q3": percentile(ratios, 0.75) if ratios else None,
                }
            )
            vectors.append(vector)
    intervals = paired_intervals(vectors, seed=seed, replicates=replicates)
    for contrast, interval in zip(contrasts, intervals, strict=True):
        contrast["descriptive_95_percent_interval_pp"] = interval
    examples = []
    if 5000 in plan["budgets"]:
        for position in positions:
            decisions = {
                variant: cells[(variant, 5000, position["name"])][0]
                for variant in variants
            }
            if not any(outcome(c) == 0 for c in decisions.values()):
                continue
            examples.append(
                {
                    "position": position["name"],
                    "fen": position.get("fen"),
                    "expected_moves": position.get("expected_moves"),
                    "source_row": position.get("source_row"),
                    "decisions": {
                        variant: c["decision"] if successful(c) else None
                        for variant, c in decisions.items()
                    },
                }
            )
            if len(examples) == 8:
                break
    return {
        "status": "needs_investigation"
        if (
            nondeterminism or any(r["first_missing"] or r["first_failed"] for r in rows)
        )
        else "validated",
        "split": plan["split"],
        "positions": n,
        "repeats": plan["repeats"],
        "bootstrap_seed": seed,
        "bootstrap_replicates": replicates,
        "interval_scope": "Descriptive marginal complete-pair intervals; no "
        "significance or family-wise coverage claim.",
        "nondeterministic_conditions": nondeterminism,
        "variants": rows,
        "contrasts": contrasts,
        "failure_examples": examples,
        "example_selection": "First eight source-order positions with any primary-"
        "budget miss; illustrative only, without relabelling or tuning.",
    }


def render_report(summary: JSON, metadata: JSON) -> str:
    """Generate a measured-results memo without automated novelty/strength claims."""
    lines = [
        "# Tactical baseline study v1",
        "",
        f"Analysis status: **{summary['status']}**. Split: {summary['split']}.",
        "",
        f"{summary['positions']} independent retained puzzle groups; "
        f"{summary['repeats']} timing passes on the same positions. "
        "Quality uses only the first pass. Timing repeats do not increase sample size.",
        "",
        "## Measured quality and runtime",
        "",
        "Agreement is with frozen accepted first moves, not full-puzzle solving.",
        "",
        "| Nodes | Variant | Correct / planned | Failed / missing | "
        "Median case seconds | Complete timing positions |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["variants"]:
        timing = row["median_case_seconds"]
        timing_text = f"{timing:.6f}" if timing is not None else "unavailable"
        lines.append(
            f"| {row['budget']:,} | {row['variant']} | "
            f"{row['first_successes']} / {row['planned_positions']} | "
            f"{row['first_failed']} / {row['first_missing']} | {timing_text} | "
            f"{row['complete_timing_positions']} |"
        )
    lines += [
        "",
        "Median time is the median across positions of each position's "
        "median over its complete successful timing passes.",
        "",
        "## Primary comparisons at 5,000 nodes",
        "",
        "| Variant minus plain | Delta pp | Descriptive 95% interval pp | "
        "Complete pairs | Candidate-only / plain-only successes | Runtime ratio |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in summary["contrasts"]:
        if row["budget"] != 5000:
            continue
        delta, interval = (
            row["complete_pair_delta_pp"],
            row["descriptive_95_percent_interval_pp"],
        )
        delta_text = f"{delta:+.2f}" if delta is not None else "unavailable"
        interval_text = (
            f"[{interval[0]:+.2f}, {interval[1]:+.2f}]" if interval else "unavailable"
        )
        ratio = row["median_paired_runtime_ratio"]
        ratio_text = f"{ratio:.3f}x" if ratio is not None else "unavailable"
        lines.append(
            f"| {row['variant']} | {delta_text} | {interval_text} | "
            f"{row['complete_pairs']} | {row['candidate_only_success']} / "
            f"{row['reference_only_success']} | {ratio_text} |"
        )
    lines += [
        "",
        summary["interval_scope"],
        f"Intervals use {summary['bootstrap_replicates']:,} shared paired bootstrap "
        f"resamples (seed {summary['bootstrap_seed']}). "
        "Few discordant cases can yield discrete/degenerate intervals. "
        "Missing-outcome bounds, coverage and all budgets are in analysis.json.",
        "",
        "## Integrity and limitations",
        "",
        "Repeated-search disagreements: "
        f"{len(summary['nondeterministic_conditions'])}.",
        "A nonzero count requires investigation before interpreting aggregates.",
        "Source positions are tactics-selected Lichess puzzles, not ordinary chess "
        "positions. Labels are fallible, full earlier repetition history is absent, "
        "and this small single-snapshot sample limits generalization. "
        "The material evaluator is fixed. No Elo, novelty or general-strength claim.",
        "Equal node budgets do not imply equal runtime; nominal completed depths "
        "are not equivalent tactical horizons across quiescence variants. "
        "Timings are machine-specific. Session notes record setup overlap "
        "and power/load conditions.",
        "",
        "## Failure examples",
        "",
        "analysis.json retains the first eight source-order primary-budget cases "
        "where any variant missed, with frozen labels, FEN, source row and decisions. "
        "These are illustrative selections, not a representative failure taxonomy.",
        "",
        "## Provenance",
        "",
        f"Run ID: {metadata['run_id']}. Git state and runtime versions: "
        "see run metadata and copied source/protocol hashes.",
        "The artifact plan, raw per-case files and source snapshots identify the "
        "executed code even when the working tree is dirty. analysis-provenance.json "
        "records the separate analysis/plot scripts.",
        "",
        "## Next research decision",
        "",
        "Review the paired quality/runtime trade-offs and failure examples before "
        "choosing another algorithm, evaluator or dataset. Do not tune on these "
        "test positions and then reuse them as an unbiased benchmark.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan, metadata, positions, cells = load_run(args.run)
    summary = summarize(plan, positions, cells)
    amendment = load_logging_amendment(args.run, plan)
    if amendment is not None:
        summary["logging_amendment"] = amendment
    recovery = args.run / "recovery-v1"
    if recovery.exists():
        summary["execution_recovery"] = {
            "original_failure": json.loads(
                (recovery / "original-metadata.json").read_text()
            ),
            "original_session": json.loads(
                (recovery / "original-session.json").read_text()
            ),
            "note": "Windows progress-file access interrupted execution; "
            "Original recovery preserved code/protocol and cases; later logging "
            "amendments are recorded separately. "
            "Retain this interruption as a timing limitation.",
        }
    args.output.mkdir(parents=True, exist_ok=False)
    write_artifact_json(args.output / "analysis.json", summary)
    with (args.output / "variant-metrics.csv").open(
        "x", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary["variants"][0]))
        writer.writeheader()
        writer.writerows(summary["variants"])
    report = render_report(summary, metadata)
    if "execution_recovery" in summary:
        report += (
            "\n## Execution recovery\n\n"
            + summary["execution_recovery"]["note"]
            + " Original failure/session details are preserved in analysis.json.\n"
        )
    if amendment is not None:
        report += (
            "\n## Disclosed logging amendment\n\n"
            "A Windows atomic-write retry fix was applied to logging only. "
            "Search ran from the original copied source tree; the original plan "
            "and checkpoints were retained. Both writer hashes and the exact "
            "amendment/launcher sources are recorded. Interrupted timing passes "
            "remain a limitation; no cases were selectively discarded.\n"
        )
    (args.output / "report.md").write_text(report, encoding="utf-8")
    source = Path(__file__).resolve()
    analysis_sources = [source, source.with_name("plot_tactical.py")]
    provenance = {
        "analysed_at": datetime.now(UTC).isoformat(),
        "run_plan_digest": configuration_digest(plan),
        "analysis_sources": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in analysis_sources
        },
    }
    for path in analysis_sources:
        (args.output / path.name).write_bytes(path.read_bytes())
    if amendment is not None:
        for name in ("amendment.json", "logging-writer.py", "launcher.py"):
            (args.output / f"logging-amendment-{name}").write_bytes(
                (args.run / "recovery-v2" / name).read_bytes()
            )
    write_artifact_json(args.output / "analysis-provenance.json", provenance)
    plotting_python = (
        source.parents[1] / "artifacts" / "plot-env" / "Scripts" / "python.exe"
    )
    if plotting_python.exists():
        result = subprocess.run(
            [
                str(plotting_python),
                str(source.with_name("plot_tactical.py")),
                str(args.output / "analysis.json"),
            ],
            check=False,
        )
        if result.returncode:
            return result.returncode
    if summary["status"] != "validated":
        return 2
    print(f"Validated analysis and report written to {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
