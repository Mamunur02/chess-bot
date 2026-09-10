"""Command-line entry point for fixed-budget chess benchmarks."""

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from chesslab.eval.benchmarks import (
    BenchmarkAgentConfig,
    BenchmarkPosition,
    BenchmarkSpec,
    capture_provenance,
    run_benchmark,
)
from chesslab.search import DepthBudget, NodeBudget, SearchBudget, TimeBudget


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    return value


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _budget(value: object) -> SearchBudget:
    data = _mapping(value, "budget")
    kind = _string(data.get("kind"), "budget.kind")
    amount = _integer(data.get("value"), "budget.value")
    if kind == "depth":
        return DepthBudget(amount)
    if kind == "nodes":
        return NodeBudget(amount)
    if kind == "milliseconds":
        return TimeBudget(amount)
    raise ValueError("budget.kind must be depth, nodes, or milliseconds")


def _agent(value: object) -> BenchmarkAgentConfig:
    data = _mapping(value, "agent")
    return BenchmarkAgentConfig(
        capture_ordering=_boolean(
            data.get("capture_ordering", False), "agent.capture_ordering"
        ),
        transposition_table=_boolean(
            data.get("transposition_table", False), "agent.transposition_table"
        ),
        quiescence_depth=_integer(
            data.get("quiescence_depth", 0), "agent.quiescence_depth"
        ),
    )


def _positions(value: object) -> tuple[BenchmarkPosition, ...]:
    if not isinstance(value, list):
        raise ValueError("positions must be a JSON array")
    positions: list[BenchmarkPosition] = []
    for index, raw_position in enumerate(value):
        data = _mapping(raw_position, f"positions[{index}]")
        raw_expected = data.get("expected_moves", [])
        if not isinstance(raw_expected, list) or not all(
            isinstance(move, str) for move in raw_expected
        ):
            raise ValueError(f"positions[{index}].expected_moves must be strings")
        positions.append(
            BenchmarkPosition(
                name=_string(data.get("name"), f"positions[{index}].name"),
                fen=_string(data.get("fen"), f"positions[{index}].fen"),
                expected_moves=tuple(raw_expected),
            )
        )
    return tuple(positions)


def benchmark_spec_from_dict(value: object) -> BenchmarkSpec:
    """Validate and construct a benchmark specification from JSON data."""
    data = _mapping(value, "configuration")
    return BenchmarkSpec(
        name=_string(data.get("name"), "name"),
        seed=_integer(data.get("seed"), "seed"),
        budget=_budget(data.get("budget")),
        agent=_agent(data.get("agent", {})),
        positions=_positions(data.get("positions")),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="input JSON configuration")
    parser.add_argument("output", type=Path, help="output JSON result")
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path.cwd(),
        help="Git repository used for provenance (default: current directory)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Load configuration, run the benchmark, and write structured JSON."""
    arguments = _parser().parse_args(argv)
    try:
        if arguments.output.exists():
            raise ValueError(f"output already exists: {arguments.output}")
        raw_config = json.loads(arguments.config.read_text(encoding="utf-8"))
        spec = benchmark_spec_from_dict(raw_config)
        provenance = capture_provenance(arguments.repository, spec.digest)
        result = run_benchmark(spec, provenance)
        arguments.output.write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        _parser().error(str(error))
    return 0
