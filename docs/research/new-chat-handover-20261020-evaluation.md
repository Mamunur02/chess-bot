# Fixed-start evaluation continuation, 20 October 2026

Read this alongside new-chat-handover-20261020-continuation.md and the original
new-chat-handover-20261020.md; their scientific invariants, required context,
resource limits and subsequent roadmap remain applicable. Check account usage
FIRST. Start checkpointing at 35% remaining or earlier on rapid consumption;
stop before either window reaches 10%. Never use reset credits.

Starting HEAD was 2e9ed03 on codex/opponent-dependence, matching local origin
tracking. Preserve the five preexisting document changes listed in the previous
handover. Routine reviewed commits/pushes to the existing remote are authorized.
The completed seed9001 pilot must not be restarted or overwritten.

## Evaluation cadence to resolve before final-data access

Retain static quality and MSE at all saved main checkpoints (0/25/50/75/100%).
Actual play and latency are proposed at final main/matched checkpoints and
frozen controls. Reuse a zero-step evaluation only within its seed when model,
starts, RNG and configuration match exactly; never pool across seed blocks.
This gives 200 distinct static bundles (45*4+5+15), 600000 benchmark choices
and 600000 MSE predictions; 65 full bundles (45+5+15), 39000 games (13000 per p)
and 201500 timing/warmup choices. The 400-ply cap bounds games at 15.6 million
plies; it is not an expected runtime estimate. Static reference labels may be
shared. Independent scientific review and final resolution are recorded below.

## Work still required after evaluation primitives

Implement/test scripts/run_endgame_calibration.py using the verified pilot
development loader; verify pretrained and three beta checkpoint hashes against
pilot.json. Use only development data, fresh output paths, paired streams,
explicit sample/deadline limits and incremental failure records. Proposed
calibration: 100 static boards/model; 10 warmup plus 3*30 latency choices;
10 paired starts/model/p, balanced learner colours, at most 400 plies.

Measure a full-size pretraining timing surrogate by repeating development
1600/400 subsets to 20000/2500 and running all 30 epochs (patience31 solely
for timing; scientific patience remains5). Record encoding/tensor construction,
saves/loads and other overhead without double-counting nested timings. This is
not independent data or evidence of full-data stopping behavior. Isolate timing
from tests and other project work. Preserve source, environment, Git, seed,
data/model hashes, counters, failures and incomplete records.

Complete the update-aware projection for five pretraining blocks, 45 main runs,
five frozen controls, 15 matched-time runs, the cadence above, and all overhead.
Freeze only the largest of {2000,5000,10000,20000} passing
1.3*complete_projected_hours<=36 and GBP60 core with explicit cash/energy
assumptions. No core execution before this gate and reviewed orchestration.
Keep all five seeds; follow the original roadmap and reserve 31 October through
1 November for reporting. No calibration measurement or budget is implied here.
## Verified evaluation checkpoint: 20 October 2026

Fixed-start evaluation primitives and tests are complete. Luna implemented;
Astra independently reviewed scientific semantics and cadence. Root repaired
opponent reference-failure accounting and documented completed-selection-only
neural counters (failed calls can perform uncounted work). Callback persistence
failures propagate; the future harness must preserve them. No calibration run,
full projection, budget freeze or core execution occurred. No reset used.

Checks: full suite447 passed5 skipped in11.97s, elevated Windows UCI, before
last small failure-accounting patch; final focused20 passed in0.25s; final Ruff
passed; final mypy src plus pilot passed49files. Each command exited0. Agents
finished; no experiment process launched. Usage57/78 initially,35/74 at checkpoint
trigger,27/73 before review,17/71 before final documentation (remaining percent).
Initial ownership failure and root review correction remain recorded below.

Cadence resolved after Astra review: static quality/MSE at all main saved
checkpoints; games/latency only final main, matched and frozen.200 static and65
full bundles,600000 choices and MSE predictions,39000 games,201500 latency
choices. Preserve exact zero-step aliases/provenance within seed; no intermediate
game curves claimed. This resolves schedule only, not the resource gate.

Resume: read docs/research/new-chat-handover-20261020-evaluation.md alongside
prior handovers. Next implement/test the development-only calibration runner,
then isolate measurements and complete the projection/gate. Never rerun pilot.
Final verification commands used workspace uv cache and explicit .venv Python;
pytest basetemps artifacts/pytest-evaluation-20261020-full and
artifacts/pytest-eval-final-20261020. Inspect Git log/tracking for commit/push.
Preserved user documents excluded. No production dependency added.

