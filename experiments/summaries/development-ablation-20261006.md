# Development ablation: 6 October 2026

## Purpose and scope

Verify manifest execution, equal node limits, incremental artifacts, and paired
summaries for the existing material alpha-beta baseline. This is a workflow
measurement on development fixtures, not a held-out research experiment.
No feature or evaluator was tuned using this run.

## Reproduction and provenance

```powershell
uv run python -m chesslab.experiment experiments/manifests/development-ablation.json artifacts/development-ablation-20261006-002
```

Use a fresh output directory when reproducing. The manifest embeds all six
positions, source, accepted moves, switches, node budget, and seeds. Dataset:
`chesslab-synthetic-development`, version `1`, split `development`.
Manifest SHA-256:
`2e0c61e4ec7e6627061813144e000357b47a79a960138896bde4fa8438aecd12`.

Measured with CPython 3.12.14 on Windows 11, AMD64,
`Intel64 Family 6 Model 165 Stepping 2, GenuineIntel`; `chess-ai-lab` 0.1.0,
`python-chess` 1.999, and `chess` 1.11.2. Git HEAD:
`a6269ba496476a9b12087c616b678da0250da6d4`, working tree dirty. The new runner
was uncommitted; that commit alone does not reproduce it. Review and retain
the milestone 14 changes alongside this memo. Dependency lock SHA-256:
`569ca4796c7aebfc828e83f29a7ad76cd1b29242f7599d2dc0aeae3875db749e`.

Raw results remain local under the ignored artifact directory. Its metadata
records the timestamp, versions, Git state, lock hash, and status. Files
`runs/0000.json` through `runs/0007.json` are ordered by variant, then seed.
An earlier run under suffix `001` tested the preliminary summary schema; this
memo refers only to the final run under suffix `002`.

## Measurements

Each variant used seeds 17 and 23 and the same six ordered positions. Each
search visited exactly 1,000 nodes. All 48 evaluations completed without
failures. Decisions and search statistics matched across the two seeds within
each variant. All four variants matched both accepted-move labels on both
repetitions. The other four positions have no accepted-move labels.

| Variant | Evaluations | Total nodes | Completed depth range | Quiescence nodes | Cache hits | Cutoffs |
|---|---:|---:|---:|---:|---:|---:|
| Plain | 12 | 12,000 | 3–4 | 0 | 0 | 1,806 |
| Capture ordering only | 12 | 12,000 | 3–5 | 0 | 0 | 2,682 |
| Transposition table only | 12 | 12,000 | 3–4 | 0 | 0 | 1,806 |
| Quiescence depth 1 only | 12 | 12,000 | 2–4 | 10,032 | 0 | 7,566 |

Across the 12 paired evaluations per variant, capture ordering changed two
actions and had a summed completed-depth delta of +6 relative to plain.
Caching changed no actions and had depth delta 0. Quiescence changed no actions
and had depth delta -2. All paired node deltas were zero, as expected for fully
used fixed node budgets. Raw elapsed times are retained but no speed ranking
or timing inference is drawn from this small sequential run.

## Conclusions and limitations

The observed run demonstrates that the comparison workflow executes and
records the intended configurations. It does not establish a playing-strength
benefit for any variant. Depth numbers alone are not comparable measures of
decision quality, especially when quiescence changes the work beyond the
ordinary search horizon. Cutoffs include search work and are not a quality
metric.

These fixtures have already informed correctness tests. There are only six
unique positions, only two accepted-move labels, and no independent held-out
sample. Repeated seeds for deterministic agents are not independent chess
evidence. No transposition hits occurred, so caching effectiveness cannot be
assessed here. Timing is host/load dependent, and the working tree was dirty.

The next task is to review and pin a substantive benchmark source, freeze
independent splits, and specify the primary metric and stopping rule. The
research-direction decision can then use an explicit evaluation design rather
than these development counts as evidence of strength.
