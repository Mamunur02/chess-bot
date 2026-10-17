# Tactical evaluation protocol v1

Prepared and frozen 2026-10-17 before held-out execution. The user selected
three timing passes and explicitly confirmed the computer is available now.
Dataset selection is frozen by the recorded hashes. Changes after execution
begins require a separate protocol/version and must not overwrite this run.

## Question and scope

How do capture ordering, transposition caching and bounded quiescence affect
first-move tactical solution agreement at fixed visited-node budgets, and how
much wall time does each configuration consume? This is a classical baseline
study, with material evaluation fixed. No novelty or general-strength claim.

The score used inside search is not the external outcome metric. Terminal
utilities and material weights retain their existing tested conventions.

## Frozen data

Source: the full CC0 Lichess puzzle export retrieved 2026-10-17, not a prefix.
See `experiments/manifests/lichess-tactics-v1.json` for source and split hashes,
source row count, preparation version, seed and exact selection rules.
Preparation scans the whole CSV using a 1,200-row reservoir; validates full
legal solution lines; forms connected game/position/ID components; retains one
representative per component; shuffles; assigns 50 development, 50 validation,
200 test positions. No rating or engine-success filter was applied. Invalid
sampled rows and duplicate components would be reported, not replaced silently.
This two-stage selection is not a uniform sample of all valid Lichess puzzles.

Apply the source setup move before presenting the puzzle. Accept the listed
first solver move, except accept all legal immediate mates where any exists.
This measures first-move agreement, not full-line solving. Labels are fallible.
The sample is selected for tactics upstream; conclusions do not extend to all
chess positions. Earlier repetition history is unavailable from the source FEN.

Pilot and validation outcomes are development evidence. Do not use the test
split to tune settings, thresholds, labels, eligibility or reporting choices.

## Frozen comparison settings

- Variants: plain iterative-deepening alpha-beta, capture-ordering only,
  transposition-table only, quiescence-depth-one only. No combined variant.
- Node budgets: 1,000, 5,000, 20,000 per move. Primary budget: 5,000.
- Quality outcome: accepted first move, recorded as a binary success per puzzle.
  Use the first scheduled pass for primary quality. Subsequent passes are
  timing repeats and must agree on deterministic decisions/search statistics;
  discrepancies require investigation rather than selective aggregation.
- Three comparisons against plain at the primary budget; all must be reported.
  Other budgets and descriptive theme/rating results are exploratory.
- Node counts include all entered nodes, partial iterations and quiescence.
  Quiescence counts are already part of total nodes. Completed depth is a
  diagnostic, not an equivalent tactical horizon across variants.
- RNG seed: 20261017. Agents are deterministic; repeats do not increase the
  effective quality sample size beyond the 200 puzzles.

## Timing and execution

Use a single sequential process on the local computer. Alternate budget order
between positions/passes and rotate variant order; start a fresh agent for
each search. Thus transposition caches do not carry between puzzles or trials.
Run a development warmup in the same session before formal execution. Record
machine, power mode and competing load before starting; avoid unrelated heavy
work. Any interruption, restart, change of environment or temperature/power
concern belongs in the run notes. Hardware timings remain machine-specific.

Three passes are prespecified: first-pass quality plus per-position median
timings over three passes. The pilot extrapolates to roughly
56 minutes per full pass, before headroom; three passes roughly 2.8 hours.
These are estimates from ten development positions, not measured full-run costs.
Use resumable per-case artifacts and a 14,400-second invocation cap to respect
the approximately four-hour window. This cap is checked between searches, not
a hard per-search timeout. If capped, retain partial results and arrange any
additional run window rather than changing the planned comparisons.

## Analysis specified before test inspection

For every variant/budget report planned puzzles, completed/failed/missing
cases, first-pass successes out of all 200 planned positions, and complete-pair
coverage. Failures/missing cases cannot count as successful answers. Also show
complete-pair deltas and missing-outcome bounds so infrastructure failures are
not mistaken for chess mistakes. Never silently discard failures.

For paired solution-agreement changes, use a seeded paired percentile bootstrap
over source-game components (here one retained puzzle per component), preserving
all configurations/budgets for each sampled unit. Seed 20261018; 10,000
replicates; nominal 95% intervals using linear-interpolated 2.5th and 97.5th
percentiles. Report marginal intervals as descriptive, with no significance
claims or family-wise coverage claim for the three comparisons. With few
discordant cases, intervals can be discrete or degenerate; report discordant
counts and do not interpret a zero-width interval as certainty.

For repeated timings, use per-position medians across the prespecified passes,
then report distributions and paired runtime ratios on positions with all
timing passes successful. Give excluded counts. Also report first-pass runtime
coverage. Plot agreement versus nodes and versus wall time separately, without
a composite reward or speed/quality score. Report actual nodes, fallback
frequency, completed depth, cutoffs, cache hits and quiescence work as diagnostics.
Inspect quality failures with examples after aggregate results are fixed; do
not relabel or replace cases to improve the outcome.

No new reference engine or centipawn-loss metric is required for this study.
Any later engine-judged metric requires a separate protocol and reference-version
record. No paid compute is currently needed or authorized.

## Reproduction and artifacts

See `docs/tactical-data.md` for preparation and run commands. The runner requires
an explicit protocol file for test execution, records its hash and copies it
into the artifact directory. It also records the split hash, source snapshots,
configuration digests, Git state, lock hash, versions, environment, per-case
decisions, timings and failures. Resume requires unchanged code/data/settings.
The repository may be dirty because committing requires explicit user approval;
copied source and hashes identify the actual executed code.

Deliverables: reproducible data/protocol manifests, raw runs, comparison tables
and plots, paired uncertainty summaries, failure examples and a short report.
Positive results are not required. The subsequent user decision is which
research direction, if any, to investigate after this baseline study.
