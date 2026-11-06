# Continue calibration repair after the lifecycle checkpoint

Continuation request prepared 6 November 2026 for `C:\Projects\chess-bot`.
This handover updates implementation state. It does not approve measurements.
The chat producing it is documentation/commit/push only.

## Usage, authority and working method

Check account usage FIRST. Stop before either window reaches 10% remaining.
Begin checkpointing at 35%, earlier if consumption is rapid, leaving substantial
headroom for review, fixes, verification, checkpointing, commits and pushes.
Check before/after bounded tasks and delegation. Do not use reset credits or buy
credits. Limits are shared across agents. If readings fail, do not assume enough
allowance to launch a supervised experiment. Historical reserve breaches remain
in checkpoint.md; do not erase them. The last implementation reading was 14%
five-hour / 86% weekly before final checkpoint/commit/push, not a verified
post-push reading. This documentation turn began at 86% / 83%; obtain fresh usage.

Normal reviewed commits and pushes to the existing project remote are explicitly
authorized. Do not ask again for routine authorized work. No force pushes,
destructive history, unrelated remotes, credentials changes or binary dumps.
Ask before adding production dependencies. No paid cloud without explicit
provider/configuration/cost/shutdown approval.

Use actual `gpt-6-astra` for narrow scientific planning/review and `gpt-6-luna`
for bounded implementation where supported. Do not claim unavailable models were
used. Keep delegation narrow and sequential. Root reads broad context once and
gives agents specific files, interfaces, invariants and acceptance criteria.
Avoid repeated broad context ingestion. Back up uncommitted drafts before risky
edits; use small patches and immediate syntax/focused checks. Do not assume old
agent sessions persist or are working. Continue the approved direction, not a
new research-direction discussion.

## Required reading and precedence

Read this file in full, then `docs/research/new-chat-handover-20261104.md` in full
and all prior handovers/context it requires:

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
Historical infrastructure-only, pilot-unrun and evaluation-absent passages are
superseded. In particular, the 4 November claim that the calibration drafts are
untracked is now superseded: both are committed in 586b0d6. Read the required
context once, avoiding truncated tool output, and inspect actual repository,
artifacts and processes before acting.

## Verified starting state and protected work

Branch `codex/opponent-dependence`; origin
`https://github.com/Mamunur02/chess-bot.git`. Starting HEAD `586b0d6` matches local
origin tracking on 6 November. It was successfully pushed in the previous chat.
This documentation commit follows it; inspect Git log/status for its hash.

- `5849057`: reviewed fixed-start evaluation primitives.
- `2ad7dd8`: reviewed optional pretraining deadline/progress callbacks.
- `af4b6cf`: 4 November handover.
- `586b0d6`: tested calibration lifecycle slice, explicitly unfinished runner.

Preserve and exclude the five preexisting document changes from routine commits:
modified `README.md`, `docs/research/practical-project-scope.md`; untracked
`docs/research/opponent-dependence-decisions.md`,
`docs/research/opponent-dependence-protocol-draft.md`, and
`docs/research/opponent-dependence-scope.md`.
Their saved baseline hashes are in
`artifacts/calibration-repair-20261104/preserved-document-hashes.json`.

The calibration script and tests are now available in a fresh clone, but ignored
data, environments, models and raw artifacts are not. Current local byte hashes:

- `scripts/run_endgame_calibration.py`:
  `76f4c701f526c549540a83d0bd220bf19d53d983fcbbef83693d316c2bfe8cf0`
- `tests/test_endgame_calibration.py`:
  `c57ede2b28b2a905632caad3447eb7b53eb90765bea2b3ea417ea6b303c02b38`

Git checkout line-ending conversion can alter byte hashes; inspect Git diffs too.
No Python process appeared in the 6 November `Get-Process python*` inspection.
No experiment or automatic background continuation is implied.

Development seed9001 pilot is COMPLETE. Never restart or overwrite
`artifacts/opponent-dependence-v1/pilot-9001-v1/`. Its `pilot.json` SHA256 was
rechecked on 6 November and remains
`3b4ae6defd8b0fad6b3c66380ab8c6681990deb7f8309ed3dc2142a109b3186c`.
Development data: `artifacts/opponent-dependence-v1/development/`.
Tables: `data/syzygy/protocol-v1/`. Acquisition manifest:
`experiments/manifests/syzygy-protocol-v1-acquisition.json`.
Partition/audit locations and pilot measurements are in the older handovers.
Final labels remain outside calibration and tuning.

## What the lifecycle checkpoint actually accomplished

Both runners now create initial manifests before setup; setup failures,
deadlines and KeyboardInterrupt are captured. Opened tables are closed with
cleanup exceptions recorded separately. Pretraining initializes `scales`.
Duplicate acquisition verification and unused type-ignore were removed.
Torch intra/inter-op threads are configured and read back; deterministic
algorithms are enabled. CLI returned failed/deadline/interrupted statuses yield
nonzero exit. These are partial repairs, not evidence of a finished runner.

Actual Luna introduced an indentation error and stopped without testing. Root
repaired it; the failed intermediate is preserved at
`artifacts/calibration-repair-20261104/failed-luna-edit.py.txt`.
Actual Astra's narrow lifecycle review identified a bad prediction stub and
cleanup-before-final-persistence risk. Root fixed both after that review.
Astra did not approve measurements or review all accounting/provenance logic;
the final fixes were tested but not given a second independent review.

Tests now cover setup failure/deadline/interruption and unsuccessful CLI status.
The optional successful test mocks evaluation/data/table components and verifies
120 game files. Its name mentions paired streams but it does NOT establish full
pairing semantics. It also runs the real ValueNetwork/pretrain for 30 epochs on
mocked inputs with timing sizes reduced to 4/2. This catches the completed-fit
`scales` regression; it is not full-size timing or real-table evaluation evidence.

The pretrain callbacks retain default scientific training behavior and exact
regression results. Deadlines are cooperative; in-flight tensor operations cannot
be preempted. Exceptions propagate, and interrupted fitting does not return
success or restore a best state. Scientific patience remains 5; patience 31 for
30 epochs is authorized ONLY for the full-size timing surrogate.

## Immediate remaining work: repair before measurements

Inspect the current code and repair in small, tested slices:

1. Complete attempted predictor/probe counts, failure counts and timings; measure
   game runtime, setup, persistence, model loads/saves, encoding, tensor creation,
   training and reporting. Separate exclusive wall-time components from nested
   diagnostics; never add probe/predictor time twice. Preserve partial counters
   when work fails, including incomplete selections.
2. Complete deadline checks through setup, labeling/encoding, between prediction
   and choice helpers, latency items and games. Preserve partial latency records
   incrementally. Distinguish deadline, interruption, failed games and ply caps;
   unfinished reward stays None. Never report complete with failed/missing work.
3. Preserve the latest full game snapshot before attempting persistence, including
   moves, canonical keys, choices and denominators. Test initial/progress/final
   write failures and cleanup failures, retaining the original error. Current
   passing lifecycle tests do not cover these paths comprehensively.
4. Complete provenance: resolved configuration, development/pilot/model/table
   hashes, source snapshots, Git/diff state, packages, actual hardware/threads,
   determinism, seeds and timing-surrogate limitations. `_provenance` currently
   invokes bare Git, which can fail ownership checks; use command-scoped
   safe.directory. Pretraining still needs complete-pilot status validation and
   fuller configuration/model/surrogate provenance.
5. Strengthen actual orchestration tests: model hash rejection at each checkpoint,
   development/acquisition mismatch, successful and failed evaluation, paired RNG
   streams and balanced colours, deadlines/persistence/cleanup, optional real
   model/trainer paths. Default tests remain independent of Torch, tables and
   network. Run full required checks and obtain focused review before timing.

Reuse verified pilot `_load_development` without invoking the pilot. Validate
all four evaluation checkpoint hashes against pilot.json: pretrained and final
beta 0/0.5/1 only. Acquisition provenance keys match the pilot writer; an older
suspicion otherwise was incorrect.

Evaluation calibration: 100 development boards/model for choice/MSE; latency
10 warmup plus 3 passes of 30 boards with rotating model order; 10 TOTAL paired
starts/model/p, balanced learner colours, p=0/.25/.5, 400-ply cap. Use explicit CLI
bounds, fixed seeds/starts/order and model-independent paired RNG identities.
Time move selection separately from reference metrics. Call static helpers one
item at a time. Built-in game neural counters cover completed selections only;
opponent reference_failures includes selection exceptions, not proven missing
tables. Retain actual error text. Increase samples only for defensible timing,
never favorable method outcomes.

Full-size pretraining surrogate: repeat development 1600/400 subsets to
20000/2500, encode learner opposite side to move and target=-reference.value.
Run existing trainer all 30 epochs, patience31, otherwise fixed architecture and
optimizer. Repetition is not independent data or evidence of full-data stopping.
Use fresh output directories and incremental failures. Isolate measurements from
tests and other project work; disclose uncontrolled host activity. Do not start
without adequate usage to supervise and finalize.

## Fixed resource gate and roadmap

No calibration measurements, complete resource projection, budget freeze,
reviewed core orchestration or core matrix has been completed.

Retain resolved cadence: static quality/MSE at main 0/25/50/75/100%; actual play
and latency at final main/matched checkpoints and frozen controls. Reuse identical
zero-step evaluation only within seed with exact aliases/provenance. Inventory:
200 static bundles = 600000 choices + 600000 predictions; 65 full bundles =
39000 games (13000 per p) and 201500 latency/warmup choices. The 400-ply cap bounds
15.6 million plies, not expected runtime. No intermediate actual-play curves.
Record cadence in resolved configuration before final-data access.

Projection must include five full-size pretraining blocks, 45 main runs, five
frozen controls, 15 matched-time runs, all evaluation and overhead. For fully
recorded transitions use U(B)=floor(B/8)-31 and
T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33;
main=15*sum_m T_m and matched=15*T_0. Account for unrecorded decisions and disclose
p=.5 transfer assumptions. Prior training-only estimates including matched and
30% contingency are 9.252/24.842/50.826/102.793 hours at
2000/5000/10000/20000; they exclude remaining costs and approve no budget.

Freeze the largest candidate satisfying 1.3*complete_projected_hours<=36 and
GBP60 core, with explicit cash/energy assumptions. If 2000 fails, only
semantics-preserving batching/caching with tests and remeasurement before
declaring infeasibility; never drop seeds. GBP100 total = 60 core + 20 extensions
+ 20 contingency. Cash spent is zero; electricity remains unestimated.

Keep seeds101/202/303/404/505, all45 randomized within-block conditions, saved
checkpoints and15 p=.5 equal-wall-time runs. Preserve python-chess rules;
history-free clock-reset theoretical sign(WDL), including cursed/blessed signs;
full-history actual claim_draw=True; fixed learner perspective; no tablebase in
counterfactual targets; observed replay replies never resampled; terminal reward
once; epsilon .1 training/0 evaluation; UCI ties and explicit named RNGs.
All other architecture/replay/optimizer defaults remain governed by protocol v1.

After the full gate, implement/review remaining orchestration, execute core,
perform paired analysis with missing-run coverage and overlap sensitivity, then
core reporting/reproduction. Follow protocol for five paired seed differences,
t interval and paired seed/canonical bootstrap. Specialist/relative Elo,
ensembles and advice/ChessGPT remain later optional work subordinate to reporting.
Never invent measurements, novelty or completion from plans.

## Schedule

Check today's date. At handover it is 6 November 2026, Europe/London. The original
31 October-1 November reporting window has passed. The revised provisional plan
recorded on 4-5 November is: 5-8 November repair/review/calibration/full gate;
9-12 November orchestration/review and core ONLY after gates; 13-16 November
analysis/audits; 17-18 November exclusively reporting/reproducibility.
This is not an external deadline or a measured feasibility claim. Reassess it
against actual progress. If gates slip, move completion while preserving the
final two full reporting days. No replacement external deadline was supplied.
Calendar pressure never permits weakened gates, fewer seeds or omitted analysis.

## Verification and exact resume commands

Last implementation checks (4-5 November), each exit0:

- Full default: 462 passed, 6 skipped in13.46s, elevated Windows UCI;
  `artifacts/pytest-calibration-full-20261104`.
- Optional calibration: 14 passed in9.57s;
  `artifacts/pytest-calibration-neural-20261104-b`.
- Ruff . passed; mypy src plus pilot/calibration passed50 files.
- Earlier focused default: 13 passed,1 skipped in1.11s. Initial optional test
  failed on prediction batch length; preserved under
  `artifacts/pytest-calibration-neural-20261104-a`.
- Broader optional neural suite was NOT rerun in that slice. No dependency added.

No code tests rerun for this documentation-only handover. Use fresh basetemps and
observe every exit independently after repairs:

```powershell
git -c safe.directory=C:/Projects/chess-bot status -sb
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-calibration-NEW-UNIQUE
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src scripts/run_endgame_pilot.py scripts/run_endgame_calibration.py
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py tests/test_endgame_interaction.py tests/test_endgame_targets.py tests/test_endgame_pilot.py tests/test_endgame_evaluation.py tests/test_endgame_calibration.py -q --basetemp artifacts/pytest-neural-NEW-UNIQUE
```

Windows UCI may need escalation. Use workspace uv cache, explicit interpreters
and command-scoped Git safe.directory; no global security change. Torch remains
optional in ignored neural-env (historical CPU2.7.0+cpu, NumPy2.5.4,
Python3.12.14); GPU throughput unverified. Keep checkpoint.md current with exact
results/failures, process/Git state, artifact paths, usage and concrete resume
instructions. Distinguish measurements, projections and unfinished work.
