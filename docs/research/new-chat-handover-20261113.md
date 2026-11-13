# Continue after reviewed detailed calibration timing

Continuation request prepared 13 November 2026 for `C:\Projects\chess-bot`.
This updates implementation state, not protocol v1. Preparing this handover is
documentation/commit/push only; no experiments or new implementation this turn.

## Usage, authority and working method

Check account usage FIRST. Stop BEFORE either window reaches 10% remaining.
Begin checkpointing at 35%, earlier if consumption is rapid. Reserve headroom
for review, fixes, verification, checkpointing, commits and pushes. Check before
and after each bounded task/delegation; limits are shared account-wide. Do not
use reset credits or buy credits. If usage is unavailable, do not assume enough
allowance to supervise experiments. Preserve historical reserve breaches.

The implementation ended at VERIFIED post-push 25% five-hour /86% weekly
remaining. Its committed checkpoint records the earlier31/87 reading. This
documentation turn began22/86. These readings are historical on resume.
No reset credit used. No experiment or agent is assumed running after handoff.

Normal reviewed commits and pushes to the existing project remote are explicitly
authorized. No force pushes, destructive history, unrelated remotes, credentials
or binary dumps. Preserve unrelated changes. Ask before adding a production
dependency. No paid cloud without separate provider/configuration/cost/shutdown
approval. Routine authorized local work does not need another confirmation.

Use actual `gpt-6-astra` for narrow scientific planning/review and `gpt-6-luna`
for bounded implementation where supported. Never claim unavailable models.
Keep delegation narrow and sequential. Root reads broad context once and gives
agents specific files, invariants and tested acceptance criteria. Require REAL
orchestration regressions, not helper tests or mocks hiding production control
flow. Luna omitted requested stronger regressions in the latest slice; root
completed them. Root must assess completeness before independent review.
Back up drafts before risky edits. Do not reopen direction or resolved cadence.

## Required reading and precedence

Read this file IN FULL, then `docs/research/new-chat-handover-20261110.md` IN FULL
and EVERY prior handover and required context it lists, including:

- docs/research/new-chat-handover-20261109.md
- docs/research/new-chat-handover-20261108.md
- docs/research/new-chat-handover-20261107.md
- docs/research/new-chat-handover-20261106.md
- docs/research/new-chat-handover-20261104.md
- docs/research/new-chat-handover-20261024.md
- docs/research/new-chat-handover-20261020-evaluation.md
- docs/research/new-chat-handover-20261020-continuation.md
- docs/research/new-chat-handover-20261020.md
- docs/research/new-chat-handover-20261019.md (historical pilot-unrun state)
- AGENTS.md; checkpoint.md newest entries first
- CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md; docs/status.md; README.md
- docs/research/opponent-dependence-protocol-v1.md
- docs/research/opponent-dependence-implementation.md
- docs/research/opponent-dependence-literature.md
- experiments/summaries/endgame-pilot-9001-v1.md and companion JSON

Protocol v1 governs science; newer handovers/checkpoints govern implementation
state. Older infrastructure-only, pilot-unrun and evaluation-absent passages are
superseded. This handover supersedes the absence of detailed phase timing and
snapshots at existing writes, NOT remaining deadline/progress/provenance gates.
Read without truncated output. Inspect actual source, artifacts, Git and processes.

## Repository, protected work and environment

Branch `codex/opponent-dependence`; existing origin
`https://github.com/Mamunur02/chess-bot.git`. Implementation `ef6a4b9` is pushed
and matches local origin tracking. It follows `a81cb97` and `abe4756`. This new
documentation commit follows ef6a4b9; inspect log/status for its hash.

Preserve and exclude FIVE preexisting document changes from routine commits:
modified README.md and docs/research/practical-project-scope.md; untracked
opponent-dependence-decisions.md, opponent-dependence-protocol-draft.md and
opponent-dependence-scope.md under docs/research/.
Baseline: artifacts/calibration-repair-20261104/preserved-document-hashes.json.
All five matched after implementation and only these changes remained after push.

Development seed9001 pilot is COMPLETE. NEVER restart or overwrite
artifacts/opponent-dependence-v1/pilot-9001-v1/. Its pilot.json SHA256 remains
3b4ae6defd8b0fad6b3c66380ab8c6681990deb7f8309ed3dc2142a109b3186c.
Development: artifacts/opponent-dependence-v1/development/.
Tables: data/syzygy/protocol-v1/; acquisition manifest:
experiments/manifests/syzygy-protocol-v1-acquisition.json.
12 November inspection checked pilot/four checkpoints, development JSONL,
acquisition and eight table hashes against saved records; all matched. The
development loader was NOT rerun;9 November verified all2,000 rows through it.
Hash integrity is not hash-rejection orchestration coverage. Final labels stay
outside tuning/calibration. No Python process appeared after verification/push.

Backups/hash audit: artifacts/calibration-repair-20261112/ (runner, calibration
tests, neural trainer/tests and original virtual-environment configurations).
Both venvs initially failed because their Python3.12.14 home was missing.
Restored exactly3.12.14 under
artifacts/python-runtime/cpython-3.12.14-windows-x86_64-none/ and repointed
.venv/pyvenv.cfg and artifacts/neural-env/pyvenv.cfg. Sandbox download failed DNS;
elevated uv download succeeded. An existing external python3.12 executable was
NOT force-replaced. Torch2.7.0+cpu imports successfully. No production dependency
or lockfile changed. Ignored data/tables/models/environments/runtime require
separate restoration in a fresh clone. GPU throughput remains unverified.

## What ef6a4b9 implements, and its limits

Changed scripts/run_endgame_calibration.py, src/chesslab/endgames/neural.py,
tests/test_endgame_calibration.py, tests/test_endgame_neural.py and checkpoint.md.

- Schema-v2 exclusive ledger replaces coarse work with setup, model_setup,
  labeling, encoding, tensor_setup, training, warmup, latency, prediction, choice,
  games and reporting, plus persistence, cleanup and finalization.
- Phases include driver overhead. model_setup includes loads/construction;
  reporting includes provenance/source copies. These runners perform NO model
  checkpoint saves: do not infer save calibration from this instrumentation.
- Optional trainer phase callback marks tensor conversion/validation and then
  optimizer/training. Scientific defaults, RNG, optimizer and results stay fixed;
  callback exceptions propagate. Reporting callbacks/JSON writes suspend caller
  game/training timing. Failed operations retain their elapsed work.
- Existing JSON writes, including initial and game records, carry incremental
  lifecycle snapshots. Each snapshot excludes its OWN write and includes prior
  write attempts. Final SAVED wall_time remains pre-final-write with inclusion
  false. Returned/attached IN-MEMORY final timing includes the final attempted
  write, including failed writes. Do not recursively rewrite a file claiming to
  include its own completed write.
- Legacy elapsed_seconds ends before cleanup/final write; legacy scales
  training_seconds includes tensor setup and progress writes. These and nested
  predictor/probe diagnostics overlap the ledger: NEVER add them to it.

Preserve cumulative attempted-work accounting, original-error authority, cleanup
once, full active-game snapshots installed BEFORE I/O, incremental latency/static
persistence and isolated per-game attempted deltas. Completed selections and
attempted work are different. exception.partial_manifest remains in-memory only,
NOT guaranteed durable recovery after termination/storage loss.

No new persistence cadence was added. Setup/labeling/encoding still need finer
progress and cooperative deadline coverage. Instrumentation is NOT completion
of the whole runner. Actual Astra found no blocker and approved ONLY this slice
for checkpointing, without running tests. Root fixed its cosmetic indentation
note and a test fixture import issue afterward, then ran full checks.
WHOLE CALIBRATION RUNNER REMAINS UNAPPROVED FOR MEASUREMENTS.

## Next small slices BEFORE measurements

1. Complete remaining cooperative setup, labeling, encoding and pretraining
   deadlines and partial progress. Preserve records; distinguish deadline,
   interruption, failure and ply cap. Unfinished reward stays None. In-flight
   tensor operations cannot be preempted. Never mark failed/missing work complete.
2. Finish provenance: resolved configuration; development/pilot/model/table hashes;
   source snapshots; Git/diff state; packages; actual hardware/threads/determinism;
   seeds; full model/config/surrogate limitations. _provenance still uses bare
   Git: use command-scoped safe.directory. Require complete pilot status in
   pretraining. Review model-save/load overhead needed for the resource projection.
3. Verify all FOUR checkpoint rejection paths; development/acquisition mismatches;
   truly paired model-independent RNG streams and balanced learner colours.
   Add deterministic per-game seconds deltas and explicit deltas in real deadline/
   interruption regressions. Keep default suite Torch/table/network independent.
4. Required checks and focused independent WHOLE-RUNNER review before measurements.

Reuse verified pilot _load_development WITHOUT invoking the pilot. Preserve
scientific settings and trainer defaults. reference_failures counts opponent
selection exceptions, not proven missing files; retain actual error text.

## Calibration, complete resource gate and subsequent roadmap

NO calibration measurements, complete resource projection, budget freeze,
reviewed core orchestration or core matrix has been completed.

After runner repair/review, run isolated DEVELOPMENT-ONLY evaluation:
100 boards/model for choice/MSE;10 warmup plus3 passes of30 boards with rotating
model order;10 TOTAL paired starts/model/p, balanced colours, p0/.25/.5,400-ply
cap. Explicit CLI bounds/seeds/starts/order, model-independent paired streams,
fresh outputs and partial records. Separate selection latency from reference work.

Then full-size pretraining timing surrogate: repeat development1600/400 subsets
to20000/2500, learner opposite side to move, target=-reference.value. Existing
trainer, all30 epochs, patience31 ONLY for timing; scientific patience5 and all
other defaults unchanged. Repeated examples are not independent training evidence
or proof of full-data stopping. No concurrent project tests/work during timing;
disclose uncontrolled host activity and reserve usage to supervise/finalize.

Resolved cadence: static quality/MSE at main0/25/50/75/100%; actual play/latency
at final main/matched and frozen controls. Exact zero-step reuse only within seed
with aliases/provenance.200 static bundles=600000 choices+600000 predictions;
65 full bundles=39000 games+201500 latency/warmup choices.400-ply cap bounds
15.6million plies, NOT expected runtime. No intermediate actual-play curves.
Record cadence before final-data access; do not reopen it.

Complete projection includes FIVE full-size pretraining blocks,45 main runs,
five frozen controls,15 matched-time runs, ALL evaluation and overhead.
For fully recorded transitions U(B)=floor(B/8)-31;
T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33;
main=15*sum_m T_m; matched=15*T_0. Account for unrecorded decisions and p=.5
transfer assumptions. Prior training-only estimates including matched+30%
contingency:9.252/24.842/50.826/102.793h at2000/5000/10000/20000.
They exclude remaining costs and approve NO candidate budget.

Freeze largest candidate satisfying1.3*complete_projected_hours<=36 and GBP60
core, with explicit cash/energy assumptions. If2000 fails, only semantics-preserving
batching/caching, tests and remeasurement before infeasibility; NEVER drop seeds.
GBP100 total=60core+20extensions+20contingency. Cash spent0; electricity unestimated.
No paid cloud without separate approval.

After gate, implement/review remaining core orchestration BEFORE execution:
seeds101/202/303/404/505,45 randomized within-block conditions, common pretrained
initialization per block, saved checkpoints and15 p=.5 equal-wall-time runs.
Preserve python-chess rules; history-free clock-reset sign(WDL), including cursed/
blessed signs; actual full-history claim_draw=True; fixed learner perspective;
no tablebase in counterfactual targets; replay replies never resampled; terminal
reward once; epsilon.1 training/0 evaluation; UCI ties; named RNG streams.
Protocol v1 governs remaining architecture/replay/optimizer defaults.

Then paired analysis with missing-run coverage and trajectory-overlap sensitivity:
five paired seed differences, t interval and paired seed/canonical bootstrap.
Core reporting/reproduction BEFORE optional specialist/relative-Elo, ensembles,
advice and ChessGPT. Optional work must not displace core seeds/analysis/reporting.
Preserve negative results/failures; no unsupported novelty or strength claims.

## Schedule and verification

Today13 November2026 Europe/London.8 November gate and9-12 November core window
were missed.18 November completion is NOT established. No replacement external
deadline supplied. Reassess after measured gates; move completion as needed while
preserving TWO FULL reporting/reproducibility days AFTER execution AND analysis.
Do not compress gates or imply that reserved days have fixed calendar dates.

Latest implementation checks, independently observed exit0:
- Default519 passed10 skipped31.47s (elevated Windows UCI):
  artifacts/pytest-detailed-full-20261113.
- Optional neural/interaction/targets/pilot/evaluation/calibration161 passed25.61s:
  artifacts/pytest-detailed-neural-full-20261113.
- Focused optional calibration/neural94 passed14.23s:
  artifacts/pytest-detailed-root-neural-20261113-b.
- Focused default70 passed5 skipped6.28s:
  artifacts/pytest-detailed-root-20261113.
- Ruff . passed; combined mypy src plus pilot/calibration passed50 files.
- Protected document/pilot hashes unchanged; staged scope/whitespace passed.

Tests overlapped for verification; durations are NOT calibration measurements.
Preserve failures: missing interpreter and sandbox DNS above; root Ruff11 long
lines fixed; first optional root run11 failed/83 passed15.29s due to reimporting
Torch in a new fixture (duplicate registration/downstream tensor-layout errors).
Fixed by capturing/reusing real modules before mocked setup;94 and161 reruns
passed. Failed path: artifacts/pytest-detailed-root-neural-20261113.
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
and command-scoped safe.directory, no global security change. Maintain checkpoint.md
with exact results/failures, process/Git/artifact state, usage and concrete resume
instructions. Distinguish measurements, projections and unfinished work.
