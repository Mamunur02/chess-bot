"""Manifest-driven baseline comparisons with incremental, auditable artifacts."""

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from chesslab.benchmark import benchmark_spec_from_dict
from chesslab.config import (
    json_object as _object,
)
from chesslab.config import (
    nonempty_string as _text,
)
from chesslab.config import (
    reject_unknown_fields as _keys,
)
from chesslab.eval.artifacts import (
    capture_run_metadata,
    configuration_digest,
    write_artifact_json,
)
from chesslab.eval.benchmarks import (
    BenchmarkResult,
    BenchmarkSpec,
    capture_provenance,
    run_benchmark,
)


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    """Validated common inputs and a variant-by-seed grid, in execution order.

    Construct through ``experiment_manifest_from_dict``. The first variant is
    the paired reference; each specification embeds the same ordered dataset.
    """

    name: str
    question: str
    dataset_id: str
    dataset_version: str
    dataset_split: str
    dataset_source: str
    variants: tuple[str, ...]
    specs: tuple[BenchmarkSpec, ...]

    def to_dict(self) -> dict[str, object]:
        first = self.specs[0].to_dict()
        return {
            "schema_version": 1,
            "name": self.name,
            "question": self.question,
            "dataset": {
                "id": self.dataset_id,
                "version": self.dataset_version,
                "split": self.dataset_split,
                "source": self.dataset_source,
                "positions": first["positions"],
            },
            "budget": first["budget"],
            "seeds": [s.seed for s in self.specs if s.name == self.variants[0]],
            "variants": [
                {
                    "name": name,
                    "agent": next(
                        s for s in self.specs if s.name == name
                    ).agent.to_dict(),
                }
                for name in self.variants
            ],
        }

    @property
    def digest(self) -> str:
        """Identity of the normalized manifest, including dataset metadata."""
        return configuration_digest(self.to_dict())


def experiment_manifest_from_dict(value: object) -> ExperimentManifest:
    """Validate one explicit comparison grid; reject silent configuration typos."""
    data = _object(value, "manifest")
    _keys(
        data,
        {
            "schema_version",
            "name",
            "question",
            "dataset",
            "budget",
            "seeds",
            "variants",
        },
        "manifest",
    )
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    name = _text(data.get("name"), "name")
    question = _text(data.get("question"), "question")
    dataset = _object(data.get("dataset"), "dataset")
    _keys(dataset, {"id", "version", "split", "source", "positions"}, "dataset")
    dataset_id = _text(dataset.get("id"), "dataset.id")
    dataset_version = _text(dataset.get("version"), "dataset.version")
    dataset_source = _text(dataset.get("source"), "dataset.source")
    split = _text(dataset.get("split"), "dataset.split")
    if split not in {"development", "validation", "test"}:
        raise ValueError("dataset.split must be development, validation, or test")
    seeds = data.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(type(s) is not int for s in seeds)
    ):
        raise ValueError("seeds must be a non-empty array of integers")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique")
    variants = data.get("variants")
    if not isinstance(variants, list) or len(variants) < 2:
        raise ValueError("at least two variants are required")
    budget = _object(data.get("budget"), "budget")
    _keys(budget, {"kind", "value"}, "budget")
    positions = dataset.get("positions")
    if not isinstance(positions, list):
        raise ValueError("dataset.positions must be an array")
    for position in positions:
        _keys(
            _object(position, "position"), {"name", "fen", "expected_moves"}, "position"
        )
    specs: list[BenchmarkSpec] = []
    names: list[str] = []
    for variant in variants:
        item = _object(variant, "variant")
        _keys(item, {"name", "agent"}, "variant")
        variant_name = _text(item.get("name"), "variant.name")
        if variant_name in names:
            raise ValueError("variant names must be unique")
        names.append(variant_name)
        agent = _object(item.get("agent"), "agent")
        _keys(
            agent,
            {"kind", "capture_ordering", "transposition_table", "quiescence_depth"},
            "agent",
        )
        for seed in seeds:
            specs.append(
                benchmark_spec_from_dict(
                    {
                        "name": variant_name,
                        "seed": seed,
                        "budget": budget,
                        "agent": agent,
                        "positions": positions,
                    }
                )
            )
    # FEN-only inputs contain no repetition history. Reject duplicate positions
    # even if only the fullmove number or case name differs.
    identities = [" ".join(p.fen.split()[:5]) for p in specs[0].positions]
    if len(set(identities)) != len(identities):
        raise ValueError("dataset contains duplicate FEN positions")
    return ExperimentManifest(
        name,
        question,
        dataset_id,
        dataset_version,
        split,
        dataset_source,
        tuple(names),
        tuple(specs),
    )


def summarize_experiment(
    manifest: ExperimentManifest, results: Sequence[BenchmarkResult]
) -> dict[str, object]:
    """Aggregate observed counts and paired deltas without dropping failures.

    Repeated seeds are repeated executions, not independent chess positions.
    No confidence interval or playing-strength inference is made here.
    """
    expected = {(spec.name, spec.seed): spec for spec in manifest.specs}
    observed: dict[tuple[str, int], BenchmarkResult] = {}
    for result in results:
        key = (result.spec.name, result.spec.seed)
        if key in observed or key not in expected:
            raise ValueError("unexpected or duplicate experiment run")
        if result.spec.digest != expected[key].digest:
            raise ValueError("run specification does not match manifest")
        observed[key] = result
    rows: list[dict[str, object]] = []
    for name in manifest.variants:
        runs = [r for r in results if r.spec.name == name]
        cases = [case for run in runs for case in run.cases]
        decisions = [case.decision for case in cases if case.decision is not None]
        scored = sum(bool(p.expected_moves) for p in manifest.specs[0].positions)
        rows.append(
            {
                "variant": name,
                "runs_recorded": len(runs),
                "runs_planned": sum(s.name == name for s in manifest.specs),
                "cases_completed": sum(c.status == "completed" for c in cases),
                "cases_failed": sum(c.status == "failed" for c in cases),
                "scored_cases_attempted": scored * len(runs),
                "expected_move_matches": sum(
                    c.expected_move_match is True for c in cases
                ),
                "total_nodes": sum(c.decision.nodes for c in cases if c.decision),
                "total_quiescence_nodes": sum(d.quiescence_nodes for d in decisions),
                "total_transposition_hits": sum(
                    d.transposition_hits for d in decisions
                ),
                "total_cutoffs": sum(d.cutoffs for d in decisions),
                "min_completed_depth": min((d.depth for d in decisions), default=None),
                "max_completed_depth": max((d.depth for d in decisions), default=None),
                "depth_zero_decisions": sum(d.depth == 0 for d in decisions),
                "total_case_elapsed_seconds": sum(c.elapsed_seconds for c in cases),
            }
        )
    reference = manifest.variants[0]
    pairs: list[dict[str, object]] = []
    for name in manifest.variants[1:]:
        comparable = unavailable = changed = node_delta = match_delta = 0
        depth_delta = 0
        seconds_delta = 0.0
        for spec in manifest.specs:
            if spec.name != reference:
                continue
            left = observed.get((reference, spec.seed))
            right = observed.get((name, spec.seed))
            if left is None or right is None:
                unavailable += len(spec.positions)
                continue
            for a, b in zip(left.cases, right.cases, strict=True):
                if a.decision is None or b.decision is None:
                    unavailable += 1
                    continue
                comparable += 1
                changed += a.decision.action != b.decision.action
                node_delta += b.decision.nodes - a.decision.nodes
                depth_delta += b.decision.depth - a.decision.depth
                seconds_delta += b.elapsed_seconds - a.elapsed_seconds
                match_delta += int(b.expected_move_match is True) - int(
                    a.expected_move_match is True
                )
        pairs.append(
            {
                "reference": reference,
                "variant": name,
                "comparable_cases": comparable,
                "unavailable_cases": unavailable,
                "changed_actions": changed,
                "node_delta": node_delta,
                "completed_depth_delta": depth_delta,
                "case_elapsed_seconds_delta": seconds_delta,
                "expected_move_match_delta": match_delta,
            }
        )
    return {"manifest_digest": manifest.digest, "variants": rows, "pairs": pairs}


def run_experiment(
    manifest: ExperimentManifest, output: Path, repository: Path
) -> dict[str, object]:
    """Run a fresh grid, preserving raw results and interrupted/failed status.

    Existing output directories are never reused. Run filenames use numeric
    indices rather than caller-supplied variant names.
    """
    output.mkdir(parents=True, exist_ok=False)
    results: list[BenchmarkResult] = []
    metadata = capture_run_metadata(
        repository, output.name, manifest.digest, len(manifest.specs)
    )
    write_artifact_json(output / "manifest.json", manifest.to_dict())
    write_artifact_json(output / "metadata.json", metadata)
    (output / "runs").mkdir()
    try:
        for index, spec in enumerate(manifest.specs):
            result = run_benchmark(spec, capture_provenance(repository, spec.digest))
            write_artifact_json(output / "runs" / f"{index:04d}.json", result.to_dict())
            results.append(result)
            metadata["runs_written"] = len(results)
            write_artifact_json(output / "metadata.json", metadata, replace=True)
        metadata["status"] = (
            "failed"
            if any(c.status == "failed" for r in results for c in r.cases)
            else "completed"
        )
    except KeyboardInterrupt:
        metadata["status"] = "interrupted"
        metadata["error"] = "KeyboardInterrupt: execution interrupted"
        raise
    except Exception as error:
        metadata["status"] = "failed"
        metadata["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        write_artifact_json(
            output / "summary.json", summarize_experiment(manifest, results)
        )
        write_artifact_json(output / "metadata.json", metadata, replace=True)
    return metadata


def main(argv: Sequence[str] | None = None) -> int:
    """Run one manifest. Exit 1 on case failures, 130 on interruption."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path, help="fresh artifact directory")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        manifest = experiment_manifest_from_dict(
            json.loads(args.manifest.read_text(encoding="utf-8"))
        )
        metadata = run_experiment(manifest, args.output, args.repository)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0 if metadata["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
