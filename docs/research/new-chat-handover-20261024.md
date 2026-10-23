# Continue from evaluation primitives to cost calibration

User continuation request, 24 October 2026. Continue the approved research in
`C:\Projects\chess-bot`. Do not reopen research direction or restart the completed
development seed9001 pilot. This handover updates state, not scientific protocol.

## Usage, models and authority

Check account usage FIRST, before repository work. Stop before either window
reaches 10% remaining. Begin checkpointing at 35% remaining, earlier if usage
falls quickly; check before/after bounded tasks and before delegation. Leave
enough headroom for review, fixes, checks, checkpoint, commit and push. Do not
use reset credits or buy credits. The 20 October implementation ended at
13% five-hour/71% weekly remaining; 24 October documentation began at96%/98%.
These are historical readings; obtain fresh ones. An earlier continuation
breached the reserve (5% remaining); the corrected historical record must remain.

Use actual `gpt-6-astra` for narrow scientific planning/review and `gpt-6-luna`
for bounded implementation where supported. Root reads broad context once;
delegate precise relevant files/invariants rather than repeated broad reading.
Keep agents narrow and sequential. Do not assume old agents persist.

Normal reviewed commits and pushes to the existing remote are explicitly
authorized, including this handover. No force pushes, destructive history,
unrelated remotes, credential changes or binary dumps. Do not ask again for
routine authorized work. No new production dependency without authorization.

## Required reading

Read this file in full, then these prior handovers in full:

- `docs/research/new-chat-handover-20261020-evaluation.md`
- `docs/research/new-chat-handover-20261020-continuation.md`
- `docs/research/new-chat-handover-20261020.md`

Also read all their required context: `AGENTS.md`, `checkpoint.md` newest first,
`CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`, `docs/status.md`,
`docs/research/opponent-dependence-protocol-v1.md`,
`docs/research/opponent-dependence-implementation.md`,
`docs/research/opponent-dependence-literature.md`,
`experiments/summaries/endgame-pilot-9001-v1.md` and companion JSON, and `README.md`.
Protocol v1 governs science; later handovers govern implementation state.
Historical statements that neural work is unauthorized, the pilot unrun, or
evaluation primitives absent are superseded. Inspect actual code and artifacts.

## Verified starting state

- Branch `codex/opponent-dependence`, remote
  `https://github.com/Mamunur02/chess-bot.git`.
- `5849057` is committed and pushed, following `2e9ed03`. It adds
  `src/chesslab/endgames/evaluation.py`, `tests/test_endgame_evaluation.py`,
  the evaluation handover and checkpoint updates. This documentation commit
  follows5849057; inspect Git log/tracking for its hash and push state.
- Preserve modified `README.md`, `docs/research/practical-project-scope.md`,
  and untracked `docs/research/opponent-dependence-decisions.md`,
  `docs/research/opponent-dependence-protocol-draft.md`,
  `docs/research/opponent-dependence-scope.md`; exclude them from routine commits.
- On24 October, `scripts/run_endgame_calibration.py` is absent. No calibration
  measurements, complete resource projection, budget freeze or core matrix
  resulted from the preceding work. This request is documentation only.
- No Python process appeared in24 October `Get-Process python*` inspection.
  Inspect processes again before timing; no experiment is assumed running.

## What evaluation now implements and its limits

`evaluate_choices` uses learner=board.turn, epsilon0 existing selection,
selected/best theoretical q, outcome-loss indicator, categorical loss divided
by2, canonical identity, selected UCI and best-q strata. `evaluate_predictions`
uses learner opposite side to move and target minus reference.value.
`play_fixed_game` accepts a supplied board, learner, caller-owned RNGs and p;
retains full history, checks claim-aware terminals, records moves, visited
learner choice errors/denominators, neural counts, canonical keys, failures,
cap/deadline truncations and progress callbacks. Default cap400 plies; unfinished
games have reward=None. General runner semantics were not changed.

Root review repaired confusion between exceptions and policy mistakes; Astra
review then found missing opponent reference-failure accounting, also repaired.
Neural counters cover completed selections only; failed calls may do uncounted
work. Callback persistence failures propagate; the calibration harness must
preserve partial state and failure/interruption status. Static helpers currently
process a supplied sequence without per-item deadline/progress reporting; call
bounded items or add tested support before claiming a total deadline. Latency
must time move selection separately from reference-metric work. Instrument
prediction/reference work in the harness where needed; do not infer missing
cost counters from existing records. All exceptions during opponent selection
currently increment reference_failures: preserve the actual failure text and
do not equate that counter with proven missing-table errors.

Checks on20 October: full default447 passed5 skipped in11.97s before the final
small opponent-failure patch; final focused20 passed in0.25s; final Ruff passed;
final mypy src plus pilot passed49files. No full-suite rerun after that last
patch was claimed. Initial focused coverage was insufficient and was expanded.
The prior whitespace check reported an extra checkpoint EOF blank line; this
documentation update removes it. No tests were run for this documentation-only
update; record its whitespace check separately.

## Resolved evaluation cadence

Astra reviewed and accepted this cadence on20 October; it is resolved planning,
not an implemented matrix or a resource-budget freeze. Preserve it explicitly
in the later resolved run configuration before final-data access:

- Static quality and MSE at main0/25/50/75/100% checkpoints.
- Actual play and latency at final main/matched checkpoints and frozen controls.
- Reuse zero-step evaluations only within a seed with identical model, starts,
  RNG and configuration. Retain aliases/provenance, never pool seed blocks.
- 200 distinct static bundles:45*4+5+15. At3000 boards,600000 benchmark choices
  and600000 MSE predictions. Static reference labels may be shared.
- 65 full bundles:45+5+15. Each has200 starts against each p0/.25/.5:
  39000 games total,13000 per p. Latency100 warmup+3*1000 gives201500 choices.
- 400-ply cap gives15.6million maximum game plies, not expected duration.

Static curves meet the intermediate learning-curve requirement; do not claim
intermediate actual-play curves. Older245-full-bundle inventories are superseded.

## Next bounded implementation and measurements

1. Inspect/reuse evaluation primitives and verified pilot `_load_development`.
   Implement/test `scripts/run_endgame_calibration.py`; never launch the pilot
   script or overwrite `artifacts/opponent-dependence-v1/pilot-9001-v1/`.
2. Load development only. Verify pretrained and three beta model hashes against
   pilot.json before use. Keep final data/labels outside calibration access.
3. Proposed bounded sample:100 development boards/model for choice/MSE;
   latency10 warmup plus3 passes of30 boards;10 paired starts/model/p with
   balanced learner colours and400-ply cap. Four models: pretrained and three
   beta finals. Fix seeds/starts/order explicitly. Increase only if necessary
   for defensible timing, not to choose a favorable method result.
4. Explicit CLI item bounds and total deadline checked between items/plies;
   fresh output directories; incremental partial records; distinct failures,
   interruptions and truncations. Test successful and failed runner paths.
5. Full-size pretraining timing surrogate: repeat development1600/400 subsets
   to20000/2500, time encoding/tensor construction and all30 epochs using the
   existing trainer. Patience31 forces timing workload ONLY; scientific patience
   remains5 and other optimizer/architecture settings remain fixed. Repetition
   supplies no independent data or evidence of full-data stopping behavior.
6. Measure saves, loads, reporting and other overhead separately; never add
   nested probe/target/optimizer time twice. Preserve sources, Git/diff state,
   environment, hardware, threads, seeds, data/model hashes and counters.
   Isolate timing from tests and other project work. Record uncontrolled host
   activity as a limitation. Do not start a run without enough usage to supervise.

## Resource gate and subsequent roadmap

Use pilot update-aware scaling: for fully recorded transitions,
U(B)=floor(B/8)-31; T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33.
Account explicitly for decisions without recorded transitions. Main training
15*sum_m T_m; matched-time15*T_0. Pilot p=.5 transfer rates are assumptions.
Training-only plus matched and30% contingency estimates9.252/24.842/50.826/
102.793h at2000/5000/10000/20000 exclude remaining costs; none is approved.

Complete projection includes five full-size pretraining blocks,45 main runs,
five frozen controls,15 matched-time runs, all scheduled evaluation and overhead.
Freeze largest of{2000,5000,10000,20000} satisfying
1.3*complete_projected_hours<=36 and GBP60 core. Make cash/energy assumptions
explicit. If2000 fails, only semantics-preserving batching/caching with tests
and remeasurement before reporting infeasibility; do not drop seeds.
GBP100 ceiling=60core+20extensions+20contingency. Cash spent0; electricity still
unestimated. No paid cloud resource without provider/config/cost/shutdown approval.

After gate: implement/review core orchestration before execution. Preserve all
five seeds101/202/303/404/505,45 conditions, randomized within-block order,
saved checkpoints and15 p=.5 equal-wall-time runs. Follow original handover and
protocol for paired analysis, missing-run accounting, overlap sensitivity,
reporting and extensions. Core report precedes optional specialist/relative-Elo,
ensemble and advice/ChessGPT work. Today is24 October; original calendar targets
are now tighter, not permission to skip gates. Reserve31 October-1 November for
reporting/reproducibility and record any infeasibility honestly.

Scientific invariants remain: python-chess rules; history-free clock-reset
theoretical sign(WDL), including cursed/blessed signs; actual full-history
claim_draw=True; fixed learner perspective; no tablebase in counterfactual
targets; observed replay replies never resampled; terminal reward once;
epsilon.1 training/0 evaluation; UCI ties; explicit named RNGs. Architecture,
optimizer, replay and all remaining defaults are in the original handover and
protocol. Never tune on final labels or invent results/novelty.

## Verification and durable checkpoint

Use command-scoped Git safe.directory, workspace uv cache and explicit Python:

```powershell
git -c safe.directory=C:/Projects/chess-bot status -sb
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-NEW-UNIQUE
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src scripts/run_endgame_pilot.py
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py tests/test_endgame_interaction.py tests/test_endgame_targets.py tests/test_endgame_pilot.py tests/test_endgame_evaluation.py -q --basetemp artifacts/pytest-neural-NEW-UNIQUE
```

Extend checks to the calibration script/tests. Observe each exit independently;
fresh basetemps; Windows UCI may need escalation. Torch remains optional in
ignored artifacts/neural-env (CPU2.7.0, NumPy2.5.4 historically); no GPU throughput
verified. Data/table paths and provenance are in the original handover. Maintain
checkpoint.md with exact checks, failures, artifacts, process/Git state, usage
and concrete resume commands. No automatic background continuation is implied.
