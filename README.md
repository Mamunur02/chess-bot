# Chess Agent Research Project

This repository is a work-in-progress project to build and evaluate a chess
agent. Its immediate purpose is to establish a correct, reproducible classical
baseline; its broader purpose is to support controlled research into how
search, evaluation, learning, and agent design affect game-playing behaviour.

The project is being developed as a research artefact for a Statistics,
Machine Learning, and Artificial Intelligence PhD application. The emphasis is
therefore not just on playing strength, but on transparent methods, controlled
comparisons, reproducible experiments, and conclusions supported by recorded
measurements.

## What has been built

The current implementation provides:

- a tested chess-state layer built on `python-chess`, including legal moves,
  terminal outcomes, repetition-aware state identity, and perft checks;
- typed game and agent interfaces with explicit depth, node, and time budgets;
- seeded random, deterministic one-ply material-greedy, and material
  alpha-beta agents;
- exhaustive minimax as a shallow correctness reference;
- iterative-deepening alpha-beta search with principal variations, move
  ordering, transposition tables, and bounded quiescence search;
- deterministic match execution with structured completion, interruption, and
  failure records;
- a minimal synchronous UCI interface for use by compatible chess tools; and
- a JSON benchmark harness that records configurations, seeds, Git state,
  environment information, per-position decisions, search statistics,
  timings, and failures.

Search optimisations are optional so that they can be compared against the
same underlying material evaluator. Tests cover game semantics and edge cases
such as castling, en passant, promotion, check evasions, repetition, draw
rules, illegal actions, and exact search-budget handling.

This is currently a classical baseline, not a trained chess system. The
repository does not yet include a learned model, training data pipeline, MCTS
implementation, substantive benchmark dataset, Elo estimate, or claimed
research result.

## Evaluation

The evaluation strategy is deliberately multi-axis: no single metric is
sufficient to describe an agent.

For the current classical baseline, the implemented tools can record:

- selected moves and optional agreement with reviewed accepted moves;
- search value, completed depth, iterations, and principal variation;
- nodes searched, quiescence nodes, alpha-beta cutoffs, and transposition-table
  hits;
- elapsed search time;
- match completion, outcomes, ply counts, interruptions, and failures; and
- the budget, configuration, random seed, Git commit and dirty state, Python
  version, and host environment associated with a run.

Formal baseline comparisons will primarily use fixed node budgets because they
are more comparable across machines than wall-clock limits. Planned evaluation
work includes a versioned, held-out collection of positions; tactical accuracy;
endgame correctness where suitable references are available; head-to-head
win/draw/loss results; search efficiency; ablations of move ordering,
transposition tables, and quiescence search; and uncertainty estimates once
sample sizes support them. Elo may be reported later if a defensible match
methodology and enough games are available, but no Elo value is currently
claimed.

Any benchmark data used for tuning will be kept separate from final test data.
The project will define primary metrics and stopping rules before large
experiments, change one major factor at a time where possible, and retain
failures or null results when they are informative.

## Using the current baseline

The project requires Python 3.12 and uses
[`uv`](https://docs.astral.sh/uv/) for dependency management.

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

Start the UCI-compatible engine:

```powershell
uv run chesslab-uci
```

Run the fixed-budget benchmark harness with a reviewed configuration and a new
output path:

```powershell
uv run chesslab-benchmark config.json result.json
```

The input and output schema is documented in
[`docs/benchmark-format.md`](docs/benchmark-format.md).

## What remains to be built

The next baseline work is experimental infrastructure rather than a jump to a
large learning system. It includes selecting and versioning a substantive
benchmark dataset, defining tuning and held-out splits, adding experiment
manifests and artifact organisation, and producing repeatable multi-run
comparison summaries. Further classical evaluation may expose smaller
correctness or search-engineering tasks that should be resolved first.

After that foundation is complete, the research direction will be selected
using evidence about the research question, prior work, data and compute
requirements, implementation risk, evaluation quality, and time to an
informative result. Candidate directions currently under consideration are:

- learned evaluation within alpha-beta search, compared with the handcrafted
  evaluator at fixed compute;
- human-like or strength-conditioned move prediction, evaluated with
  likelihood, accuracy, calibration, and subgroup analyses;
- controlled comparisons of MCTS variants across games whose complexity is
  explicitly characterised;
- small-scale self-play after validating the learning loop in a simpler game;
  and
- a bounded tool-using language-model layer around a legal chess engine,
  treated as an optional interface or agent experiment rather than assumed to
  be the move-selection core.

These are possible research branches, not implemented features or claims of
novelty. A direction will be chosen with user input after the common baseline
and evaluation infrastructure are ready.

## Project documentation

- [`docs/status.md`](docs/status.md) records the implementation milestone and
  verification results.
- [`CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`](CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md)
  describes the broader engineering roadmap, experimental standards, and
  research decision gate.
- [`docs/benchmark-format.md`](docs/benchmark-format.md) documents the current
  benchmark format and its limitations.

The repository should be read as active work in progress. Planned work,
hypotheses, and measured findings will remain explicitly distinguished as the
project develops.
