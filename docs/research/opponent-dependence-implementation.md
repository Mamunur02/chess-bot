# Implementation log

Implementation began on 18 October 2026 under protocol v1. The user authorized
the neural phase, bounded Luna implementation tasks, Astra scientific review,
and normal reviewed commits and pushes. Earlier infrastructure-only and
planning-only notes are historical. No paid resources are authorized.

## Schedule

The working window is 18 October–1 November 2026 (Europe/London).
18–23 October: reference data, rule validation, split audit and correctness
tests; implement the model and bounded feasibility pilot. 24–25 October:
freeze the feasible configuration and start the core matrix only if its gates
pass. 26–30 October: complete core runs and analysis; integration and extensions
only if resources permit. 31 October–1 November are reserved for reporting and
reproduction. These are targets, not claims that unattended jobs are running.

## Audit on 18 October

Baseline HEAD was `539ee5b`. Classical search, UCI opponents, controlled tactical
and match runners, and the supervised linear evaluator are implemented. Existing
planning edits in README/status/scope and five untracked research documents were
present before implementation; preserve them. Existing experimental evidence is
unchanged and is not a fresh test set for this study.

Verified hardware: Intel i7-10875H, 16,954,482,688 bytes physical RAM,
RTX 2070 Max-Q with 8,192 MiB VRAM, NVIDIA driver 566.36. Project Python is
3.12.14; PyTorch is absent. No Syzygy directory was present in data/artifacts.
CPU/RAM queries and network access required execution outside the sandbox.

Git needs a command-scoped `-c safe.directory=C:/Projects/chess-bot` because
the sandbox account differs from the repository owner. No global Git security
settings were changed. Working uv invocation uses
`uv --cache-dir artifacts/uv-cache run --python .venv/Scripts/python.exe`;
the default sandbox uv cache failed with access denied.

## Foundation

Added separate experiment rules using `outcome(claim_draw=True)` and full-history
child copies. The existing general runner retains its draw policy. Reference
queries use history-free, clock-reset copies, preserve cursed/blessed signs,
retain raw WDL/DTZ, and fail on missing tables. Canonical keys use all eight D4
symmetries and colour exchange with turn exchanged; identity and RNG hash
serializations are documented in code.

Astra review caught and Luna corrected two defects before integration: square
maps passed to a bitboard transform, and actual draw claims incorrectly gating
theoretical q. Regression tests cover both. Mock tests are not a substitute for
real-table verification.

The protocol's Lichess `/3-4-5/` directory returned HTTP 404. The same publisher
lists separate `/3-4-5-wdl/` and `/3-4-5-dtz/` directories; use those without
changing the data specification. Sesse HTTPS failed TLS negotiation. Generator
verification documentation is pinned to commit
`0bb8aeee525f364bb750f96df312a1a7c9b54398`. It explicitly says its embedded
checksums are not MD5. Lichess additionally publishes whole-file SHA-256 values.
Acquisition and verification results will be recorded separately.

## Next actions

1. Complete serial acquisition and verify all eight tables, recording failures.
2. Generate and screen both development families using the fixed gates.
3. Generate and audit owned partitions, keeping final labels outside tuning.
4. Implement/test encoder, replay, targets and opponent before neural pilot.
5. Freeze a resource-feasible configuration before final evaluation.

Both development screens completed: KRvKR 1,822/2,000 sensitive positions and
KQvKR 1,192/2,000. Both pass, so the protocol selects KRvKR. See the measured
development summary. All eight table hashes match the publisher SHA-256 list;
the optional integration check additionally compared embedded checksum trailers.
It did not recompute the generator's CityHash-based checksum.

The encoder, fallible opponent, pure targets and replay are implemented with
focused tests. Review strengthened learner-max/perspective tests, removed
duplicate mixed-target branch work, and protected replay against mutable Move
objects. CPU PyTorch 2.7.0+cpu is installed in ignored `artifacts/neural-env/`,
with NumPy 2.5.4. This is a correctness environment; GPU throughput is unmeasured.
The default project environment remains free of PyTorch.

Latest full check: 395 passed, two skipped (optional neural and table checks),
with subsequent focused replay/target tests also passing. Neural implementation
and KRvKR partition generation are in progress. No feasibility projection or
learning outcome comparison has been measured. No cloud resource was created;
cash spending is zero, with electricity cost not yet estimated.
