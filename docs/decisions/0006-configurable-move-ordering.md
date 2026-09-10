# Decision 0006: Configurable move ordering

Date: 2026-09-10

## Status

Accepted for Milestone 6.

## Context

Alpha-beta pruning depends on traversal order. The baseline needs a small,
controlled way to compare ordering policies without changing minimax semantics
or silently enabling an optimization in every agent.

## Decision

- Alpha-beta and iterative-deepening search accept an optional action-ordering
  callback.
- No orderer remains the default, preserving the legal-action order and the
  Milestone 4 reference behaviour.
- An orderer receives the state and its legal actions and must return every
  legal action exactly once. Search rejects omitted, duplicated, or unknown
  actions.
- The material chess agent exposes an explicit `capture_ordering` flag.
- When enabled, captures are searched before non-captures. Python's stable sort
  preserves the adapter's original order within both groups.
- Chess capture classification delegates to `python-chess`, including its
  en-passant semantics, without exposing the private mutable board.
- Ordering does not consume randomness and is applied independently at every
  entered non-terminal search node.
- Principal-variation ordering, killer moves, history heuristics, and
  transposition-table hints are not included in this milestone.

## Consequences

The unconfigured search remains directly comparable with the existing
baseline. Artificial-tree tests demonstrate that a better order can preserve
the selected action and value while reducing entered nodes, but this is a
correctness fixture rather than evidence of chess-playing strength. Capture
