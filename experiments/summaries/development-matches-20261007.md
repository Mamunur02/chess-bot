# Match-suite smoke measurement: 7 October 2026

## Purpose

Verify colour pairing, outcome attribution, raw-game persistence, and summary
counts. Two synthetic near-mate positions were used: a White mate-in-one fixture
from correctness tests and its colour mirror. This is development data, not a
representative opening corpus or held-out strength benchmark.

## Reproduction

```powershell
uv run python -m chesslab.match_suite experiments/manifests/development-matches.json artifacts/development-matches-20261007-001
```

Use a fresh directory for a repeat. The embedded dataset is
`chesslab-synthetic-matches`, version `1`, split `development`. Manifest digest:
`7cf326964cb5a835c4a6b8374b30c003e648dd5c555beb2002eaff6c0db2abf1`.

The observed run used CPython 3.12.14, Windows 11 AMD64,
`Intel64 Family 6 Model 165 Stepping 2, GenuineIntel`; engine package 0.1.0,
`python-chess` 1.999, and `chess` 1.11.2. Git HEAD was
`a6269ba496476a9b12087c616b678da0250da6d4` with a dirty working tree. The new suite
was uncommitted, so that commit alone does not reproduce the implementation.
Retain and review milestone 15 source changes alongside this memo.
Dependency lock SHA-256:
`569ca4796c7aebfc828e83f29a7ad76cd1b29242f7599d2dc0aeae3875db749e`.
Raw metadata timestamp was `2026-10-06T23:19:34.042346+00:00` (7 October in London).

## Observations

Material-greedy and material alpha-beta played both colour assignments for
each of two positions and root seeds 17/23. The shared budget was depth 1 and
the ply limit was 4. Greedy evaluates one ply independently of that budget.

- Eight games were planned and recorded; all completed after one move.
- Four colour pairs completed; no game failed, hit its ply limit, or was missing.
- Each agent recorded four wins, zero draws, and four losses; its descriptive
  completed-game score fraction was 0.5.
- Raw records, seeds, colour mappings, and provenance remain under the local
  ignored artifact directory. No result was fabricated or extrapolated.

## Interpretation

These observations verify execution and result bookkeeping only. The side
already holding mate-in-one determines each game; these outcomes cannot compare
playing strength. Colour-swapped games and repeated deterministic seeds are
not independent observations. No Elo, uncertainty interval, or strength claim
is supported by this smoke run.

Separate tests verify automatic draws, random repeatability, agent failures,
ply limits, and partial execution aborts. Substantive evaluation next requires
agreement on priority, then a reviewed source/protocol and independent data.
