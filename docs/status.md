# Project status

Last updated: 2026-10-19

Final resume checks:429 passed,4 skipped in the default suite;18 optional pilot
tests and37 optional neural/interaction/target tests passed. Ruff passed and
mypy src plus the pilot script passed48 files. Pilot import, perspective,
seed/stream pairing, dataset/acquisition interfaces, Windows memory handles,
failure records and cost accounting were repaired. No pilot or core matrix has
run; stopping before the account reserve. See root checkpoint.md for commands
and preserved failures. Earlier in-progress notes below are historical.

## Resume verification on 19 October

The structural audit was rerun successfully: 29,500 canonical positions across
development and five KRvKR partitions, with correct quotas, ownership, source
and data hashes, and no duplicate keys. Report:
`artifacts/opponent-dependence-v1/partition-audit-20261019.json`. This checks
start-board separation, not later trajectory overlap; final performance labels
have not been inspected for tuning.

Optional CPU neural/interaction/target checks passed 37 tests; lightweight
audit/interaction checks passed 15 tests. These are focused checks, not a new
full-suite pass. Astra scientific review identified pilot runner defects in
learner-perspective encoding, seed/stream pairing, metadata, failure records
and cost accounting. Repairs and full verification are in progress; no pilot
or core matrix has been launched. Earlier verification below is historical.

## Research implementation underway

The 18 October implementation handover authorizes the neural study and normal
reviewed commits/pushes. The rule/reference adapter, canonical split identities,
serial acquisition and exact 775-feature encoder are implemented. All eight
Syzygy files have been acquired and match publisher whole-file SHA-256 values.
An opt-in real-table check also passed embedded trailer comparisons and
theoretical Bellman consistency on fixed boards and colour exchanges. The
generator-specific checksum algorithm was not recomputed.

Dataset screening and the learning pipeline are still in progress; no neural
training or method comparison has run. The full suite passed 332 tests before
the subsequent encoder/dataset additions; final checkpoint checks follow those
changes. See `docs/research/opponent-dependence-implementation.md` for the current
schedule, environment, corrections, and next actions. The older planning and
milestone records below remain historical evidence.

## Approved research direction (planning record)

Current planning authority: `docs/research/opponent-dependence-protocol-v1.md`.
It specifies algorithms, reference/draw semantics, generated data, neural
architecture, training defaults, five-seed comparisons, statistical analysis,
runtime/strength evaluation, both extensions and bounded feasibility gates.
Earlier drafts and the decisions ledger are historical. This chat remains
planning-only; no experiments have run. Dataset hashes, dependency/model
versions and measured runtime choices are implementation artifacts, not
outstanding discussion questions.

The user approved a two-week RL study of dependence on opponent mistakes,
with secondary tactical/runtime and playing-strength evaluation, including
relative Elo with uncertainty where supported. See
`docs/research/opponent-dependence-protocol-v1.md` for scope and resource limits.
Next: a separate implementation chat should validate data acquisition and
semantics, implement the bounded pilot, and freeze its resolved configuration.
No RL implementation, training or cloud run has started.
The milestone 20 results and earlier evidence below remain unchanged.

Initial planning work on 2026-10-18: targeted literature memo and development
protocol draft added. Close prior work rules out claiming search-informed TD
as new. Protocol v1 distinguishes theoretical board WDL from actual games with
automatic draw claims. Local inventory found RTX 2070 Max-Q (8 GiB), no PyTorch in inspected
project/plot environments, and no Syzygy tables under data/artifacts. No new
training, paid compute or experimental performance measurements. See
`docs/research/opponent-dependence-literature.md` and
`docs/research/opponent-dependence-protocol-draft.md`.

## Current milestone

Milestone 20 complete: our own supervised linear evaluator is trained and usable
through plain alpha-beta, shared tactics/matches and the UCI server. Ordinary
Python handles inference; NumPy 2.5.4 was used only in an existing isolated
training environment. No production dependency or lockfile changed.

The grouped rollout pilot produced 512/128/128 labelled train/validation/test
positions from 64/16/16 trajectories, with old evaluation identities excluded.
Validation selected lambda 0.1 before a separate new-test assessment. New-test
RMSE was 373.90 cp learned versus 389.20 material; MAE was slightly worse
(283.52 versus 282.48). Observed development tactics: learned 5/10 versus material
6/10 at both 1,000 nodes and 50 ms. Four learned-vs-material games yielded one
learned win, one draw and two ply-limit interruptions, with no complete pairs.
Stockfish won all four additional learned-vs-reference smoke games. No Elo or
playing-strength improvement is inferred. The first label attempt's 117 bound
failures and the before-fit label-policy amendment are preserved and disclosed.
See `docs/learned-evaluator.md` and
`experiments/summaries/linear-evaluator-pilot-v1.md` for provenance and limitations.

Verification: 273 tests passed; Ruff and mypy src/src-tests passed; NumPy analytic
ridge self-test and independent pilot audit passed. Original tactical report
files remain byte-identical. Raw datasets/checkpoints/engines stay ignored.
The user selected option 1 and commit/push authorization remains active. The next
meaningful input is the next training-data source: bounded public human games
or engine-guided generated trajectories, with a new sealed test set before tuning.
This pilot model and both observed test sets must remain fixed.

### Preserved milestone 19 history

Milestone 19 complete: one shared tactical runner now evaluates internal and
external agents under the same explicit budget and labelled inputs. It reuses
agent settings, separates setup from decision time, rotates agent order, records
failures/interruption/missing pairs and audits raw results/source/engine pins.
A development-only smoke completed 40/40 searches on ten previously observed
positions: plain alpha-beta 6/10, random 0/10, greedy 2/10, Stockfish 19 10/10
accepted first moves; zero search or cleanup failures. No held-out/Elo claim.
See `docs/tactical-comparisons.md` and
`experiments/summaries/shared-development-tactics-20261017.md`.

Verification: 248 tests passed; Ruff and mypy src/src-tests passed. No dependency
was added. Frozen study artifacts/protocol remain untouched. The next work needs
the user's first learning-method choice, with bounded options in
`docs/research/first-learned-bot-decision.md`; no training/data pipeline was started.
Commit/push remains explicitly authorized.

### Preserved milestone 18 history

Milestone 18 complete: external UCI opponents integrated into colour-paired
matches, with binary pins, full board history, lifecycle/watchdog handling,
failure records, timings and source/version metadata. No dependency was added.
The final local Stockfish 19 smoke run completed four games and two colour pairs:
Stockfish 4 wins, our material alpha-beta 4 losses; zero final-run failures.
The first attempt's four configuration failures and a successful validation
rerun remain disclosed. No Elo or general-strength estimate is inferred.
See `docs/external-opponents.md` and
`experiments/summaries/external-stockfish19-20261017.md`.

Verification: 226 tests passed; Ruff passed; mypy src and src/tests passed.
Windows asyncio required running tests and real games outside the sandbox.
Local CPU only; engine binaries, raw logs, datasets and environments stay ignored.
The user explicitly authorized committing/pushing reviewed existing work and this
milestone on 2026-10-17, superseding earlier no-commit notes below.

### Preserved milestone 17 history

Milestone 17 complete: first held-out tactical quality/search-cost study.
The user selected three timing passes and explicitly authorized an immediate
quiet computer window on 2026-10-17. The frozen 7,200-search local run started
at 13:51 UTC (14:51 Europe/London), with per-case checkpoints and a four-hour cap.
The initial process stopped at 14:11 UTC (15:11 BST) on a Windows metadata-file
replacement PermissionError after 891 completed cases. All saved case/spec hashes
were verified, with zero recorded search failures. It resumed at 14:16 UTC
(15:16 BST) through `scripts/resume_tactical_study.py`, preserving frozen code,
protocol, saved cases and the original 17:51 UTC (18:51 BST) deadline. The wrapper
retries only metadata WinError 5 failures, at most eight times. Original failure
records are retained under the run's `recovery-v1/` directory.
Recovery v1 later exhausted its retries at 2,235 saved cases. At 15:13 UTC
(16:13 BST), recovery v2 resumed with a tested atomic-writer sharing-retry fix,
using the original copied engine/runner plus a disclosed logging-only override.
The original plan/source snapshots remain intact. Hashes, replacement writer
and launcher are recorded in `recovery-v2/amendment.json`; see
`docs/research/tactical-logging-amendment-20261017.md`. The deadline is unchanged.
The study and automatic analysis completed at 17:05 UTC (18:05 BST). All 7,200
searches completed with zero failed/missing search cases, 62.4 million visited
nodes and no repeated-decision/statistic disagreements. Reanalysis reproduced
the summary byte for byte; independent raw-record and source-label audits passed.
The reviewed interpretation is `reports/tactical-study-v1/research-memo.md`.
Long-term research-branch selection and model building have not started.

## Implemented

- Minimal `src`-layout Python package.
- Project and development dependency declarations for `uv`.
- Configuration for pytest, Ruff, and mypy.
- A package-import smoke test.
- Initial repository guidance and ignore rules.
- A minimal deterministic, alternating, two-player game-state protocol.
- An agent protocol with an explicit computation budget and caller-owned RNG.
- Positive depth and node budget representations.
- Documented conventions for state transitions, players, terminal returns,
  actions, and randomness.
- A `python-chess` state adapter with private board ownership and
  immutable-looking transitions.
- Explicit chess player, terminal-outcome, optional-draw, and FEN-history
  semantics.
- Fast initial-position perft verification through depth 3.
- Chess fixtures covering terminal outcomes, castling, en passant, promotion,
  repetition, move-count draws, and illegal actions.
- A seeded random agent that uses caller-owned randomness.
- A generic deterministic two-player match runner with independent player RNGs.
- Structured completed, interrupted, and failed match results.
- Caller-defined action encoding and JSON-compatible match serialization.
- Explicit legal-action validation, ply limits, and runtime failure reporting.
- Immutable chess piece snapshots for safe evaluation access.
- Material evaluation with explicit stable-player perspective.
- Depth-limited exhaustive minimax as a shallow correctness reference.
- Deterministic alpha-beta search with documented depth and node semantics.
- Fixed mate and draw scores that take precedence over heuristic evaluation.
- Search results containing action, value, visited nodes, and completed depth.
- A material alpha-beta chess agent supporting explicit depth and node budgets.
- Artificial-tree tests that compare alpha-beta with exhaustive search and
  measure pruning, plus focused tactical chess fixtures.
- Deterministic iterative deepening that preserves legal-action order.
- Exact cumulative node-budget stopping across completed and partial
  iterations.
- Last-completed-iteration decisions with a documented depth-zero fallback
  when a node budget cannot complete depth one.
- Principal-variation, cutoff, and completed-iteration search statistics.
- An opt-in action-ordering hook that validates the reordered legal actions.
- Safe chess capture classification, including en passant.
- Stable capture-first ordering in the material agent behind an explicit flag.
- An opt-in, per-search transposition table using caller-defined stable keys.
- Depth-aware exact, lower-bound, and upper-bound cache entries.
- Measured transposition-table hits included in search results.
- A diamond-tree correctness fixture comparing cached and uncached search.
- A public chess transposition key containing normalized position identity,
  the halfmove clock, and repetition counts since the last irreversible move.
- Opt-in transposition-table use by the material alpha-beta agent.
- Key tests covering reconstructed states, reversible move-order transpositions,
  and irrelevant history before an irreversible move.
- A generic bounded quiescence hook with caller-selected tactical actions and
  explicit stand-pat legality.
- Tactical actions validated as a duplicate-free subset of legal actions.
- Terminal evaluation before heuristic stand-pat evaluation throughout
  quiescence search.
- Quiescence work included in the same exact node budget as ordinary search.
- Separately reported quiescence-node counts and extended principal variations.
- Public chess check status for safe handling of forced evasions.
- Opt-in material-agent quiescence over captures and promotions.
- All legal evasions searched when the side to move is in check, with stand pat
  disabled.
- A poisoned-pawn regression for a one-ply material horizon error.

- A positive integer millisecond time-budget contract.
- Monotonic-clock deadline checks before every ordinary and quiescence node.
- Last-completed-iteration decisions when a deadline interrupts deeper search.
- A legal depth-zero fallback when time expires before root entry.
- Measured elapsed seconds on time-budget search results.
- No clock sampling or result changes for depth and node budgets.
- Injectable clocks for deterministic deadline tests.
- Millisecond budget kind and value in match metadata.
- Material alpha-beta agent support for wall-clock budgets.

- A `chesslab-uci` console entry point over standard input and output.
- UCI identification, readiness, new-game, stop, and quit commands.
- Atomic `position startpos` and six-field `position fen` setup with optional
  legal UCI move sequences.
- `go depth`, `go nodes`, and `go movetime` budget mapping.
- UCI centipawn and mate score fields, search statistics, principal variation,
  and best-move output.
- Null best moves and diagnostic information for invalid searches.
- Session-level error handling that preserves the command loop.
- Stream and installed console-entry smoke coverage.

- A `chesslab-benchmark` console entry point using JSON input and output.
- Caller-supplied named FEN positions with optional accepted UCI moves.
- Explicit material-agent switches and depth, node, or millisecond budgets.
- Stable SHA-256 configuration digests and deterministic per-position seeds.
- Git commit, dirty state, timestamp, Python, platform, machine, and processor
  provenance.
- Raw per-position decisions, search statistics, timings, failures, and seeds.
- Exact aggregate completion, failure, accepted-move, and node counts.
- Digest matching between benchmark specification and provenance.
- Result overwrite protection.
- Later milestones added versioned puzzle manifests and measured tactical results;
  generated datasets remain ignored.

- A deterministic one-ply material-greedy chess agent.
- Terminal scores taking precedence over immediate material.
- Stable legal-action-order tie breaking.
- Explicit independence from caller budget and RNG.
- A `material_greedy` benchmark agent kind.
- Rejection of alpha-beta-only switches for greedy benchmark runs.

Additional implemented infrastructure:

- Versioned, strict JSON experiment manifests with explicit question, dataset
  identity/version/source/split, shared budget, named variants, and seeds.
- Full variant-by-seed execution through the existing benchmark runner.
- Fresh artifact directories with normalized manifests, incremental raw runs,
  metadata, and descriptive paired comparison summaries.
- Installed engine/rules versions and dependency lock SHA-256 provenance.
- Structured failed/interrupted grid status and partial summaries.
- Explicit failure denominators, unavailable pairs, depth/cutoff/cache/quiescence
  statistics, and variant-minus-reference deltas.
- A versioned development-only synthetic fixture manifest and measured summary.
- Strict two-agent match manifests supporting random, greedy, and alpha-beta
  configurations with shared per-move budgets and explicit ply limits.
- Both agent colour assignments for every seed-position pair, with recorded
  root/match/player seeds and correct Black-to-move attribution.
- Incremental raw game artifacts and completed-game win/draw/loss summaries.
- Failed, interrupted, unrecorded, and incomplete-pair counts kept separate
  from actual draws; no automatic forfeits or ply-limit adjudication.
- Raw-game input validation against the suite manifest and active-game identity
  captured when execution aborts.
- Shared artifact/provenance and JSON validation helpers used by both commands.

Milestone 16 additions:

- Full-snapshot reservoir sampling of a versioned CC0 Lichess puzzle export.
- Setup-ply handling, full-line legality checks and all-immediate-mate labels.
- Connected source-game/position/ID deduplication before disjoint splits.
- Source/split hashes, original metadata, rejection records and provenance.
- 50 development, 50 validation, 200 held-out test positions stored locally.
- Counterbalanced variant/budget schedules with timing repeats, per-case
  checkpoints, runtime caps between searches, and explicit resume validation.
- Source snapshots and code/protocol hashes for dirty-tree reproducibility.
- An explicit protocol-file requirement before executing the held-out test split.
- A reproducible development pilot and optional Node 24 PZstandard preparation
  tool; no new project Python dependency, GPU or reference engine.

## Verification

Latest checks on 2026-10-17, Windows CPython 3.12.14:

- Workspace uv cache and explicit existing interpreter bypassed sandbox cache
  permissions; pytest also needed a workspace base-temp directory.
- Full pytest: 201 passed. Ruff: passed. mypy src: passed (30 source files).
  mypy src tests: passed (50 files). Commands used a workspace cache, explicit
  interpreter and fresh pytest base-temp directory; see `docs/tactical-data.md`.
- Locked offline uv sync: 18 installed packages checked; no change/download.
- Optional Node decompression integration check: passed, including multiple
  frames, overwrite protection and corrupt-input cleanup.
- Complete preparation repeated: identical manifests and split hashes. The
  1,200 sampled rows all validated, with 1,200 independent components.
- Development pilot: 10 puzzles x 4 variants x 3 node budgets = 120 completed
  searches, no failures; 167.189 seconds measured grid wall time.
- Validation preflight: 50 puzzles x 4 variants x 1 budget = 200 completed
  searches, no failures; 44.650 seconds measured invocation wall time.
- Held-out run: 7,200/7,200 searches completed; zero failed/missing search cases.
  Source setup/solution labels were independently rechecked on all 200 positions.
  All 2,400 conditions agreed across three decision/statistic repeats. Total
  visited nodes: 62,400,000. Recording interruptions/amendment remain disclosed.
- At the primary 5,000-node budget: plain 127/200, ordering 137/200, caching
  128/200, quiescence-1 134/200 accepted first moves. Median paired runtime ratios
  versus plain: 2.24x / 1.23x / 4.53x. See report for descriptive paired intervals;
  no population improvement, significance, general-strength or Elo claim.
- Fresh analysis reproduced `analysis.json` byte for byte. A separate audit
  reproduced quality counts, paired differences and timing medians from raw
  records. See `reports/tactical-study-v1/audit.json`.
- Development-only post-study cProfile identifies repeated capture/terminal/
  legality checks and history-key construction as optimisation candidates;
  no code optimisation or speedup is implemented/claimed from this profile.
- Analysis validation tests cover paired bootstrap/percentiles, missing-pair
  bounds and denominators, timing medians, repeat disagreements, source/case
  tampering and unfinished-run rejection. A synthetic end-to-end report/plot
  smoke test passed. Matplotlib is isolated under ignored `artifacts/plot-env/`;
  no frozen project dependency or lockfile changed.
- See `experiments/summaries/tactical-pilot-20261017.md` for measured tables,
  capacity estimates, environment, Git state and limitations.

Historical verification:

Milestone 15 was verified on Windows with CPython 3.12.14:

- `uv run pytest`: passed; 162 tests passed.
- `uv run ruff check .`: passed.
- `uv run mypy src`: passed; no issues found in 28 source files.
- `uv run mypy src tests`: passed; no issues found in 43 source files.
- Development manifest: 4 variants x 2 seeds x 6 positions; all 48 evaluations
  completed with no failures, using 1,000 nodes per search.
- Repeated-seed decisions and search statistics matched within each variant.
- Synthetic match suite: 2 agents x 2 seeds x 2 positions x 2 colour assignments;
  all 8 games completed, all 4 pairs complete, no failures/interruptions.
  Each agent recorded 4 wins, 0 draws, and 4 losses on trivial near-mate fixtures.

Required uv checks needed execution outside the sandbox because its interpreter
and cache access failed. No dependency was added. These changes are being
checkpointed at the user's request on 2026-10-07.
The measurements recorded a dirty Git working tree.

See `experiments/summaries/development-ablation-20261006.md` for observations
and limitations of milestone 14, and
`experiments/summaries/development-matches-20261007.md` for milestone 15.
No held-out accuracy, Elo, or strength improvement is claimed.

## Planned, not implemented

- A more representative next training-data version after source selection, using
  fresh source-group splits and a new sealed test set. The first supervised linear
  evaluator is implemented; neural/RL/self-play/LLM pipelines remain unimplemented.
- Richer quiescence policies such as check generation, delta pruning, or
  selective-depth adaptation.
- Learned models, MCTS experiments, datasets, interfaces, and deployment.

## Open decisions

- The long-term research branch will be selected only after the common
  infrastructure and classical baseline provide evidence for a decision.
- On 2026-10-17 the user chose tactical move quality and search efficiency.
- Target: finish a bounded evaluation and report within approximately one week
  (target 2026-10-24), primarily on the user's computer. Free Colab is optional.
- Up to GBP 50 might be available for compute only after the experiment has been
  checked carefully. This is a ceiling, not authorization to purchase compute.
- Keep terminal utility, the material search heuristic, and external evaluation
  metrics distinct. Define quality before formal experiments, not afterwards.
- Lichess source and preparation are adopted under the user's instruction to
  continue. No reference engine is needed for the first study.
- The run-window/repetitions gate is resolved and the study finished. Do not
  restart it or request another window for this completed experiment.
- The user clarified the practical scope: build a chess bot, compare bots made
  with different methods and existing opponents, and evaluate them. The exact
  research question may develop later. Do not block common setup on a thesis
  question or independently turn engine optimisation into the main objective.
  See `docs/research/practical-project-scope.md` for current gaps and sequence.
- See `docs/research/tactical-evaluation-protocol.md` for the concrete protocol
  and `docs/tactical-data.md` for tested preparation and run commands.

## Resume here next session

The user resumed on 2026-10-17 and selected tactical quality/search efficiency.
Do not ask that priority question again. Read the proposal alongside this file,
`AGENTS.md`, and the implementation guide, then inspect Git status.

The run and analysis are complete, with no background compute needed. Read
`reports/tactical-study-v1/research-memo.md`, `analysis.json`, `audit.json` and
`quality-cost.png`. The first result, data selection and protocol remain frozen.
The user corrected the direction: this is their ML research project, and Codex
must follow their guide rather than choose a research programme independently.
The supplied PDF has been read; consult `docs/research/user-guide-alignment.md`.
The subsequent clarification is recorded in `docs/research/practical-project-scope.md`:
make practical comparisons work now and add methods progressively; do not demand
a fixed ML question before shared setup. The external UCI opponent bridge and
first ordinary-game colour-paired smoke
comparison are now complete. Match configs accept internal or pinned external
agents. Shared tactical comparison is also implemented and smoke-tested on
observed development inputs. The user then chose the supervised evaluator;
the first grouped-data linear pilot is complete. Preserve its checkpoint,
selection/test results and failures. Next choose a new training-data source,
freeze fresh splits/evaluation inputs and do not tune on either observed test set.
Do not build every training pipeline upfront or continue optimisation by default.
Do not repeat the original tactical-vs-Elo choice. A later confirmatory study
must use fresh held-out positions; the original test set is now observed.
Existing positions may serve clearly labelled regression checks.
Preparation data remain at `data/lichess/prepared-v1-verified/`. Analysis and
plotting scripts are outside `src/` and have separate provenance. Commit/push
authorization was subsequently supplied on 2026-10-17. Additional setup/load notes are in
`artifacts/tactical-test-v1-run-notes.json`.

Local raw measurements and data are ignored under `artifacts/` and `data/`;
compact summaries and manifests are being included in the user-authorized
reviewed checkpoint. No paid compute has been used. Held-out
first-move agreement has been measured; general playing strength has not.
