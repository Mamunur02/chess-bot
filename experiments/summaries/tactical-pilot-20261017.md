# Tactical development pilot, 2026-10-17

This is a preparation/capacity check, not held-out research evidence. Source:
CC0 Lichess puzzle snapshot identified in
`experiments/manifests/lichess-tactics-v1.json`.

## Preparation measurements

- Full CSV scanned: 6,157,341 rows; sampled reservoir: 1,200 rows.
- Full solution lines validated: 1,200; rejected: 0.
- Independent connected game/position/ID components in reservoir: 1,200.
- Prepared splits: 50 development, 50 validation, 200 test.
- Repeated complete preparation produced identical manifests and split hashes.
- No test searches have been run.

Original source FEN and setup move are retained. The benchmark receives the
position after setup. All immediate mates are accepted where applicable.
Source-game and equivalent-position overlap is removed before split assignment.

## Pilot measurements

Ten development puzzles, four existing variants, three node budgets, one seed
(20261017), one timing pass: 120/120 searches completed with zero failures.
Timing table totals are search-case wall seconds for ten puzzles, rounded to
three decimals. Quality counts are accepted first moves out of ten development
positions, not complete solved puzzles.

| Nodes per move | Variant | Accepted / 10 | Total case seconds |
| ---: | --- | ---: | ---: |
| 1,000 | Plain | 6 | 0.649 |
| 1,000 | Capture ordering | 6 | 1.298 |
| 1,000 | Transposition table | 6 | 0.769 |
| 1,000 | Quiescence depth 1 | 8 | 2.831 |
| 5,000 | Plain | 8 | 3.170 |
| 5,000 | Capture ordering | 8 | 7.858 |
| 5,000 | Transposition table | 8 | 3.983 |
| 5,000 | Quiescence depth 1 | 8 | 16.024 |
| 20,000 | Plain | 8 | 13.624 |
| 20,000 | Capture ordering | 6 | 34.840 |
| 20,000 | Transposition table | 8 | 17.730 |
| 20,000 | Quiescence depth 1 | 6 | 63.142 |

Every search used its full node allowance, including quiescence and incomplete
iterations. No depth-zero fallback occurred. Decisions need not improve
monotonically with budget: material evaluation and finite search horizons can
produce different choices. This tiny development sample does not establish
relative quality or speed in the target population. Variant ordering was fixed,
and other verification/preparation work overlapped portions of the pilot.

Measured wall duration for the three grids: 167.189 seconds, excluding warmup.
Raw pilot artifacts: `artifacts/tactical-pilot-20261017-01/` (ignored).

## Validation preflight

The counterbalanced runner completed 200/200 searches (50 validation puzzles,
four variants, 1,000 nodes, one pass), with no failures. Measured invocation
duration: 44.650 seconds. These validation searches exercise the runner and
logging; their quality outcomes are not promoted to held-out findings.
Raw artifacts: `artifacts/tactical-validation-preflight-20261017-01/` (ignored).
The preflight source snapshot identifies its executed code. Later driver
validation improvements do not change any agent/search algorithm.

## Capacity estimate, not a measurement

Linear scaling of pilot grid wall time from 10 to 200 positions estimates
55.7 minutes for one complete pass over all three budgets and all four variants.
Three timing passes estimate 167.2 minutes (2.8 hours). With 50% headroom, allow
about 84 minutes or 4.2 hours respectively. These estimates can be wrong because
position difficulty, thermals, power mode, background load and artifact overhead
vary. This pilot is not a runtime guarantee or formal hardware benchmark.

Hardware/environment recorded: Windows 11, AMD64, CPython 3.12.14; processor
string `Intel64 Family 6 Model 165 Stepping 2, GenuineIntel`; rules package
`chess` 1.11.2 and `python-chess` 1.999. Exact CPU marketing name/power mode were
not captured. CIM hardware access was unavailable in the sandbox. No GPU,
reference engine, new Python dependency or paid compute was used.

Git base: `2b591700d28c69b94e00ab877bd9308623781bf7`; working tree dirty.
Lock SHA-256: `569ca4796c7aebfc828e83f29a7ad76cd1b29242f7599d2dc0aeae3875db749e`.

Preparation tooling failures were resolved before sampling: the default uv
cache/pytest temporary location was inaccessible in the sandbox, and direct
Node stream decoding failed on the export's PZstandard metadata/data pairs.
Workspace cache/temp paths and the frame-pair adapter resolved these issues;
the complete decompression and repeated preparation succeeded. The optional
adapter test covers multi-frame decoding and cleanup of corrupt input.

Final code checks: 188 pytest tests passed, Ruff passed, mypy src passed (30
files), mypy src tests passed (47 files), optional Node integration test passed,
and locked offline uv sync checked 18 installed packages without changes.

## Next decision

Choose a quiet local execution window and one versus three timing passes,
then finalize `docs/research/tactical-evaluation-protocol.md` before starting
the held-out run. Three passes are preferred for timing stability if a roughly
four-hour quiet window is available. One pass preserves the quality comparison
but makes runtime findings more exploratory. Paid compute is not needed based
on this pilot. Analysis and plotting are still to be implemented and verified;
no formal result or confidence interval is claimed here.
