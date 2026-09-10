# Project status

Last updated: 2026-09-10

## Current milestone

Milestone 12: fixed-budget benchmark harness. Caller-supplied position
configuration, raw per-case measurements, structured failures, configuration
digests, environment provenance, and JSON output are implemented and verified.

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
- Immutable chess piece snapshots for safe evaluation access.
- Material evaluation with explicit stable-player perspective.
- Depth-limited exhaustive minimax as a shallow correctness reference.
- Deterministic alpha-beta search with documented depth and node semantics.
- Fixed mate and draw scores that take precedence over heuristic evaluation.
- Search results containing action, value, visited nodes, and completed depth.
- A material alpha-beta chess agent supporting explicit depth and node budgets.
- Artificial-tree tests that compare alpha-beta with exhaustive search and
  measure pruning, plus focused tactical chess fixtures.
- Deterministic iterative deepening that preserves legal-action order.
- Exact cumulative node-budget stopping across completed and partial
  iterations.
- Last-completed-iteration decisions with a documented depth-zero fallback
  when a node budget cannot complete depth one.
- Principal-variation, cutoff, and completed-iteration search statistics.
- An opt-in action-ordering hook that validates the reordered legal actions.
- Safe chess capture classification, including en passant.
- Stable capture-first ordering in the material agent behind an explicit flag.
- An opt-in, per-search transposition table using caller-defined stable keys.
- Depth-aware exact, lower-bound, and upper-bound cache entries.
- Measured transposition-table hits included in search results.
- A diamond-tree correctness fixture comparing cached and uncached search.
- A public chess transposition key containing normalized position identity,
  the halfmove clock, and repetition counts since the last irreversible move.
- Opt-in transposition-table use by the material alpha-beta agent.
- Key tests covering reconstructed states, reversible move-order transpositions,
  and irrelevant history before an irreversible move.
- A generic bounded quiescence hook with caller-selected tactical actions and
  explicit stand-pat legality.
- Tactical actions validated as a duplicate-free subset of legal actions.
- Terminal evaluation before heuristic stand-pat evaluation throughout
  quiescence search.
- Quiescence work included in the same exact node budget as ordinary search.
- Separately reported quiescence-node counts and extended principal variations.
- Public chess check status for safe handling of forced evasions.
- Opt-in material-agent quiescence over captures and promotions.
- All legal evasions searched when the side to move is in check, with stand pat
  disabled.
- A poisoned-pawn regression for a one-ply material horizon error.

- A positive integer millisecond time-budget contract.
- Monotonic-clock deadline checks before every ordinary and quiescence node.
- Last-completed-iteration decisions when a deadline interrupts deeper search.
- A legal depth-zero fallback when time expires before root entry.
- Measured elapsed seconds on time-budget search results.
- No clock sampling or result changes for depth and node budgets.
- Injectable clocks for deterministic deadline tests.
- Millisecond budget kind and value in match metadata.
- Material alpha-beta agent support for wall-clock budgets.

- A `chesslab-uci` console entry point over standard input and output.
- UCI identification, readiness, new-game, stop, and quit commands.
- Atomic `position startpos` and six-field `position fen` setup with optional
  legal UCI move sequences.
- `go depth`, `go nodes`, and `go movetime` budget mapping.
- UCI centipawn and mate score fields, search statistics, principal variation,
  and best-move output.
- Null best moves and diagnostic information for invalid searches.
- Session-level error handling that preserves the command loop.
- Stream and installed console-entry smoke coverage.

- A `chesslab-benchmark` console entry point using JSON input and output.
- Caller-supplied named FEN positions with optional accepted UCI moves.
- Explicit material-agent switches and depth, node, or millisecond budgets.
- Stable SHA-256 configuration digests and deterministic per-position seeds.
- Git commit, dirty state, timestamp, Python, platform, machine, and processor
  provenance.
- Raw per-position decisions, search statistics, timings, failures, and seeds.
- Exact aggregate completion, failure, accepted-move, and node counts.
- Digest matching between benchmark specification and provenance.
- Result overwrite protection.
- No committed substantive benchmark dataset or claimed experimental result.

## Verification

Milestone 12 was verified on Windows with CPython 3.12.14:

- `uv run pytest`: passed; 121 tests passed.
- `uv run ruff check .`: passed.
- `uv run mypy src`: passed; no issues found in 23 source files.
- `uv run mypy src tests`: passed; no issues found in 35 source files.

## Planned, not implemented

- Experiment manifests, artifact layout, and multi-run comparison summaries.
- Richer quiescence policies such as check generation, delta pruning, or
  selective-depth adaptation.
- Learned models, MCTS experiments, datasets, interfaces, and deployment.

## Open decisions

- The long-term research branch will be selected only after the common
  infrastructure and classical baseline provide evidence for a decision.
