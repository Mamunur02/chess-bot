# Benchmark configuration format

The benchmark command evaluates caller-supplied chess positions under one
fixed search configuration:

```powershell
uv run chesslab-benchmark config.json result.json
```

The output path must not already exist. Use a reviewed, version-controlled
configuration for any result intended to support a research claim.

## Input

```json
{
  "name": "descriptive-run-name",
  "seed": 1234,
  "budget": {
    "kind": "nodes",
    "value": 10000
  },
  "agent": {
    "capture_ordering": false,
    "transposition_table": false,
    "quiescence_depth": 0
  },
  "positions": [
    {
      "name": "unique-case-name",
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "expected_moves": []
    }
  ]
}
```

Budget kinds are `depth`, `nodes`, and `milliseconds`. Positive integers
are required. Fixed-node budgets are preferred for cross-machine comparisons;
wall-clock budgets are sensitive to hardware and system load.

Every position requires a unique name and a valid six-field FEN. The optional
`expected_moves` array contains legal UCI moves accepted as correct for that
position. Choosing and validating those answers is a research-data decision;
the harness does not infer them.

Agent switches default to the values shown. Change one switch at a time for a
simple ablation unless a reviewed experiment design says otherwise.

## Output

The result JSON contains:

- the normalized input specification;
- a SHA-256 digest of that specification;
- UTC start time;
- Git commit and dirty state, or a captured Git error;
- Python and operating-system information;
- deterministic derived seed for each position;
- selected move, value, nodes, depths, principal variation, cutoffs,
  transposition hits, quiescence nodes, and timings;
- structured per-position failures;
- exact aggregate counts.

An accepted-move match is reported only when `expected_moves` is non-empty.
It is not an engine-strength measure by itself. The harness does not calculate
Elo, confidence intervals, or statistical significance.

## Data discipline

Do not tune search settings repeatedly against the final benchmark positions.
Keep tuning, validation, and held-out test positions separate once a substantive
dataset is selected. Record the source and version of that dataset in the
experiment manifest; this basic format does not invent those fields or values.

The repository currently includes only synthetic test fixtures used to verify
the harness. It does not include a substantive benchmark dataset or measured
research result.
