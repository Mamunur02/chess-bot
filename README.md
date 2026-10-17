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
- a minimal synchronous UCI interface;
- a JSON benchmark tool that records the configuration, seeds, Git state,
  environment, moves, search statistics, timings, and failures; and
- a manifest-driven ablation runner with dataset versions, dependency lock
  hashes, incremental artifacts, paired summaries, and interruption records; and
- a head-to-head suite runner with swapped agent colours, raw game records,
  win/draw/loss counts, and explicit incomplete-pair coverage.

The engine currently evaluates positions using material only. It does not yet
contain a learned model, MCTS, or a training pipeline. I have completed a first
held-out study on 200 versioned Lichess tactical positions, comparing four search
configurations at three node budgets with three timing passes. I have not
measured or claimed an Elo rating or a general playing-strength improvement.

The [first study memo](reports/tactical-study-v1/research-memo.md) reports the
quality/runtime trade-offs, paired uncertainty and recording interruptions.
At 5,000 nodes, capture ordering matched 137/200 accepted first moves versus
127/200 for plain search, at a median paired runtime ratio of 2.24x. This measures
first-move solution agreement, not complete puzzle solving or Elo. The
[data/protocol guide](docs/tactical-data.md) describes reproduction and provenance.

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

Run the versioned development ablation with:

```powershell
uv run python -m chesslab.experiment experiments/manifests/development-ablation.json artifacts/development-ablation-001
```

Use a new artifact directory for each run. See
[`docs/experiment-format.md`](docs/experiment-format.md) for the manifest,
failure handling, and interpretation. The example uses development fixtures
from correctness tests; it is not a held-out strength benchmark.

Run the synthetic head-to-head bookkeeping example with:

```powershell
uv run python -m chesslab.match_suite experiments/manifests/development-matches.json artifacts/development-matches-001
```

See [`docs/match-suite-format.md`](docs/match-suite-format.md) for colour pairing,
game outcomes, and failure handling. Random and greedy are behavioural
comparators; they do not consume the supplied search budget. This example uses
near-mate fixtures and does not establish playing strength.

## Next steps

The classical baseline, first versioned tactical dataset, held-out comparison
and external UCI match integration are implemented and verified. A local four-game
colour-paired smoke comparison against Stockfish 19 completed with four Stockfish
wins and no final-run failures; this does not establish Elo. See the
[measured summary](experiments/summaries/external-stockfish19-20261017.md) and
[external opponent guide](docs/external-opponents.md). Shared internal/external
tactical evaluation is also working: a ten-position development smoke measured
6/10 accepted first moves for plain alpha-beta and 10/10 for Stockfish, without
failures. These observed development inputs support no held-out accuracy claim.
See the [shared tactics report](experiments/summaries/shared-development-tactics-20261017.md).
The next decision is the first learned method; see the
[bounded options](docs/research/first-learned-bot-decision.md). The precise research question is still developing.
No learning method has been implemented yet. I will keep the first result frozen
and use fresh confirmatory positions for later comparisons.

The first development-only ablation is recorded in
[`experiments/summaries/development-ablation-20261006.md`](experiments/summaries/development-ablation-20261006.md).

The longer-term research direction is still open.
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
- [`docs/experiment-format.md`](docs/experiment-format.md) describes repeatable
  baseline comparisons and artifact provenance.
- [`docs/match-suite-format.md`](docs/match-suite-format.md) describes reproducible
  head-to-head games, colour pairing, and outcome metrics.
- [`CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`](CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md)
  contains the broader roadmap and research standards.
