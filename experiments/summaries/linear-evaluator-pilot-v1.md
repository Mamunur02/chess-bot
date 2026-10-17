# Our first learned evaluator: pilot v1

Completed locally on 2026-10-17. We trained our own 385-coefficient linear
correction to material evaluation and connected it to the existing plain
alpha-beta search, tactical runner, match runner and UCI server. It works as a
bot. The measurements below do **not** establish improved playing strength.

## Label fidelity: separate train, validation and test

| Split | Positions / source trajectories | Material RMSE / MAE (cp) | Learned RMSE / MAE (cp) |
| --- | --- | --- | --- |
| Train | 512 / 64 | 391.78 / 299.39 | 314.91 / 242.28 |
| Validation | 128 / 16 | 401.93 / 315.28 | 371.22 / 288.91 |
| New test | 128 / 16 | 389.20 / 282.48 | 373.90 / 283.52 |

Validation selected lambda **0.1** from the frozen [0.1,1,10,100] grid. The model
was saved and hashed before a separate command opened the new test split. It
was not refitted on validation data or changed after test assessment. Test RMSE
was lower by 15.30 cp, while MAE was worse by 1.04 cp. These are descriptive
point measurements on only 16 test source groups; no population, significance
or chess-strength claim follows. This test set is now observed and cannot be
used to select the next model.

The targets are limited-budget teacher estimates, clipped to +/-2000 cp, with
mates saturated to signed 2000. Both label-fidelity columns use clipped full
predictions. Material here is the clipped material control; the ordinary search
baseline retains its original unclipped material heuristic. Terminal search
utilities remain +/-1,000,000 or zero for both bots.

## Tactical and playing diagnostics

| Development tactical budget | Material accepted first moves | Learned accepted first moves | Median material / learned decision time |
| --- | --- | --- | --- |
| 1,000 visited nodes | 6 / 10 | 5 / 10 | 67.391 / 69.707 ms |
| 50 ms | 6 / 10 | 5 / 10 | 50.057 / 50.073 ms |

All 40 decisions completed without errors, missing cases or cleanup failures.
The two runs use the same ten previously observed development puzzles, not 20
independent positions. They measure first-move solution agreement, not full
puzzle solving. An unlisted good alternative may count as a disagreement.
Learned model loading/hash checking is included in setup, outside decision time;
inference is inside the search timer. Equal nodes do not imply equal wall time.

At 50 ms per move, the learned bot versus material used the two existing opening
starts with both colours and a 160-ply cap. Of four games, the learned bot won
one and drew one by fivefold repetition; **two games hit the ply cap** and have
no result. No colour pair had two completed games. The completed-only score
fraction of 0.75 is therefore not evidence of a strength gain. There were zero
agent/illegal-move failures, 512 total plies, and no forfeits or fabricated draws.

An additional practical integration check, planned after the checkpoint froze,
compared it directly with the pinned Stockfish 19 opponent under the same two
starts, colour swaps, 50 ms and 160-ply cap. Stockfish won all four by checkmate;
both pairs completed, with 110 total plies and zero failures. This check did not
select or change the model. Neither small match sample supports an Elo estimate.

## What was trained and how

- New artificial source trajectories use seed 20261018 and a 50/50 mixture of
  random legal moves and random tie-breaking among immediate material-maximizing
  moves. Trajectories are assigned to splits before position extraction. Sample
  plies are 12,20,28,36,44,52,60,68; maximum trajectory length is 80 plies.
- 768 unique sampled identities from 96 source groups were retained. Cross-split
  collisions, including colour mirrors, reject whole trajectories; existing
  prepared puzzle and ordinary-game evaluation identities are excluded. No old
  puzzle labels or measured outcomes are training targets. The original 200-
  position held-out tactical study remains byte-identical.
- Teacher is third-party Stockfish 19 (`sf_19`), one thread, 16 MiB hash, full
  strength, no tablebases, requested 2,000 nodes per position and new-game reset
  per label. Executable SHA-256:
  `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`.
  Embedded network is `nn-1a298aa575a0.nnue`. Reported total: 1,536,543 nodes;
  cooperative node limits can slightly overshoot.
- Labels use the latest completed non-bound UCI score in that budget; label
  depth/nodes and final analysis depth/nodes/bound flags are recorded separately.
  117 final iterations ended on bounds; earlier completed scores provided their
  labels. There were zero failures in the corrected label run. Of the 768 targets,
  15 are mates and 18 are saturated. No failed label was silently imputed.
- Our model uses signed, colour-shared piece/square weights and tempo, with no
  intercept and no feature scaling. It fits residual teacher cp relative to
  material using mean squared error plus an L2 coefficient penalty. It is a
  supervised linear model, not a neural network or RL/self-play system.
- NumPy **2.5.4** in the existing ignored plotting environment was used only for
  training. BLAS/OMP/MKL thread environment variables were set to 1. Production
  inference uses ordinary Python; `pyproject.toml` and `uv.lock` are unchanged.
- Model SHA-256:
  `93adbed58f5b19e4835d37526cb7218b51a707c60286e2635944afa3b1475b3e`.
  The JSON checkpoint remains local at
  `artifacts/linear-evaluator-model-v1/model.json`; no weights or dataset is
  committed. Reproduction instructions are in [the guide](../../docs/learned-evaluator.md).

## Failures, provenance and audit

The first labelling attempt made 768 attempts: 651 returned acceptable final
scores and 117 were rejected because the final score was a bound. It correctly
blocked training. A training-position message-stream diagnostic revealed a
completed score followed by an incomplete iteration. The full pilot was repeated
in a new directory using latest completed-score labelling, with identical frozen
position/split bytes and unchanged teacher budgets. The first attempt, its errors
and the pre-fit protocol amendment are retained; no test metric informed this fix.

The corrected generation/label run started at 22:46:02 UTC; model selection was
recorded at 22:46:39 UTC, before test assessment at 22:46:39 UTC. Git base was
`a9866c951a075a7aa55f750fd3b3b6fac119a83f`, with a dirty working tree. Source,
protocol, lock, input, split, checkpoint and raw-case hashes preserve the actual
versions. Later changes tightened validation and added UCI/reporting support;
the measured sources and original training script remain snapshotted.

Host: Windows 11, CPython 3.12.14, python-chess 1.999/chess 1.11.2, Intel Core
i7-10875H at nominal 2.30 GHz, 8 cores/16 logical processors and 16,954,482,688 bytes
RAM, measured using Windows CIM. Local CPU only; no paid resource, GPU or API.

The [compact audited record](linear-evaluator-pilot-v1.json) preserves configuration,
hardware, selection grid, split metrics, both tactical summaries, both match
summaries and game identities/outcomes, all source hashes and initial failures.
The independent audit replayed trajectories/games, checked exclusions and group
separation, recomputed features and all label metrics through production inference,
verified source/model pins, and reaggregated tactical/match summaries. No raw data
or checkpoints enter Git. Original snapshot/script hashes are retained even where
later validation-only changes differ from the final repository code.

## Limits and next task

This is a functioning learned baseline with mixed results. Artificial rollouts,
small group counts, shallow labels, missing history/castling features and a
linear model limit what can be learned or concluded. Lower teacher RMSE did not
translate into better agreement on these ten tactics; the partial game sample
cannot settle playing strength. Distribution mismatch is a hypothesis, not a
measured causal explanation. No improvement is claimed from changing features,
data, teacher budget or regularization after viewing the test result.

The next sensible task is to choose a more representative **new training-data
version**, with fresh source-group splits and a sealed new test set, keeping this
model and all first results fixed. The meaningful input is whether to adopt a
bounded public human-game sample or use engine-guided generated trajectories.
Do not reuse either observed test set to choose the next model.
