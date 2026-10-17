"""Audit saved comparison records and export a compact, reproducible summary."""

import argparse
import json
from pathlib import Path

from chesslab.agents.external_uci import file_sha256
from chesslab.compare_tactics import (
    TacticalCase,
    comparison_spec_from_dict,
    summarize_comparison,
)
from chesslab.eval.artifacts import write_artifact_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--hardware", type=Path, help="optional measured hardware JSON")
    args = parser.parse_args()
    spec = comparison_spec_from_dict(
        json.loads((args.run / "manifest.json").read_text())
    )
    metadata = json.loads((args.run / "metadata.json").read_text())
    if metadata["status"] not in {"completed", "failed", "interrupted"}:
        raise ValueError("cannot summarize a running comparison")
    if metadata["manifest_digest"] != spec.digest:
        raise ValueError("metadata digest differs from manifest")
    cases = []
    records = []
    engines = {}
    for path in sorted((args.run / "cases").glob("*.json")):
        case = TacticalCase(**json.loads(path.read_text()))
        if path.name != f"{case.index:04d}.json":
            raise ValueError("case filename differs from recorded index")
        cases.append(case)
        records.append(
            {
                "index": case.index,
                "agent": case.agent,
                "position": case.position,
                "action": case.action,
                "agreement": case.agreement,
                "error": case.error,
                "phase": case.phase,
                "cleanup_error": case.engine.get("cleanup_error"),
                "case_sha256": file_sha256(path),
            }
        )
        if case.engine:
            engine = engines.setdefault(case.agent, {})
            for key in (
                "config",
                "identity",
                "executable",
                "executable_sha256",
                "assets",
                "advertised_options",
                "managed_settings",
                "seed_policy",
            ):
                if key in case.engine:
                    if key in engine and engine[key] != case.engine[key]:
                        raise ValueError(
                            "engine identity/settings changed across cases"
                        )
                    engine[key] = case.engine[key]
    summary = summarize_comparison(spec, cases)
    if summary != json.loads((args.run / "summary.json").read_text()):
        raise ValueError("saved summary differs from raw records")
    if metadata["runs_written"] != len(cases):
        raise ValueError("metadata case count differs from raw records")
    if metadata["status"] == "completed" and any(
        summary[key] for key in ("failed", "interrupted", "missing", "cleanup_failures")
    ):
        raise ValueError("completed metadata contains failures or missing cases")
    for name, expected in metadata["source_sha256"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("invalid source snapshot path")
        if file_sha256(args.run / "source" / relative) != expected:
            raise ValueError("source snapshot digest mismatch")
    write_artifact_json(
        args.output,
        {
            "manifest": spec.to_dict(),
            "metadata": metadata,
            "summary": summary,
            "cases": records,
            "engines": engines,
            "hardware": json.loads(args.hardware.read_text())
            if args.hardware
            else None,
            "audit": {
                "schedule_legality_labels_timings_and_summary": "passed",
                "source_snapshots": "passed",
                "script_sha256": file_sha256(Path(__file__)),
            },
            "interpretation": "First-move source-solution agreement only. Development "
            "positions are observed; no held-out, Elo or population claim.",
        },
    )


if __name__ == "__main__":
    main()
