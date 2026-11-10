# Continue after reviewed coarse lifecycle timing

Continuation request prepared 10 November 2026 for `C:\Projects\chess-bot`.
This updates implementation state, not protocol v1. Preparing this handover is
documentation/commit/push only; no new implementation or measurements this turn.

## Usage, authority and working method

Check account usage FIRST. Stop before either window reaches 10% remaining.
Begin checkpointing at 35%, earlier if consumption is rapid. Reserve headroom
for review, fixes, verification, checkpointing, commits and pushes. Check before
and after each bounded task/delegation; limits are account-wide. Do not use reset
credits or buy credits. If usage is unavailable, do not assume enough allowance
to supervise experiments. Preserve historical reserve breaches in checkpoint.md.

The implementation ended at VERIFIED post-push 42% five-hour / 33% weekly
remaining. Its committed checkpoint records the earlier 48/34 reading. This
documentation turn began at 40/33. These readings are historical on resume.
No reset credit used. No experiment or agent is assumed running after handoff.

Normal reviewed commits and pushes to the existing project remote are explicitly
authorized. No force pushes, destructive history, unrelated remotes, credentials
or binary dumps. Ask before production dependencies. No paid cloud without
separate provider/configuration/cost/shutdown approval.

Use actual `gpt-6-astra` for narrow scientific planning/review and `gpt-6-luna`
for bounded implementation where supported. Never claim unavailable models.
Keep delegation narrow and sequential. Root reads broad context once, then gives
agents specific files, invariants and tested acceptance criteria. Require REAL
runner regressions, not helpers alone or mocks concealing production control flow.
Root assesses completeness before review. Back up drafts before risky edits.
Do not reopen research direction or resolved evaluation cadence.

## Required reading and precedence

Read this file in full, then `docs/research/new-chat-handover-20261109.md` in full
and EVERY prior handover and required context it lists, including:

- docs/research/new-chat-handover-20261108.md
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
infrastructure-only, pilot-unrun and evaluation-absent passages are superseded.
The 9 November accounting contracts remain applicable. This handover supersedes
only the absence of coarse lifecycle timing, NOT remaining detailed accounting.
Read without truncated output; inspect actual source, Git, artifacts and processes.

## Repository and protected artifacts

Branch `codex/opponent-dependence`; existing origin
`https://github.com/Mamunur02/chess-bot.git`. Commit `abe4756` is pushed and matches
local origin tracking. It follows `f49c235`, `ec979be` and `deeb305`. This new
documentation commit follows abe4756; inspect log/status for its hash.

Preserve and exclude five preexisting document changes from routine commits:
modified README.md and docs/research/practical-project-scope.md; untracked
opponent-dependence-decisions.md, opponent-dependence-protocol-draft.md and
opponent-dependence-scope.md under docs/research/.
Baseline: artifacts/calibration-repair-20261104/preserved-document-hashes.json.
All five hashes matched after implementation; only these changes remained after
push. Backups: artifacts/calibration-repair-20261110/runner.before.py.txt and
tests.before.py.txt. Hash audit: same directory's artifact-audit.json.

Development seed9001 pilot is COMPLETE. NEVER restart or overwrite
artifacts/opponent-dependence-v1/pilot-9001-v1/. Its pilot.json SHA256 remains
3b4ae6defd8b0fad6b3c66380ab8c6681990deb7f8309ed3dc2142a109b3186c.
Development: artifacts/opponent-dependence-v1/development/.
Tables: data/syzygy/protocol-v1/; acquisition manifest:
experiments/manifests/syzygy-protocol-v1-acquisition.json.

10 November inspection checked pilot/four checkpoint hashes, development JSONL,
acquisition manifest and eight table hashes against saved audit records. All
matched. The development loader was NOT rerun on 10 November; the prior
9 November audit verified all 2,000 rows through that loader. Artifact integrity
is NOT hash-rejection orchestration coverage. No Python process appeared after
verification/push. Ignored tables/data/models/environments need separate restoration
in a fresh clone. Final labels remain outside calibration and tuning.

## What abe4756 implements, and its limits

Changed scripts/run_endgame_calibration.py, tests/test_endgame_calibration.py and
checkpoint.md. No dependency changed.

- Per-run monotonic ledger partitions coarse wall time into work, persistence,
  cleanup and finalization. All runner JSON writes, including failed attempts,
  suspend the caller phase; cleanup/final snapshot preparation are included.
- Versioned wall_time includes elapsed time, scope and explicit boundary.
  Saved calibration.json ends BEFORE its own final write and says
  final_write_included=false. Returned or attached IN-MEMORY state includes the
  completed or failed final write attempt with a distinct boundary label.
  Do not recursively rewrite a file claiming it includes its own completed write.
- Legacy elapsed_seconds still ends before cleanup/final persistence. Legacy
  scales training_seconds includes tensor setup and progress-callback writes.
  Those timings overlap the exclusive ledger; do not add them to it.
- Detailed work-phase decomposition remains UNFINISHED. Incremental manifests
  currently lack lifecycle timing until finalization. Do not call either complete.

Preserve cumulative attempted predictor/probe counters, isolated per-game deltas,
incremental latency/static persistence, original-error authority, cleanup once,
and full active-game snapshots installed before I/O. Nested predictor/probe
seconds remain diagnostics, never additional exclusive components. Completed
selection counters and attempted work are different. exception.partial_manifest
is in-memory recovery only, NOT guaranteed durable recovery after termination.

Actual Luna implemented this slice. Root strengthened exact fake-clock runner
tests for nonzero work/write/cleanup costs, disk/return boundaries and simultaneous
ValueError/KeyboardInterrupt plus cleanup/final-write failures. Actual Astra
found no blocker and approved ONLY the narrow slice for checkpointing. It reviewed
source without running tests; its Git diff command failed with Not a git repository,
so it compared source with its earlier inspection. Root inspected the actual diff.
Astra noted zero injected finalization duration; root added that assertion and
reran focused checks. WHOLE RUNNER REMAINS UNAPPROVED FOR MEASUREMENTS.

## Next small slices BEFORE measurements

1. Split coarse work into exclusive setup, model loading/saving, labeling,
   encoding, tensor construction, training, latency/static evaluation, game
   runtime and reporting. Preserve failure-time accounting, exclude callbacks
   from caller work where applicable, and retain honest final-write boundaries.
   Add tested incremental lifecycle snapshots before claiming durable progress.
2. Complete cooperative deadlines through setup, labeling, encoding/pretraining.
   Retain partial records and distinguish deadline/interruption/failure/ply cap.
   Unfinished reward stays None; in-flight tensor work cannot be preempted.
   Never report complete with missing or failed required work.
3. Finish provenance: resolved config, development/pilot/model/table hashes,
   source snapshots, Git/diff state, packages, actual hardware/threads/determinism,
   seeds, model/config/surrogate limitations. _provenance still uses bare Git;
   use command-scoped safe.directory. Require complete pilot status in pretraining.
4. Verify all FOUR checkpoint rejection paths, development/acquisition mismatches,
   truly paired model-independent RNG streams and balanced learner colours.
   Add deterministic per-game seconds deltas and explicit delta assertions in
   real deadline/interruption regressions. Keep default suite Torch/table/network
   independent and optional real integration bounded.
5. Run required checks and obtain focused independent WHOLE-RUNNER review.

Reuse the pilot's verified _load_development without invoking the pilot.
reference_failures counts opponent selection exceptions, not proven missing
files; retain actual error text. Preserve scientific settings and trainer defaults.

## Calibration, resource gate and roadmap

No calibration measurements, complete projection, budget freeze, reviewed core
orchestration or core matrix has been completed. Do not infer these from test passes.

After runner repairs/review, run isolated DEVELOPMENT-ONLY evaluation: 100 boards
per model for choice/MSE; 10 warmup plus 3 passes of 30 boards, rotating model order;
10 TOTAL paired starts/model/p with balanced colours, p=0/.25/.5 and 400-ply cap.
Use explicit CLI limits/seeds/starts/order, paired model-independent RNG identities,
fresh outputs and partial records. Separate selection latency from reference work.

Then full-size pretraining timing surrogate: repeat development 1600/400 subsets
to 20000/2500, learner opposite side to move, target=-reference.value. Existing
trainer, all 30 epochs, patience31 ONLY for timing; scientific patience5 and other
settings unchanged. Repetition is not independent training evidence or proof of
full-data stopping. No concurrent project tests/work during timing; disclose
uncontrolled host activity and reserve enough usage to supervise/finalize.

Resolved cadence remains: static quality/MSE at main 0/25/50/75/100%; actual play
and latency at final main/matched and frozen controls. Exact zero-step reuse only
within seed with aliases/provenance. 200 static bundles = 600000 choices plus
600000 predictions; 65 full bundles = 39000 games and 201500 latency/warmup choices.
400-ply cap bounds 15.6 million plies, NOT expected runtime. No intermediate
actual-play curves. Record cadence before final-data access.

Complete projection includes FIVE full-size pretraining blocks, 45 main runs,
five frozen controls, 15 matched-time runs, ALL evaluations and overhead.
U(B)=floor(B/8)-31 for fully recorded transitions;
T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33;
main=15*sum_m T_m; matched=15*T_0. Account for unrecorded decisions and p=.5
transfer assumptions. Prior training-only estimates including matched+30%
contingency: 9.252/24.842/50.826/102.793 hours at 2000/5000/10000/20000.
They exclude remaining costs and approve NO candidate budget.

Freeze largest candidate with 1.3*complete_projected_hours<=36 and GBP60 core,
with explicit cash/energy assumptions. If 2000 fails, only semantics-preserving
batching/caching, tests and remeasurement before infeasibility; never drop seeds.
GBP100 total = 60 core + 20 extensions + 20 contingency. Cash spent0; electricity
unestimated. No paid cloud without separate approval.

After the gate, implement/review remaining core orchestration BEFORE execution.
Preserve seeds101/202/303/404/505, 45 randomized within-block conditions, common
pretrained initialization per block, saved checkpoints and 15 p=.5 equal-wall-time
runs. Protocol v1 governs all remaining defaults and invariants:
python-chess rules; theoretical history-free clock-reset sign(WDL), including
cursed/blessed signs; actual full-history claim_draw=True; fixed learner perspective;
no tablebase in counterfactual targets; replay replies never resampled; terminal
reward once; epsilon.1 training/0 evaluation; UCI ties; named RNG streams.

Then paired analysis with missing-run coverage and trajectory-overlap sensitivity:
five paired seed differences, t interval and paired seed/canonical bootstrap.
Complete core reporting/reproduction before optional specialist/relative Elo,
ensembles and advice/ChessGPT. Optional work must not displace core seeds, analysis
or reporting. Preserve negative results and failures; no unsupported novelty claims.

## Schedule and verification

Today at handover is 10 November 2026, Europe/London. The 8 November gate was
missed. Neither the 9-12 November core window nor 18 November completion is
established. No replacement external deadline supplied. Reassess after measured
gates; move completion as needed while preserving the final TWO FULL reporting/
reproducibility days AFTER execution and analysis. Do not compress scientific gates.

Latest implementation checks, independently observed exit0:
- Default517 passed6 skipped21.31s (elevated Windows UCI):
  artifacts/pytest-lifecycle-timing-full-20261110.
- Optional neural/interaction/targets/pilot/evaluation/calibration153 passed30.56s:
  artifacts/pytest-lifecycle-timing-neural-20261110.
- Ruff . passed; combined mypy src plus pilot/calibration passed50 files.
- Focused calibration/evaluation88 passed1 skipped6.51s:
  artifacts/pytest-lifecycle-timing-root-20261110.
- After final test-only finalization assertion: calibration68 passed1 skipped5.92s,
  artifacts/pytest-lifecycle-timing-final-20261110; Ruff . passed again.
No production code changed after full checks. Tests ran concurrently; durations
are verification observations, NOT isolated calibration measurements. No observed
test/lint/type failures in this slice. Historical failures remain in checkpoint.md.
No code tests rerun for this documentation-only handover.

After changes use NEW basetemps and observe each exit independently:

```powershell
git -c safe.directory=C:/Projects/chess-bot status -sb
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-calibration-NEW-UNIQUE
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src scripts/run_endgame_pilot.py scripts/run_endgame_calibration.py
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py tests/test_endgame_interaction.py tests/test_endgame_targets.py tests/test_endgame_pilot.py tests/test_endgame_evaluation.py tests/test_endgame_calibration.py -q --basetemp artifacts/pytest-neural-NEW-UNIQUE
```

Windows UCI may require escalation. Use workspace uv cache, explicit interpreters
and command-scoped safe.directory; no global security changes. Torch stays optional
in ignored neural-env (historical CPU2.7.0+cpu, NumPy2.5.4, Python3.12.14); GPU
throughput unverified. Maintain checkpoint.md with exact results/failures, process/
Git/artifact state, usage and concrete resume instructions. Distinguish measurements,
projections and unfinished work. No automatic background continuation is implied.
