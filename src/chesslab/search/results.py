"""Results produced by deterministic search agents."""

from dataclasses import dataclass

from chesslab.agents.protocols import AgentDecision


@dataclass(frozen=True, slots=True)
class SearchResult[ActionT](AgentDecision[ActionT]):
    """An action choice and directly measured deterministic search data."""

    value: int
    nodes: int
    depth: int
    principal_variation: tuple[ActionT, ...] = ()
    cutoffs: int = 0
    iterations: int = 1
    transposition_hits: int = 0
