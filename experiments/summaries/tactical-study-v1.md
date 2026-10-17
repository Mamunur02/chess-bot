# First held-out tactical study, 2026-10-17

Completed and audited: 7,200 searches on 200 positions, four single-feature
variants, 1,000/5,000/20,000 visited nodes and three timing passes. 62.4 million
visited nodes; no failed/missing search cases; no repeated decision/statistic
disagreements. First-pass quality has sample size 200, not 600.

At the prespecified 5,000-node primary budget:

| Variant | Accepted / 200 | Change versus plain | Descriptive paired 95% interval | Median paired runtime ratio |
| --- | ---: | ---: | --- | ---: |
| Plain | 127 | reference | — | 1.00x |
| Capture ordering | 137 | +5.0 pp | [0.0, +10.0] pp | 2.24x |
| Transposition table | 128 | +0.5 pp | [0.0, +1.5] pp | 1.23x |
| Quiescence depth 1 | 134 | +3.5 pp | [-1.5, +8.5] pp | 4.53x |

These are source first-move agreement measurements on tactics-selected puzzles,
not full puzzle solving, general strength or Elo. Marginal bootstrap intervals
are descriptive, without multiple-comparison significance claims. The tiny
cache effect has only one discordant primary-budget case. Equal nodes do not
mean equal wall time. No positive population improvement or novelty is asserted.

Windows progress-file failures interrupted the first pass. All saved searches
were retained; a tested logging-only amendment resumed the original engine
snapshot. Interruption/setup effects remain timing limitations. No paid compute
or GPU was used. The completed test split must not become tuning data for an
unbiased future claim.

The full interpretation, failure examples, figures, independent audit and
reproduction/provenance pointers are in:

- `reports/tactical-study-v1/research-memo.md`
- `reports/tactical-study-v1/report.md`
- `reports/tactical-study-v1/analysis.json`
- `reports/tactical-study-v1/audit.json`
- `reports/tactical-study-v1/quality-cost.png` (also SVG/PDF)
- `docs/research/tactical-evaluation-protocol.md`
- `docs/research/tactical-logging-amendment-20261017.md`

Raw data and source snapshots remain ignored under `artifacts/tactical-test-v1/`;
the small source/split manifest is `experiments/manifests/lichess-tactics-v1.json`.
Git base: `2b591700d28c69b94e00ab877bd9308623781bf7`; working tree dirty,
with copied source and explicit operational/analysis provenance. No commit was
requested or made. Next decision: deepen implementation efficiency on development
positions, or broaden external move-quality assessment before a further study.
