# Continue after reviewed attempted-work accounting

Continuation request prepared 7 November 2026 for `C:\Projects\chess-bot`.
This updates implementation state, not the scientific protocol. The chat
preparing this file is documentation/commit/push only; no measurements approved.

## Usage, authority and working method

Check account usage FIRST. Stop before either window reaches 10% remaining.
Begin checkpointing at 35%, earlier if consumption is rapid. Reserve enough
headroom for review, fixes, verification, checkpointing, commits and pushes.
Check before/after bounded tasks and delegation; usage is shared across agents.
Do not use reset credits or buy credits. If usage cannot be read, do not assume
enough allowance to launch a supervised experiment. Preserve historical reserve
breaches in checkpoint.md. The 6 November implementation ended at a VERIFIED
post-push 14% five-hour / 71% weekly remaining; its committed checkpoint records
the earlier 23% / 73% reading. This documentation turn began at 89% / 67%.
These are historical readings, not permission to skip a fresh check.

Normal reviewed commits and pushes to the existing project remote are explicitly
authorized. Do not ask again for routine authorized work. No force pushes,
destructive history, unrelated remotes, credentials changes or binary dumps.
Ask before adding production dependencies. No paid cloud without explicit
provider/configuration/cost/shutdown approval. No reset was used by this agent.

Use actual `gpt-6-astra` for narrow scientific planning/review and `gpt-6-luna`
for bounded implementation where supported. Never claim unavailable models
were used. Keep delegation narrow and sequential. Root reads broad context once
and gives agents specific files, interfaces, invariants and acceptance criteria.
Do not repeat broad reading across agents. Require tested slices: recent Luna
work needed root to complete requested orchestration regressions. Back up drafts
before risky edits. Do not assume previous agents remain active or continue
automatically. Do not reopen the approved research direction.

## Required reading and precedence

Read this file in full, then `docs/research/new-chat-handover-20261106.md` in full
and all prior handovers/context it lists:

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
calibration-file passages are superseded. Both calibration files were committed
in 586b0d6; fbf213e adds the accounting slice described below. Read context once
without truncated output. Inspect actual repository, artifacts and processes.

## Verified starting state and protected work

Branch `codex/opponent-dependence`; origin
`https://github.com/Mamunur02/chess-bot.git`. Starting HEAD `fbf213e` matches local
origin tracking on 7 November; its push succeeded in the previous implementation
turn. This documentation commit follows it; inspect log/status for its hash.

- `5849057`: reviewed fixed-start evaluation primitives.
- `2ad7dd8`: reviewed optional pretraining deadline/progress callbacks.
- `586b0d6`: tested calibration lifecycle repairs, runner unfinished.
- `8fbc2ff`: 6 November handover.
- `fbf213e`: reviewed cumulative attempted-work accounting and tests.

Preserve and exclude five preexisting document changes from routine commits:
modified `README.md`, `docs/research/practical-project-scope.md`; untracked
`docs/research/opponent-dependence-decisions.md`,
`docs/research/opponent-dependence-protocol-draft.md`, and
`docs/research/opponent-dependence-scope.md`. All five matched saved hashes on
7 November. Baseline: `artifacts/calibration-repair-20261104/preserved-document-hashes.json`.
Pre-accounting backups: `artifacts/calibration-repair-20261106/`.
No Python process appeared in the 7 November `Get-Process python*` inspection.

Development seed9001 pilot is COMPLETE and verified. Never restart or overwrite
`artifacts/opponent-dependence-v1/pilot-9001-v1/`. Its `pilot.json` SHA256 was
rechecked on 7 November and remains
`3b4ae6defd8b0fad6b3c66380ab8c6681990deb7f8309ed3dc2142a109b3186c`.
Development: `artifacts/opponent-dependence-v1/development/`.
Tables: `data/syzygy/protocol-v1/`; acquisition manifest:
`experiments/manifests/syzygy-protocol-v1-acquisition.json`.
Data, tables, models, raw artifacts and environments are ignored and unavailable
in a fresh clone unless separately restored. Final labels remain outside tuning.

## What fbf213e accomplished, and its limits

Only scripts/run_endgame_calibration.py, tests/test_endgame_calibration.py and
checkpoint.md changed. `_TimedPredictor` now retains cumulative attempted calls,
input boards, failures and elapsed seconds through local phase resets.
`_TimedTablebase` wraps WDL/DTZ probes, retaining attempted calls, elapsed seconds,
failures and raw exception text. Both runners write `attempted_work` during
finalization and close the original table once. These timings are NESTED
diagnostics, never extra exclusive wall components to add to elapsed time.

Actual Luna implemented counters and initial tests; its follow-up added a
labeling failure test but omitted requested evaluation/reset regressions. Root
expanded coverage to real selector/reference failures and KeyboardInterrupt
through mocked setup, plus deterministic cumulative-reset accounting. Actual
Astra reviewed the final diff, found no introduced blocker and approved this
narrow slice for checkpointing. Astra did not rerun tests and did NOT approve
the complete runner or measurements. No production dependency changed.

Cumulative attempted_work currently reaches the FINAL manifest. Continuous
durable counters, per-game attempted-work deltas, complete exclusive timings,
partial latency persistence and write-failure recovery remain unfinished.
Passing tests do not establish complete orchestration or measurement readiness.
The existing optional success test still mocks game/static evaluation, writes
120 game files and trains the real network for 30 epochs on reduced 4/2 inputs.
Its name mentions pairing but does not prove paired streams or balanced colours.

Retain accepted evaluation primitives and pretraining callbacks. Trainer default
results/settings remain unchanged. Deadlines are cooperative; tensor operations
cannot be preempted. Scientific patience stays 5; patience 31 for 30 epochs is
authorized ONLY for the full-size timing surrogate.

## Immediate remaining repairs, before any measurement

1. Complete incremental latency/static/game accounting and persistence. Measure
   exclusive setup, game runtime, persistence, model loads/saves, encoding,
   tensor construction, training and reporting. Retain partial attempted work
   in incomplete selections. Separate nested probe/predictor diagnostics to
   avoid double-counting. Do not present cumulative totals as per-game costs.
2. Preserve latest FULL game snapshot before writes (moves, canonical keys,
   choices and denominators). Test initial/progress/final write failures and
   cleanup failures, retaining the original error and accessible partial state.
   Failed persistence must not silently turn an incomplete run into success.
3. Complete deadline checks through setup, labeling/encoding, between prediction
   and choice helpers, latency items and games. Persist partial latency records
   incrementally. Distinguish deadline/interruption/failed games/ply caps;
   unfinished reward stays None. Never report complete with missing/failed work.
4. Complete provenance: resolved config, development/pilot/model/table hashes,
   source snapshots, Git/diff state, packages, actual hardware/threads,
   determinism, seeds and surrogate limitations. `_provenance` still invokes
   bare Git; use command-scoped safe.directory. Pretraining must require a
   complete pilot status and record full model/config/surrogate provenance.
5. Strengthen successful and failed orchestration tests: reject each of the four
   model hash mismatches, development/acquisition mismatches, prove paired RNG
   streams and balanced colours, test deadline/persistence/cleanup paths and
   optional real model/trainer integration. Default tests need no Torch/tables/
   network. Run required checks and focused independent review before timing.

Reuse verified pilot `_load_development` without invoking the pilot. Validate
four checkpoint hashes against pilot.json: pretrained and final beta 0/0.5/1.
Acquisition provenance keys match the pilot writer; earlier suspicion was wrong.
Game primitive neural counters cover completed selections only. Opponent
reference_failures counts selection exceptions, not proven missing tables;
retain actual error text. Do not alter scientific behavior to simplify logging.

## Measurements only after repairs and approval

Evaluation calibration: 100 development boards/model for choice/MSE; latency
10 warmup plus 3 passes of 30 boards with rotating model order; 10 TOTAL paired
starts/model/p, balanced learner colours, p=0/.25/.5, 400-ply cap. Explicit CLI
bounds, fixed seeds/starts/order and model-independent paired RNG identities.
Time selection separately from reference metrics; call static helpers one item
at a time. Increase samples only for defensible timing, never favorable outcomes.

Full-size pretraining timing surrogate: repeat development 1600/400 subsets to
20000/2500, encode learner opposite side to move, target=-reference.value.
Use the existing trainer for all 30 epochs, patience31, otherwise fixed model
and optimizer. Repeated data are not independent data or evidence of actual
full-data stopping. Fresh output directories and incremental failure records.
Isolate measurements from tests and other project work; disclose uncontrolled
host activity. Do not start without enough usage to supervise and finalize.

## Resource gate and subsequent roadmap

No calibration measurements, complete resource projection, budget freeze,
reviewed core orchestration or core matrix has been completed.

Retain resolved cadence: static quality/MSE at main 0/25/50/75/100%; actual play
and latency at final main/matched checkpoints and frozen controls. Reuse exact
zero-step evaluations only within seed with aliases/provenance. Inventory:
200 static bundles = 600000 choices + 600000 predictions; 65 full bundles =
39000 games (13000 per p) and 201500 latency/warmup choices. 400-ply cap bounds
15.6 million plies, not expected runtime. No intermediate actual-play curves.
Record cadence in resolved config before final-data access.

Projection includes five full-size pretraining blocks, 45 main runs, five frozen
controls, 15 matched-time runs, all evaluation and overhead. For fully recorded
transitions: U(B)=floor(B/8)-31 and
T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33;
main=15*sum_m T_m, matched=15*T_0. Account for unrecorded decisions and disclose
p=.5 transfer assumptions. Prior training-only estimates including matched and
30% contingency:9.252/24.842/50.826/102.793 hours at2000/5000/10000/20000;
they exclude remaining costs and approve no candidate budget.

Freeze largest candidate satisfying1.3*complete_projected_hours<=36 and GBP60
core, stating cash/energy assumptions. If2000 fails, only semantics-preserving
batching/caching with tests and remeasurement before declaring infeasibility;
never drop seeds. GBP100 total=60core+20extensions+20contingency. Cash spent0;
electricity unestimated. No paid cloud without separate explicit approval.

Preserve seeds101/202/303/404/505,45 randomized within-block conditions, saved
checkpoints and15 p=.5 equal-wall-time runs. Scientific invariants: python-chess
rules; history-free clock-reset theoretical sign(WDL) including cursed/blessed
signs; actual full-history claim_draw=True; fixed learner perspective; no
tablebase inside counterfactual targets; replay replies never resampled;
terminal reward once; epsilon.1 training/0 evaluation; UCI ties; named RNGs.
Protocol v1 governs architecture/replay/optimizer and all remaining defaults.

After full gate, implement/review orchestration, execute core, perform paired
analysis with missing-run coverage and overlap sensitivity, then core report/
reproduction. Preserve five paired seed differences, t interval and paired
seed/canonical bootstrap. Specialist/relative Elo, ensembles and advice/ChessGPT
are later optional work subordinate to reporting. Never invent results/novelty.

## Schedule reassessment

Today at handover is7 November2026 Europe/London. Original31 October-1 November
reporting window has passed. Provisional revised plan:5-8 November repair/review/
calibration/full gate;9-12 November orchestration/review/core ONLY after gates;
13-16 November analysis/audits;17-18 November exclusively reporting/reproducibility.
Substantial runner repairs remain on7 November;8 November gate completion is
uncertain and neither execution feasibility nor18 November completion is proven.
Reassess against actual progress. If gates slip, shift completion while keeping
the final TWO FULL reporting days. No replacement external deadline supplied.
Calendar pressure never permits weakened gates, fewer seeds or omitted analysis.

## Verification and resume commands

Latest implementation checks,6 November, each observed exit0:

- Focused21 passed,1 skipped in1.17s: artifacts/pytest-accounting-root-20261106.
- Full default470 passed,6 skipped in15.57s, elevated Windows UCI:
  artifacts/pytest-accounting-full-20261106.
- Broader optional neural/interaction/targets/pilot/evaluation/calibration:
  106 passed in21.12s: artifacts/pytest-accounting-neural-20261106.
- Ruff . passed; mypy src plus pilot/calibration passed50 files.
- Whitespace/staged checks passed. No experiment launched; no Python process
  appeared after tests. Prior failures remain recorded in checkpoint.md.

No code tests rerun for this documentation-only handover. After repairs use
fresh basetemps and observe every exit independently:

```powershell
git -c safe.directory=C:/Projects/chess-bot status -sb
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-calibration-NEW-UNIQUE
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src scripts/run_endgame_pilot.py scripts/run_endgame_calibration.py
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py tests/test_endgame_interaction.py tests/test_endgame_targets.py tests/test_endgame_pilot.py tests/test_endgame_evaluation.py tests/test_endgame_calibration.py -q --basetemp artifacts/pytest-neural-NEW-UNIQUE
```

Windows UCI may require escalation. Use workspace uv cache, explicit interpreters
and command-scoped Git safe.directory, no global security change. Torch stays
optional in ignored neural-env (historical CPU2.7.0+cpu, NumPy2.5.4,
Python3.12.14); GPU throughput unverified. Maintain checkpoint.md with exact
results/failures, process/Git state, artifact paths, usage and concrete resume
instructions. Distinguish measurements, projections and unfinished work.
