# Project status

Last updated: 2026-09-01

## Current milestone

Milestone 0: repository and environment scaffold. The scaffold is implemented
and verified.

## Implemented

- Minimal `src`-layout Python package.
- Project and development dependency declarations for `uv`.
- Configuration for pytest, Ruff, and mypy.
- A package-import smoke test.
- Initial repository guidance and ignore rules.

## Verification

Verified on Windows with CPython 3.12.14 and `uv` 0.12.8:

- `uv sync`: passed; 18 locked packages are installed.
- `uv run pytest`: passed; 1 test passed.
- `uv run ruff check .`: passed.
- `uv run mypy src`: passed; no issues found in 1 source file.

## Planned, not implemented

- Game-state and agent contracts.
- A `python-chess` state adapter and chess correctness suite.
- Search budgets, agents, match execution, and experiment logging.
- Classical search baselines.
- Learned models, MCTS experiments, datasets, interfaces, and deployment.

## Open decisions

- The long-term research branch will be selected only after the common
  infrastructure and classical baseline provide evidence for a decision.
