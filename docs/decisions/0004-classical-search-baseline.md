# Decision 0004: Classical search baseline

Date: 2026-09-02

## Status

Accepted for Milestone 4.

## Context

The first meaningful chess baseline needs transparent evaluation and search
semantics that can also be checked on tiny deterministic games. Correct player
perspective, terminal handling, depth interpretation, and node measurement are
more important here than playing strength.

## Decision

- Material is scored in centipawns with pawn 100, knight 320, bishop 330,
  rook 500, queen 900, and king 0. Scores use an explicit stable-player
  perspective; positive values favor that player.
- Chess piece inspection uses an immutable snapshot. The adapter never exposes
  its mutable internal `chess.Board`.
- Reference and alpha-beta search use minimax with a fixed root perspective.
  A node maximizes when its current player is the root player and minimizes
  otherwise.
- Terminal states are scored before the depth cutoff. A root-player win is
  `+1_000_000`, a loss is `-1_000_000`, and a draw is zero.
- A root action consumes one ply, so depth one evaluates immediate children.
  Public action searches require positive depth.
- The root and every entered child count as nodes, including terminal and
  horizon leaves. Nodes skipped by alpha-beta pruning are not counted.
- Legal-action order is preserved and the first equal-valued action wins.
  Search consumes no randomness and performs no implicit move ordering.
- Search results report the action, root-perspective value, visited nodes, and
  completed fixed depth. Principal variations and additional statistics wait
  until they have an immediate consumer and dedicated correctness tests.
- The material alpha-beta agent supports `DepthBudget` only. `NodeBudget` is
  rejected rather than approximated or silently ignored.

## Consequences

The unpruned implementation provides a shallow correctness oracle for
alpha-beta. Node reductions can be measured under identical traversal order,
and chess terminal outcomes cannot be overridden by material. The baseline is
intentionally weak: it has no positional terms, quiescence search, move
ordering, iterative deepening, transposition table, or mate-distance preference.
