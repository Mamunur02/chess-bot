# Baseline experiment manifests

The classical engine and single-run benchmark tool are implemented. The
manifest runner adds a shared-input grid, incremental artifacts, and paired
descriptive summaries. It uses the existing benchmark runner and adds no
dependencies or statistical strength claims.

Run the versioned development example from the repository root:

```powershell
uv run python -m chesslab.experiment experiments/manifests/development-ablation.json artifacts/development-ablation-001
```

The output directory must be new. A repeat needs a different output path.
Exit codes are 0 for completed runs, 1 for recorded case failures, 2 for invalid
configuration or filesystem errors, and 130 for keyboard interruption.

## Manifest

The example is the complete schema. Version 1 requires:

- `schema_version`: integer 1.
- `name` and `question`: explicit non-empty descriptions.
- `dataset`: `id`, `version`, `source`, `split`, and ordered `positions`.
  Split is `development`, `validation`, or `test`. Position and accepted-move
  semantics match [the benchmark format](benchmark-format.md).
- `budget`: one positive depth, node, or millisecond budget shared by variants.
- `seeds`: distinct integer root seeds, in execution order.
- `variants`: at least two unique named agent configurations. The first is
  the reference for paired deltas. Supported agents and switches match the
  benchmark format. Unknown fields are errors rather than ignored typos.

Every variant runs every seed on the same ordered positions. Per-position
derived RNG seeds consequently match between variants. The normalized
manifest, including source, split, version, accepted moves, and all agent
switches, is hashed with SHA-256. Duplicate FENs differing only in name or
fullmove number are rejected to avoid inadvertent double weighting.

These checks do not validate source quality or enforce independence across
different manifests. Dataset labels describe caller intent; they do not prove
that data is held out. FEN inputs lack repetition history. Greedy ignores the
supplied budget and is a behavioural comparator, not equal-compute search.

## Artifacts

Each fresh output directory contains:

```text
manifest.json       normalized configuration and dataset snapshot
metadata.json       run ID, status, provenance, versions, lock hash, errors
runs/0000.json      first raw benchmark result
runs/0001.json      next raw benchmark result, etc.
summary.json        aggregate counts and pairs against the first variant
```

Raw runs are written immediately after completion, using numeric filenames so
variant names cannot create paths. Metadata records Git commit/dirty state,
UTC start time, Python, operating system, CPU identifiers, installed package
versions, and the repository `uv.lock` hash (or a captured read error).
Every raw result includes its configuration digest, seeds, decisions, search
statistics, timings, and failures. Artifacts are ignored by Git.

A failed position remains in the attempted scored-case denominator and has
no accepted-move match. It is never counted as a draw. Successful paired cases
report variant-minus-reference node, completed-depth, time, and accepted-match
deltas, plus
changed actions. Failed or missing pairs are explicitly unavailable. Repeated
seeds do not increase the count of independent positions. Current material
agents are deterministic under depth/node budgets; repetitions verify
repeatability and provide timing observations, not independent strength data.

Keyboard interruption or a runner exception preserves previously written raw
runs, a partial summary, and status `interrupted` or `failed`. An abrupt process
kill or power loss can leave status `running`; do not treat that as completion.
Storage failure can also prevent finalization. No incomplete run is resumed or
overwritten automatically.

## Boundary before research

The example uses six synthetic development fixtures already used in tests.
Only the two existing reviewed accepted-move labels are carried over. It
verifies the comparison workflow; its counts are not tactical-suite accuracy,
Elo, or evidence that an optimization improves playing strength.

Before substantive research, select a source with usable licensing and reliable
answers, pin its version/checksum, document preparation, and freeze disjoint
tuning/validation/test positions. Review near-duplicate positions and game
overlap, define the primary metric and stopping rule, and choose an uncertainty
analysis appropriate to the actual independent units. Do not tune on the test
split. Source selection and research-direction choice remain deliberate data
and methodology decisions.
