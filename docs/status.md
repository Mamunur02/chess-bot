# Project status

Last updated: 2026-09-01

## Current milestone

Milestone 2: chess adapter and correctness suite. The adapter is implemented and
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

## Verification

Milestone 2 was verified on Windows with CPython 3.12.14:

- `uv run pytest`: passed; 36 tests passed.
- `uv run ruff check .`: passed.
- `uv run mypy src`: passed; no issues found in 10 source files.
- `uv run mypy src tests`: passed; no issues found in 14 source files.

## Planned, not implemented

- Concrete agents, match execution, and experiment logging.
- Classical search baselines.
- Learned models, MCTS experiments, datasets, interfaces, and deployment.

## Open decisions

- The long-term research branch will be selected only after the common
  infrastructure and classical baseline provide evidence for a decision.
