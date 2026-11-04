# Continue calibration repair after reviewed pretraining hooks

Continuation request prepared 4 November 2026 for C:\Projects\chess-bot.
This is a documentation handover, not a new experiment or an approved runner.

## Authority, usage and schedule

Check account usage FIRST. Stop before either window reaches10% remaining.
Begin checkpointing at35%, earlier if consumption is rapid; allow substantial
headroom for review, fixes, checks, commits and pushes. Check before/after each
bounded task and delegation. Never use reset credits or buy credits. Previous
implementation ended at14% five-hour/86% weekly remaining after push; checkpoint
records17/86 before finalization. On4 November documentation began at74/96.
These are historical readings; obtain fresh ones. Preserve earlier recorded
reserve breaches rather than rewriting history.

Use actual GPT-6 Astra for narrow scientific planning/review and GPT-6 Luna for
bounded implementation where supported. Select the actual model identifiers;
do not claim a model was used if unavailable. Keep delegation sequential and
narrow. Root reads broad context once and supplies specific files, interfaces,
invariants and acceptance criteria. Previous broad implementation consumed usage
before producing a trustworthy runner; use smaller tested slices. Do not assume
old agent sessions persist or are working.

Normal reviewed commits and pushes to the existing project remote are authorized.
No force pushes, destructive history, unrelated remotes, credentials changes or
binary dumps. No new production dependency without authorization. Do not ask again
for routine authorized work. The current user request was handover plus commit/
push only; this document requests continuation work in the new chat.

Today at handover is4 November Europe/London. Original18 October–1 November
calendar and31 October–1 November reporting reserve have passed. Do not describe
those dates as future or imply the study finished on schedule. Reassess remaining
work and establish an explicit revised schedule, reserving its final two days for
reporting/reproducibility. No replacement external deadline has been supplied.
Continue bounded repair while clarifying any deadline needed for later execution;
calendar pressure never permits skipping gates, seeds, failure accounting or
analysis. Do not reopen the research-direction discussion.

## Required reading

Read this file in full, then docs/research/new-chat-handover-20261024.md in full
and every prior handover/context file it requires:

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
infrastructure-only, pilot-unrun, evaluation-absent and calibration-script-absent
claims are superseded. Inspect actual source, artifacts and processes before work.

## Verified Git, artifacts and preserved changes

Branch codex/opponent-dependence; origin https://github.com/Mamunur02/chess-bot.git.
Starting HEAD2ad7dd8 matches origin tracking on4 November. It follows83fe0f2 and
5849057. This documentation commit follows2ad7dd8; inspect log/status for its hash
and push state. No Python process appeared in4 November Get-Process python*.

Preserve and exclude from routine commits the five preexisting document changes:
modified README.md and docs/research/practical-project-scope.md; untracked
docs/research/opponent-dependence-decisions.md,
docs/research/opponent-dependence-protocol-draft.md and
docs/research/opponent-dependence-scope.md.

Two additional UNTRACKED LOCAL draft files exist and must be inspected/preserved:

- scripts/run_endgame_calibration.py — SHA256
  190e3eb5fed46455b02f246b9177ba956700a1e4230259ab293fb630932db2bd
- tests/test_endgame_calibration.py — SHA256
  9dc8a4fb3aee5fef2bb5b4478e0c9ef5fe134f7f27a821cf4cd9e04fc91f57b7

These drafts are not part of the pushed implementation and will not appear in a
fresh clone. Continue in this local checkout. If absent elsewhere, reconstruct
from the requirements; do not claim the runner was already committed or verified.
Do not run the drafts as experiments before repairs, tests and review.

Development seed9001 pilot is COMPLETE and verified. Never restart or overwrite
artifacts/opponent-dependence-v1/pilot-9001-v1/. Its pilot.json SHA256 remains
3b4ae6defd8b0fad6b3c66380ab8c6681990deb7f8309ed3dc2142a109b3186c.
Development data: artifacts/opponent-dependence-v1/development/.
Tables: data/syzygy/protocol-v1/; acquisition manifest:
experiments/manifests/syzygy-protocol-v1-acquisition.json.
Other partition locations/audit details are in the original handover; do not
access final labels for calibration or tuning.

## Implemented versus unfinished

5849057 adds reviewed fixed-start evaluation primitives and tests. Their API and
accounting limits are described in the24 October handover and remain applicable.
2ad7dd8 adds reviewed optional pretrain callbacks in
src/chesslab/endgames/neural.py and tests/test_endgame_neural.py:

- deadline_check returns bool; checks before tensor setup, epochs, minibatches,
  validation and after completed-epoch callbacks; raises TimeoutError.
- progress_callback receives EpochRecord after completed-epoch bookkeeping.
- Exceptions propagate; interrupted training does not return success or restore
  best state. An in-flight tensor operation cannot be preempted.
- Defaults preserve optimizer, shuffle, validation, stopping and restoration.
  Exact-result regression covers callback-enabled versus default execution.

Root implemented hooks; actual gpt-6-astra reviewed them without blockers. Actual
gpt-6-luna wrote the unfinished runner draft and was interrupted for usage.
No calibration measurements, complete resource projection, budget freeze,
reviewed core orchestration or core matrix has been completed.

## Immediate repair scope and known blockers

Inspect the draft rather than trusting helper tests. Root/Astra found:

1. Pretraining appends to result['scales'] without initializing that key, so a
   completed fit can crash before success persistence.
2. Evaluation reports one Torch thread without setting/reading actual settings.
3. Setup failures occur before the durable manifest/exception handler.
4. Probe, game-runtime, persistence, load/save and other overhead accounting is
   incomplete. Nested diagnostic times must not be added twice.
5. Acquisition verification is duplicated. Its provenance keys DO match the
   pilot writer; the initial root suspicion about those keys was incorrect.
6. CLI can exit successfully for a returned failed/deadline manifest.
7. Combined mypy fails on an unused type-ignore at script line23.

Earlier draft defects included extra initial model, model-specific RNG streams,
doubled games, latency order/deadline gaps and lost partial game snapshots.
Some were subsequently edited: independently verify their final behavior.
Tests must cover real orchestration success and failures, not merely helpers.
Default tests must remain independent of Torch/table files; optional neural
integration should exercise actual model/trainer with bounded mocked inputs.

Patience31 for30 epochs is explicitly authorized for the full-size TIMING
SURROGATE ONLY. Astra initially misflagged this; scientific patience stays5.
Repetition is not independent data or evidence of actual full-data stopping.

Repair in small bounded slices, with focused tests and a narrow review before
timing. Use the existing verified pilot _load_development helper without invoking
the pilot. Verify development provenance and all four model hashes against
pilot.json before use. Models: pretrained and final beta0/0.5/1 only.

Evaluation calibration defaults:100 development boards/model for choice/MSE;
latency10 warmup plus3 passes of30 boards;10 total paired starts/model/p with
balanced learner colours, p0/.25/.5 and400-ply cap. Explicit CLI item bounds,
fixed seeds/starts/order; rotate model order across latency passes. Pair RNG
streams across models (no model name in paired stream identity). Increase samples
only for defensible timing, never favorable method outcomes.

Call static helpers one item at a time for deadline checks. Time move selection
separately from reference metrics. Instrument attempted predictor/probe work and
failures; game built-in neural counts cover completed selections only. Opponent
reference_failures counts all selection exceptions, not proven missing tables.
Keep actual error text. Preserve latest full game snapshot before persistence,
including canonical keys, choices, moves and denominators; handle callback write
failures, KeyboardInterrupt, deadlines, failed games and ply truncations distinctly.
Unfinished reward stays None. Never report complete with failed/missing work.

Pretraining timing: repeat development1600/400 subsets to20000/2500, encode
learner opposite side to move and target = -reference.value, run existing trainer
all30 epochs with patience31; other optimizer/architecture settings fixed.
Measure encoding, tensor construction, training, saves, loads and reporting
separately. Use fresh output directories and incremental failure records, source
snapshots, Git/diff state, hardware/packages/threads, seeds and data/model hashes.
Isolate timing from tests and other project work; disclose uncontrolled host
activity. Do not start a run without adequate usage to supervise and finalize it.

## Resolved cadence and resource gate

Do not reopen cadence: static quality/MSE at main0/25/50/75/100%; actual play and
latency at final main/matched checkpoints and frozen controls. Reuse identical
zero-step evaluations only within seed, preserving aliases and provenance.
200 static bundles =600000 choices+600000 predictions;65 full bundles =39000
games (13000 per p) and201500 latency/warmup choices.400-ply cap bounds15.6million
plies, not expected duration. No intermediate actual-play curves are claimed.
Record this in the eventual resolved run configuration before final-data access.

Complete projection: five full-size pretraining blocks,45 main runs,5 frozen
controls,15 matched-time runs, all scheduled evaluation and overhead. Pilot
update-aware scaling for fully recorded transitions: U(B)=floor(B/8)-31;
T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33. Main15*sum_m T_m;
matched15*T_0. Account for unrecorded decisions and disclose p=.5 transfer
assumptions. Training-only estimates including matched and30% contingency are
9.252/24.842/50.826/102.793h at2000/5000/10000/20000; these exclude other costs.

Freeze largest candidate satisfying1.3*complete_projected_hours<=36 and GBP60
core. State cash/energy assumptions explicitly. If2000 fails, only semantics-
preserving batching/caching with tests and remeasurement before infeasibility;
never drop seeds. GBP100 total=60core+20extensions+20contingency. No paid cloud
without provider/config/cost/shutdown approval. Cash spent0; electricity remains
unestimated. No core execution before full gate and reviewed orchestration.

Keep seeds101/202/303/404/505,45 randomized within-block conditions, saved
checkpoints and15 p=.5 equal-wall-time runs. Scientific invariants remain
python-chess rules; theoretical history-free clock-reset sign(WDL), including
cursed/blessed signs; actual full-history claim_draw=True; fixed learner
perspective; no tablebase in counterfactual targets; observed replay replies
never resampled; terminal reward once; epsilon.1 training/0 evaluation; UCI ties;
explicit named RNGs. All remaining defaults are in protocol/original handover.

After gate, implement/review orchestration, execute core, perform paired analysis
with missing-run coverage and overlap sensitivity, then core reporting and
reproduction. Specialist/relative Elo, ensembles and advice/ChessGPT are optional
later work and must not displace core reporting. Never invent measurements,
novelty or infer finished features from plans.

## Verification history and resume commands

24 October final checks, NOT rerun on4 November:

- Optional neural hooks17 passed10.79s.
- Default suite EXCLUDING draft449 passed5 skipped10.99s, elevated Windows UCI,
  artifacts/pytest-calibration-hooks-20261024-full-b.
- Ruff . passed; mypy src plus pilot passed49 files.
- Including draft mypy failed unused type-ignore. Draft default4 passed1 skipped
  in0.90s; optional runner success was NOT verified by root.
- Earlier full attempt had a draft failure then sandbox UCI stall; interrupted
  exit1. Do not call that a pass. Initial89-character Ruff line was fixed.

Commands after repairs, observing every exit independently and fresh basetemps:

```powershell
git -c safe.directory=C:/Projects/chess-bot status -sb
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-calibration-NEW-UNIQUE
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src scripts/run_endgame_pilot.py scripts/run_endgame_calibration.py
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py tests/test_endgame_interaction.py tests/test_endgame_targets.py tests/test_endgame_pilot.py tests/test_endgame_evaluation.py tests/test_endgame_calibration.py -q --basetemp artifacts/pytest-neural-NEW-UNIQUE
```

Windows UCI may need escalation. Keep Torch optional in ignored neural-env;
historical CPU Torch2.7.0+cpu, NumPy2.5.4, Python3.12.14; GPU unverified.
Use command-scoped Git safe.directory and workspace uv cache. Preserve failures.
Maintain checkpoint.md with exact results, process/Git/artifact state, current
usage and concrete resume commands. No background continuation is implied.
