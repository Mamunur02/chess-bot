# Decision 0007: Generic transposition-table baseline

Date: 2026-09-10

## Status

Accepted for Milestone 7.

## Context

Repeated states can cause alpha-beta to search the same subtree more than once.
Caching can reduce that work, but only if state identity includes every rule
that affects future outcomes. In chess, a FEN string does not contain repetition
history and is therefore not a sound key under the adapter's automatic
fivefold-repetition semantics.

## Decision

- Alpha-beta and iterative-deepening search accept an optional caller-supplied
  state-key callback.
- Supplying no key disables caching and preserves the previous baseline.
- A table is local to one public search call. No mutable cache persists between
  moves, matches, or experiments.
- Cache identity combines the caller's state key with remaining search depth.
- Entries record exact values or standard lower and upper bounds based on the
  node's original alpha-beta window.
- Exact entries can return immediately. Bound entries tighten the search window
  and return only when they prove a cutoff.
- A cache hit still counts as an entered node, while descendants avoided by the
  hit are not counted.
- Search results report the total number of cache hits across all complete and
  partial iterative-deepening passes.
- The caller is responsible for supplying a hashable key that captures all
  state semantics relevant to future play.
- The material chess agent does not enable the table yet. A history-safe chess
  key must be designed and tested before integration; current FEN serialization
  is explicitly insufficient.

## Consequences

The generic implementation can be tested honestly on artificial game graphs
with known transpositions. A diamond-tree fixture demonstrates an identical
action, value, and principal variation with fewer entered nodes. That fixture
is a correctness measurement, not evidence of improved chess strength.

Bound-aware entries support normal alpha-beta windows without treating a cutoff
value as exact. Table memory is unbounded within one search call for now; size
