# ADR 0009: Bounded quiescence search

## Status

Accepted.

## Context

Fixed-depth material search can stop immediately after a superficially
favourable capture and miss a forced recapture just beyond the horizon. The
classical baseline needs a small, inspectable way to reduce this effect without
committing the project to a tuned research policy.

The generic search layer cannot identify tactical game actions itself. Chess
also requires special handling while the side to move is in check, because
static stand-pat evaluation is not a legal alternative to responding.

## Decision

Alpha-beta and iterative-deepening search accept an optional quiescence
selector and a non-negative extension depth. Both are disabled by default. A
positive depth requires a selector, and a selector requires a positive depth.

At an ordinary depth-zero non-terminal node, enabled search:

1. Counts the node as both an ordinary visited node and a quiescence node.
2. Evaluates the static stand-pat score.
3. Validates the selector's actions as a duplicate-free subset of legal
   actions.
4. Searches those actions with alpha-beta until the configured extension depth
   is exhausted.

Quiescence descendants count toward the same node budget as all other search
work. Interrupted iterative-deepening iterations remain in the cumulative
statistics but never replace the last completed decision. The separate
`quiescence_nodes` statistic makes extension work visible. A principal
variation may be longer than its nominal completed depth.

The material chess agent opts in through `quiescence_depth`. Outside check, it
selects captures and promotions. In check, it selects every legal evasion and
disables stand pat. Terminal outcomes are scored before static evaluation.

The existing action-ordering hook also orders selected quiescence actions.
Transposition-table entries are retained only for ordinary depth-positive
nodes; quiescence results are not cached.

## Consequences

- The default agent and generic search behaviour are unchanged.
- The bounded extension catches simple exchange sequences such as a poisoned
  pawn followed by a forced recapture.
- Exact node limits remain comparable because tactical work shares the same
  counter.
- Callers retain responsibility for choosing game-specific tactical actions.
- Quiescence policy is explicit and testable instead of embedded in the generic
  search.

The depth bound is hard. At its final horizon the evaluator is used even if the
side to move remains in check. The baseline does not add checking moves, delta
pruning, static-exchange evaluation, adaptive extensions, or quiescence-table
caching. These are possible future comparison points, not measured
improvements.

## Validation

Artificial-tree tests cover configuration validation, action-subset
validation, extended principal variations, and exact shared-node-budget
stopping. Chess tests cover check detection and a poisoned-pawn horizon case.
The default suite remains deterministic and independent of external engines,
network access, and large data.
