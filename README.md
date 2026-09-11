# Chess Agent Project

I'm building a chess agent and a reproducible framework for testing it. The
current focus is a trustworthy classical baseline: correct chess rules, simple
agents, alpha-beta search, controlled compute budgets, and enough logging to
support honest comparisons.

My goal is not just to make the strongest engine I can. I want to understand
which changes improve performance, what they cost, and whether the result holds
across different positions and runs.

## Current state

So far, I have built:

- a chess-state layer using `python-chess` for legal moves and game rules;
- tests for perft, terminal positions, castling, en passant, promotion,
  repetition, draws, and illegal moves;
- typed interfaces for games, agents, and depth, node, or time budgets;
- seeded random, one-ply material-greedy, and material alpha-beta agents;
- exhaustive minimax for checking shallow search results;
- iterative-deepening alpha-beta search with principal variations;
- optional move ordering, transposition tables, and bounded quiescence search;
- deterministic match execution with structured results and failure records;
- a minimal synchronous UCI interface; and
- a JSON benchmark tool that records the configuration, seeds, Git state,
  environment, moves, search statistics, timings, and failures.

The engine currently evaluates positions using material only. It does not yet
contain a learned model, MCTS, a training pipeline, or a substantive benchmark
dataset. I have not measured or claimed an Elo rating or any other formal
strength result.

## How I will evaluate performance

I will use several kinds of evaluation rather than reduce the project to one
number.

The current tools already record:

- the selected move and, when supplied, whether it matches a reviewed set of
  accepted moves;
- the search value, completed depth, iterations, and principal variation;
- total nodes, quiescence nodes, alpha-beta cutoffs, and transposition-table
  hits;
- elapsed search time;
- match outcomes, ply counts, interruptions, and failures; and
- the budget, configuration, seed, Git commit, Python version, and host
  environment for each benchmark run.

For controlled baseline comparisons, I plan to use fixed node budgets as the
primary compute limit because they are easier to compare across machines than
wall-clock limits. The broader baseline evaluation will include:

- accuracy on a versioned, held-out set of tactical positions;
- endgame correctness where reliable reference answers are available;
- head-to-head win, draw, and loss results;
- search efficiency and depth reached under fixed budgets;
- ablations of move ordering, transposition tables, and quiescence search; and
- uncertainty estimates when there are enough observations to support them.

I may report Elo later if I have a defensible match setup and enough games. I
will keep positions used for development or tuning separate from final test
positions, and I will not present expected-move agreement as a complete measure
of playing strength.

## Running the current baseline

The project requires Python 3.12 and uses
[`uv`](https://docs.astral.sh/uv/) for dependency management.

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

Start the UCI engine with:

```powershell
uv run chesslab-uci
```

Run a benchmark from a reviewed JSON configuration with:

```powershell
uv run chesslab-benchmark config.json result.json
```

See [`docs/benchmark-format.md`](docs/benchmark-format.md) for the input and
output format.

## Next steps

Before moving beyond the baseline, I still need to:

- select and version a substantive benchmark dataset;
- define separate tuning and held-out test splits;
- add experiment manifests and a clear artifact layout; and
- produce repeatable summaries across multiple runs.

Once that foundation is ready, I will choose a more focused research direction.
The options I am considering include:

- replacing or extending the handcrafted evaluator with a learned evaluator
  while keeping the alpha-beta search framework fixed;
- modelling human move choices, possibly conditioned on player strength;
- comparing MCTS variants across games under controlled budgets;
- experimenting with small-scale self-play after testing the learning loop in a
  simpler game; and
- exploring a tool-using language-model layer around a legal chess engine.

These are possible directions, not completed features or claims of novelty. I
have not selected the final direction yet.

## Documentation

- [`docs/status.md`](docs/status.md) tracks what is currently implemented and
  verified.
- [`docs/benchmark-format.md`](docs/benchmark-format.md) describes the benchmark
  format and its current limitations.
- [`CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`](CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md)
  contains the broader roadmap and research standards.
