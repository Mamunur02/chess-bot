# ADR 0015: Colour-paired match suites

## Status

Accepted.

## Decision

Close the gap between the existing match library and reproducible head-to-head
evaluation by adding a strict JSON-configured two-agent suite. Reuse the existing
agents, game rules, budgets, RNG handling, and match failure semantics. For each
position and seed, play both agent colour assignments on the same FEN and derived
match seed. Do not alter the generic game or agent protocols.

Persist raw games incrementally and report completed-game wins/draws/losses,
score fractions, game statuses, and pair coverage. Count neither a ply limit as
a draw nor an agent failure as a forfeit. Validate raw pairing and inputs against
the manifest before summarizing. Record an active-game identity on execution
abort. Share configuration validation and artifact/provenance helpers with the
existing ablation command; preserve its output format and configuration digests.

The example suite contains synthetic near-mate development fixtures, not a
chosen opening corpus. No external engine, dataset, model, dependency, or
statistical method is introduced.

## Consequences and limits

Colour mapping remains correct for Black-to-move initial positions. Random
execution is reproducible under recorded seeds; greedy and random remain
behavioural rather than equal-compute comparators. Completed-only score fractions
are descriptive and may be biased by incomplete pairs. Pair members and repeated
deterministic seeds cannot be counted as independent strength evidence.

The next substantive step requires agreement on evaluation priority before
selecting a tactical corpus, opening corpus, reference engine, or model.

## Validation

Tests exercise both winning colours, automatic draws, non-draw ply limits,
colour swaps, seed mapping, random repeatability, manifest identity, strict input
validation, duplicate/mismatched raw games, partial pair interruption, failure
denominators, CLI execution, and artifact overwrite protection.
