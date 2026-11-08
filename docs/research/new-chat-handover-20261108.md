# Continue after reviewed calibration persistence repair

Continuation request prepared 8 November 2026 for `C:\Projects\chess-bot`.
This handover updates implementation state, not protocol v1. Its preparation
is documentation/commit/push only; no measurements or new code work authorized
by the act of writing this document.

## Usage, authorization and working method

Check account usage FIRST. Stop before either window reaches 10% remaining.
Begin checkpointing at 35%, earlier if consumption is rapid. Reserve headroom
for independent review, fixes, verification, checkpointing, commits and pushes.
Check before/after each bounded task and delegation. Limits are account-wide.
Do not use reset credits or buy credits. If usage cannot be read, do not assume
enough allowance to supervise an experiment. Preserve historical reserve breaches.

The 7 November implementation ended at a VERIFIED post-push 29% five-hour /
58% weekly remaining; its committed checkpoint records 31/58 before commit.
This documentation turn began at27/58. These are historical, not fresh readings.
No reset credit was used in either turn.

Normal reviewed commits and pushes to the existing project remote are explicitly
authorized. Do not ask again for routine authorized work. No force pushes,
destructive history, unrelated remotes, credentials changes or binary dumps.
Ask before adding production dependencies. No paid cloud without explicit
provider/configuration/cost/shutdown approval.

Use actual `gpt-6-astra` for narrow scientific planning/review and `gpt-6-luna`
for bounded implementation where supported. Never claim an unavailable model
was used. Keep delegation narrow and sequential. Root reads broad context once;
give agents specific files/interfaces/invariants and tested acceptance criteria.
Recent Luna slices omitted requested orchestration tests; require those tests,
not only helper tests. Root must assess completeness before scientific review.
Back up drafts before risky edits. Do not assume agents survive a chat handoff.
Do not reopen research direction or resolved evaluation cadence.

## Required reading and precedence

Read this file in full, then `docs/research/new-chat-handover-20261107.md` in full
and EVERY prior handover and required context it lists:

- `docs/research/new-chat-handover-20261106.md`
- `docs/research/new-chat-handover-20261104.md`
- `docs/research/new-chat-handover-20261024.md`
- `docs/research/new-chat-handover-20261020-evaluation.md`
- `docs/research/new-chat-handover-20261020-continuation.md`
- `docs/research/new-chat-handover-20261020.md`
- `AGENTS.md`; `checkpoint.md` newest entries first
- `CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`; `docs/status.md`; `README.md`
- `docs/research/opponent-dependence-protocol-v1.md`
- `docs/research/opponent-dependence-implementation.md`
- `docs/research/opponent-dependence-literature.md`
- `experiments/summaries/endgame-pilot-9001-v1.md` and companion JSON

Protocol v1 governs science; later handovers update implementation state.
Historical infrastructure-only, pilot-unrun, evaluation-absent and untracked
calibration-file passages are superseded. Likewise, the 7 November handover's
persistence blockers are partially resolved by3550b13 as detailed below; do not
repeat the completed slice. Read without truncated output. Inspect actual code,
Git, artifacts and processes before acting; a test pass is not measurement approval.

## Verified repository and protected work

Branch `codex/opponent-dependence`; origin
`https://github.com/Mamunur02/chess-bot.git`. Starting HEAD3550b13 matches local
origin tracking on8 November and was successfully pushed in the preceding turn.
This documentation commit follows it; inspect log/status for its hash.

Relevant history:
- 5849057: reviewed fixed-start evaluation primitives.
- 2ad7dd8: optional pretraining deadline/progress callbacks.
- 586b0d6: calibration lifecycle repairs; unfinished runner.
- fbf213e: reviewed cumulative attempted predictor/probe accounting.
- beaa117: 7 November continuation documentation.
- 3550b13: reviewed persistence/error/full-game snapshot repair.

Preserve and exclude five preexisting document changes from routine commits:
modified `README.md`, `docs/research/practical-project-scope.md`; untracked
`docs/research/opponent-dependence-decisions.md`,
`docs/research/opponent-dependence-protocol-draft.md`, and
`docs/research/opponent-dependence-scope.md`.
Baseline: `artifacts/calibration-repair-20261104/preserved-document-hashes.json`.
All matched before the7 November push. Persistence backups, including evaluation,
are in `artifacts/calibration-repair-20261107/` (`*.before.py.txt`).
No Python process appeared in the8 November initial inspection.

Development seed9001 pilot is COMPLETE and verified. Never restart or overwrite
`artifacts/opponent-dependence-v1/pilot-9001-v1/`. Its pilot.json SHA256 remains
`3b4ae6defd8b0fad6b3c66380ab8c6681990deb7f8309ed3dc2142a109b3186c`.
Development: `artifacts/opponent-dependence-v1/development/`.
Tables: `data/syzygy/protocol-v1/`; acquisition manifest:
`experiments/manifests/syzygy-protocol-v1-acquisition.json`.
Ignored data, tables, models and environments need separate restoration in a
fresh clone. Final labels remain outside tuning and calibration.

## What 3550b13 implements, and what it does not

Changed scripts/run_endgame_calibration.py, src/chesslab/endgames/evaluation.py,
tests/test_endgame_calibration.py and checkpoint.md. No dependency changed.

- Initial manifest writes now participate in runner failure handling.
- Finalization retains original work/deadline/interruption errors through cleanup
  and write failures, recording secondary errors separately. Cleanup occurs once.
- A failed durable write exposes latest state through exception.partial_manifest;
  a preserved original may also carry persistence_error/cleanup_error. This is
  IN-MEMORY recovery while the exception/process survives, not guaranteed disk
  recovery after process termination or storage failure.
- Full latest active-game snapshot is installed before writes: start/perspective/p,
  moves, canonical keys, choices, denominators and all existing game counters.
  Game write failure aborts further work; no unbounded list of historical snapshots.
  Persistence or cleanup failures cannot return success.
- In play_fixed_game, ordinary-error progress callbacks run inside the active
  exception handler. A flag avoids duplicate callback during unwinding. This
  permits original error preservation if callback writing also fails. Successful
  callbacks retain the existing returned-game-failure contract; rules/selection
  and scientific outputs are unchanged.

Actual Luna implemented helpers but omitted requested run-level regressions.
Root completed those tests and simplified recovery. Actual Astra found that an
ordinary game error could be masked after leaving its exception handler; root
fixed it and extended real-game tests to ValueError, TimeoutError and
KeyboardInterrupt with simultaneous game/final-write failures. Astra re-review
approved ONLY this slice for checkpointing. Astra did not rerun tests and did
NOT approve the full runner or measurements.

Retain fbf213e cumulative attempted predictor calls/boards/failures/elapsed
and WDL/DTZ probe counts/failures/raw errors/timings. These remain nested
diagnostics, never additional exclusive wall components. Final manifests have
attempted_work, but continuous durable counters, per-game deltas and partial
latency/static records remain unfinished. Existing successful optional runner
test mocks game/static evaluation and exercises the real trainer on4/2 inputs;
its name does not prove paired streams or balanced colours.

## Immediate remaining repairs BEFORE measurements

1. Incremental latency/static accounting and deadline records: retain partial
   attempted work between items, persist partial latency, and check deadlines
   between prediction and choice helpers. Call static helpers one item at a time.
2. Complete per-game attempted-work deltas and exclusive setup/game runtime/
   persistence/model load-save/encoding/tensor/training/reporting wall accounting.
   Do not label cumulative totals per-game or add nested diagnostics twice.
   Audit finalization overhead too; current elapsed is not complete exclusive
   accounting. Preserve the new original-error and full-snapshot contracts.
3. Complete cooperative checks through setup, labeling, encoding, latency and
   games. Distinguish deadlines, interruptions, failed games and ply caps;
   unfinished reward stays None. Never report complete with missing/failed work.
   In-flight tensor operations cannot be preempted.
4. Finish provenance: resolved config, development/pilot/model/table hashes,
   source snapshots, Git/diff state, packages, actual hardware/threads,
   determinism, seeds and timing-surrogate limitations. _provenance still calls
   bare Git; use command-scoped safe.directory. Require complete pilot status
   in pretraining and record complete model/config/surrogate provenance.
5. Strengthen orchestration tests: all four checkpoint-hash mismatches,
   development/acquisition mismatches, genuinely paired RNG streams and balanced
   colours, remaining deadline/partial-accounting paths, and bounded optional real
   model/trainer integration. Keep default tests free of Torch/tables/network.
6. Required checks and focused whole-runner review before ANY timing measurement.

Reuse verified pilot _load_development without invoking the pilot. Validate
pretrained and final beta0/0.5/1 hashes against pilot.json. Acquisition provenance
keys match the pilot writer. Neural game counters describe completed selections;
retain attempted work separately. Opponent reference_failures counts selection
exceptions, not proven missing-table errors; keep actual exception text.

## Calibration, resource gate and subsequent roadmap

No calibration measurements, complete resource projection, budget freeze,
reviewed core orchestration or core matrix has been completed.

After repairs/review, run isolated DEVELOPMENT-ONLY evaluation:
100 boards/model for choice/MSE; latency10 warmup +3 passes of30 boards with
rotating model order;10 TOTAL paired starts/model/p with balanced learner colours,
p0/.25/.5 and400-ply cap. Explicit CLI bounds, seeds, starts and model-independent
paired RNG identities. Separate selection time from reference metrics.

Then full-size pretraining timing surrogate: repeat development1600/400 subsets
to20000/2500, learner opposite side to move, target=-reference.value. Existing
trainer runs all30 epochs, patience31 ONLY for timing; scientific patience5 and
other architecture/optimizer defaults unchanged. Repeated data are not independent
training evidence or proof of full-data stopping. Use fresh output directories,
incremental failures and enough usage for supervision/finalization. No concurrent
project tests/work during timing; disclose uncontrolled host activity.

Retain resolved evaluation cadence: static quality/MSE at main0/25/50/75/100%;
actual play and latency at final main/matched checkpoints and frozen controls.
Exact zero-step reuse only within seed with aliases/provenance.200 static bundles
=600000 choices+600000 predictions;65 full bundles=39000 games (13000 per p)
and201500 latency/warmup choices.400-ply cap bounds15.6 million plies, not expected
runtime. No intermediate actual-play curves. Record cadence before final-data access.

Complete projection includes five full-size pretraining blocks,45 main runs,
five frozen controls,15 matched-time runs, every evaluation and overhead.
For fully recorded transitions U(B)=floor(B/8)-31;
T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33;
main=15*sum_m T_m, matched=15*T_0. Account for unrecorded decisions and p=.5
transfer assumptions. Prior training-only estimates including matched+30%
contingency:9.252/24.842/50.826/102.793 hours at2000/5000/10000/20000; these
exclude remaining costs and approve no budget.

Freeze largest candidate with1.3*complete_projected_hours<=36 and GBP60 core,
stating cash/energy assumptions. If2000 fails, only semantics-preserving batching/
caching with tests and remeasurement before infeasibility; never drop seeds.
GBP100 total=60core+20extensions+20contingency. Cash spent0; electricity unestimated.
No paid cloud without explicit separate approval.

After gate, implement/review remaining core orchestration before execution.
Keep seeds101/202/303/404/505,45 randomized within-block conditions, checkpoints
and15 p=.5 equal-wall-time runs. Protocol invariants: python-chess rules;
history-free clock-reset sign(WDL), including cursed/blessed signs; actual
full-history claim_draw=True; fixed learner perspective; no tablebase inside
counterfactual targets; replay replies never resampled; terminal reward once;
epsilon.1 training/0 evaluation; UCI ties; named RNGs. All other defaults: protocol v1.

Then paired analysis, missing-run coverage and trajectory-overlap sensitivity;
five paired seed differences, t interval and paired seed/canonical bootstrap.
Core report/reproduction precedes optional specialist/relative Elo, ensembles,
and advice/ChessGPT. Preserve negative results and failures; never invent novelty.

## Schedule reassessment

Today at handover is8 November2026 Europe/London. Original31 October-1 November
reporting window passed. Provisional revised plan was5-8 November repairs/review/
calibration/full gate;9-12 November orchestration/core conditional on gates;
13-16 November analysis/audits;17-18 November reporting/reproducibility.
Only the persistence slice was completed late7 November; substantial repairs
still remain.8 November full-gate completion is unsubstantiated, as is delivery
on18 November. Treat dates as provisional, not commitments or an external deadline.
If gates slip, move completion and preserve the final TWO FULL reporting days.
No replacement external deadline supplied. Calendar pressure must not weaken gates,
reduce seed blocks, omit analysis or displace reporting with optional extensions.

## Verification and resume commands

Latest implementation checks7 November, independently observed exit0:
- Focused calibration+evaluation63 passed1 skipped2.94s:
  artifacts/pytest-persistence-reviewfix-20261107.
- Full default492 passed6 skipped13.70s (elevated Windows UCI):
  artifacts/pytest-persistence-full-final-20261107.
- Broader optional neural/interaction/targets/pilot/evaluation/calibration128
  passed17.86s: artifacts/pytest-persistence-neural-final-20261107.
- Ruff . passed; mypy src plus pilot/calibration passed50 files.
- Staged scope/whitespace passed. Five protected document hashes and pilot
  manifest rechecked unchanged. No Python process after checks/push.
Earlier pre-review-fix490/6 and126 passes were superseded by final checks above.
No code tests rerun for this documentation-only handover.

After repairs, use NEW basetemps and observe each exit independently:

```powershell
git -c safe.directory=C:/Projects/chess-bot status -sb
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-calibration-NEW-UNIQUE
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src scripts/run_endgame_pilot.py scripts/run_endgame_calibration.py
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py tests/test_endgame_interaction.py tests/test_endgame_targets.py tests/test_endgame_pilot.py tests/test_endgame_evaluation.py tests/test_endgame_calibration.py -q --basetemp artifacts/pytest-neural-NEW-UNIQUE
```

Windows UCI may require escalation. Use workspace uv cache, explicit interpreters
and command-scoped safe.directory, no global security change. Torch stays optional
in ignored neural-env (historical CPU2.7.0+cpu, NumPy2.5.4, Python3.12.14); GPU
throughput unverified. Maintain checkpoint.md with exact results, failures,
process/Git state, artifact paths, usage and concrete resume instructions.
Distinguish measurements, projections and unfinished work.
