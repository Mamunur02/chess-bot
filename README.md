# Chess AI Lab

Chess AI Lab is a work-in-progress research platform for controlled comparisons
of game-playing methods. The initial focus is trustworthy infrastructure and
classical chess baselines; the longer-term research direction has not yet been
selected.

The project has completed **Milestone 12**. It provides typed game and agent
contracts, a tested `python-chess` state adapter, deterministic match execution,
and a transparent material-based alpha-beta baseline checked against exhaustive
shallow minimax. The baseline supports iterative deepening under depth, exact
node, or wall-clock budgets, reports search timing and statistics, and offers
opt-in deterministic capture-first move ordering. Generic alpha-beta search
also supports a caller-keyed, per-search transposition table with hit statistics
and bounded quiescence extensions supplied by the caller. The material chess
agent can enable repetition-aware caching and a capture-and-promotion
quiescence baseline. A minimal synchronous UCI subset exposes the engine to
standard input and output. A JSON-configured fixed-budget harness records raw
search measurements and reproducibility metadata. No substantive benchmark
dataset, learned model, research experiment, or graphical interface is included.

## UCI baseline

After `uv sync`, start the engine with:

```powershell
uv run chesslab-uci
```

## Benchmark harness

Supply a reviewed JSON configuration and a new output path:

```powershell
uv run chesslab-benchmark config.json result.json
```

See `docs/benchmark-format.md` before creating benchmark configurations.

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
