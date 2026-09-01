# Chess AI Lab

Chess AI Lab is a work-in-progress research platform for controlled comparisons
of game-playing methods. The initial focus is trustworthy infrastructure and
classical chess baselines; the longer-term research direction has not yet been
selected.

The project has completed **Milestone 2**. It provides typed game and agent
contracts, explicit search budgets, and a tested `python-chess` state adapter.
It does not yet implement a concrete agent, search algorithm, learned model,
experiment runner, or user interface.

## Development setup

The project uses Python 3.12 and
[`uv`](https://docs.astral.sh/uv/) for dependency management.

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

See `docs/status.md` for the current implementation status and
`CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md` for the broader roadmap.

## Research integrity

Planned features and hypotheses are not results. Future experiments will record
their configuration, random seeds, software state, computational budgets, and
failures so that reported findings can be reproduced and defended.
