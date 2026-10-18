# Opponent fallibility and neural reinforcement learning: protocol v1

Planning specification, 18 October 2026. This document supersedes conflicting
research drafts and the decisions ledger. No training results are claimed.
Implementation belongs in a subsequent chat. Numerical defaults below are
decisions, not measurements of feasibility. The bounded pilot can select only
the alternatives explicitly listed here; its choices must be recorded before
the final experiment begins.

## 1. Question and interpretation

Does fine-tuning a neural chess value function against fallible opponents reduce
its ability to preserve theoretically available outcomes? Does mixing observed
opponent replies with defensive counterfactual replies reduce that deterioration,
and at what cost to exploiting mistakes and computation?

This is a controlled empirical study of existing ideas, not a claim to invent
robust RL. Supervised learning supplies an initial value network; subsequent
interaction, bootstrapped targets and action selection constitute off-policy
neural RL. There is no requirement to add transformers or full-game self-play.
Success means a reproducible comparison with interpretable negative or positive
results. A literature gap is not established simply because this exact grid has
not been published.

The primary contrast is mixed minus observed learning at training opponent
p=0.5, on decision-sensitive held-out positions. Lower outcome-loss rate is
better. Defensive-only learning, other opponent conditions, learning curves,
exploitation, general playing strength and extensions are secondary analyses.

## 2. Reference truth and actual game rules

Use pawnless KRvKR as the preferred primary family, with KQvKR as fallback or
separate replication. Each family includes its legal capture descendants.
No castling rights or en-passant squares. Starts have halfmove clock zero,
fullmove number one and empty history. Sample both colours as learner equally.

Keep two explicitly different notions of outcome:

1. Reference labels are theoretical board WDL, ignoring move-count and repetition
   draws. Let v(s) be the sign of Syzygy WDL from the side-to-move perspective.
   Cursed wins remain +1; blessed losses remain -1. Probe a history-free copy
   with halfmove clock zero. Handle checkmate, stalemate and insufficient material
   consistently before probing. For legal a, q(s,a)=-v(s+a).
2. Actual games and RL branches retain full move history and use
   `board.outcome(claim_draw=True)`. This intentionally includes python-chess's
   prospective claim semantics. Check termination before every action and after
   every hypothetical move. Reward is +1/0/-1 from the fixed learner's perspective.
   A 400-ply administrative cap produces a truncation, not a draw.

Consequently p=0 means reference-preserving, not an infallible history-aware
opponent. Reference WDL error and actual game score answer different questions.
Do not describe WDL labels as exact predictions of games under the claim policy.
Keep the existing general game runner's default semantics unchanged; introduce
an experiment-specific adapter and use it consistently for experiment matches.

## 3. Data acquisition and generation

Obtain local Syzygy WDL and DTZ files for KRvKR, KQvKR, KRvK and KQvK: eight
files with extensions `.rtbw` and `.rtbz`. Bare kings need no table. Sources:
[Lichess mirror](https://tablebase.lichess.ovh/tables/standard/3-4-5/) and
[Sesse mirror](https://tablebase.sesse.net/syzygy/3-4-5/).
Use serial downloads respecting publisher guidance. Do not use an online
tablebase API for bulk data generation or training.

The implementation acquisition step must record source URL, retrieval time,
byte count, local SHA-256, publisher notices and table verification results.
Consult the [generator checksum directory](https://github.com/syzygy1/tb/tree/master/checksums)
and its documented verification algorithm; do not assume its checksum strings
are ordinary whole-file MD5. Pin the retrieved checksum resource by commit/hash.
No binary hashes, availability, download sizes or data redistribution licence
have been verified here. Keep downloaded binaries outside version control and
do not redistribute them in the project. Acquisition failure blocks tablebase
experiments; it must not silently switch to approximate engine labels.

Generate boards by uniformly assigning required labelled pieces to distinct
squares and choosing side to move uniformly. Reject invalid or terminal starts
using python-chess; do not claim uniformity over naturally encountered chess
positions. Colour-swapped material assignments are included. Deduplicate by the
lexicographically smallest serialization over eight board symmetries and colour
exchange, transforming side to move too. Canonical identity ignores clocks and
history. No augmentations cross a split.

Use SHA-256 of `protocol-v1|family|canonical-position` modulo 100 for ownership:
0-9 development, 10-54 pretraining, 55-69 RL starts, 70-79 validation,
80-89 final broad and 90-99 final diagnostic. Hash serialization and modulo
conversion must be specified in code and tested. Deterministic generation seeds
are 1101 development, 1102 pretraining, 1103 RL starts, 1104 validation,
1105 broad test and 1106 diagnostic test. Use separate seeds 1201-1206 for a
second family. Canonical keys include material so descendant sets stay disjoint.

Per family targets:

| Partition | Size and selection |
| --- | --- |
| Development | 2,000 valid primary-family boards |
| Pretraining | 16,000 primary + 4,000 legal three-piece descendants |
| RL starts | 2,000 primary-family boards, sampled uniformly with replacement per episode |
| Validation | 2,000 primary + 500 descendants |
| Final broad | 2,000 primary-family boards, no outcome balancing |
| Final diagnostic | 1,000 primary boards with at least two distinct legal-action q values |

For KQvKR descendants split the 4,000 equally between KQvK and KRvK; KRvKR
uses KRvK alone. Pretraining examples treat the opposite of side to move as
learner, consistent with an afterstate. Labels are therefore -v(s).

Screen both families only on development labels, before training comparisons.
A family passes if at least 100 of its 2,000 development boards have different
q values across legal moves and at least 100 have an available worsening move.
Prefer KRvKR if it passes, otherwise KQvKR. If neither passes, report an
infeasible prespecified design and revise explicitly; do not search until a
positive method effect appears. Cap generation at two million proposals per
partition. If diagnostic target size is not reached, freeze the attained size
if at least 200; otherwise fail the family feasibility gate.

Final labels must remain outside tuning and training access. Record encountered
training canonical keys: trajectories may reach held-out boards despite disjoint
starts. Report overlap and both all-position and unvisited-only sensitivity
metrics without removing positions after seeing outcomes. Existing observed
tactical datasets are regression evidence, not a newly untouched final test.

## 4. Neural model and pretraining

Use an MLP with 775 inputs, hidden widths 128 and 128, ReLU activations and one
tanh output U. Inputs: 12 piece planes in white P,N,B,R,Q,K then black order,
each flattened a1 through h8 (768); side-to-move-is-white (1); learner-is-white
(1); min(halfmove-clock,100)/100 (1); repetition-at-least-two and at-least-three
(2); can-claim-fifty-moves and can-claim-threefold flags (2). No learned embeddings.
History flags are a summary, not a sufficient representation of all future draw
claims. Branch legality and termination still use full board history.

Seed blocks are 101, 202, 303, 404, 505. Derive independent named RNG streams
for initialization, starts, exploration, opponent replies and replay using a
documented stable hash; never Python's process-randomized hash. Pair streams
across methods where feasible; divergent trajectories prevent perfect pairing.

For each block, pretrain using MSE, Adam learning rate 0.001, batch 256,
maximum 30 epochs, early stopping after five epochs without validation MSE
improvement of 0.0001. Save the earliest best checkpoint. No class reweighting
or WDL balancing. Copy this exact checkpoint into every RL condition of its
block and keep a frozen-pretrained baseline. Reset the optimizer for RL.
Record seed, library versions, determinism settings and nondeterministic kernels.

## 5. Learning algorithms

U(x) evaluates an afterstate immediately after the learner's action, with the
opponent to move. The learner identity stays fixed throughout an episode.
Let H(z) be actual terminal reward if z is terminal, otherwise detached target
network U_target(z). For opponent reply b define:

```
F(x,b) = terminal_reward(x+b), if x+b is terminal
         max over learner moves a of H(x+b+a), otherwise
y_observed = F(x,b_observed)
y_defensive = min over legal opponent b of F(x,b)
y = (1-beta)*y_observed + beta*y_defensive
loss = 0.5*(U_online(x)-stop_gradient(y))**2
```

Use beta=0 observed, beta=0.5 mixed and beta=1 defensive. Discount is one.
Compute only needed branches for beta=0. Defensive counterfactual values come
from the target network, not tablebase labels. Check actual terminals at every
branch. Immediate terminal learner actions instead train directly on terminal
reward. Do not add a terminal reward twice. Store the observed opponent reply
with each transition; do not resample it when drawing replay.

RL defaults: Adam 0.0001; replay capacity 10,000; uniform replay batch 32;
begin updates after 256 recorded learner transitions; one update every eight
transitions; hard-copy online weights to target every 250 optimizer updates;
global gradient norm clipping at 5. No prioritized replay, reward shaping,
Huber loss or hyperparameter search in the core. Checkpoints at 0,25,50,75,100%
of decision budget; headline uses the final checkpoint. An interrupted episode
at budget is truncated; never invent terminal feedback. The last eligible
afterstate may still receive its observed opponent response to form its sample,
but no extra learner decision may be taken.

Behavior: with probability 0.1 choose uniformly among all legal moves; otherwise
maximize terminal reward or U_online of the resulting afterstate. Resolve exact
ties by lexicographic UCI. Evaluation uses epsilon zero and the same one-ply
selector. Batched evaluation and caching are allowed only if semantics remain
identical; caches must include relevant history and model version.

These are bootstrapped neural control methods with function approximation,
not algorithms with proven convergence in this setting. Their main difference
is which opponent replies enter the target, not a robust regression loss.

## 6. Fallible opponent

At each live opponent turn, compute q for every legal move from that opponent's
perspective. Best moves maximize q; worsening moves have q strictly below that
maximum. If worsening moves exist, sample one uniformly with probability p;
otherwise use a best move. p is 0, 0.25 or 0.5. Record conditional opportunities,
actual worsening frequency and WDL-category loss severity separately.

Within the best set use a fixed progress heuristic: prefer fewer occurrences
of the successor board in actual history, then for theoretical wins minimize
absolute successor DTZ, for theoretical losses maximize it, and for draws ignore
DTZ; final ties use UCI order. Immediate mate takes precedence. This heuristic
does not promise optimal conversion or shortest mate, especially for cursed
outcomes. Keep raw five-valued WDL and DTZ for audit, and never let this tie-break
override the best q category. Its imperfections are shared experimental controls.

## 7. Pilot, run matrix and resource gates

Pilot runs use development data and a separate seed 9001. Check terminals,
perspectives and target calculations against hand-constructed small trees before
learning. Run each target for up to 512 transitions and measure wall time,
branch evaluations, peak memory and update throughput; this is feasibility,
not a test of which method wins. Learning must produce finite gradients and
parameter changes; label distribution and untrained/frozen errors are logged.

Choose the largest common decision budget in {2,000,5,000,10,000,20,000}
whose projected core execution fits 36 machine-hours and the GBP60 core
allocation, including 30% runtime contingency. Projection includes all runs,
pretraining, evaluation and matched-compute work. If 2,000 does not fit, optimize
batching/caching, then report infeasibility rather than dropping seeds or quietly
changing the question. Hardware costs and quotes are obtained during implementation.

Main matrix: three betas x three p values x five seed blocks = 45 RL runs per
family, plus five frozen controls. Randomize execution order within seed blocks.
At p=0.5 additionally train all three methods for an equal wall-clock allowance,
chosen from the development beta=0 time for the selected decision budget.
Exclude process/model loading; include simulation, reference opponent queries,
target construction and updates. Record actual decisions, update counts, neural
forward evaluations and small budget overruns. No time allowance based on final
method performance. Use the same device and isolated workload for comparisons.

Add a second family only if both screening and a doubled execution projection
fit these limits; analyze it separately. All optional work is subordinate to
finishing the primary five-seed matrix and report.

Total spending default GBP100: GBP60 core, GBP20 extensions, GBP20 contingency.
GBP200 is a possible user-approved expansion, not automatic authority to spend.
No cloud purchase is made in this planning chat. Use the local GPU if suitable;
measure whether Python tree expansion, rather than GPU arithmetic, is limiting.
The reported laptop RTX2070 Max-Q has 8 GiB; verify actual hardware at execution.

## 8. Evaluation and analysis

Primary per-position outcome-loss indicator is
`q(s, chosen_move) < max_a q(s,a)`. Primary dataset is the diagnostic set;
the broad set estimates error under the stated board generator. Also report
mean categorical loss `(max_q-chosen_q)/2`, WDL-stratified counts and error,
prediction MSE against reference labels, and changes from each frozen baseline.
Do not describe U as a calibrated probability of beating every opponent.

For exploitation and actual play, use 200 broad-test starts per block, selected
by fixed hash, each against evaluation p=0,0.25,0.5; reuse starts and RNG streams
across methods. Report W/D/L, score, truncations, move counts and reference-error
rate on visited learner turns. Scores exclude unfinished games only with explicit
coverage plus pessimistic/optimistic bounds treating their score as 0/1.

Compute each method's benchmark mean per seed, then paired differences within
seed. For the primary contrast report the five differences, their mean, standard
deviation and a two-sided 95% t interval (df=4, critical value 2.776445).
This interval assumes approximately normal seed effects and conditions on the
fixed benchmark. Supplement with 10,000 paired bootstrap resamples of seeds
and canonical position groups, preserving method pairing; label the small-five-
seed uncertainty limitation. No claim of equivalence from non-significance.
Report all secondary contrasts descriptively; no selective significance search.
Infrastructure failures can be rerun with identical seeds/configs. Algorithmic
divergence is a result, not an infrastructure failure. Missing seed blocks remain
visible; an incomplete matrix loses its planned confirmatory interpretation.

Runtime: 100 fixed validation positions for warmup, then 1,000 broad-test
positions, three timing passes with method order rotated. Synchronize GPU
around timing, batch size one for per-move latency, exclude loading, and report
median/p95 plus hardware, thread count and neural/node counts. Report training
time and inference time separately. No claim of latency superiority across
different devices or unequal searches.

## 9. General-engine demonstration and relative Elo

This is secondary integration, not fine-tuning Stockfish. Keep the existing
alpha-beta engine and its evaluator outside supported material. Within the
trained family and descendants, use the specialist. For an arbitrary search
leaf evaluate U with learner opposite side to move, convert to white perspective,
then map `cp = 400*atanh(clamp(U_white,-0.99,0.99))`. This fixed engineering scale
is not probability calibration. Terminal search scores retain existing priority.
If two specialists overlap, the primary-family model owns shared descendants.
Use identical routing and scale for frozen, observed, mixed and defensive models.

Compare those four variants at training p=0.5 to the unchanged baseline engine,
with all five seed blocks. Use 20 colour-swapped opening pairs per block and
variant, at 50 ms per move with recorded overruns. A separate 20-pair set starts
in the supported endgame family. Ordinary starts: fixed legal 8-ply sequences
generated by a seeded baseline policy before evaluation, filtered for unique
final canonical positions; save PGNs and generator configuration. These are
synthetic openings, not claimed to be a representative opening book. Report
specialist activation frequency; ordinary games may almost never activate it.

Report paired game scores, coverage and uncertainty. Relative Elo is
`400*log10(score/(1-score))` against this baseline under these conditions.
Bootstrap whole colour-swapped pairs within seed blocks, not independent plies;
use 10,000 resamples and retain seed clustering. All-win/all-loss results have
unbounded estimates; do not fabricate finite values. This is not a chess.com,
FIDE or universal Elo rating. Skip this demonstration with a recorded resource
reason if it threatens the core report; retain existing tactics as regression
checks and clearly label previously observed benchmarks.

## 10. Extensions, in priority order

### Ensemble exploration

Compare epsilon-greedy ensemble-mean behavior to episode-sampled-member behavior
for observed and mixed targets at p=0.5, five seed blocks, same selected decision
budget. Each agent has five separately initialized/pretrained MLP members;
both exploration conditions share those members' starting checkpoints. Each
transition receives a fixed independent Bernoulli(0.8) inclusion mask per member,
stored in replay. Each member uses its own online/target weights and its own
backup maxima. Empty member minibatches skip that member's update.

Episode sampling selects one member uniformly at episode start, acts greedily
under it throughout the episode, and uses no additional epsilon. The comparator
uses epsilon=0.1 and the mean prediction. Both evaluate with the ensemble mean
and epsilon zero. Report extra training compute and matched-time sensitivity
if affordable. Members are not independent experimental seeds. Call this
bootstrapped exploration inspired by Thompson sampling, not exact Bayesian
posterior sampling. Kelly Zhang's bandit work motivates careful adaptive-data
analysis; this is not an implementation of a contextual-bandit theorem in chess.

### Advice-triggered defensive targets

Use p=0.5 and five seed blocks. Compare observed, always-mixed and flagged-mixed
learning, where beta=0.5 on a flagged observed opponent worsening reply and zero
otherwise. Advice changes training targets only; no advisor at evaluation.
Flag sources: exact reference oracle, corrupted oracle, and ChessGPT if feasible.
The oracle has privileged information and is an upper-information control.
Corrupted variants separately flip 20% of positives to negatives, or 20% of
negatives to positives; independent seeded flips, not combined corruption.

Use a shared deterministic 10% transition query schedule for all flag sources.
Always-mixed remains always active; the queried-oracle comparison reveals the
cost of sparse advice. Nonqueried, invalid and failed advice defaults to beta=0
and is counted. Keep observed/always-mixed core results as controls where their
configuration matches exactly.

Candidate model is `Waterhorse/chessgpt-chat-v1`; pin the actual downloaded
revision, tokenizer, precision and license. This is a candidate requiring a
feasibility check, not a verified competent FEN blunder classifier. Supply only
the before-reply FEN, legal UCI opponent reply and resulting FEN. Fixed prompt:
"Assess whether this move worsens the mover's theoretical win/draw/loss outcome,
ignoring repetition and the fifty-move rule. Before: {fen_before}. Move: {uci}.
After: {fen_after}. Return exactly {\"blunder\": true} or {\"blunder\": false}."
Use greedy decoding, maximum 32 new tokens, strict JSON boolean parsing and no
retry to repair answers. Cache by model revision, prompt, decoding settings and
input. Never supply tablebase values, intended blunder probability or true flags.

Before online work, report detection confusion matrices, precision, recall,
balanced accuracy, parse failure rate and latency on 200 balanced development
examples and 200 natural-frequency validation examples. Balance only the former.
Do not tune prompts on final examples. Benchmark all attempts even if poor.
Allow up to 2,000 unique model calls including this benchmark. Project calls,
memory and spend before starting the five-seed online matrix; if it will not fit,
retain oracle/noisy controls and report ChessGPT as detection-only. Do not begin
a selectively incomplete online comparison or interpret exhausted-query fallback
as a full-advice result. Advisor imperfection is a result, not proof the central
RL experiment failed. Natural-language explanations are not fed directly into
the numeric learner.

## 11. Prior work and claims

| Reference | Role and boundary |
| --- | --- |
| [Baxter, Tridgell & Weaver, TDLeaf](https://arxiv.org/abs/cs/9901001) and [KnightCap](https://doi.org/10.1023/A:1007634325138) | Historical search/TD chess learning; examine opponent-blunder handling before claiming originality. |
| [Veness et al., Bootstrapping from Game Tree Search](https://cgi.cse.unsw.edu.au/~blair/pubs/2009VenessSilverUtherBlairNIPS.pdf) | Closest motivation for targets from hypothetical search and reduced dependence on opponent play. Our shallow mixed target is a specified variant, not a reproduction of every RootStrap/TreeStrap detail. |
| [Lai, Giraffe](https://arxiv.org/abs/1509.01549) | Neural evaluation and TD chess context; no comparable strength claim. |
| [Wang et al., Safe Opponent Exploitation](https://ojs.aaai.org/index.php/AAAI/article/view/7981) | Defensive play versus exploitation; no safety theorem transfers automatically. |
| [Osband et al., Deep Exploration](https://arxiv.org/abs/1602.04621) | Bootstrapped ensemble exploration extension. |
| [Replicable Bandits](https://arxiv.org/abs/2407.15377) | Adaptive-data/reproducibility interest connected to Kelly Zhang, not direct chess algorithm equivalence. |
| [ChessGPT](https://arxiv.org/abs/2306.09200) and [model card](https://huggingface.co/Waterhorse/chessgpt-chat-v1) | Optional language-based detector; reliability must be measured. |
| [python-chess Syzygy documentation](https://python-chess.readthedocs.io/en/latest/syzygy.html) | Probe conventions, cursed/blessed outcomes and dependencies. |

Before the report, record a short search log with queries, dates, papers screened,
and why the closest works differ. Safe claim: a reproducible, resource-bounded
comparison of opponent-conditioned targets in this defined setting. Unsupported
claim: first robust chess RL algorithm or a demonstrated previously unknown gap.
PhD relevance is empirical design, uncertainty, adaptive learning and careful
computation; do not invent a direct connection to individual supervisors' projects.

## 12. Implementation order, tests and deliverables

1. Inspect repository and preserve current work. Add experiment configuration,
   table acquisition manifest, rule adapter, canonical generator and dataset audit.
2. Test perspective signs, all WDL classes, captures/descendants, mate/stalemate,
   claimable repetition including prospective claims, halfmove draws, symmetry
   grouping, deterministic sampling and missing-table failure. Default tests use
   tiny mock fixtures; downloaded-table checks are marked integration tests.
3. Implement encoder, pretraining and replay/targets. Verify target formulas by
   enumerating toy trees; beta endpoints, detached gradients, target refresh,
   terminal reward once, history isolation and truncation must be covered.
4. Run bounded pilot, record final resource choices and freeze a resolved config
   with dataset/checkpoint hashes before inspecting any final evaluations.
5. Run primary matrix and matched-compute comparisons; save raw records, failures,
   checkpoints, Git state/diff hash, environment, seeds, hardware and timings.
6. Analyze and draft the core report before starting optional work. Integrate
   the specialist, then ensemble exploration, then advisor work as resources allow.
7. Reproduce summaries from raw artifacts, update README with methods, figures,
   uncertainty, limitations, costs, references and commands. Archive a run manifest.

Suggested two-week allocation: first weekend implementation/data/pilot; weekdays
unattended core runs plus short checks; second weekend analysis and integration;
remaining time extensions and writing. Reserve at least the final two days for
reporting and reproducibility. If time runs short, drop optional experiments in
reverse priority, not analysis, seeds or failure accounting.

Required checks after code changes: relevant tests plus `uv run pytest`,
`uv run ruff check .`, `uv run mypy src`, explaining unavailable checks. Training
dependencies should be isolated from lightweight engine/default tests. Do not
commit, buy cloud services, or claim measured outcomes without the corresponding
authorization/evidence. Routine choices governed by this protocol do not require
another user question. Any scientific change outside these bounded rules must be
versioned and explained before the affected final evaluation.
