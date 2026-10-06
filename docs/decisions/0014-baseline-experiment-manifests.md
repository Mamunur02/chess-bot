# ADR 0014: Baseline experiment manifests and paired summaries

## Status

Accepted.

## Decision

Add a manifest-driven command over the existing fixed-budget benchmark runner.
One manifest specifies one versioned dataset snapshot, one budget, named
variants, and explicit seeds. Execute the full variant-by-seed grid and pair
cases against the first variant. Strict validation rejects unknown fields,
duplicate seeds/variants, and duplicate FEN inputs. No new production dependency
or search behavior is introduced.

Preserve raw results incrementally under a fresh artifact directory. Record
installed engine/rules versions and the dependency lock hash alongside existing
Git, runtime, and host provenance. Capture failed and interrupted runs; keep
missing/failed pairs visible and scored failures in attempted denominators.
Summaries describe measured counts/deltas only, without confidence intervals
that would incorrectly treat deterministic repetitions as independent positions.

The checked-in manifest is explicitly development-only and reuses correctness
fixtures. A substantive dataset and held-out evaluation are separate research
decisions. This closes the experiment-infrastructure gap without selecting a
research branch or inventing benchmark answers.

## Limitations

Split labels cannot enforce independence across manifests. Exact duplicate
checks do not detect related positions, transpositions, or shared source games.
FENs cannot encode repetition history. Hard termination and storage failures
may prevent final status updates. Dirty Git state requires retaining/reviewing
the implementation diff before attempting reproduction from a commit.

The existing synchronous UCI interface and material-only evaluator remain
appropriate baseline limitations; a strong tournament engine is not required
for this platform.

## Validation

Tests cover grid identity, paired seeds and deltas, round trips and digests,
strict validation, failures in denominators, artifact overwrite protection,
lock/version provenance, partial interruption/exception records, and CLI input.
The development ablation records actual observations without strength claims.
