"""Explicit, reproducible limits for agent computation."""

from dataclasses import dataclass


def _require_positive_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class DepthBudget:
    """Limit search to a positive maximum depth."""

    depth: int

    def __post_init__(self) -> None:
        _require_positive_integer(self.depth, "depth")


@dataclass(frozen=True, slots=True)
class NodeBudget:
    """Limit search to a positive number of expanded nodes."""

    nodes: int

    def __post_init__(self) -> None:
        _require_positive_integer(self.nodes, "nodes")


type SearchBudget = DepthBudget | NodeBudget
