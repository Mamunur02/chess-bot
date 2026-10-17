# Tactical baseline study v1

Analysis status: **validated**. Split: test.

200 independent retained puzzle groups; 3 timing passes on the same positions. Quality uses only the first pass. Timing repeats do not increase sample size.

## Measured quality and runtime

Agreement is with frozen accepted first moves, not full-puzzle solving.

| Nodes | Variant | Correct / planned | Failed / missing | Median case seconds | Complete timing positions |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1,000 | plain | 121 / 200 | 0 / 0 | 0.064585 | 200 |
| 1,000 | capture-ordering | 128 / 200 | 0 / 0 | 0.131138 | 200 |
| 1,000 | transposition-table | 121 / 200 | 0 / 0 | 0.080510 | 200 |
| 1,000 | quiescence-1 | 126 / 200 | 0 / 0 | 0.276101 | 200 |
| 5,000 | plain | 127 / 200 | 0 / 0 | 0.325113 | 200 |
| 5,000 | capture-ordering | 137 / 200 | 0 / 0 | 0.713081 | 200 |
| 5,000 | transposition-table | 128 / 200 | 0 / 0 | 0.405258 | 200 |
| 5,000 | quiescence-1 | 134 / 200 | 0 / 0 | 1.457959 | 200 |
| 20,000 | plain | 137 / 200 | 0 / 0 | 1.315362 | 200 |
| 20,000 | capture-ordering | 145 / 200 | 0 / 0 | 3.084331 | 200 |
| 20,000 | transposition-table | 136 / 200 | 0 / 0 | 1.742603 | 200 |
| 20,000 | quiescence-1 | 142 / 200 | 0 / 0 | 5.906082 | 200 |

Median time is the median across positions of each position's median over its complete successful timing passes.

## Primary comparisons at 5,000 nodes

| Variant minus plain | Delta pp | Descriptive 95% interval pp | Complete pairs | Candidate-only / plain-only successes | Runtime ratio |
| --- | ---: | --- | ---: | ---: | ---: |
| capture-ordering | +5.00 | [+0.00, +10.00] | 200 | 18 / 8 | 2.238x |
| transposition-table | +0.50 | [+0.00, +1.50] | 200 | 1 / 0 | 1.230x |
| quiescence-1 | +3.50 | [-1.50, +8.50] | 200 | 16 / 9 | 4.529x |

Descriptive marginal complete-pair intervals; no significance or family-wise coverage claim.
Intervals use 10,000 shared paired bootstrap resamples (seed 20261018). Few discordant cases can yield discrete/degenerate intervals. Missing-outcome bounds, coverage and all budgets are in analysis.json.

## Integrity and limitations

Repeated-search disagreements: 0.
A nonzero count requires investigation before interpreting aggregates.
Source positions are tactics-selected Lichess puzzles, not ordinary chess positions. Labels are fallible, full earlier repetition history is absent, and this small single-snapshot sample limits generalization. The material evaluator is fixed. No Elo, novelty or general-strength claim.
Equal node budgets do not imply equal runtime; nominal completed depths are not equivalent tactical horizons across quiescence variants. Timings are machine-specific. Session notes record setup overlap and power/load conditions.

## Failure examples

analysis.json retains the first eight source-order primary-budget cases where any variant missed, with frozen labels, FEN, source row and decisions. These are illustrative selections, not a representative failure taxonomy.

## Provenance

Run ID: tactical-test-v1. Git state and runtime versions: see run metadata and copied source/protocol hashes.
The artifact plan, raw per-case files and source snapshots identify the executed code even when the working tree is dirty. analysis-provenance.json records the separate analysis/plot scripts.

## Next research decision

Review the paired quality/runtime trade-offs and failure examples before choosing another algorithm, evaluator or dataset. Do not tune on these test positions and then reuse them as an unbiased benchmark.

## Execution recovery

Windows progress-file access interrupted execution; Original recovery preserved code/protocol and cases; later logging amendments are recorded separately. Retain this interruption as a timing limitation. Original failure/session details are preserved in analysis.json.

## Disclosed logging amendment

A Windows atomic-write retry fix was applied to logging only. Search ran from the original copied source tree; the original plan and checkpoints were retained. Both writer hashes and the exact amendment/launcher sources are recorded. Interrupted timing passes remain a limitation; no cases were selectively discarded.
