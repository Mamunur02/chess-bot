# Continue after reviewed incremental calibration accounting

Continuation request prepared 9 November 2026 for `C:\Projects\chess-bot`.
This updates implementation state, not protocol v1. Preparing this handover is
documentation/commit/push only; no new implementation or measurement in this turn.

## Usage, authority and working method

Check account usage FIRST. Stop before either window reaches 10% remaining.
Begin checkpointing at 35%, earlier if consumption is rapid. Reserve headroom
for review, fixes, verification, checkpointing, commits and pushes. Check before
and after each bounded task/delegation. Limits are account-wide. Do not use reset
credits or buy credits. If usage is unavailable, do not assume enough allowance
to supervise experiments. Preserve historical reserve breaches in checkpoint.md.

The preceding implementation ended at VERIFIED post-push 34% five-hour / 45%
weekly remaining; its committed checkpoint records the earlier 37/45 reading.
This documentation turn began at31/44. These are historical readings on resume.
No reset credit was used. No Python process appeared at this turn's inspection.

Normal reviewed commits and pushes to the existing project remote are explicitly
authorized. Do not ask again for routine authorized work. No force pushes,
destructive history, unrelated remotes, credential changes or binary dumps.
Ask before adding a production dependency. No paid cloud without separate
provider/configuration/cost/shutdown approval.

Use actual `gpt-6-astra` for narrow scientific planning/review and `gpt-6-luna`
for bounded implementation where supported. Do not claim unavailable models.
Keep delegation narrow and sequential. Root reads broad context once; give agents
specific files, invariants and tested acceptance criteria. Require REAL runner
regressions, not only helpers or mocks that hide production control flow. Root
must assess completeness before review. Back up drafts before risky edits.
Do not assume agents survive handoff. Do not reopen direction or resolved cadence.

## Required reading and precedence

Read this file in full, then `docs/research/new-chat-handover-20261108.md` in full
and EVERY prior handover/required context it lists, including:

- docs/research/new-chat-handover-20261107.md
- docs/research/new-chat-handover-20261106.md
- docs/research/new-chat-handover-20261104.md
- docs/research/new-chat-handover-20261024.md
- docs/research/new-chat-handover-20261020-evaluation.md
- docs/research/new-chat-handover-20261020-continuation.md
- docs/research/new-chat-handover-20261020.md
- AGENTS.md; checkpoint.md newest entries first
- CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md; docs/status.md; README.md
- docs/research/opponent-dependence-protocol-v1.md
- docs/research/opponent-dependence-implementation.md
- docs/research/opponent-dependence-literature.md
- experiments/summaries/endgame-pilot-9001-v1.md and companion JSON

Protocol v1 governs science; later handovers update implementation state. Older
infrastructure-only, pilot-unrun, evaluation-absent and untracked-runner passages
are superseded. This handover also supersedes pending latency/static incremental
records and per-game deltas in the8 November handover: those slices are completed.
Read without truncated output. Inspect actual source, Git, artifacts and processes.

## Verified repository, artifacts and protected work

Branch `codex/opponent-dependence`, existing origin
`https://github.com/Mamunur02/chess-bot.git`. Starting HEAD `ec979be` matches local
origin tracking and its push succeeded. This documentation commit follows it;
inspect log/status for its hash.

Relevant pushed history:
- 5849057: fixed-start evaluation primitives.
- 2ad7dd8: optional pretraining deadline/progress callbacks.
- fbf213e: cumulative attempted predictor/probe accounting.
- 3550b13: original-error/full-active-game-snapshot persistence repair.
- a7bd829:8 November handover.
- deeb305: incremental latency/static attempts and deadline persistence.
- ec979be: isolated per-game attempted-work deltas.

Preserve and exclude five preexisting document changes from routine commits:
modified README.md and docs/research/practical-project-scope.md; untracked
opponent-dependence-decisions.md, opponent-dependence-protocol-draft.md and
opponent-dependence-scope.md under docs/research/.
Baseline: artifacts/calibration-repair-20261104/preserved-document-hashes.json.
All five matched after implementation checks. Only these changes remained after
push. Backups: artifacts/calibration-repair-20261109/runner.before.py.txt,
tests.before.py.txt, runner.before-deltas.py.txt and tests.before-deltas.py.txt.

Development seed9001 pilot is COMPLETE and verified. Never restart or overwrite
artifacts/opponent-dependence-v1/pilot-9001-v1/. Its pilot.json SHA256 remains
3b4ae6defd8b0fad6b3c66380ab8c6681990deb7f8309ed3dc2142a109b3186c.
Development: artifacts/opponent-dependence-v1/development/.
Tables: data/syzygy/protocol-v1/; acquisition manifest:
experiments/manifests/syzygy-protocol-v1-acquisition.json.
Fresh9 November audit verified all FOUR checkpoint hashes (pretrained and beta
0/0.5/1 finals), all2,000 development rows via pilot loader, acquisition manifest
hash and all8 table hashes against pilot provenance. Saved audit:
artifacts/calibration-repair-20261109/artifact-audit.json.
This is artifact integrity verification, NOT hash-rejection orchestration coverage.
Ignored tables/data/models/environments require separate restoration in a fresh
clone. Final labels remain outside calibration/tuning.

## What the latest slices implement and their limits

Both slices changed scripts/run_endgame_calibration.py,
tests/test_endgame_calibration.py and checkpoint.md. No dependency changed.

Incremental latency/static:
- Latency attempts retain phase/pass/index/FEN/status/duration/error and partial
  summaries. Selection timing stops before persistence. Warmup/sample completion
  counts reflect actual work, including partial failure/deadline/interruption.
- Static prediction and choice helpers run one item at a time. Results and phase
  status/duration persist separately, with a deadline check between helpers.
  Completed prediction survives subsequent choice failure or deadline.
- Cumulative attempted predictor/probe work persists between items/phases.

Per-game deltas:
- Copied cumulative baselines immediately before each game prevent static work
  and prior games leaking into per-game attempted counts/boards/seconds/failures.
- Newly appended raw probe errors are sliced per game; cumulative totals retained.
- Progress, completion and failure install full latest snapshot and deltas before
  writes; game progress also persists cumulative attempted_work in the manifest.
- Game/manifest writes in progress share original-error preservation. A failed
  write must abort instead of being swallowed by ordinary game failure handling.

Retain previous contracts: original work/deadline/interruption errors survive
secondary cleanup/write failures; cleanup occurs once; full active-game snapshots
retain moves, keys, choices, denominators and counters before I/O. Failed durable
writes expose exception.partial_manifest only IN MEMORY while process/exception
survives. This is NOT guaranteed durable recovery after termination/storage loss.
All predictor/probe timings are NESTED diagnostics, never additional exclusive
wall components. Completed-selection primitive counts and attempted counts differ.

Actual Luna implemented both slices; root expanded/corrected tests and persistence.
A mocked game explicitly re-raised after its callback, hiding a swallowed-write
risk; root fixed the write path and added REAL play_fixed_game regressions for
ValueError/TimeoutError/KeyboardInterrupt with either progress-write target failing.
Root also checked two-game raw-error isolation and latency exclusion of persistence.
Actual Astra approved each NARROW slice for checkpointing only, read-only without
independently rerunning checks. WHOLE RUNNER REMAINS UNAPPROVED FOR MEASUREMENTS.

## Immediate remaining repairs BEFORE measurements

1. Complete EXCLUSIVE wall-time accounting: setup, game runtime, persistence,
   model loading/saving, encoding, tensor construction, training, reporting and
   finalization overhead. Do not add nested diagnostics twice or call incomplete
   elapsed accounting complete. Preserve all new error/snapshot/delta contracts.
2. Complete cooperative deadlines through setup, labeling, encoding and pretraining;
   retain partial records. Distinguish deadlines, interruptions, failed games and
   ply caps; unfinished reward remains None. In-flight tensor work cannot be
   preempted. Never mark complete with failed/missing required work.
3. Finish provenance: resolved config, development/pilot/model/table hashes, source
   snapshots, Git/diff state, packages, actual hardware/threads/determinism/seeds,
   full model/config/surrogate limitations. _provenance still uses bare Git;
   use command-scoped safe.directory. Require complete pilot status in pretraining.
4. Strengthen runner tests: reject each of FOUR checkpoint hash mismatches,
   development/acquisition mismatches; prove truly paired model-independent RNG
   streams and balanced colours. Existing optional success-test name does not
   establish these semantics. Add deterministic per-game seconds-delta assertions
   and explicit delta checks in real deadline/interruption tests as hardening.
   Keep default suite free of Torch/tables/network and optional real integration
   bounded. Do not confuse mocked setup with actual measurements.
5. Required verification and focused independent WHOLE-RUNNER review before timing.

Reuse verified pilot _load_development without running pilot. Acquisition keys
match the pilot writer. Opponent reference_failures counts selection exceptions,
not proven missing-table errors; retain actual text. Preserve evaluation primitives,
pretraining callback behavior and scientific defaults.

## Calibration and complete resource gate

NO calibration measurements, complete resource projection, budget freeze,
reviewed core orchestration or core matrix has been completed.

After repairs/review, isolated DEVELOPMENT-ONLY evaluation:100 boards/model for
choice/MSE;10 warmup +3 passes of30 boards with rotating model order;10 TOTAL paired
starts/model/p with balanced learner colours, p0/.25/.5 and400-ply cap. Explicit
CLI bounds/seeds/starts/order and model-independent paired RNG identities. Separate
selection timing from reference metrics. Use fresh output paths and partial records.

Then full-size pretraining timing surrogate: repeat development1600/400 subsets
to20000/2500, learner opposite side to move, target=-reference.value. Existing
trainer, all30 epochs, patience31 ONLY for timing; scientific patience5 and other
architecture/optimizer settings unchanged. Repeated data are not independent
training evidence or proof of full-data stopping. No concurrent project tests/work
during timing; disclose uncontrolled host activity. Reserve usage for supervision.

Resolved cadence: static quality/MSE at main0/25/50/75/100%; actual play/latency at
final main/matched and frozen controls. Exact zero-step reuse only within seed with
aliases/provenance.200 static bundles=600000 choices+600000 predictions;65 full
bundles=39000 games (13000 per p) and201500 latency/warmup choices.400-ply cap bounds
15.6million plies, not expected runtime. No intermediate actual-play curves.
Record cadence before final-data access.

Complete projection includes five full-size pretraining blocks,45 main runs,
five frozen controls,15 matched-time runs, ALL evaluations and overhead.
U(B)=floor(B/8)-31 for fully recorded transitions;
T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33;
main=15*sum_m T_m; matched=15*T_0. Account for unrecorded decisions and p=.5 transfer
assumptions. Prior training-only estimates including matched+30% contingency:
9.252/24.842/50.826/102.793 hours at2000/5000/10000/20000. These exclude remaining
costs and approve NO budget.

Freeze largest candidate satisfying1.3*complete_projected_hours<=36 and GBP60 core,
with explicit cash/energy assumptions. If2000 fails, only semantics-preserving
batching/caching, tests and remeasurement before infeasibility; never drop seeds.
GBP100 total=60core+20extensions+20contingency. Cash spent0; electricity unestimated.
No paid cloud without separate approval.

## Subsequent roadmap and scientific invariants

After gate, implement/review remaining core orchestration BEFORE execution.
Preserve seeds101/202/303/404/505;45 randomized within-block conditions, common
pretrained initialization per block, saved checkpoints and15 p=.5 equal-wall-time
runs. Protocol v1 governs all remaining defaults.

Invariants: python-chess rules; history-free clock-reset sign(WDL), including
cursed/blessed signs; actual full-history claim_draw=True; fixed learner perspective;
no tablebase in counterfactual targets; replay replies never resampled; terminal
reward once; epsilon.1 training/0 evaluation; UCI ties; named RNG streams.

Then paired analysis with missing-run coverage and trajectory-overlap sensitivity:
five paired seed differences, t interval and paired seed/canonical bootstrap.
Complete core reporting/reproduction before optional specialist/relative Elo,
ensembles and advice/ChessGPT. Optional work must not displace core seeds, analysis
or reporting. Preserve negative results and failures; no unsupported novelty claim.

## Schedule reassessment

Today at handover is9 November2026 Europe/London. Original31 October-1 November
reporting window passed. Provisional5-8 November repair/calibration/full gate was
NOT achieved.9-12 November orchestration/core and18 November completion are not
established.17-18 November reporting/reproducibility remains only provisional.
Reassess after actual gates and measured runtime; move completion as necessary
while preserving the final TWO FULL reporting/reproducibility days after execution
and analysis. No replacement external deadline supplied. Do not compress scientific
gates or drop seed blocks to meet an unsupported date.

## Verification and resume commands

Latest implementation checks9 November, each independently observed exit0:
- Full default511 passed6 skipped14.41s (elevated Windows UCI):
  artifacts/pytest-game-deltas-full-20261109.
- Optional neural/interaction/targets/pilot/evaluation/calibration147 passed18.49s:
  artifacts/pytest-game-deltas-neural-20261109.
- Ruff . passed; mypy src plus pilot/calibration passed50 files.
- Focused82 passed1 skipped4.26s before final raw-error assertions:
  artifacts/pytest-game-deltas-root-20261109. Full suites above include those assertions.
- Protected document/pilot hashes unchanged; staged scope/whitespace passed.
Earlier slice506/6 and142 passes are superseded. Root initially hit two Ruff long
lines, fixed before successful checks. Earlier failures remain in checkpoint.md.
No code tests rerun for this documentation-only handover.

After changes use NEW basetemps and observe each exit independently:

```powershell
git -c safe.directory=C:/Projects/chess-bot status -sb
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-calibration-NEW-UNIQUE
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src scripts/run_endgame_pilot.py scripts/run_endgame_calibration.py
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py tests/test_endgame_interaction.py tests/test_endgame_targets.py tests/test_endgame_pilot.py tests/test_endgame_evaluation.py tests/test_endgame_calibration.py -q --basetemp artifacts/pytest-neural-NEW-UNIQUE
```

Windows UCI may require escalation. Workspace uv cache, explicit interpreters and
command-scoped safe.directory; no global security change. Torch stays optional in
ignored neural-env (historical CPU2.7.0+cpu, NumPy2.5.4, Python3.12.14); GPU throughput
unverified. Keep checkpoint.md exact: results/failures, process/Git/artifact state,
usage and concrete resume instructions. Distinguish measurements, projections and
unfinished work. No background continuation is implied.
