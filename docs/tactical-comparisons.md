# Shared internal/external tactical comparisons

`chesslab.compare_tactics` runs named internal agents and external UCI opponents
on the same explicitly labelled positions. It does not alter the original
held-out study runner, protocol, inputs or reports.

```powershell
uv run python -m chesslab.compare_tactics experiments/manifests/shared-development-tactics-v1.json artifacts/shared-tactics-new --repository .
uv run python scripts/summarise_tactical_comparison.py artifacts/shared-tactics-new artifacts/shared-tactics-summary.json
```

The example requires the pinned local Stockfish binary described in
[external opponents](external-opponents.md). All default tests use synthetic
positions and mocks; no external binary, internet or downloaded dataset is needed.
Use fresh output paths. There is no automatic retry or resume.

## Inputs and measurement

The strict version-1 manifest specifies name/question, dataset id/version/source/
split, explicit named FENs with nonempty legal `expected_moves`, at least two
unique named agents, distinct integer seeds and a shared depth/node/millisecond
budget. Agent settings reuse the match-suite parser. Duplicate names or equivalent
board positions are rejected. A split label records intent; it cannot prove
independence from training or tuning data.

The outcome is accepted **first-move agreement**, not complete puzzle solving or
an engine-centipawn accuracy score. Multiple accepted moves are supported. These
are source-solution labels; an unlisted alternative need not be a chess mistake.
There is no automatic relabelling against the reference engine.

For every root seed/position, derive a seed shared by all agents, rotate agent
order, and create fresh agents. Each external case gets a fresh process and game
token, avoiding cross-position search/cache carryover. FEN inputs omit earlier
history. Harness RNG seeds do not seed engines implicitly.

`setup_seconds` covers state preparation plus external process startup, executable
hashing, configuration and ready handshake. The separate decision wall timer
covers `select_action`, including protocol/first-search overhead. Shutdown is
excluded and errors retained. `setup_seconds` does not cover configuration object
construction. Limits remain cooperative and machines/load affect timings.
Random and greedy accept but ignore search budgets; their small runtimes do not
represent equal-compute searched agents. Engine node/depth metrics are diagnostic
and cannot be treated as equal work across implementations.

## Failures, pairing and provenance

Per-case JSON contains schedule identity, seeds, chosen move, agreement, setup/
decision timing, native search diagnostics or external engine metadata, phase and
error. Setup failures have no decision time. Failed/illegal decisions have no
selected action or agreement label, and remain in planned denominators. A
keyboard interruption during setup/selection is recorded before the suite stops.
Hard process kills, shutdown interruption or filesystem failures can prevent
finalization; inspect active-case identity and missing counts.

Summary rows separate completed, failed, interrupted and missing cases. Agreement
is reported over both planned and completed denominators. Timings summarize
successful decisions only; setup totals cover all attempted cases. Cleanup errors
are separate reliability failures and fail suite status; a valid move's agreement
can still be reported when only cleanup failed. Pair tables compare each agent
with the first manifest agent on complete decision pairs, with incomplete-pair
counts. They report discordant agreements without confidence or Elo estimates.
Repeated seeds on the same positions do not create independent puzzle samples.

The runner snapshots source files and the lock and records their hashes, Git
state, package versions, dataset/configuration and engine provenance. The audit
script checks schedule identity, legal decisions, labels, finite timings, engine
pins, saved summary/counts and source hashes before exporting a compact record.
Raw records, binary files, data and environments stay under ignored paths.

## Current result and next decision

The [development smoke report](../experiments/summaries/shared-development-tactics-20261017.md)
uses ten previously observed development puzzles and four agents. It is a
functional comparison, with no parameter tuning or new held-out claim. Future
confirmatory comparisons need fresh, disjoint positions frozen before tuning.

The common interfaces now support a learned bot in both ordinary games and
tactics. The next meaningful input is which first learning task to implement;
see [the bounded options](research/first-learned-bot-decision.md).
