# Shared tactical comparison: development smoke

Run began 2026-10-17 at 17:47:19 UTC (18:47:19 BST). This verifies shared
evaluation of our bots and an existing opponent. It does not introduce a learned
bot, tune settings or reopen the completed held-out study.

## Measured results

| Agent | Accepted first moves | Median decision wall time | Total setup time | Decision failures |
| --- | ---: | ---: | ---: | ---: |
| Our plain material alpha-beta | 6 / 10 | 50.072 ms | 0.001 s | 0 / 10 |
| Random control | 0 / 10 | 0.092 ms | 0.001 s | 0 / 10 |
| Material-greedy control | 2 / 10 | 2.189 ms | 0.001 s | 0 / 10 |
| Third-party Stockfish 19 | 10 / 10 | 55.783 ms | 4.929 s | 0 / 10 |

All 40 scheduled decisions completed. Zero missing, interrupted, illegal-decision
or cleanup failures. All ten paired comparisons per candidate/reference were
available. Relative to plain alpha-beta, Stockfish uniquely agreed on four
positions and plain uniquely agreed on none. Greedy uniquely agreed on one,
plain uniquely agreed on five. These are descriptive counts on observed inputs.

The per-search requested budget was 50 ms; random and greedy ignore it. Actual
wall times include protocol/first-search overhead and can exceed the requested
time. Searches can finish early, including immediate mates. Process startup,
hashing, configuration and ready handshake are measured separately in setup;
shutdown is excluded. Stockfish gets a fresh process for every position. The
timing totals and medians describe different aggregates; no speedup or equal
total process-compute claim is made.

## Inputs, settings and provenance

- First ten positions in the existing 50-position development split, in stored
  order; these were previously observed during the pilot. They are not fresh
  held-out positions. One retained source-game group per position was checked.
- Prepared development-file SHA-256
  `767557215b8087b7f258c7fd4c7801145115349f84d82c22e74172fe8c8c8a1e`.
  Preparation `lichess-reservoir-components-v1`, source CSV SHA-256
  `ec2dd1a8f9cbd139ebb4aee228f72e77f8e2a581a24d25f61f71e6cf306b10f8`.
- [Manifest](../manifests/shared-development-tactics-v1.json) contains exact
  solver FENs after setup moves, accepted labels, seed 20261017 and every agent
  setting. The manifest digest is
  `880817d1d06f49a37b3a7dfbb162a105abbb7a29f8cd30ecddf6be75c22a24f4`.
  Agent order rotates across positions; all agents share the derived position
  seed. Engine RNG is not implicitly seeded. FEN prehistory is unavailable.
- Stockfish 19, official `sf_19` Windows universal executable, SHA-256
  `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`,
  embedded network `nn-1a298aa575a0.nnue`. Threads 1, hash 16 MiB, Skill Level 20,
  full strength, no Syzygy path, pondering off and one PV. Exact advertised
  defaults, requested settings and identity are in the compact record. This is
  a third-party search/NNUE reference, not a model built or trained here.
- Our alpha-beta uses plain material evaluation with capture ordering, cache and
  quiescence disabled. No search feature was selected using held-out outcomes.
- Windows 11, CPython 3.12.14, python-chess 1.999 / chess 1.11.2. Intel Core
  i7-10875H at nominal 2.30 GHz, 8 physical cores / 16 logical processors,
  16,954,482,688 bytes RAM; Windows CIM measurement recorded. Local CPU only.
- Git base `3c5cf263795bd8b38024cc0098ed5a63807bd408`, dirty tree. The runner
  retained complete source/lock snapshots and hashes. Subsequent changes added
  provenance validation/reporting; measured source snapshots remain intact.
- [Audited compact record](shared-development-tactics-20261017.json) contains
  configuration, environment, summary, chosen moves, raw-case hashes and source
  identities. Raw records remain in ignored `artifacts/shared-development-tactics-v1/`.

The audit reaggregated counts, pair availability and timings; checked scheduled
identity/seeds, legal moves, source-label agreement, engine pins and source hashes;
and matched the saved summary. No engine/configuration failures occurred in this
new tactical run. Historical failures from the prior ordinary-game milestone
remain disclosed in its separate report.

## Relation to playing outcomes and limits

The earlier [ordinary-game smoke](external-stockfish19-20261017.md), with two
development opening starts and swapped colours, measured four Stockfish wins
and four losses for plain alpha-beta. That is a separate four-game sample;
the controls above have no ordinary-game results in that run. Combining the two
reports does not create an Elo estimate or statistical strength claim. The game
runner included startup in the first decision's wall time; this tactical runner
reports startup separately, so their timing aggregates differ.

First-move solution agreement is not full puzzle solving. Alternative good moves
may be absent from the source line. Ten observed puzzles and one seed do not
establish general tactical accuracy, performance differences or reliability.
The original held-out report remains unchanged, and its results are not reused
as tuning data. Confirmatory evaluation of a future tuned/learned bot needs fresh,
disjoint positions frozen before validation tuning.

The next step needs a method choice: our own supervised evaluator, a human-move
policy or another existing trained comparator. See the
[bounded decision note](../../docs/research/first-learned-bot-decision.md).
