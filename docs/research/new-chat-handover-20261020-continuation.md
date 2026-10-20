# Continuation after evaluation design and usage stop

This is the latest continuation request, dated 20 October 2026. Continue the
approved chess research project in `C:\Projects\chess-bot`; do not reopen the
research direction or rerun the completed development seed9001 pilot.

## Required reading and authority

Check current account usage first. Then read this file, followed by
`docs/research/new-chat-handover-20261020.md` **in full**, including every required
context file listed in its section 2. Read `checkpoint.md` newest entries first.
The earlier handover remains the detailed specification for scientific
invariants, measured pilot results, artifact locations, resource limits,
verification and the subsequent roadmap. This supplement updates continuation
state; it does not replace the authoritative research protocol.

Required files are AGENTS.md, checkpoint.md,
CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md, docs/status.md,
docs/research/opponent-dependence-protocol-v1.md,
docs/research/opponent-dependence-implementation.md,
docs/research/opponent-dependence-literature.md,
experiments/summaries/endgame-pilot-9001-v1.md and its companion JSON, and README.md.
Historical claims that the pilot is unrun or the neural phase unauthorized are
superseded. Inspect actual code and artifacts before implementation.

## Exact current state

- Branch `codex/opponent-dependence`; existing remote
  `https://github.com/Mamunur02/chess-bot.git`.
- Commits fe57385 (completed pilot), 1705d96 (original handover), and 418965a
  (evaluation design/usage checkpoint) were pushed. This documentation update
  follows 418965a; inspect log/tracking for its hash and push state.
- The preceding implementation turn made **no source or test changes**. No
  evaluation module, calibration runner, measurement, full projection, budget
  freeze or core matrix was completed. No tests ran; whitespace checks passed.
- Actual selected models were `gpt-6-astra` for scientific planning/review and
  `gpt-6-luna` for bounded implementation. Agents were interrupted before writing
  implementation files. Do not assume agents persist into the new chat.
- No experiment was started. No Python process appeared in the final process
  inspection of that turn. Inspect current processes again before timing.
- Preserve modified README.md and docs/research/practical-project-scope.md, plus
  untracked docs/research/opponent-dependence-decisions.md,
  docs/research/opponent-dependence-protocol-draft.md, and
  docs/research/opponent-dependence-scope.md. Exclude these from routine commits.
- User explicitly authorizes normal reviewed commits and pushes to the existing
  project remote, reconfirmed for this handover. No force pushes or binary dumps.

## Usage correction and efficient continuation

The preceding turn began at 64% five-hour / 94% weekly remaining. Active agents
were interrupted at 18% / 87%, but the final reading after checkpoint/push was
**5% / 85%**. Thus the requested 10% reserve was breached. The earlier checkpoint
records the 18% interruption point, not the final allowance. Preserve this fact.
No reset credit was used. During this later documentation-only request a fresh
reading was 66% / 79%; all these readings are historical on resume.

Stop before either window reaches 10% remaining. Reduce concurrency early and
begin checkpointing well above the reserve (use 35% remaining as an operational
trigger, earlier if consumption is rapid). Check before/after each bounded task
and before delegation. Shared usage can move between polls; use sufficient
headroom rather than treating 10% as a safe checkpoint-start threshold. Do not
use reset credits, buy credits, or continue research below the reserve.

Use Astra for scientific planning/review and Luna for bounded implementation
where supported, selecting actual identifiers. Avoid simultaneously starting
multiple agents that each reread all large context files. Root reads required
context once; give one bounded writer precise invariants, relevant files and
acceptance criteria, then use a narrow independent review. Avoid repeating the
already completed research-direction review. Keep durable checkpoints concise.

## Next smallest implementation

1. Add `src/chesslab/endgames/evaluation.py` and focused tests. Reuse existing
   `select_learner_move` at epsilon zero, `child_board`, `terminal_reward`, and
   `choose_action`. Existing `run_interaction` samples starts with replacement
   until a training decision budget; it is unsuitable for fixed-start evaluation
   games. Do not modify general game-runner semantics.
2. Benchmark learner is each board's side to move. Compute selected/best q,
   outcome loss, categorical loss and WDL strata. Prediction MSE encodes learner
   opposite side to move with target `-reference.value`.
3. Actual games use fixed supplied starts/learner colours, explicit paired RNG
   streams, p=0/0.25/0.5, full history and claim-aware terminal checks. The 400-ply
   cap is truncation with reward=None, never an adjudicated draw. Record visited
   learner reference errors, moves, neural work, encountered canonical keys,
   failures and accessible incremental partial progress.
4. Test both colours, sign conventions, claim/repetition semantics, deterministic
   UCI ties, cap handling, terminal precedence and failure accounting. Default
   tests require no Torch, table files or network.
5. Then implement `scripts/run_endgame_calibration.py` and tests, using the
   pilot's verified `_load_development` helper or a reviewed shared equivalent.
   Only load development data; verify existing pretrained and three beta
   checkpoint hashes against pilot.json. Do not launch or overwrite the pilot.

Harness design proposed, not implemented or frozen: benchmark and MSE on 100
development boards per model; latency 10 warmup plus three passes of 30 boards;
10 paired starts per model/opponent p, with balanced learner colours and 400-ply
cap. Establish explicit CLI bounds and a total deadline checked between work
items/plies, preserve incomplete records, and use fresh output directories.
Increase samples only if needed for defensible cost calibration. No testing or
other project workload concurrently with timing. Record source snapshots, Git
state, dependencies, hardware, threads, seeds, data/model hashes and counters.

Full-size pretraining timing: repeat the development 1600/400 subsets into
20000/2500 examples, measure encoding/tensor construction and all 30 epochs
using the existing trainer. `patience=31` can force this **timing surrogate**;
other optimizer/architecture settings stay fixed. Clearly distinguish this
override from scientific pretraining with patience 5. Repetition provides no
independent data or evidence of full-data stopping behavior. Measure saves,
loads and other overhead separately and avoid double-counting nested timings.

## Evaluation cadence proposal from Astra

Resolve and record this schedule explicitly before final-data access; it is a
reviewed proposal, not an implemented or frozen configuration:

- Static quality and MSE at all saved main checkpoints (0/25/50/75/100%).
- Actual play and latency at final main/matched checkpoints and frozen controls.
- Reuse identical zero-step evaluations within a seed only when model, starts,
  RNG and configuration match; no pooling across seed blocks.
- Distinct static bundles: 45*4 + 5 frozen + 15 matched = 200, giving 600000
  benchmark choices and 600000 MSE predictions on 3000 benchmark positions.
- Full final/frozen bundles: 45 + 5 + 15 = 65, giving 39000 games (13000 per p)
  and 201500 timing/warmup choices [65*(100+3*1000)].
- The 400-ply bound gives at most 15.6 million game plies, not expected duration.

The protocol requires saved intermediate checkpoints and secondary learning
curves, but not full games/latency at every intermediate checkpoint. This
proposal resolves the earlier conservative 245-full-bundle assumption without
silently dropping prescribed final evaluations. Static reference labels can
be shared. Confirm correctness and record the schedule in the resolved plan.

## Resource gate and subsequent work

No common budget is approved. Include five full-size pretraining blocks, 45 main
RL runs, five frozen controls, 15 matched-time runs, all scheduled evaluation,
checkpoints/loading/reporting overhead and honest cash/energy assumptions.
Use the handover's update-aware projection, not whole-pilot linear scaling:
U(B)=floor(B/8)-31 for fully recorded transitions; handle unrecorded decisions.
Freeze the largest of {2000,5000,10000,20000} satisfying
1.3*complete_projected_hours <= 36 and GBP60 core. Existing training-only
estimates including matched time and contingency are 9.252/24.842/50.826/102.793
hours; they are extrapolations and exclude remaining costs.

If 2000 does not fit, attempt only semantics-preserving batching/caching with
tests and remeasurement, then report infeasibility rather than dropping seeds.
GBP100 total ceiling remains GBP60 core/GBP20 extensions/GBP20 contingency;
no paid cloud resource without provider/configuration/cost/shutdown approval.
No cash spent so far; electricity unestimated. Reserve 31 October-1 November
for reporting. After the gate, implement/review core orchestration before any
matrix execution, then follow the original handover and protocol roadmap.

Run relevant tests and normally full pytest, Ruff and mypy using the exact
workspace-cache/interpreter commands in the original handover. Extend coverage
to new files, use fresh basetemp paths, keep optional Torch isolated, and report
each exit independently. Windows UCI tests may need escalation. Maintain
checkpoint.md with failures, exact checks, Git/process state, artifacts and
concrete resume commands. Never claim completion or measurement without evidence.
