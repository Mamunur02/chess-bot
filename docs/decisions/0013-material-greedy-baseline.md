# ADR 0013: Material-greedy baseline

## Status

Accepted.

## Context

The implementation guide calls for random, material-greedy, and alpha-beta
baselines. Random and alpha-beta agents exist, but using depth-one alpha-beta
implicitly as the greedy comparator obscures the intended experimental role.
The benchmark harness also needs an explicit way to select the simplest
chess-specific baseline.

## Decision

Add `MaterialGreedyAgent` as a named deterministic one-ply baseline. It
evaluates every legal child using the existing material evaluator and fixed
terminal scoring, preserving `python-chess` legal-action order for ties.

The agent accepts the common `SearchBudget` and caller-owned RNG to satisfy the
agent contract, but consumes neither. Its computation is always exactly one
ply; the returned search result reports the root and evaluated children as
visited nodes.

The benchmark agent configuration gains an explicit `kind` field:

- `material_alpha_beta`, which remains the default for compatibility;
- `material_greedy`, which rejects capture-ordering, transposition-table, and
  quiescence switches.

The normalized agent kind is included in the benchmark configuration digest.

## Consequences

- Future evaluations can distinguish random choice, greedy material choice,
  and deeper alpha-beta search without relying on implicit depth conventions.
- Immediate mates and draws are scored as outcomes rather than material.
- Greedy tie breaking is deterministic and inspectable.
- Larger supplied budgets do not change greedy decisions or work, so greedy is
  a behavioural baseline rather than an equal-budget search configuration.
- No new evaluator term, tuning constant, or research hypothesis is introduced.

This baseline does not perform opponent-response search, quiescence, caching,
or move ordering. It should not be interpreted as a strong chess engine.

## Validation

Tests cover protocol compatibility, a free material capture, preference for
immediate mate, independence from budget and RNG, stable tie order, terminal
and non-chess errors, explicit benchmark execution, and rejection of
incompatible benchmark switches.
