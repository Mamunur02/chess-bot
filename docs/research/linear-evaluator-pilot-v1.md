# Linear evaluator pilot v1: frozen plan

Written before label generation/training, 2026-10-17. The user selected our own
supervised evaluator. This is a bounded engineering pilot, not a novelty or
strength claim. Existing tactical study inputs/results remain evaluation-only.

- Generate 96 new legal trajectories from the standard start with seed 20261018;
  assign 64/16/16 source groups to training/validation/test before extraction.
  At each ply choose a uniformly random legal move with probability 0.5;
  otherwise choose uniformly among moves maximizing immediate material, with
  mate/draw utilities taking precedence. Maximum 80 plies per trajectory.
- Sample nonterminal positions at plies 12,20,28,36,44,52,60,68. Reject incomplete
  trajectories. Reserve canonical position identities including colour mirrors;
  reject entire trajectories with sampled identities crossing split boundaries.
  Deduplicate sampled identities within each split. Cap generation at 1,000
  trajectories; do not adapt to label/model performance.
- Reject sampled identities found in any existing prepared puzzle split or the
  ordinary-game development starts. Read position identity only for this
  exclusion; do not use old labels or measured outcomes. Save input file hashes.
- Teacher: the already pinned Stockfish 19 executable/network/settings, one CPU
  thread, 16 MiB hash, no tablebases, full strength. Analyse each position with
  2,000 requested nodes, a fresh UCI game token and a 10-second response watchdog.
  Reuse one process; new-game notifications clear search state between positions.
  Record reported nodes/depth, raw White-perspective cp or mate, timings/errors.
  No automatic retry; total labelling cap 600 seconds, checked between searches.
- Target: teacher White-perspective cp clipped to [-2000,2000]. Map a teacher
  forced mate to signed 2000; retain raw cp/mate for audit. Terminal boards are
  excluded. Terminal search utilities remain +/-1,000,000 or zero.
- Features: 384 signed piece/square indicators, using vertically mirrored Black
  squares and shared piece-type weights, plus signed side-to-move. No intercept.
  This enforces colour-mirror antisymmetry. Learn a correction to the existing
  material prior, with plain-Python inference clipped to +/-2000 cp.
- Fit residual ridge objective `mean((Xw - (target - material))**2) + lambda*||w||²`
  for lambda in [0.1,1,10,100]. No feature scaling or extra hyperparameter search.
  Choose lowest validation RMSE of the clipped full prediction; ties use the
  larger lambda. Do not refit on validation data. No test data is read by training.
- Write/hash the selected JSON checkpoint and selection record before a separate
  assessment command reads the test split. Report RMSE/MAE against clipped teacher
  targets and the clipped material control. These are label-fidelity metrics,
  not playing strength. Test outcomes cannot select another checkpoint.
- Exercise the frozen model against plain material alpha-beta at 1,000 nodes and
  50 ms on the same observed ten development puzzles. Use existing two opening
  starts and both colours for a small learned-vs-material smoke at 50 ms, capped
  at 160 plies. No tuning from these diagnostics; no Elo inference. These are
  observed development fixtures, not new confirmatory tactics or match samples.
- Record source/lock/config/model/data/engine hashes, seeds, Git state, hardware,
  failures and isolated NumPy version. Keep generated data/checkpoints/raw logs
  ignored. No paid resources, GPU or additional production dependency.

Main limitations: artificial rollout distribution, small group counts, limited
teacher budget, omitted history/castling features, teacher-label dependence,
target saturation and potentially slower leaf evaluation. A negative result is
acceptable; do not redesign the model after seeing test results.

## Labelling amendment before fitting

The first label run completed 768 attempts but rejected 117 final bound scores;
training was blocked, and no model/test evaluation occurred. A training-position
message-stream diagnostic showed completed iterations followed by an unfinished
iteration's UCI bound at the node cap. The corrected label policy is the latest
completed, non-bound UCI score within the same 2,000-node search. Record label
depth/node count and final analysis depth/nodes/bound status separately. A UCI
non-bound score is still a limited search estimate, not exact game-theoretic value.
Bound flags belong to individual score messages; python-chess's merged info can
also retain older flags, so consume the message stream. If no completed score is
available, retain a failure and block training. Repeat the entire label pilot in
a new directory with unchanged generation, splits, budgets and targets; preserve
the first attempt. This operational correction is made before fitting or viewing
test label metrics, not in response to model performance.

API references: [score perspective](https://python-chess.readthedocs.io/en/latest/engine.html#chess.engine.PovScore),
[NumPy linear solve](https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html).
