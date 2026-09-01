# Chess AI Research Project: Codex Workflow and Implementation Guide

> A self-contained project handover for starting a fresh Codex chat inside the chess project folder.

## 1. How to use this document

Place this file in the root of the chess project repository. A suggested filename is:

```text
CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md
```

When starting a new Codex chat from the project folder:

1. Ask Codex to read this file completely.
2. Ask it to inspect the actual repository before proposing changes.
3. Use the kickoff prompt in Section 17.
4. Keep durable engineering instructions in `AGENTS.md`, using the template in Section 12.
5. Treat this document as a strategy and workflow guide. Keep current implementation status in `docs/status.md` or GitHub issues so this file does not become stale.

This guide is deliberately self-contained. The two original planning reports can also be placed in `docs/planning/`, but a new chat should not need them in order to begin the first implementation phase.

---

## 2. Executive recommendation

Start implementation now while continuing the reading in parallel. The final research question does not need to be fixed before the common infrastructure is built.

The strongest immediate plan is:

1. Build a reproducible repository and development environment.
2. Use `python-chess` for reliable chess rules, board representation, legal moves, PGN/FEN handling, and later UCI integration.
3. Define small `GameState` and `Agent` interfaces so search algorithms can later be evaluated on simpler games as well as chess.
4. Create legality, terminal-state, and perft tests.
5. Implement a deterministic match runner and structured experiment logging.
6. Add random, material-greedy, and classical alpha-beta baselines.
7. Add iterative deepening, transposition tables, move ordering, UCI support, and benchmark tooling.
8. Use the resulting platform to choose the first substantive research branch.

The early foundation is useful for all three of the most plausible directions:

- **Human-like chess modelling:** predict human moves, condition on rating or time control, study calibration and blunders.
- **Learned evaluation and hybrid search:** compare handcrafted evaluation against supervised learned evaluation at fixed compute.
- **MCTS across game complexity:** compare MCTS variants on games such as Connect Four, Othello, and chess under controlled budgets.

Do not spend weeks perfecting the development workflow before coding. The initial setup should take approximately one focused session. The workflow should then improve gradually in response to real friction.

---

## 3. Project purpose and research standard

The aim is not merely to build a chess engine or deploy a bot that can beat casual players. The aim is to create a compact, defensible research artifact demonstrating:

- clean software design;
- knowledge of classical search and modern learning methods;
- controlled experimental comparisons;
- statistical evaluation;
- reproducibility;
- honest reporting of negative and positive results;
- the ability to connect theory, implementation, and empirical evidence.

A suitable high-level description is:

> A reproducible game-playing research platform for comparing classical search, learned evaluation, human-like modelling, and Monte Carlo planning under controlled computational budgets.

The project should eventually answer clear questions rather than accumulating disconnected features. Examples include:

- How much does learned evaluation improve alpha-beta search at a fixed node budget?
- How do different MCTS selection or backup rules behave as game complexity increases?
- Does conditioning on player strength improve human move prediction and calibration?
- Which search improvements increase playing strength because they examine better positions, rather than simply examining more positions?
- How stable are conclusions across openings, tactical positions, endgames, time controls, and random seeds?

The repository should ultimately read like a small research lab notebook, not a product demo.

### Non-negotiable academic rule

Every claim must be defensible.

- Never present a planned component as completed.
- Never present an estimate as a measurement.
- Never invent an Elo rating, accuracy, speedup, confidence interval, or result.
- Do not call an idea novel unless a literature search supports that claim.
- Keep the distinction between replication, extension, and original investigation explicit.
- Record failures and null results when they are informative.

---

## 4. Reconciling the possible project directions

The planning work suggests two attractive long-term narratives:

### Direction A: human-like, strength-conditioned chess

Train models on public human games and evaluate:

- next-move prediction;
- top-k accuracy;
- negative log-likelihood;
- calibration;
- blunder prediction;
- performance by rating bucket;
- performance by opening, time control, or tactical theme;
- the gap between optimal engine play and realistic human play.

This direction is statistically rich and tractable for a solo project. It does not require superhuman playing strength to produce worthwhile results.

### Direction B: search, learned evaluation, and MCTS

Build a classical baseline, introduce learned components, and compare planning algorithms under controlled compute. The original idea of testing MCTS variants on increasingly complex games fits here.

Possible games might include:

1. Tic-tac-toe as a correctness check, not a serious benchmark.
2. Connect Four as a small deterministic planning task.
3. Othello/Reversi as a larger branching and positional task.
4. Chess as the most complex target environment.

The exact sequence should be justified using measurable properties such as branching factor, typical episode length, state-space scale, tactical depth, and availability of exact or strong reference solutions. Avoid casually asserting that one game is simply “more complex” without defining the relevant dimension.

### Why no final choice is needed yet

Both directions require:

- correct game-state handling;
- repeatable agents;
- controlled compute budgets;
- match execution;
- structured metrics;
- baselines;
- reliable tests;
- experiment configuration;
- documentation.

Therefore the first implementation phase should remain neutral. Do not introduce a large neural architecture, Lichess data pipeline, full AlphaZero loop, or LLM component until the foundation is working.

---

## 5. Recommended division of tools

### ChatGPT Work

Use ChatGPT Work for:

- breaking down papers;
- comparing possible research directions;
- clarifying mathematical concepts;
- designing experiments;
- discussing statistical methodology;
- interpreting plots and failures;
- drafting research notes and reports;
- challenging whether a result supports a claim.

Do not leave important decisions only in chat history. Once a decision is made, record it in the repository.

### Codex in the IDE

Use the Codex IDE integration for:

- focused changes involving open files or selected code;
- implementing a small feature;
- tracing bugs;
- adding or updating tests;
- reviewing diffs beside the source;
- asking questions about unfamiliar code;
- delegating a larger but clearly scoped task.

This is the closest analogue to an agent-oriented Copilot workflow. It is not primarily a replacement for character-by-character or line-by-line autocomplete. Its main advantage is that it can understand a wider task, edit multiple files, run commands, inspect failures, and verify the result.

### Codex CLI

Use the CLI when:

- working mainly from the terminal;
- running repo-wide investigation or review;
- using `/init`, `/plan`, `/status`, `/review`, or other commands;
- scripting a stable repeated workflow;
- starting a task from a precise repository directory.

For normal local use, sign in with the ChatGPT account rather than using an API key. An API key is separately billed and is more appropriate for programmatic automation or CI after such automation is actually required.

### Git and GitHub

Git is required from the beginning. GitHub is highly recommended once the initial repository exists.

Use Git for:

- recoverable checkpoints;
- inspecting exactly what Codex changed;
- separating milestones and experiments;
- linking experiment results to a commit;
- avoiding an untraceable sequence of AI-generated edits.

Use GitHub later for:

- issues representing bounded tasks;
- pull requests for substantial milestones;
- CI;
- external code review;
- presenting the finished research artifact.

An optional GitHub integration can allow Codex to inspect repositories, pull requests, issues, and CI. It is useful, but it is not required for the first local milestone.

---

## 6. Recommended local setup

### Core tools

- Git
- Python 3.11 or 3.12
- `uv` for virtual environments, dependency resolution, and locking
- VS Code with the Python, Ruff, and Codex extensions
- `pytest`
- `pytest-cov`
- Ruff
- mypy
- `python-chess`

Do not install PyTorch, JAX, OpenSpiel, PettingZoo, MLflow, DVC, Docker, or a database during the initial scaffold unless an immediate task requires it.

### Initial commands

From a terminal in the parent directory:

```bash
mkdir chess-ai-lab
cd chess-ai-lab

git init

uv init --package
uv add python-chess
uv add --dev pytest pytest-cov ruff mypy
```

If the project directory already exists, do not run commands blindly. Open the existing folder, inspect its contents, and adapt the commands to avoid overwriting user work.

### Initial verification commands

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

It is acceptable for the first `pytest` run to report that no tests exist. Once the scaffold task is complete, all three checks should pass.

### Windows recommendation

Native Windows is sufficient for the classical baseline and infrastructure. Do not introduce WSL solely for the initial phase. Reconsider WSL or Linux when GPU training, Linux-specific tooling, or deployment creates a concrete reason.

---

## 7. Proposed repository structure

```text
chess-ai-lab/
├── AGENTS.md
├── CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── configs/
│   ├── baselines/
│   └── experiments/
├── docs/
│   ├── decisions/
│   ├── planning/
│   ├── research/
│   └── status.md
├── experiments/
│   ├── manifests/
│   └── summaries/
├── reports/
├── scripts/
├── src/
│   └── chesslab/
│       ├── __init__.py
│       ├── games/
│       │   ├── __init__.py
│       │   ├── protocols.py
│       │   └── chess/
│       │       ├── __init__.py
│       │       ├── state.py
│       │       ├── perft.py
│       │       └── outcomes.py
│       ├── search/
│       │   ├── __init__.py
│       │   ├── budgets.py
│       │   ├── results.py
│       │   └── classical/
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── evaluation/
│       │   └── uci/
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── protocols.py
│       │   └── random_agent.py
│       ├── learning/
│       │   └── __init__.py
│       └── eval/
│           ├── __init__.py
│           ├── matches.py
│           ├── metrics.py
│           └── logging.py
└── tests/
    ├── unit/
    ├── integration/
    ├── perft/
    └── fixtures/
```

This is a target structure, not a requirement to create every empty directory immediately. Create modules when their first real responsibility appears. Empty architecture can create the illusion of progress without working behaviour.

### Data and artifacts

Do not commit large datasets, model checkpoints, engine binaries, or generated match logs.

The `.gitignore` should eventually include entries such as:

```gitignore
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
data/
artifacts/
checkpoints/
*.pyc
```

Commit:

- small deterministic fixtures;
- dataset manifests;
- download or preparation scripts;
- configuration files;
- compact result summaries;
- plots used in the report when reasonable;
- documentation explaining how results were produced.

---

## 8. Core interface design

The interfaces should support the current chess work and preserve the later MCTS comparison without becoming a universal game framework.

### Game-state protocol

The initial protocol only needs to describe deterministic, alternating, two-player, zero-sum games.

Conceptually:

```python
class GameState(Protocol[ActionT]):
    @property
    def current_player(self) -> int: ...

    def legal_actions(self) -> Sequence[ActionT]: ...

    def apply(self, action: ActionT) -> Self: ...

    def is_terminal(self) -> bool: ...

    def returns(self) -> tuple[float, float]: ...
```

This is a design sketch, not mandatory code. Codex should inspect typing support and the desired mutability model before implementing it.

Important decisions:

- Public state transitions should be easy to reason about.
- Avoid exposing accidental mutation from an internal `python-chess.Board`.
- Player identifiers and terminal returns must have a documented convention.
- Illegal actions should fail clearly.
- Repetition and draw-claim behaviour must be specified rather than assumed.
- Do not add chance nodes, simultaneous actions, multiplayer support, or imperfect information until a real experiment requires them.

### Agent protocol

Conceptually:

```python
class Agent(Protocol[StateT, ActionT]):
    def select_action(
        self,
        state: StateT,
        budget: SearchBudget,
        rng: random.Random,
    ) -> AgentDecision[ActionT]: ...
```

The explicit random-number generator prevents agents from silently using global random state.

### Search budget

Support the idea of a controlled computational budget from the beginning.

Potential budget types:

- fixed node expansions;
- fixed simulations;
- fixed depth;
- wall-clock time.

Fixed node or simulation budgets are generally more reproducible across machines. Wall-clock performance is still valuable, but it should be reported with hardware and software details.

### Agent decision and search result

Conceptually record:

```text
action
score
nodes
depth
elapsed_seconds
principal_variation
metadata
```

Later metadata can include transposition-table hits, cutoffs, simulations, average search depth, or policy entropy. Do not add fields merely because they might someday be useful.

---

## 9. Correctness and testing strategy

### What `python-chess` should own

Use `python-chess` for:

- legal move generation;
- board representation;
- FEN and PGN parsing;
- check, checkmate, stalemate, and draw-related logic;
- move application and reversal;
- later UCI engine communication;
- later Syzygy tablebase access.

Do not spend weeks writing a chess move generator. The research value lies in search, learning, evaluation, and experimental design.

### Perft

Perft recursively counts legal move sequences to a chosen depth. It is primarily a correctness test for state transitions and move handling, not a strength benchmark.

For the standard initial chess position, commonly used counts are:

| Depth | Nodes |
|---:|---:|
| 1 | 20 |
| 2 | 400 |
| 3 | 8,902 |
| 4 | 197,281 |

The initial implementation does not need very deep perft runs. Keep routine tests fast and place slower validations behind an explicit marker.

Additional fixtures should eventually cover:

- castling rights;
- en passant;
- promotion;
- check evasions;
- pinned pieces;
- checkmate;
- stalemate;
- insufficient material;
- repetition behaviour;
- fifty-move-rule behaviour.

### Test layers

Use three main layers:

1. **Unit tests:** a small component or invariant.
2. **Integration tests:** interactions such as state + agent + match runner.
3. **Research/benchmark checks:** slower comparisons, perft suites, matches, puzzles, or tablebases.

Do not make the ordinary test suite depend on a large download, GPU, Stockfish binary, or internet connection.

### Determinism

Where randomness is present:

- pass an explicit RNG or seed;
- record the seed;
- test that repeated runs with the same seed agree when they should;
- do not confuse deterministic execution with statistical robustness;
- use multiple seeds for claims about stochastic methods.

---

## 10. Reproducible experiment design

Every experiment should be reproducible from a configuration and a Git commit.

### Minimum run metadata

Record:

```text
run_id
timestamp
git_commit
working_tree_dirty
config_path or embedded config
random_seed
Python version
dependency-lock hash or version reference
operating system
CPU/GPU information when relevant
agent/engine versions
dataset identifier and preparation version
budget type and value
status: completed, failed, or interrupted
metrics
notes or error summary
```

### Suggested output structure

```text
artifacts/
└── RUN_ID/
    ├── config.toml
    ├── metadata.json
    ├── metrics.json
    └── run.log
```

Large artifacts should remain untracked. Commit compact tables, manifests, scripts, and figures needed to reproduce the reported result.

### Early metrics

For classical search:

- nodes searched;
- depth reached;
- elapsed time;
- nodes per second;
- transposition-table hits;
- alpha-beta cutoffs;
- tactical-suite accuracy;
- match outcomes;
- confidence intervals when match counts become meaningful.

For learned human-move models later:

- negative log-likelihood;
- top-1 and top-k accuracy;
- expected calibration error or another justified calibration measure;
- Brier score where appropriate;
- blunder-prediction metrics;
- breakdown by rating, opening, time control, or tactical class.

For MCTS later:

- simulations;
- node expansions;
- root visit distribution;
- selected action value;
- depth statistics;
- win rate or exploitability when available;
- sensitivity to exploration constants;
- performance under fixed simulations and fixed time;
- results across multiple seeds and starting positions.

### Experimental discipline

- Define the question and primary metric before running a large experiment.
- Separate development positions from final test positions.
- Avoid repeatedly tuning against the same benchmark and then treating it as an unbiased evaluation.
- Compare against the simplest credible baseline.
- Change one major factor at a time for interpretable ablations.
- Preserve failed configurations when they teach something.
- Report uncertainty rather than only point estimates.
- Document stopping rules for sequential or adaptive evaluation.

---

## 11. Working with Codex effectively

### The basic task loop

For each bounded task:

1. Make sure the working tree is understood.
2. State the goal.
3. Point to relevant files or documentation.
4. State constraints and non-goals.
5. Define completion criteria.
6. Ask for a plan first if the task is ambiguous.
7. Let Codex implement the smallest coherent slice.
8. Require tests and verification.
9. Inspect the diff.
10. Run a separate review.
11. Understand the important code personally.
12. Commit only after review.

### Standard prompt shape

Use:

```text
Goal:
What should change?

Context:
Which files, designs, errors, or previous decisions matter?

Constraints:
What architecture, dependencies, safety rules, or exclusions apply?

Done when:
What observable conditions prove completion?
```

### Model and reasoning guidance

Where the available interface provides different models or reasoning levels:

- Use a stronger model and higher reasoning for architecture, research methodology, subtle algorithmic correctness, difficult debugging, and final review.
- Use a balanced setting for ordinary feature implementation.
- Use faster/lighter settings for repo exploration, formatting, repetitive test parametrisation, or documentation cleanup.
- Do not use maximum reasoning for every small task.
- Do not use subagents for a task that one agent can complete cleanly.
- Use `/status` or the relevant usage display to monitor plan usage.

### What the user should always inspect

The user should personally inspect and understand:

- state transition semantics;
- terminal values and perspective conventions;
- negamax/minimax sign handling;
- alpha-beta bounds;
- mate-score conventions;
- transposition-table bound types;
- MCTS selection, expansion, backup, and perspective changes;
- training-target construction;
- data leakage risks;
- evaluation splits;
- confidence intervals and statistical tests;
- any sentence making a research claim.

AI assistance is most useful when it accelerates implementation and review without replacing understanding.

### Review prompt

After implementation:

```text
Review the uncommitted changes against AGENTS.md and the task specification.

Prioritise:
1. Incorrect chess or game semantics.
2. Sign or player-perspective bugs.
3. Hidden mutation and nondeterminism.
4. Missing or weak tests.
5. Experiment leakage or irreproducible results.
6. Unnecessary abstraction or dependencies.
7. Claims not supported by measured evidence.

Do not modify files. Report findings by severity with file references and
explain how each issue can affect correctness or research conclusions.
```

---

## 12. Recommended `AGENTS.md`

Run `/init` if useful, then replace or refine the generated file. The following is a suitable starting point.

```md
# Project purpose

Build a reproducible research platform for comparing game-playing methods,
beginning with chess infrastructure and classical baselines. The repository
is intended to support a rigorous Stats/ML/AI PhD application project.

# Required context

Read `CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md` before planning a new
milestone. Check `docs/status.md` for current progress. Do not assume that
planned features are implemented.

# Current scope

The current phase is infrastructure and classical baselines unless the user
explicitly changes it. Do not introduce neural networks, large datasets,
self-play training, MCTS frameworks, an LLM layer, a GUI, or deployment as
part of an unrelated task.

# Research integrity

- Never invent or estimate experimental results and present them as measured.
- Distinguish plans, hypotheses, measurements, and conclusions.
- Do not claim novelty without evidence from a literature review.
- Record seeds, configurations, Git state, hardware, data versions, and
  failures for experiments.
- Prefer controlled comparisons under explicit node, simulation, depth, or
  time budgets.
- Keep benchmark/test data separate from data used for tuning.

# Engineering rules

- Inspect the repository and existing changes before editing.
- Preserve user changes and avoid unrelated rewrites.
- Make the smallest coherent change that satisfies the task.
- Use `python-chess` for chess rules and legal move generation.
- Do not build a custom legal-move generator.
- Keep the generic game protocol limited to requirements that are currently
  used by at least one implementation or an approved near-term milestone.
- Pass randomness explicitly; avoid hidden global random state.
- Prefer typed, documented Python for public interfaces.
- Ask before adding a production dependency unless the task explicitly
  requires it.
- Do not add empty modules or speculative architecture solely to match a
  future folder diagram.

# Tests

- Add or update tests for changed behaviour.
- Test game semantics and edge cases, not only happy paths.
- Keep the default test suite independent of GPUs, large downloads, internet
  access, and external engine binaries.
- Mark slower benchmark or integration tests clearly.

# Verification

Before declaring a coding task complete, run the relevant subset and normally:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

If a command cannot run, explain exactly why. Never claim a check passed when
it was not run.

# Completion report

Summarise:

1. Files changed.
2. Important design decisions.
3. Tests and checks run.
4. Known limitations or risks.
5. The next smallest sensible task.

Do not commit changes unless the user explicitly asks.
```

---

## 13. Milestone plan

### Milestone 0: repository and environment scaffold

Deliverables:

- `uv` project and lockfile;
- package under `src/chesslab/`;
- development dependencies;
- basic `README.md` that clearly labels the work as in progress;
- `.gitignore`;
- `AGENTS.md`;
- initial smoke test;
- Ruff and mypy configuration;
- `docs/status.md`.

Acceptance criteria:

- `uv sync` succeeds;
- `uv run pytest` succeeds;
- `uv run ruff check .` succeeds;
- `uv run mypy src` succeeds;
- no ML or engine code is added prematurely;
- the working tree contains only deliberate files.

### Milestone 1: game and agent contracts

Deliverables:

- minimal game-state protocol;
- minimal agent protocol;
- search-budget and agent-decision representations;
- documented conventions for players, actions, terminal returns, and randomness;
- tests with a tiny fake game if useful.

Acceptance criteria:

- interfaces are exercised by tests;
- no speculative multiplayer or stochastic-game features;
- random state is passed explicitly;
- conventions are recorded in `docs/decisions/`.

### Milestone 2: chess adapter and correctness suite

Deliverables:

- `python-chess` state adapter;
- legal action conversion;
- state transitions;
- terminal results;
- perft implementation or adapter-level verification;
- terminal-state and special-move tests.

Acceptance criteria:

- standard initial-position perft counts pass to a reasonable routine depth;
- checkmate and draw-related fixtures pass;
- invalid actions fail clearly;
- parent-state mutation behaviour is tested and documented.

### Milestone 3: random agent and match runner

Deliverables:

- seeded random agent;
- game runner;
- termination handling;
- match result representation;
- structured run metadata;
- deterministic integration tests.

Acceptance criteria:

- two random agents can complete games;
- repeated runs with the same seed behave consistently where expected;
- illegal moves cannot silently enter the game record;
- results can be serialised.

### Milestone 4: first classical baseline

Deliverables:

- material evaluation;
- optional simple piece-square terms;
- depth-limited negamax/minimax;
- alpha-beta pruning;
- mate and draw scoring;
- search statistics;
- tactical unit fixtures.

Acceptance criteria:

- search agrees with exhaustive minimax on tiny constructed trees;
- player-perspective signs are tested;
- mate is preferred appropriately;
- alpha-beta returns the same action/value as the unpruned reference on test cases;
- node-count reductions are measured rather than asserted.

### Milestone 5: stronger classical baseline

Deliverables:

- iterative deepening;
- transposition table;
- principal variation;
- basic move ordering;
- quiescence search only after the earlier components are correct;
- UCI interface;
- fixed-budget benchmark scripts.

Acceptance criteria:

- each optimisation can be enabled or disabled;
- ablations compare against the same underlying evaluator and positions;
- correctness remains stable;
- speed and node changes are recorded;
- UCI commands needed for standard engine use behave correctly.

### Milestone 6: research-direction decision gate

Do not select the next branch merely because it sounds impressive. Write a short decision memo comparing:

- research question;
- novelty relative to existing work;
- required compute;
- data availability;
- implementation risk;
- evaluation quality;
- likely time to first informative result;
- alignment with the desired PhD narrative.

Candidate branches:

1. Learned evaluator inside alpha-beta.
2. Human-like strength-conditioned policy model.
3. MCTS variants across games of increasing defined complexity.
4. Lightweight self-play extension after success on a simpler game.
5. Tool-using or language-conditioned interface as a bounded extension.

---

## 14. Suggested first two weeks

The precise schedule should adjust to available time and debugging difficulty.

### Week 1: trustworthy infrastructure

#### Session 1

- Inspect or create the repository.
- Configure `uv`, tests, Ruff, and mypy.
- Add `AGENTS.md` and `docs/status.md`.
- Make one clean initial commit.

#### Session 2

- Design the minimal game and agent protocols.
- Write the conventions before or alongside implementation.
- Test with a small fake deterministic game if that helps expose perspective and terminal-value conventions.

#### Session 3

- Implement the `python-chess` adapter.
- Test legal actions, state transitions, terminal outcomes, and mutation behaviour.

#### Session 4

- Add perft and chess edge-case fixtures.
- Keep routine tests fast.
- Create a separate marker or command for slower checks.

#### Session 5

- Implement the seeded random agent and game runner.
- Produce a serialisable match record.
- Update `docs/status.md` and record unresolved questions.

End-of-week outcome:

> The repository can execute legal, reproducible games and produce structured results, even though the agent has no meaningful chess strength.

### Week 2: classical baseline

#### Session 6

- Implement a transparent material evaluator.
- Add tests for sign and player perspective.

#### Session 7

- Implement reference minimax or negamax at shallow depth.
- Validate it on tiny constructed trees and tactical fixtures.

#### Session 8

- Add alpha-beta pruning.
- Prove correctness empirically against the unpruned reference on a large set of small positions or artificial trees.
- Measure node counts.

#### Session 9

- Add iterative deepening and search statistics.
- Establish fixed-depth and fixed-node benchmark modes.

#### Session 10

- Add a simple transposition table and move ordering behind configuration flags.
- Run the first explicit ablation.
- Write a short results memo including failures and limitations.

End-of-week outcome:

> The repository contains a credible classical baseline and the first controlled comparison, providing a stable foundation for the research branch.

Do not force all five sessions into a calendar week if that causes rushed code. The ordering is more important than the dates.

---

## 15. Agent and worktree strategy

### Start with one implementing agent

For early milestones, one main agent should normally inspect, implement, test, and summarise. The repository is small, and multiple writers create more coordination work than value.

### Good uses of subagents

Use subagents for independent, usually read-only work such as:

- auditing game-rule correctness;
- checking test gaps;
- reviewing experimental methodology;
- inspecting nondeterminism;
- comparing two possible library designs;
- analysing long logs;
- reviewing documentation against implementation;
- performing a final multi-angle review.

Example:

```text
Review the current baseline milestone using three read-only subagents:

1. Audit chess-rule, terminal-state, and perft correctness.
2. Audit test coverage, hidden mutation, and nondeterminism.
3. Audit experiment metadata and reproducibility.

Do not modify files. Wait for all agents and synthesise the findings by
severity with file references. Clearly separate confirmed bugs from risks
or suggestions.
```

### Poor uses of subagents

Avoid:

- assigning several agents to edit the same engine files;
- spawning agents for tiny tasks;
- asking each agent the same broad question;
- using parallel agents without a defined synthesis step;
- delegating the main research judgement without reviewing their evidence;
- consuming extra usage merely because agents are available.

### Worktrees

After the repository is stable, worktrees can isolate truly independent tasks. Examples:

- one worktree for the benchmark harness;
- one for a dataset loader;
- one for documentation or a report;
- one for an experimental MCTS branch.

Do not create multiple worktrees until tests and Git practices are reliable. An isolated branch does not prevent two bad designs from being difficult to merge.

---

## 16. Prompt library

### A. Plan a bounded feature

```text
Read `AGENTS.md`, `CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`, and
`docs/status.md`. Inspect the repository and current Git diff.

Goal:
[State one bounded outcome.]

Context:
[Name relevant modules, prior decisions, failures, or issue numbers.]

Constraints:
[State architecture, dependencies, non-goals, and research requirements.]

Done when:
[List observable acceptance criteria and verification commands.]

First propose a file-level implementation plan, identify ambiguous design
decisions, and state the tests you intend to add. Do not edit files yet.
```

### B. Implement an approved plan

```text
Implement the approved plan as the smallest coherent change.

- Preserve unrelated user changes.
- Add or update tests for changed behaviour.
- Run the relevant tests, Ruff, and mypy.
- Inspect the final diff for accidental or unnecessary changes.
- Do not commit.

At the end, report:
1. Files changed.
2. Important design decisions.
3. Checks run and their outcomes.
4. Known limitations or risks.
5. The code I should inspect most carefully.
```

### C. Diagnose without fixing

```text
Diagnose the reported problem without modifying files.

Reproduce it if safely possible, trace the relevant code paths, and identify
the most likely root cause. Separate evidence from hypotheses. Report:

1. Reproduction steps.
2. Observed behaviour.
3. Expected behaviour.
4. Root cause with file references.
5. Smallest plausible fix.
6. Tests that would prevent regression.
```

### D. Review a completed change

```text
Review the uncommitted changes against the task, `AGENTS.md`, and existing
design decisions. Do not modify files.

Prioritise correctness, game semantics, player perspective, hidden mutation,
nondeterminism, missing tests, reproducibility, data leakage, and unsupported
claims. Report findings by severity with file references. Do not report
formatting preferences unless they materially affect maintainability.
```

### E. Design an experiment

```text
Help design this experiment before writing implementation code.

Research question:
[Question]

Candidate methods:
[Methods]

Available data and compute:
[Constraints]

Propose:
1. Primary hypothesis and credible null result.
2. Baselines.
3. Independent and dependent variables.
4. Fixed computational budgets.
5. Data splits and leakage risks.
6. Primary and secondary metrics.
7. Uncertainty estimates or statistical tests.
8. Ablations.
9. Failure analysis.
10. Minimum result that would still be informative.

Challenge weak assumptions and do not imply novelty or expected success.
```

### F. Explain generated code for personal understanding

```text
Teach me the implementation in [files] so I can defend it in a technical or
PhD interview. Do not change code.

Explain:
1. The main invariants.
2. Control flow on one concrete example.
3. Player-perspective and sign conventions.
4. Time and space complexity.
5. Why the tests are sufficient or insufficient.
6. Failure modes.
7. Three questions an expert might ask me.
8. A small exercise that would demonstrate I understand the component.
```

---

## 17. Detailed kickoff prompt for the new chat

Open the chess project folder in VS Code, the ChatGPT desktop app, or Codex CLI. Place this guide in the repository root. Then paste the prompt below.

```text
You are working inside my chess AI research project repository.

Before doing anything else, completely read:

- `CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`
- `AGENTS.md`, if it already exists
- `docs/status.md`, if it already exists
- the current `README.md` and `pyproject.toml`, if they exist

Then inspect the repository structure and Git status. Preserve any existing
work. Do not assume the repository is empty and do not overwrite files merely
to match the target structure in the guide.

Project purpose:

I am building a reproducible research platform for a Stats/ML/AI PhD
application. The long-term research direction is deliberately still open.
Possibilities include:

1. Human-like, strength-conditioned chess modelling.
2. Learned evaluation combined with classical search.
3. Comparing MCTS variants across games of increasing, explicitly defined
   complexity.

The immediate work must remain useful for all three directions. Academic
honesty is essential: do not invent results, overstate progress, or imply
novelty.

Immediate goal:

Prepare and complete Milestone 0: repository and environment scaffold.

Required outcomes:

- A clean Python package using the `src/` layout.
- `uv` project configuration and a lockfile.
- `python-chess` as the only required runtime dependency unless the existing
  repo already justifies others.
- Development dependencies for pytest, pytest-cov, Ruff, and mypy.
- A concise `.gitignore`.
- A truthful work-in-progress `README.md`.
- `docs/status.md` recording what actually exists and what is only planned.
- `AGENTS.md` based on the template in the guide, adapted to the actual repo.
- A minimal smoke test.
- Configuration allowing these commands to pass:

  `uv run pytest`
  `uv run ruff check .`
  `uv run mypy src`

Constraints:

- Do not implement chess search, a game protocol, neural networks, MCTS,
  datasets, an LLM component, a GUI, or deployment in this milestone.
- Do not create a large tree of empty speculative modules.
- Do not add Docker, MLflow, DVC, PyTorch, JAX, OpenSpiel, PettingZoo, or a
  database.
- Do not delete, replace, or rewrite existing user work without explaining
  why and obtaining approval when the conflict is material.
- Keep the structure minimal and suitable for expansion in the next milestone.
- Do not commit changes.

Working method:

1. Inspect first.
2. Summarise the current state and any conflicts with the guide.
3. Propose a precise file-level plan and the commands you intend to run.
4. Ask only questions whose answers would materially change the scaffold.
5. Wait for my approval before editing.

When implementation is later approved, perform the work, run the required
checks, inspect the diff, and report:

1. Files changed.
2. Important choices.
3. Verification results.
4. Known limitations.
5. The exact next prompt for Milestone 1.
```

### Approval response after reviewing the plan

If the proposed plan is appropriate, respond with:

```text
The plan is approved. Implement Milestone 0 exactly within the agreed scope.
Run all required verification commands, inspect the final diff, and do not
commit. If you encounter a material conflict with existing work, stop and ask
before resolving it.
```

### Fast-start alternative

If the repository is genuinely empty and the initial inspection reveals no meaningful choices, the user may replace “Wait for my approval before editing” with:

```text
If the repository is empty and there are no material ambiguities, you may
implement the scaffold immediately after briefly stating the plan. Otherwise,
stop for approval.
```

The approval-based version is recommended for the first use because it shows how Codex intends to structure the repository before files are created.

---

## 18. Prompt for Milestone 1 after the scaffold

Once Milestone 0 has been reviewed and committed, start a fresh focused chat or continue with a clean context and use:

```text
Read `AGENTS.md`, `CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md`,
`docs/status.md`, and the current source/tests. Inspect Git status first.

Goal:
Design and implement Milestone 1: the smallest useful deterministic,
alternating, two-player game-state contract and agent contract.

The purpose is to support a `python-chess` adapter now while preserving a
future controlled MCTS comparison on simpler board games. This is not a
request for a universal game framework.

Required design questions to resolve before editing:

1. Mutable versus immutable-looking state transitions.
2. Player identifier convention.
3. Terminal return convention and perspective.
4. Action typing.
5. Explicit RNG handling.
6. Search-budget and agent-decision information needed immediately.

Constraints:

- Do not implement the chess adapter yet unless a tiny test double is
  insufficient to exercise the contract.
- Do not support chance nodes, simultaneous actions, imperfect information,
  multiplayer games, or generic environment wrappers.
- Avoid interfaces containing unused future methods.
- Add tests demonstrating the semantics.
- Record important conventions in a short decision document.

Done when:

- The contracts exist and are exercised by tests.
- The conventions are explicit and internally consistent.
- pytest, Ruff, and mypy pass.
- No unrelated features are introduced.

First propose the design and file-level plan. Do not edit until I approve.
```

---

## 19. Common failure modes to avoid

### Workflow procrastination

Do not spend multiple weeks configuring tools, agents, plugins, and automation. The baseline itself is the priority.

### Blind acceptance of generated code

Code that passes tests can still encode the wrong player perspective, terminal convention, data split, or metric. Understand the research-critical sections.

### Over-generalisation

A generic game interface is useful. A universal environment framework supporting every possible game is not required.

### Premature deep learning

Do not add PyTorch and a large dataset before the match runner, metrics, baselines, and data-split plan are trustworthy.

### Full AlphaZero ambition

Do not make “train a superhuman chess engine from scratch” the core target. Small-scale self-play can be an informative extension after a simpler environment works.

### Raw LLM chess as the core engine

If an LLM component is added later, prefer tool use, explanation, controlled reranking, annotation, or language conditioning. Legal moves and engine tools should constrain the system.

### UI-first development

A polished interface is not the research contribution. Build it only after the experimental system is credible.

### Benchmark overfitting

Do not repeatedly tune on the same positions and then present their result as an unbiased test.

### Single-number evaluation

Elo alone is insufficient. Combine match strength with efficiency, tactics, endgames, calibration, prediction, or failure analysis as appropriate to the chosen branch.

### Parallel write conflicts

Subagents are valuable for independent investigation. They are not automatically valuable when several agents edit overlapping search code.

### AI-written claims without verification

Every factual statement in the eventual report should be checked against code, logs, results, and cited literature.

---

## 20. Decision gate after the classical baseline

Once the classical baseline and evaluation harness work, write a decision memo containing the following table.

| Criterion | Human-like model | Learned evaluator | MCTS across games | Small self-play | LLM/tool layer |
|---|---|---|---|---|---|
| Precise research question | | | | | |
| Closest prior work | | | | | |
| Required data | | | | | |
| Required compute | | | | | |
| Engineering risk | | | | | |
| Evaluation quality | | | | | |
| Time to first result | | | | | |
| Statistical depth | | | | | |
| Alignment with interests | | | | | |
| Minimum informative outcome | | | | | |

The decision should be based on the evidence available at that point, not on the apparent prestige of the method.

---

## 21. Immediate checklist

Before opening the new chat:

- [ ] Place this file in the project root.
- [ ] Open the project folder in the chosen local Codex surface.
- [ ] Confirm Git is initialised or ask Codex to inspect whether it is.
- [ ] Confirm the correct ChatGPT account is signed in.
- [ ] Keep permissions at a sensible default for a new repository.
- [ ] Paste the kickoff prompt from Section 17.
- [ ] Review the proposed plan before approving edits.
- [ ] Inspect the final diff.
- [ ] Run or confirm the checks.
- [ ] Make the first commit yourself after understanding the scaffold.

After Milestone 0:

- [ ] Update `docs/status.md`.
- [ ] Commit a clean checkpoint.
- [ ] Start Milestone 1 using Section 18.
- [ ] Keep reading, but do not delay the implementation sequence for unrelated papers.

---

## 22. Useful official Codex documentation

These links describe the current Codex workflow. Product availability and plan limits can change, so re-check them if this guide is used much later.

- Codex IDE: <https://learn.chatgpt.com/docs/codex/ide>
- Codex CLI: <https://learn.chatgpt.com/docs/codex/cli>
- Codex best practices: <https://learn.chatgpt.com/guides/best-practices>
- `AGENTS.md`: <https://learn.chatgpt.com/docs/agent-configuration/agents-md>
- Subagents: <https://learn.chatgpt.com/docs/agent-configuration/subagents>
- Git worktrees: <https://learn.chatgpt.com/docs/environments/git-worktrees>
- Authentication: <https://learn.chatgpt.com/docs/auth>
- Pricing and availability: <https://learn.chatgpt.com/docs/pricing>

## 23. Planning documents that informed this guide

- `Building a Chess Bot as a Stats ML and AI PhD Application Project`
- `Self-Study Chess Bot Project for a PhD Application`

The recommendations extracted from them are intentionally narrowed here into an actionable implementation workflow. The original reports remain valuable for the reading list, literature context, later experiments, datasets, and longer-term project alternatives.

