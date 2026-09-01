# Project status

Last updated: 2026-09-01

## Current milestone

Milestone 3: random agent and match runner. The runner is implemented and
verified, pending user review.

## Implemented

- Minimal `src`-layout Python package.
- Project and development dependency declarations for `uv`.
- Configuration for pytest, Ruff, and mypy.
- A package-import smoke test.
- Initial repository guidance and ignore rules.
- A minimal deterministic, alternating, two-player game-state protocol.
- An agent protocol with an explicit computation budget and caller-owned RNG.
- Positive depth and node budget representations.
- Documented conventions for state transitions, players, terminal returns,
  actions, and randomness.
- A `python-chess` state adapter with private board ownership and
  immutable-looking transitions.
- Explicit chess player, terminal-outcome, optional-draw, and FEN-history
  semantics.
- Fast initial-position perft verification through depth 3.
- Chess fixtures covering terminal outcomes, castling, en passant, promotion,
  repetition, move-count draws, and illegal actions.
- A seeded random agent that uses caller-owned randomness.
- A generic deterministic two-player match runner with independent player RNGs.
- Structured completed, interrupted, and failed match results.
- Caller-defined action encoding and JSON-compatible match serialization.
- Explicit legal-action validation, ply limits, and runtime failure reporting.

## Verification

Milestone 3 was verified on Windows with CPython 3.12.14:

- `uv run pytest`: passed; 51 tests passed.
- `uv run ruff check .`: passed.
- `uv run mypy src`: passed; no issues found in 13 source files.
- `uv run mypy src tests`: passed; no issues found in 20 source files.

## Planned, not implemented

- Full experiment logging and classical search baselines.
- Learned models, MCTS experiments, datasets, interfaces, and deployment.

## Open decisions

- The long-term research branch will be selected only after the common
  infrastructure and classical baseline provide evidence for a decision.
