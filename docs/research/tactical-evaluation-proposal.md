# Proposed first tactical evaluation

Date: 2026-10-17. Original planning proposal; the user subsequently authorized
continued work. Lichess preparation and development/validation preflights are
now complete. See `tactical-evaluation-protocol.md` and
`../../experiments/summaries/tactical-pilot-20261017.md` for the current protocol
and measured preflight evidence. No reference engine has been adopted and no
held-out result is claimed. Numbers below are planning targets unless stated.

## Agreed purpose and limits

The user selected tactical move quality and search efficiency, with a target of
approximately one week (2026-10-24). Aim to finish one reproducible classical
baseline study and short report within that period, not the entire long-term
research programme. Use local CPU compute first. Free Colab is optional; the
existing Python search has no GPU implementation. Up to GBP 50 is potentially
available only after careful experimental checks; do not purchase compute from
this statement alone. No training, new algorithm family, or model is required.

Proposed question: under fixed visited-node budgets, how do capture ordering,
transposition caching, and bounded quiescence change first-move tactical solution
agreement, and what runtime costs accompany those changes?

This is a controlled baseline investigation, with no novelty claim.

## What is being optimised and measured

Keep three definitions separate:

1. Terminal game utility is currently win +1, draw 0, loss -1, from an explicitly
   named player's perspective. Search maps these to its fixed terminal scores.
2. The nonterminal search heuristic is currently material balance. Keep its
   piece values fixed across variants. A larger internal score is not evidence
   of a better move. This study has no reinforcement-learning reward to train.
3. External move-quality measurement uses held-out labels. Proposed primary
   outcome: agreement with the accepted first solution move at a prespecified
   node budget. Call it first-move solution agreement, not complete puzzle
   solving, general chess accuracy, or playing strength.

Do not mix these in one weighted quality/speed score. Plot solution agreement
against node budget and against measured runtime. A low or null result is useful.

## Source options reviewed

| Candidate | Benefits | Limitations and proposed role |
| --- | --- | --- |
| Lichess puzzle export | CC0; source-game links, solution moves, ratings and tactical themes | Tactics-selected, engine-generated labels; not representative of all chess. Recommended first source. |
| Lichess evaluation export | CC0; scored variations and recorded depth/node counts | Source evaluations use heterogeneous analysis budgets; listed variations need not cover our agent's move. More preparation and reference-analysis work. Defer. |
| Existing synthetic repository fixtures | Small, deterministic, already available | Used in development; retain for smoke checks only, never as the held-out research benchmark. |

Sources checked on 2026-10-17:
[Lichess export documentation](https://database.lichess.org/#puzzles) and its
[evaluation format](https://database.lichess.org/#evals).
The live export is mutable: record retrieval time, source URL, file SHA-256,
schema, preparation version and exact selected IDs. Check download size and
decompression options before transfer; a small sample does not imply a small
upstream download. Do not introduce a production dependency without asking.

Important puzzle semantics from the source: apply the first UCI move to the
supplied FEN; the second listed move is the solver's first move. Validate the
entire supplied line for legality. For mate in one, accept every legal immediate
checkmate rather than only the listed move. Record rejected rows and reasons.
Lichess describes other solution moves as unique, but labels remain fallible.
Freeze label rules; do not relabel test cases opportunistically after failures.

## Proposed preparation and split

- Begin with 20-30 development positions for legality, label and runtime checks.
  These positions must never enter the final test split.
- Planning targets, subject to runtime measured on development data: 50
  development, 50 validation and 200 held-out test positions. These counts are
  a scope proposal, not a statistical power calculation or precision guarantee.
- Fix eligibility rules, sampling seed and rating-band/theme treatment before
  selecting the final test set. Human puzzle rating is a descriptive difficulty
  variable, not a compute requirement or quality label for our agent.
- Group by source game, strip URL perspective/ply suffixes when extracting game
  IDs, and deduplicate equivalent post-setup positions across all splits. Join
  duplicate-position and same-game groups before split assignment to prevent
  leakage. Record all sampling exclusions and the population actually sampled;
  do not describe a file prefix or convenience subset as database-wide random.
- Preserve original FEN, setup move, resulting FEN, source ID, metadata and
  accepted moves. FEN omits earlier repetition history: evaluation concerns
  reconstructed positions, not the complete historical game.
- Reserve validation for protocol checks and explicitly recorded choices. Lock
  the protocol before opening test outcomes. Do not replace test positions
  because the engine performs poorly on them.

## Proposed comparisons and analysis

Use the existing four single-factor configurations: plain alpha-beta,
capture-ordering only, transposition-table only, and quiescence-depth-one only.
All use iterative deepening and the same material evaluator. Avoid a broad
hyperparameter sweep or an unplanned combined variant this week.

Provisional node grid: 1,000, 5,000 and 20,000 per move; provisional primary
budget: 5,000. Confirm or revise these on development runtime evidence, record
the final primary budget, then freeze before test evaluation. Run every variant
on the same positions. Count all visited nodes, including incomplete iterations
and quiescence, according to the existing contract. Quiescence nodes are a
subset of total nodes; do not add them again. Completed nominal depths are
diagnostic and are not equivalent tactical horizons across quiescence variants.

Report first-move agreement and paired percentage-point changes against plain
search. Proposed uncertainty: paired bootstrap intervals, resampling source-game
groups and retaining all variants/budgets together. Prespecify bootstrap seed,
replicates and interval method. Treat the three primary-budget feature contrasts
as one family; use simultaneous intervals or explicitly descriptive marginal
intervals with no significance claims. Other budgets and theme breakdowns are
exploratory. Include all planned cases in denominators; a failed run is not a
successful answer. Report failures separately and give complete-pair coverage
and sensitivity to missing pairs rather than silently dropping them.

Record actual nodes, wall time, completed depth, fallback frequency, cache hits,
cutoffs and quiescence work. Nodes have different costs across variants. Use
warm-up runs and balanced run ordering; if feasible, repeat timings three times
and summarize per-position medians. Keep the machine/power mode consistent.
Deterministic agents do not gain independent quality observations from extra
random seeds; the source positions provide the comparison units. Repeated
timings are runtime checks, not extra sample size. A grid's first successful
budget is not proof of a minimum required budget or monotonic performance.

## Optional reference engine

Dataset solution agreement is sufficient for the first study. Stockfish is a
candidate secondary reference if alternative good moves or label disagreement
require investigation, not an adopted dependency or agent replacement.
[Official downloads](https://stockfishchess.org/download/) provide CPU binaries;
[python-chess analysis](https://python-chess.readthedocs.io/en/latest/engine.html)
supports restricted root moves, explicit budgets and score perspectives.

If used, freeze version, binary/network hashes, options, Threads, Hash, analysis
budget and cache-reset policy. Compare reference and candidate moves using the
same original player's perspective, with matched analysis procedures. Keep
mate results separate from finite centipawn differences. Centipawn scores are
not literal win probabilities, and any WDL conversion has a specified model
and calibration limits. Finite-budget reference disagreement is uncertainty,
not mathematical proof the source label is wrong. An engine-judged quality
metric needs its own frozen protocol before held-out use; keep it out of the
critical path for this week.

## Work sequence and compute checks

1. Days 1-2: settle source/metric choices, implement the smallest preparation
   slice with tests for setup ply, both colours, illegal lines, multiple mates,
   duplicate groups and deterministic splits; run the development pilot.
2. Day 3: inspect failures, check evaluator/perspective/node accounting, measure
   actual per-position runtime, estimate full run cost and freeze the protocol.
3. Days 4-5: execute the frozen comparisons with incremental artifacts and
   completion checks. Preserve failed/interrupted runs.
4. Days 6-7: paired analysis, quality-cost plots, failure examples and a short
   report explaining uncertainty, limitations and reproduction commands.

Before a full run, estimate search runtime from measured development costs per
variant and budget, multiplied by planned cases/repetitions, with explicit
headroom. Include download, preparation and any reference-analysis costs
separately. Set a pilot-derived runtime cap and resume strategy. If the work
does not fit, reduce scope on development evidence before inspecting test
results. Use no paid compute by default. A GPU allocation does not accelerate
the existing CPU search without a different implementation.

Finish means a frozen data manifest and protocol, tested preparation/analysis,
raw runs with provenance and failures, comparison plots/tables, and an honest
report. It does not require a positive result. Next smallest task: prepare and
validate a development-only sample and measure local runtime once the proposed
source and protocol are settled.
