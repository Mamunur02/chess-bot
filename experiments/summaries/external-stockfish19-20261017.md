# External Stockfish comparison: development smoke

Measured locally on 2026-10-17. Final run began at 17:38:31 UTC (18:38:31 BST).
The goal was to exercise real external-opponent games and provenance, not estimate
Elo or select an engine/search configuration from held-out tactical results.

## Final measured result

| Agent | Wins / draws / losses | Successful timed decisions | Median decision wall time | Total decision wall time |
| --- | --- | ---: | ---: | ---: |
| Our plain material alpha-beta | 0 / 0 / 4 | 45 | 50.070 ms | 2.253 s |
| Third-party Stockfish 19 | 4 / 0 / 0 | 47 | 50.777 ms | 4.034 s |

All four games and both colour pairs completed by checkmate; 92 plies total.
Individual game lengths were 18, 25, 22 and 27 plies. There were zero game,
timeout, cleanup, illegal-move, missing-record or ply-limit failures in this
final run. Independent legal replay checked terminal outcomes, schedule seeds,
budgets and starts. Source hashes and timing reaggregation also passed.

Both agents received 50 ms per move. Wall measurements include protocol and
wrapper overhead; Stockfish's first decision in each game includes startup,
binary hashing and configuration (0.498 / 0.516 / 0.480 / 0.482 s respectively).
These are not search-only timings or a claim of equal total process compute.
No per-move node equality or exact wall-time enforcement is claimed.

The two manually chosen development starts follow four full moves of the open
game and Queen's Gambit lines written in the
[manifest](../manifests/external-stockfish19-smoke-v1.json). Each position was
played in both agent-colour assignments, with root seed 17. Exact FENs, derived
match/player seeds, settings and hardware are in the
[compact record](external-stockfish19-20261017.json). FEN starts omit earlier
repetition history; subsequent history is preserved. The cap was 160 plies.

## Opponent and environment

- Official release `sf_19`, universal Windows x86-64 binary; engine identifies
  itself as **Stockfish 19**. This is search with NNUE evaluation, developed by
  the Stockfish project. We did not train or implement it.
- [Official release](https://github.com/official-stockfish/Stockfish/releases/tag/sf_19);
  downloaded archive SHA-256
  `3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7`,
  verified against the GitHub release asset's digest.
- Executable SHA-256
  `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`.
  Default embedded network `nn-1a298aa575a0.nnue` is covered by that hash.
- Threads 1, hash 16 MiB, Skill Level 20, UCI_LimitStrength false, no Syzygy path,
  pondering off, one PV, standard chess. All advertised defaults and requested
  overrides are retained in the compact record. Engine RNG was not seeded;
  there is no generic UCI seed. Fresh engine process for each game.
- Our material alpha-beta uses no capture ordering, transposition table or
  quiescence; this was chosen as the existing plain baseline, without tuning.
- Windows 11, CPython 3.12.14, python-chess 1.999 / chess 1.11.2. Intel Core
  i7-10875H at nominal 2.30 GHz, 8 cores / 16 logical processors,
  16,954,482,688 bytes physical RAM. CPU/RAM read from Windows CIM.
- Run Git base `2b591700d28c69b94e00ab877bd9308623781bf7`, dirty tree. The final
  run's complete source/lock snapshots and hashes identify the actual code;
  the compact record preserves those hashes and lock hash. No GPU, paid compute,
  paid API or new production dependency was used.

## Failures and earlier attempts

The initial run `external-stockfish19-smoke-v1` recorded four failed games:
configuration rejected `MultiPV` because python-chess manages it. No games
completed and no forfeits were assigned. Those failures and exact inputs remain
in local artifacts and the compact record; they are not included as chess losses.
The manifest was corrected and parsing now rejects managed options before play.

`external-stockfish19-smoke-v2` was a successful validation run: four Stockfish
wins, no failures, 114 plies. The final run followed the additive startup-timing
metadata change, producing the primary table above. Across all three attempts,
12 games were scheduled, 8 completed and 4 failed configuration. The two
successful runs reuse the same starts and are not eight independent match pairs.
Time-limited play need not produce identical moves or game lengths.

Two sandbox attempts at engine/asyncio startup hung before usable measurements;
their task-owned processes were stopped. Tests and real games succeeded outside
the sandbox. No engine crash or timeout is inferred from that environment issue.

## Limits and next work

Four games on two selected openings are a smoke test. No Elo, population strength,
confidence interval or broad reliability guarantee follows. This run does not
measure tactical first-move agreement. The separate completed held-out puzzle
study stays frozen and uses different budgets; its results cannot be combined
with this table as an equal-compute external comparison. No existing test labels
were used to tune these agents. New confirmatory work needs fresh positions.

Raw games, engine diagnostics, source snapshots and binaries remain ignored under
`artifacts/external-stockfish19-smoke-{v1,v2,final}/` and `artifacts/engines/`.
The compact JSON preserves summary provenance and hashes, not the raw game logs.
See [external opponent guide](../../docs/external-opponents.md) for reproduction,
resource/failure semantics and learned-agent readiness. The next small evaluation
task is a shared fresh tactical-position comparison through this adapter. A first
learned bot can then use the existing agent/UCI contract after its objective,
data grouping, splits, checkpoint and compute budget have been chosen explicitly.
