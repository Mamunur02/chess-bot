"""Counterbalanced fixed-node tactical comparisons with per-case checkpoints."""

import argparse
import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import chess

from chesslab.benchmark import benchmark_spec_from_dict
from chesslab.eval.artifacts import (
    capture_run_metadata,
    configuration_digest,
    write_artifact_json,
)
from chesslab.eval.benchmarks import BenchmarkSpec, capture_provenance, run_benchmark

VARIANTS: tuple[tuple[str, dict[str, object]], ...] = (
    ("plain", {}),
    ("capture-ordering", {"capture_ordering": True}),
    ("transposition-table", {"transposition_table": True}),
    ("quiescence-1", {"quiescence_depth": 1}),
)


def tactical_specs(
    positions: Sequence[object], budgets: tuple[int, ...], repeats: int
) -> tuple[BenchmarkSpec, ...]:
    """Build deterministic schedules rotating variant order between positions.

    Alternating forward/reverse budget order and rotating variant order reduces
    systematic ordering effects. Repeats are timing replicates, not extra puzzles.
    """
    if type(repeats) is not int or repeats <= 0 or not positions:
        raise ValueError("positive repeats and nonempty positions required")
    if not budgets or len(set(budgets)) != len(budgets):
        raise ValueError("distinct positive node budgets required")
    specs = []
    for repeat in range(repeats):
        for index, position in enumerate(positions):
            ordered_budgets = budgets if (index + repeat) % 2 == 0 else budgets[::-1]
            offset = (index + repeat) % len(VARIANTS)
            ordered_variants = VARIANTS[offset:] + VARIANTS[:offset]
            for budget in ordered_budgets:
                for variant, agent in ordered_variants:
                    specs.append(
                        benchmark_spec_from_dict(
                            {
                                "name": variant,
                                "seed": 20261017,
                                "budget": {"kind": "nodes", "value": budget},
                                "agent": agent,
                                "positions": [position],
                            }
                        )
                    )
    # Duplicate names or equivalent input positions must not inflate sample size.
    first_positions = tuple(
        specs[i * len(budgets) * len(VARIANTS)].positions[0]
        for i in range(len(positions))
    )
    replace(specs[0], positions=first_positions)
    keys = [" ".join(chess.Board(p.fen).fen().split()[:4]) for p in first_positions]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate input positions")
    return tuple(specs)


def run_tactical(
    prepared: Path,
    output: Path,
    *,
    split: str,
    budgets: tuple[int, ...],
    repeats: int,
    max_seconds: float,
    repository: Path,
    resume: bool = False,
    protocol: Path | None = None,
) -> dict[str, object]:
    """Run a verified split, persisting every case; resume identical source only.

    The runtime cap is checked between searches, so one search may overrun it.
    Completed-case files survive interruption. Failures remain recorded rather
    than being silently retried on resume. Source snapshots cover dirty changes.
    """
    if (
        split not in {"development", "validation", "test"}
        or not math.isfinite(max_seconds)
        or max_seconds <= 0
    ):
        raise ValueError("valid split and positive runtime cap required")
    if split == "test" and protocol is None:
        raise ValueError("held-out execution requires an explicit frozen protocol")
    protocol_bytes = protocol.read_bytes() if protocol is not None else None
    preparation = json.loads((prepared / "manifest.json").read_text())
    payload = (prepared / f"{split}.json").read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != preparation["split_sha256"][split]:
        raise ValueError("split digest mismatch")
    puzzles = json.loads(payload)
    positions = [
        {key: p[key] for key in ("name", "fen", "expected_moves")} for p in puzzles
    ]
    specs = tactical_specs(positions, budgets, repeats)
    paths = sorted((repository / "src").rglob("*.py"))
    paths += [repository / "pyproject.toml", repository / "uv.lock"]
    sources = {p.relative_to(repository).as_posix(): p.read_bytes() for p in paths}
    plan = {
        "schema_version": 1,
        "split": split,
        "split_sha256": digest,
        "protocol_sha256": (
            hashlib.sha256(protocol_bytes).hexdigest()
            if protocol_bytes is not None
            else None
        ),
        "preparation": preparation,
        "budgets": budgets,
        "repeats": repeats,
        "case_digests": [s.digest for s in specs],
        "code_sha256": {
            name: hashlib.sha256(data).hexdigest() for name, data in sources.items()
        },
        "order": "repeat, source position, alternating budget order, rotating variant",
    }
    plan_digest = configuration_digest(plan)
    metadata: dict[str, object]
    if resume:
        stored = json.loads((output / "plan.json").read_text())
        if configuration_digest(stored) != plan_digest:
            raise ValueError("resume plan/source/data differs from original run")
        metadata = json.loads((output / "metadata.json").read_text())
    else:
        output.mkdir(parents=True, exist_ok=False)
        (output / "cases").mkdir()
        write_artifact_json(output / "plan.json", plan)
        write_artifact_json(output / "positions.json", puzzles)
        if protocol_bytes is not None:
            (output / "protocol.md").write_bytes(protocol_bytes)
        for name, data in sources.items():
            destination = output / "sources" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        metadata = capture_run_metadata(
            repository, output.name, plan_digest, len(specs)
        )
    metadata.update(status="running", error=None, active_case=None)
    metadata["runtime_cap_seconds_per_invocation"] = max_seconds
    started = perf_counter()
    failed = False
    written = 0
    metadata["runs_written"] = written
    try:
        for index, spec in enumerate(specs):
            destination = output / "cases" / f"{index:06d}.json"
            if destination.exists():
                recorded = json.loads(destination.read_text())
                if recorded["spec"] != spec.to_dict():
                    raise ValueError("existing case does not match scheduled spec")
                failed |= any(c["status"] != "completed" for c in recorded["cases"])
                written += 1
                metadata["runs_written"] = written
                continue
            metadata["active_case"] = index
            if perf_counter() - started >= max_seconds:
                metadata["status"] = "capped"
                break
            write_artifact_json(output / "metadata.json", metadata, replace=True)
            # New provenance timestamp per case; source identity comes from plan.
            case_provenance = capture_provenance(repository, spec.digest)
            result = run_benchmark(spec, case_provenance)
            write_artifact_json(destination, result.to_dict())
            failed |= any(c.status != "completed" for c in result.cases)
            written += 1
            metadata["runs_written"] = written
        else:
            metadata["status"] = "failed" if failed else "completed"
    except KeyboardInterrupt:
        metadata.update(status="interrupted", error="KeyboardInterrupt")
        raise
    except Exception as error:
        metadata.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        if metadata["status"] == "completed":
            metadata["active_case"] = None
        metadata["invocation_elapsed_seconds"] = perf_counter() - started
        write_artifact_json(output / "metadata.json", metadata, replace=True)
    return metadata


def main(argv: Sequence[str] | None = None) -> int:
    """Run only an explicitly selected split; no implicit held-out execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--split", choices=["development", "validation", "test"], required=True
    )
    parser.add_argument("--budgets", type=int, nargs="+", default=[1000, 5000, 20000])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-seconds", type=float, default=3600)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--protocol", type=Path, help="required for held-out test runs")
    args = parser.parse_args(argv)
    try:
        metadata = run_tactical(
            args.prepared,
            args.output,
            split=args.split,
            budgets=tuple(args.budgets),
            repeats=args.repeats,
            max_seconds=args.max_seconds,
            repository=Path.cwd(),
            resume=args.resume,
            protocol=args.protocol,
        )
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(metadata, indent=2))
    return 0 if metadata["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
