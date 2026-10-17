"""Run development-only timing/label checks through the existing experiment tool.

Usage: uv run python scripts/run_tactical_pilot.py prepared-dir fresh-output-dir
The run cap is checked between grids, not a hard per-search deadline.
"""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from chesslab.eval.artifacts import write_artifact_json
from chesslab.experiment import experiment_manifest_from_dict, run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--positions", type=int, default=10)
    parser.add_argument("--budgets", type=int, nargs="+", default=[1000, 5000, 20000])
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    if args.positions <= 0 or args.max_seconds <= 0:
        parser.error("positions and max-seconds must be positive")
    if any(n <= 0 for n in args.budgets) or len(set(args.budgets)) != len(args.budgets):
        parser.error("budgets must be distinct positive integers")
    source = args.prepared / "development.json"
    source_bytes = source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    preparation = json.loads((args.prepared / "manifest.json").read_text())
    if source_hash != preparation["split_sha256"]["development"]:
        raise ValueError("development split digest mismatch")
    puzzles = json.loads(source_bytes)
    if args.positions > len(puzzles):
        parser.error("requested more positions than the development split contains")
    positions = [
        {key: p[key] for key in ("name", "fen", "expected_moves")}
        for p in puzzles[: args.positions]
    ]
    args.output.mkdir(parents=True, exist_ok=False)
    write_artifact_json(args.output / "preparation.json", preparation)
    variants = [
        {"name": "plain", "agent": {}},
        {"name": "capture-ordering", "agent": {"capture_ordering": True}},
        {"name": "transposition-table", "agent": {"transposition_table": True}},
        {"name": "quiescence-1", "agent": {"quiescence_depth": 1}},
    ]
    warmup = experiment_manifest_from_dict(
        {
            "schema_version": 1,
            "name": "warmup",
            "question": "Unscored warmup",
            "dataset": {
                "id": "lichess-development",
                "version": source_hash,
                "split": "development",
                "source": "Unscored pilot warmup",
                "positions": positions[:1],
            },
            "budget": {"kind": "nodes", "value": 100},
            "seeds": [20261017],
            "variants": variants,
        }
    )
    run_experiment(warmup, args.output / "warmup", Path.cwd())
    start = perf_counter()
    rows: list[dict[str, object]] = []
    status = "running"
    try:
        for budget in args.budgets:
            if perf_counter() - start >= args.max_seconds:
                status = "capped"
                break
            manifest = experiment_manifest_from_dict(
                {
                    "schema_version": 1,
                    "name": f"tactical-development-{budget}",
                    "question": "Check runtime and labels before protocol freeze.",
                    "dataset": {
                        "id": "lichess-development-pilot",
                        "version": source_hash,
                        "split": "development",
                        "source": "CC0 Lichess reservoir; first development "
                        "positions only. No held-out strength claim. "
                        + preparation["source_url"],
                        "positions": positions,
                    },
                    "budget": {"kind": "nodes", "value": budget},
                    "seeds": [20261017],
                    "variants": variants,
                }
            )
            output = args.output / f"nodes-{budget}"
            metadata = run_experiment(manifest, output, Path.cwd())
            rows.append({"budget": budget, "status": metadata["status"]})
            write_artifact_json(
                args.output / "progress.json", {"completed": rows}, replace=True
            )
            print(f"Completed development grid at {budget} nodes", flush=True)
        else:
            status = "completed"
    except KeyboardInterrupt:
        status = "interrupted"
        raise
    except Exception:
        status = "failed"
        raise
    finally:
        write_artifact_json(
            args.output / "pilot.json",
            {
                "status": status,
                "development_sha256": source_hash,
                "positions": args.positions,
                "budgets_planned": args.budgets,
                "grids_finished": rows,
                "elapsed_seconds": perf_counter() - start,
                "timing_limitation": "Single pass, fixed variant order; planning "
                "only, not a balanced formal timing comparison.",
            },
        )


if __name__ == "__main__":
    main()
