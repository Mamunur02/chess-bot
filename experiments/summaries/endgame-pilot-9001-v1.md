# Development feasibility pilot, seed 9001

Measured 19 October 2026. All three methods completed; this is feasibility
evidence, not a method-quality comparison or a full-core feasibility claim.
The companion JSON records compact measurements, source hashes, checkpoint
hashes, environment, data identity and explicitly incomplete cost projections.

## Execution and provenance

Command:

```powershell
artifacts/neural-env/Scripts/python.exe scripts/run_endgame_pilot.py --development-dir artifacts/opponent-dependence-v1/development --tablebase-dir data/syzygy/protocol-v1 --acquisition-manifest experiments/manifests/syzygy-protocol-v1-acquisition.json --output-dir artifacts/opponent-dependence-v1/pilot-9001-v1 --decisions 512 --threads 1
```

Do not reuse that output directory. Raw records, copied sources and checkpoints
are retained there, ignored by Git. HEAD at execution was 798c029 with the
reviewed accounting changes uncommitted; the raw manifest records the dirty
diff hash and exact source snapshots. All source/checkpoint hashes were
independently rechecked after completion. Existing user document edits were
preserved. No final performance labels were read for this pilot.

CPU PyTorch 2.7.0+cpu, Python 3.12.14, NumPy 2.5.4; one intra/inter-op thread,
deterministic algorithms enabled. Existing verified hardware is i7-10875H,
approximately 16 GiB RAM. No GPU or cloud resource used. No simultaneous project
tests ran during measurement; unrelated host activity was not controlled.

## Measurements

Each method used the same pretrained state, p=0.5 and epsilon=0.1, recorded
512 decisions/transitions and completed 33 updates. All recorded losses and
gradient norms were finite; each online model changed. Episode decision totals
match the method totals. No failed method or unrecorded decision occurred.

| Beta | Training seconds | Target seconds | Optimizer seconds | Residual seconds | Target neural leaves |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 28.277 | 13.762 | 0.125 | 14.390 | 16,508 |
| 0.5 | 115.072 | 101.016 | 0.125 | 13.931 | 134,569 |
| 1 | 108.858 | 95.283 | 0.124 | 13.451 | 130,676 |

Residual time includes simulation, online inference, reference queries, replay,
feature encoding and logging. Reference probe times are nested diagnostics,
not additional cost. Neural leaves exclude terminal branches; total branch
expansion counts remain unavailable. These limits are disclosed in the runner.

Full pilot wall time was 260.715 seconds. Process-lifetime peak working set was
411,742,208 bytes; this is not an independent peak for each method.
Development pretraining used 1,600/400 examples, stopped after seven epochs,
restored epoch two and took 3.282 seconds including encoding, initialization,
checkpoint writes and untrained/frozen evaluation. Development validation MSE
was 0.282642 untrained and 0.201869 frozen. These are development diagnostics,
not held-out accuracy. The raw manifest retains label counts and epoch records.

## Resource gate: not frozen

For candidate budget B, assuming every decision records a transition, use
`U(B) = floor(B/8) - 31`. For method m define the illustrative extrapolation
`T_m(B) = residual_m * B/512 + (target_m + optimizer_m) * U(B)/33`.
Main training costs `15 * sum_m T_m(B)` across three opponent settings and five
seeds. Matched-time training adds `15 * T_0(B)`. Apply 1.3 contingency to their
sum. This assumes p=0.5 pilot rates transfer to other p values and later replay
distributions; those assumptions have not been verified.

| Decisions | Updates | Training + matched-time hours, including 30% |
| --- | ---: | ---: |
| 2,000 | 219 | 9.252 |
| 5,000 | 594 | 24.842 |
| 10,000 | 1,219 | 50.826 |
| 20,000 | 2,469 | 102.793 |

These are estimates, not measured core runtimes, and exclude pretraining,
evaluation, checkpoint/failure/reporting overhead. Under this extrapolation,
10,000 and 20,000 exceed 36 hours before those costs. Neither 2,000 nor 5,000
is yet approved by the gate. Simple whole-pilot scaling would incorrectly
understate the larger update count after warmup.

Next measure development-only evaluation costs and full-size pretraining cost.
Account for five 20,000/2,500-example blocks and up to 30 epochs, rather than
extrapolating seven small-development epochs as the complete cost. Include all
45 main runs, five frozen controls and 15 matched-time runs. A conservative
planning inventory evaluating every main checkpoint and matched-time final is
245 bundles: 735,000 benchmark move choices, 735,000 separate MSE predictions,
147,000 games and 759,500 timing/warmup move choices. The 400-ply cap bounds these
games at 58.8 million plies; this is not an estimate of typical duration.
Identical zero-step evaluations can be reused only with identical model,
starts, RNG and configuration (200 distinct bundles after removing 45 duplicate
zero-step evaluations). Static reference labels may also be shared.

This inventory is a conservative resource-planning assumption, not a change to
the final-checkpoint primary analysis. If its bound fails, resolve the precise
evaluation schedule and measure development costs before concluding infeasibility.
Never omit prescribed final evaluations silently. Include actual-play truncation
coverage and avoid treating truncated games as draws. Do not inspect final
outcomes to decide the budget. Record the cash projection within GBP60; cash
spending so far is zero, electricity cost remains unestimated.

## Review and verification

GPT-6 Astra reviewed scientific semantics and projection requirements; GPT-6
Luna added the bounded success regression and accounting repair. Root reviewed
the diff and independently checked artifacts. The regression uses mocked data
and references with real pretraining, interaction, targets and RL updates;
it is not experimental evidence.

- Default suite: 429 passed, 5 skipped in 12.05 seconds (outside sandbox for UCI).
- Optional neural/interaction/targets/pilot: 56 passed in 14.52 seconds.
- Pilot-only regression: 19 passed in 12.76 seconds.
- Ruff check . passed; mypy src plus pilot passed, 48 files.
- Artifact audit: source/checkpoint hashes, finite updates and decision totals passed.
- Initial new-test run failed with a missing math import; early Ruff also caught
  long lines. Both were fixed before successful verification and the real pilot.
- Initial sandbox process inspection was denied; elevated read-only CIM query
  confirmed no Python process before launch. Pilot exited successfully.

The next smallest task is a bounded development-only cost-calibration harness,
followed by the complete reviewed projection. No core matrix has launched.
