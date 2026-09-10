# ADR 0012: Fixed-budget benchmark harness

## Status

Accepted.

## Context

Search features can be enabled independently, but controlled comparisons need
a common runner that records raw measurements and enough execution context to
audit a result. Selecting a real benchmark dataset, accepted moves, and primary
research metric requires user input and should not be smuggled into an
infrastructure milestone.

## Decision

Add a JSON-configured benchmark command over caller-supplied named FEN
positions. One run uses one explicit material-agent configuration and one
depth, node, or millisecond budget for every position. Each position is
evaluated once with a deterministic seed derived from the recorded root seed.

Optional accepted UCI moves permit a simple correctness count. They are
validated as legal at configuration construction. The harness never generates
or asserts accepted answers.

The normalized specification is serialized with sorted keys and compact
separators, then hashed with SHA-256. Provenance captured before execution
contains:

- the specification digest;
- UTC start time;
- Git commit and dirty state;
- a structured Git error when repository metadata cannot be captured;
- Python version;
- operating-system platform;
- machine and processor strings.

The runner rejects provenance whose digest does not match the supplied
specification. Each case records its FEN, derived seed, status, elapsed time,
full search decision and statistics, optional accepted-move match, and error.
Exceptions are recorded as failed cases rather than draws or missing rows.

The summary contains exact counts only: positions, completed cases, failures,
cases with accepted answers, accepted-move matches, total visited nodes, and
run elapsed time. Raw cases remain available for later reviewed statistical
analysis.

The command refuses to overwrite an existing output file. It does not commit a
substantive configuration or benchmark dataset.

## Consequences

- Baseline switches can be compared through the same execution and result
  schema.
- Configuration identity, Git state, system context, seeds, and failures are
  preserved with every generated result.
- Fixed-node runs support the cleanest current compute-controlled comparison.
- Timing remains observational and machine-dependent.
- Accepted-move accuracy depends entirely on the quality and independence of
  caller-supplied answers.

The harness currently runs one configuration once. It does not manage
train/tuning/test splits, repeat grids, paired comparison summaries,
uncertainty intervals, external-engine adjudication, Elo, artifact catalogs,
or dataset versions. Those belong to reviewed experiment manifests and
analysis after the research question and data are chosen.

## Validation

Tests use synthetic chess fixtures only. They cover exact raw and aggregate
serialization, deterministic seeds and digests, structured failures,
configuration validation, illegal accepted moves, duplicate names, provenance
fallback, digest mismatch, command-line JSON execution, and output overwrite
protection. No test result is presented as a research measurement.
