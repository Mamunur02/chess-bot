"""Results produced by deterministic search agents."""

from dataclasses import dataclass

from chesslab.agents.protocols import AgentDecision


@dataclass(frozen=True, slots=True)
class SearchResult[ActionT](AgentDecision[ActionT]):
    """A fixed-depth action choice and its directly measured search data."""

    value: int
    nodes: int
    depth: int
