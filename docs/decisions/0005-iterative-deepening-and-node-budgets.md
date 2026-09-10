# Decision 0005: Iterative deepening and node budgets

Date: 2026-09-10

## Status

Accepted for Milestone 5.

## Context

Controlled comparisons need a machine-independent compute limit as well as a
fixed-depth mode. Iterative deepening must expose all work it performs rather
than reporting only the final pass, and an interrupted iteration must not
silently replace a fully evaluated shallower decision.

## Decision

- A depth budget performs complete alpha-beta iterations from depth one through
  the requested depth.
- A node budget applies cumulatively across every iteration. The root and every
  entered descendant count as one node, matching the Milestone 4 convention.
- Search checks the budget before entering a node and never exceeds it.
- If a node limit interrupts an iteration, its nodes and cutoffs remain in the
  reported totals, but its partial decision is discarded.
- The action, value, depth, and principal variation come from the last fully
  completed iteration.
- If depth one cannot complete, search returns the first legal action, a static
  evaluation of the already-counted root, completed depth zero, and zero
  completed iterations. This keeps tiny positive node budgets usable without
  presenting partial root search as a complete comparison.
- Search stops early under a node budget when the explored game tree is solved
  without reaching the heuristic horizon.
- Legal-action order remains unchanged. Iterative deepening does not yet imply
  principal-variation move ordering.
- Reported nodes and alpha-beta cutoffs are totals across completed and partial
  iterations. The principal variation belongs to the last completed iteration.
- The material alpha-beta agent accepts both `DepthBudget` and `NodeBudget`;
  it remains deterministic and does not consume its caller-owned RNG.

## Consequences

Depth-budget results do more total work than a single fixed-depth alpha-beta
call because shallower iterations are included. Node-budget comparisons are
exact with respect to entered search nodes, but evaluator cost and legal-move
