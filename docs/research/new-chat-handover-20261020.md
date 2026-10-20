# Continuation request: completed pilot to resource calibration

Continue my chess research project in `C:\Projects\chess-bot`. Read this file in
full and follow it as my continuation request, including required context.
The research protocol is approved; do not reopen the research-direction
discussion or ask whether to continue routine authorized work.

**The seed9001 neural pilot is COMPLETE. The next task is development-only
cost calibration, followed by the complete resource gate. No core budget is
frozen and no core training matrix has run.** Older handover instructions to
repair or launch the first pilot are historical.

## 1. Usage and model instructions

Check account usage FIRST and regularly thereafter. Stop before either the
five-hour or weekly window reaches 10% remaining. Remaining is
`100 - usedPercent`; limits are shared by all agents. Reduce concurrency early,
finish a durable checkpoint well before the reserve, and do not start work
that cannot be safely supervised within it. At/below the reserve stop work,
halt active agents safely and preserve process/artifact state. Do not use reset
credits or buy credits without explicit authorization. If usage is unavailable,
report that instead of assuming sufficient allowance.

Use GPT-6 Astra for scientific planning/review and GPT-6 Luna for bounded
implementation where supported. Actual identifiers previously selected were
`gpt-6-astra` and `gpt-6-luna`; select real available identifiers and never claim
a model was used unless selected. Keep delegation narrow, file ownership
separate, and independently review scientific invariants.

The prior implementation stopped at 17% five-hour / 55% weekly remaining.
The documentation handover on 20 October read 92% / 99% remaining. These are
historical readings, not current permission to skip a fresh check.

Maintain `checkpoint.md` with completed work, exact checks/failures, Git state,
process status, artifact paths and concrete resume commands. No experiment or
implementation agent was left running when the pilot session finished; inspect
actual processes rather than assuming that remains true.

## 2. Required context and authority

Read before planning or changing implementation:

1. `AGENTS.md`
2. `checkpoint.md`, newest entries first
3. `CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`
4. `docs/status.md`
5. `docs/research/opponent-dependence-protocol-v1.md`
6. `docs/research/opponent-dependence-implementation.md`
7. `docs/research/opponent-dependence-literature.md`
8. `experiments/summaries/endgame-pilot-9001-v1.md`
9. `experiments/summaries/endgame-pilot-9001-v1.json`
10. `README.md`

The protocol is the authoritative scientific specification. This handover
updates implementation state, not that protocol. Older planning-only,
infrastructure-only and "pilot unrun" passages are historical; the neural phase
is explicitly authorized. The 19 October handover is retained as history.
Inspect actual code, tests and artifacts rather than treating plans as proof.

## 3. Purpose, schedule and money

This is a Stats/ML/AI PhD application research artifact: controlled experiments,
correct implementation, uncertainty analysis and reproducibility.

Question: does learning against fallible opponents reduce preservation of
theoretically available chess outcomes, and can mixed defensive targets reduce
that dependence? What are the exploitation and computational costs?

Negative results are acceptable. Do not claim novelty, safety guarantees,
calibrated probabilities, general robustness or stronger play without evidence.
The initial literature review identifies close prior work, particularly
Bootstrapping from Game Tree Search; the final literature/search log is still
required. Preserve classical and previous linear-evaluator studies separately.

Original window: 18 October–1 November 2026, with 31 October–1 November reserved
for reporting/reproducibility. Check today's date. GBP100 total is authorized as
a ceiling: GBP60 core, GBP20 extensions, GBP20 contingency; GBP200 is not.
No paid cloud resource without provider/configuration, cost and shutdown-policy
approval. Local approved work may proceed. No cloud resource has been created;
cash expenditure is zero and electricity remains unestimated.

## 4. Git authorization and preserved work

Branch: `codex/opponent-dependence`.
Remote: `https://github.com/Mamunur02/chess-bot.git`.

I authorize normal reviewed commits and pushes to this existing project remote,
and directly reconfirmed "Also commit and push" for this handover. Do not ask
again for routine checkpoints. This excludes force pushes, destructive history,
unrelated remotes, credentials, indiscriminate binary commits and bypassing
branch protection. A historical automatic-review rejection was resolved by
direct user authorization; it is not an outstanding gate.

Pushed history:

- `85a8b00`: verified reference data and target foundations.
- `81e3fa0`: earlier usage stop record.
- `c223910`: neural/interaction foundations and repaired bounded pilot runner.
- `798c029`: previous handover.
- `fe57385`: completed pilot, successful-path regression, accounting changes,
  measured summary and open resource gate.

This new documentation handover follows `fe57385`; inspect log/tracking for its
resulting hash. Preserve these preexisting changes outside reviewed commits:

- Modified `README.md` and `docs/research/practical-project-scope.md`.
- Untracked `docs/research/opponent-dependence-decisions.md`,
  `docs/research/opponent-dependence-protocol-draft.md`,
  `docs/research/opponent-dependence-scope.md`.

Do not discard or indiscriminately stage them. Data, model checkpoints, raw
artifacts and environments remain ignored. Use command-scoped
`git -c safe.directory=C:/Projects/chess-bot ...`; do not change global security
settings. Git writes/pushes and some Windows checks may require escalation.

## 5. Data and implemented foundations

Implemented: experiment-specific claim-aware rules; history-preserving branches;
separate theoretical reference queries; canonical symmetry/colour identities;
stable named RNGs; hash ownership; serial acquisition; generated datasets;
775-input encoding; controlled fallible opponent; replay and pure targets;
MLP/pretraining/RL updates; interaction records and truncations; structural audit;
development-only pilot. The full core orchestration/evaluation pipeline must
still be inspected and completed; a successful pilot does not establish it.

Eight Syzygy tables reside in `data/syzygy/protocol-v1` for KRvKR, KQvKR, KRvK
and KQvK. All publisher whole-file SHA-256 checks passed. Provenance:
`experiments/manifests/syzygy-protocol-v1-acquisition.json`.
The old `/3-4-5/` mirror URL returned404; same-publisher paths used were
`/tables/standard/3-4-5-wdl/` and `/tables/standard/3-4-5-dtz/`.
Generator resources were pinned to `0bb8aeee525f364bb750f96df312a1a7c9b54398`.
Embedded checksum trailers were compared, but generator CityHash was NOT
recomputed. Do not overstate that verification.

Development screens: KRvKR 1,822/2,000 decision-sensitive/worsening-available
positions; KQvKR 1,192/2,000. Both passed; KRvKR was selected by the fixed
preference rule, not learning performance. Development generation seed1101,
KQvKR seed1201; pilot initialization/shuffle/interaction seed9001.

Paths:
- `artifacts/opponent-dependence-v1/development/`
- `artifacts/opponent-dependence-v1/krvkr-partitions/`
- `artifacts/opponent-dependence-v1/partition-audit-20261019.json`

Audit passed29,500 unique canonical positions with zero failures: development
2,000; pretraining20,000 (16,000 primary +4,000 descendants); RL starts2,000;
validation2,500; final broad2,000; final diagnostic1,000. It checks quotas,
ownership, material, hashes and start-board separation. Later trajectory overlap
is not excluded: retain encountered canonical keys and report all-position and
unvisited-only results. Final performance labels have not been inspected for
tuning. Keep them outside calibration access.

## 6. Completed real pilot

Raw directory: `artifacts/opponent-dependence-v1/pilot-9001-v1/`.
Do NOT overwrite or rerun it merely because an older note says "unrun".
It contains `pilot.json`, resolved config, per-beta results/checkpoints,
initial/pretrained checkpoints and exact copied sources.

All betas0/0.5/1 used identical pretrained initialization, p=0.5, epsilon0.1,
one CPU thread. Each completed512 decisions/transitions and33 updates, with
finite recorded losses/gradient norms, changed parameters and no missing
transition. Process exited0. Source/checkpoint hashes and episode decision
totals passed an independent post-run audit.

| Beta | Training seconds | Target seconds | Optimizer seconds | Residual seconds | Target neural leaves |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 28.277 | 13.762 | 0.125 | 14.390 | 16,508 |
| 0.5 | 115.072 | 101.016 | 0.125 | 13.931 | 134,569 |
| 1 | 108.858 | 95.283 | 0.124 | 13.451 | 130,676 |

Total pilot260.715 seconds; peak working set411,742,208 bytes. Pretraining on
development1,600/400 examples ran7 epochs, restored epoch2, took3.282 seconds.
Development untrained/frozen MSE0.282642/0.201869 is a diagnostic, not final
accuracy. These measurements establish execution feasibility, not superiority.

Cost boundaries:
- Residual includes simulation, online inference, encoding, replay, logging,
  opponent selection and reference queries. Probe seconds are nested; never
  add them twice.
- Target leaves count nonterminal neural inputs, not all branch expansions.
  Full expansion counts remain unavailable.
- Memory is process-lifetime peak, not independent per-method peaks.
- Pretraining time includes initialization, encoding, checkpoint writes and
  initial/frozen evaluation, not only optimizer epochs.
- No simultaneous project tests ran during pilot timing. Unrelated host
  activity was not controlled. GPU throughput is unverified.

Execution HEAD was798c029 with reviewed code changes uncommitted. The raw
manifest records source snapshots/diff hash; fe57385 subsequently commits the
runner and test changes. Do not falsely relabel execution as a clean fe57385 run.

## 7. Open resource gate and exact next task

Implement/test a bounded DEVELOPMENT-ONLY cost-calibration harness. Measure:
evaluation move selection and reference queries, prediction MSE, actual play
at evaluation epsilon0 and p=0/0.25/0.5, latency passes, and full-size
pretraining workload. Make workload bounds explicit; preserve failures,
truncations, seeds, counters, environment, Git and data/checkpoint hashes.
Keep timing workloads isolated. Do not read final labels for calibration.
Any repeated development examples used to emulate20,000/2,500 tensor sizes
must be clearly labelled a timing surrogate, not independent training evidence
or proof of full-data epoch/stopping behavior.

Then produce a complete projection including five full-size pretraining blocks
(20,000 train/2,500 validation, up to30 epochs),45 main RL runs,5 frozen
controls,15 matched-time runs, all required evaluation, checkpoints and overhead.
Do not infer this from seven small-development epochs.

Warmup correction: for B fully recorded transitions,
`U(B)=floor(B/8)-31`. Pilot512 has33 updates; candidate budgets2,000/5,000/
10,000/20,000 have219/594/1,219/2,469. Illustrative method estimate:
`T_m(B)=residual_m*B/512+(target_m+optimizer_m)*U(B)/33`.
Main training is `15*sum_m T_m(B)`; matched-time training is `15*T_0(B)`.
Do not scale whole pilot wall time by B/512. Handle unrecorded transitions.

Training-plus-matched-time estimates WITH30% contingency, excluding all other
costs:9.252h /24.842h /50.826h /102.793h respectively. These are extrapolations,
not core measurements. Rates at p=0.5 may not transfer to other opponents,
longer histories or later replay distributions. Under current estimates10k/20k
exceed36h already;2k/5k remain candidates, not approved choices.

Evaluation inventory needs an explicit schedule. Astra's conservative planning
assumption evaluates every main checkpoint plus frozen/matched finals:
45*5+5+15=245 bundles;735,000 benchmark move choices;735,000 MSE predictions;
147,000 actual games;759,500 timing/warmup move choices. The400-ply cap implies
58.8 million game plies as an administrative bound, NOT typical expected play.
Identical zero-step evaluations can be reused with matching model/starts/RNG/
config, leaving200 distinct bundles; static reference labels may be shared.
This is a conservative planning assumption, not a mandatory new scientific
requirement. If it fails, resolve protocol evaluation cadence explicitly and
measure costs before declaring infeasibility. Do not silently omit evaluations.

Freeze the largest common budget from {2000,5000,10000,20000} satisfying
`1.3*complete_projected_hours <= 36` and GBP60 core. Include cash/energy
assumptions honestly. If2k does not fit, try only semantics-preserving batching/
caching with correctness checks and remeasurement, then report infeasibility
rather than dropping seeds or silently changing the study.

## 8. Scientific invariants

Use python-chess, never a custom legal-move generator. Theoretical reference is
sign(Syzygy WDL), ignoring repetition/move-count draws: cursed wins+1, blessed
losses-1, history-free boards and halfmove clock0. Actual games and branches
retain full history and use `outcome(claim_draw=True)`, including prospective
claims. Keep general runner semantics unchanged. p=0 is reference-preserving,
not guaranteed perfect under actual claim-aware rules.400-ply caps and budget
interruptions are truncations, never draws or invented terminal rewards.

Fixed learner perspective:

```text
F(x,b) = terminal reward if x+b terminal,
         otherwise max over learner moves a of H(x+b+a)
H(z) = terminal reward if terminal, else detached target-network U(z)
y = (1-beta)*F(x,observed_reply) + beta*min_b F(x,b)
loss = 0.5*(U_online(x)-stop_gradient(y))**2
```

Betas0/0.5/1, discount1. No tablebase inside counterfactual targets. Store actual
opponent replies, never resample them from replay. Terminal reward once; retain
history and mutable-move isolation. Beta0 computes only needed branches.

Architecture775-128-128-1, ReLU/ReLU/tanh. Supervised examples encode learner
opposite side to move with label -v(s). Adam0.001,batch256,max30 epochs,
patience5,min_delta0.0001, earliest best checkpoint; fail visibly on divergence.
Reset Adam for RL0.0001; replay10,000,batch32,warmup256 recorded transitions,
update every8,target refresh every250 updates,gradient clipping5.
Behavior epsilon0.1; evaluation epsilon0; UCI-lexicographic ties.
Same pretrained checkpoint across each seed block's conditions and frozen
control. Stable named RNGs: initialization, starts, exploration, opponent,
replay and pretraining shuffle; pair method streams where feasible.

## 9. Subsequent roadmap

After budget freeze, implement/review remaining orchestration and evaluation
before executing45 conditions (3 betas * p0/0.25/0.5 * seeds101/202/303/404/505).
Randomize order within each block; save0/25/50/75/100% checkpoints. At p0.5 add
15 equal-wall-time runs using development beta0 projected time for the chosen
budget, excluding loading but including simulation/reference/targets/updates.
Record decisions, updates, neural work and overruns. Preserve all five seeds.

Primary contrast: mixed minus observed at training p0.5 on diagnostic outcome
loss. Report broad/diagnostic errors, categorical loss, WDL strata, MSE,
frozen-baseline changes, actual-play W/D/L, truncations/bounds and latency.
Use five paired seed differences, mean/SD/95% t interval(df4,critical2.776445),
plus10,000 paired seed/canonical-group bootstrap resamples. Do not equate
nonsignificance with equivalence; keep missing-run coverage visible.

Analyze/report the core before optional work. Then, if resources permit:
general-engine specialist integration/relative Elo demonstration; ensemble
exploration; advice-triggered targets with oracle/noisy controls and ChessGPT
only after its separate feasibility gate. A second family needs its own doubled
resource projection. Follow full protocol details; do not sacrifice core seeds,
analysis or final reporting for extensions.

## 10. Environment, verification and failures

Verified hardware: i7-10875H;16,954,482,688 bytes RAM; RTX2070 Max-Q8192MiB,
driver566.36. Python3.12.14. Ignored `artifacts/neural-env` has Torch2.7.0+cpu
and NumPy2.5.4; GPU Torch remains untested. Default project dependencies contain
no Torch. No new production dependency without authorization.

Latest implementation checks (19 October):
- Default full suite429 passed,5 skipped in12.05s, elevated for Windows UCI.
- Optional neural/interaction/targets/pilot56 passed in14.52s.
- Pilot-only19 passed in12.76s.
- Ruff . passed; mypy src plus pilot passed48 files.
- Source/checkpoint hashes, finite updates and episode decision totals passed.
- Staged whitespace check passed.

Preserve repaired failure history: scripts import collection failure; standalone
script mypy src-layout/optional-Torch issues; Windows ctypes handle truncation;
new success test initially missing math import and early Ruff long lines.
All repaired before the real pilot. Prior repairs also covered perspective,
platform.platform(), seed/stream pairing, ownership_split/table_sha256 interfaces,
failure/interruption status and partial counters. New success regression uses
real neural/pretraining/interaction/targets with mocked data/references and short
warmup; it is verification, not a research experiment.

Commands (use fresh unique basetemp paths, observe each exit independently):

```powershell
git -c safe.directory=C:/Projects/chess-bot status -sb
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-NEW-UNIQUE
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src scripts/run_endgame_pilot.py
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py tests/test_endgame_interaction.py tests/test_endgame_targets.py tests/test_endgame_pilot.py -q --basetemp artifacts/pytest-neural-NEW-UNIQUE
```

Extend verification to any new calibration files. Existing Windows UCI tests
need outside-sandbox execution. CIM process inspection was denied in sandbox
and succeeded with read-only escalation. Default uv cache previously failed;
use workspace cache and explicit interpreters. Do not repeatedly retry identical
permission errors. Optional real-table tests set
`CHESSLAB_SYZYGY_DIRECTORY=data/syzygy/protocol-v1` and run
`tests/test_endgame_tables.py`. Structural audit and pilot reproduction commands
are in the measured report/previous handover; always choose fresh output paths.

Begin with current usage, verified Git/artifact/process state and the next
bounded action. Continue with cost calibration, not another first pilot.
