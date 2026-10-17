# External UCI opponents

The match suite accepts `external_uci` alongside internal agents. It uses the
existing `python-chess` dependency. Run from the repository root:

```powershell
uv run python -m chesslab.match_suite experiments/manifests/external-stockfish19-smoke-v1.json artifacts/external-new --repository .
```

The supplied manifest pins the official Stockfish 19 Windows universal binary.
It is a development smoke comparison, not a strength benchmark. Download the
[official release](https://github.com/official-stockfish/Stockfish/releases/tag/sf_19)
separately into ignored `artifacts/engines/`; the project never downloads or
installs an engine automatically. Other platforms need their own executable
path and measured SHA-256, producing a different manifest digest.

## Configuration and resource limits

An external agent requires `kind: external_uci`, `path`, and executable `sha256`.
Optional `options` holds engine-specific string/integer/boolean values;
`timeout_seconds` defaults to 10; `assets` lists separately supplied evaluation
networks or other files to hash. Relative paths resolve from the invocation
directory. Set external network paths explicitly in engine options and list the
same files in `assets`. Embedded networks are covered by the executable hash.
Engines, assets and local environments stay outside Git.

The shared per-move budget maps directly to UCI `depth`, `nodes` or `movetime`.
For comparisons across methods, equal wall time is usually easier to interpret:
nodes and depths are engine-specific units. Limits are cooperative; reported
node counts and elapsed time may exceed requested values. The separate watchdog
fails a depth/node search after `timeout_seconds`, or a timed search after its
time budget plus that allowance. It never turns a watchdog failure into a move
at a smaller budget. Handshake, configuration and graceful quit use the same
response allowance. Operating-system process creation is outside that watchdog.

Options managed by python-chess (`Ponder`, `MultiPV`, `UCI_Chess960`, etc.) are
rejected during parsing. Play requests disable pondering, use one PV and standard
chess. Unsupported engine-specific settings fail explicitly at engine startup.
For Stockfish set `Threads`, `Hash`, strength settings and tablebase paths
explicitly. The example uses one CPU thread, 16 MiB hash, full strength, and no
tablebase path. Stockfish 19 combines search with NNUE evaluation; it is a
third-party hybrid opponent, not our own learned model or a material-only engine.

## Lifecycle, failures and records

Each external agent lazily starts a fresh process for each game. A stable game
token requests `ucinewgame` on first play. Full board history from the match is
sent; exported boards are independent copies. A FEN start has no earlier history.
There is no cross-game hash reuse, automatic retry, implicit engine seed, draw
claim, resignation adjudication or forfeit. The harness RNG seeds are recorded,
but do not make an external engine deterministic. Use an engine-specific seed
option if it has one. Threads, time budgets and hardware can affect decisions.

Exceptions, missing/illegal best moves, timeouts and crashes fail the game.
Ply limits interrupt it. Neither counts as a draw. Cleanup always attempts a
bounded quit and closes the transport; quit errors are retained and make suite
status failed even when board outcomes exist. Keyboard interruption preserves
engine diagnostics and the active game identity; an unfinished game remains
unrecorded in coverage counts. There is no hard OS-level kill/reap guarantee
for arbitrary hostile executables or engine-created descendant processes.

External suites add optional decision wall times for both agents, engine-reported
nodes/depth/time, identity, executable/network hashes, requested settings,
advertised option defaults, seed policy and cleanup errors. First-decision times
include process startup/hash/configuration costs. `startup_seconds` records that
component separately in new runs. Failed decisions have error records but no
successful-move timing. Summary timing statistics cover successful decisions,
including those in incomplete games; they are not pure search speed measurements.
Raw games and separate engine records are written incrementally. Source and lock
snapshots plus hashes preserve dirty-tree provenance. All run outputs remain in
ignored `artifacts/`; commit compact summaries and configurations only.

Offline tests mock engine startup/play, and separately exercise the watchdog
against a local asynchronous coroutine. They need no engine binary or internet.
On this Windows host, sandbox socket restrictions prevented asyncio event-loop
creation; the full suite and real match ran successfully outside the sandbox.

The protocol behavior follows the
[python-chess engine API](https://python-chess.readthedocs.io/en/latest/engine.html)
and the installed 1.11.2 implementation, including its public asynchronous
protocol for depth/node watchdogs.

## Adding a learned bot next

A learned bot can implement the existing `Agent.select_action(state, budget, rng)`
contract or expose UCI and use this bridge. Legal-action checks, colour pairs,
failure denominators, timings and source/version metadata can then be reused.
Before training, select one bounded method and specify its target/loss or reward,
data source, source-group splits, resource budget and a fresh evaluation set.
Record model/checkpoint hashes as external assets when using UCI. Add an internal
agent configuration only when a concrete implementation exists. No training
pipeline, model dependency, data purchase or API spending is introduced here.

The original 200-position held-out tactical study remains frozen and observed;
it must not become tuning data. Its fixed-node results are not directly
comparable with a timed external-engine game. A shared fresh tactical comparison
with external agents is still a separate task.
