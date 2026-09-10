"""Contracts for agents that select actions in supported games."""

from chesslab.agents.material_greedy import MaterialGreedyAgent
from chesslab.agents.protocols import Agent, AgentDecision
from chesslab.agents.random_agent import RandomAgent

__all__ = ["Agent", "AgentDecision", "MaterialGreedyAgent", "RandomAgent"]
