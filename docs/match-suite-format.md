# Head-to-head match suites

The match-suite command wraps the existing deterministic match runner in a
reproducible two-agent comparison. It supports seeded random, material-greedy,
and material alpha-beta agents. It does not select a research dataset or infer
playing strength from synthetic examples.

```powershell
uv run python -m chesslab.match_suite experiments/manifests/development-matches.json artifacts/development-matches-001
```

Use a fresh output directory for every invocation. The development example
uses two mate-in-one positions, two seeds, and both agent colour assignments,
producing eight games. It tests outcome bookkeeping rather than strength.

## Inputs and pairing

The checked-in JSON manifest is the complete version 1 schema:

- `name` and `question` describe the run.
- `dataset` specifies its identity, version, source, split, and named FEN
  positions. Splits are `development`, `validation`, or `test`; these labels
  describe intent and cannot establish independence across datasets.
- `agents` contains exactly two uniquely named configurations. Kind is
  `random`, `material_greedy`, or `material_alpha_beta`. Random accepts only its
  kind; greedy rejects search switches; alpha-beta supports the same switches
  as [the benchmark tool](benchmark-format.md).
- `seeds` is a non-empty list of distinct integer root seeds.
- `budget` is a shared per-move depth, node, or millisecond budget.
- `max_plies` is a positive game-length limit. It is not adjudication.

Unknown fields and duplicate starting positions are rejected. Starting positions
must be valid and non-terminal. An input FEN has no repetition history. Games
retain history after starting and use the existing automatic-draw policy:
claimable draws are not automatically taken; fivefold repetition and the
seventy-five-move rule are automatic.

For each root seed, derive one match seed per position in dataset order. Play
that position twice, swapping the two agents between White and Black without
changing the FEN. Each pair shares its match seed; independent player RNGs are
assigned by colour by the existing match runner. Streams are not attached to
agent identity, and pair members are not independent observations. Agents are
freshly built for each game. Black-to-move positions still map agents by piece
colour, not by which agent acts first.

Random and greedy accept but ignore the search budget. They are behavioural
comparators, not examples of equal-compute alpha-beta search. Time limits are
machine/load dependent; use fixed nodes for controlled search comparisons.

## Artifacts and metrics

Each run stores a normalized `manifest.json`, shared `metadata.json`, incremental
`games/0000.json` records, and `summary.json`. Metadata uses the same provenance,
installed package versions, dependency lock hash, and configuration digest as
[the ablation runner](experiment-format.md). `active_game` identifies a game in
progress when execution aborts. Raw games store pairing, initial FEN, agent
colour assignment, root/derived/player seeds, legal UCI move records, terminal
returns, and failure information.

Only completed games contribute wins, draws, and losses. Per-agent score fraction
is `(wins + draws / 2) / completed_games`, or null when none complete. The summary
separately reports failed, interrupted, unrecorded games, completed pairs, and
pairs lacking two completed games. An agent error is not a forfeit; a ply limit
is not a draw. Mixed outcomes therefore remain visible instead of silently
changing the denominator or creating results.

Completed-only scores may be biased if missing games or incomplete colour pairs
are systematic. Review the raw failures before interpreting results. The runner
does not infer Elo, confidence intervals, or significance. Choosing sampling
units, opening distributions, adjudication, and the primary metric belongs to
the substantive evaluation protocol.

Metadata status is `failed` if any game fails; otherwise `interrupted` if any
game hits its ply limit; otherwise `completed`. Execution exceptions and keyboard
interruption preserve previously returned game records and a partial summary.
Moves from the currently executing game are not saved on keyboard interruption.
A hard process kill or storage failure may prevent finalization and leave status
`running`. Existing artifacts are never resumed or overwritten automatically.

Exit codes: 0 for all completed games, 1 for game failures/ply limits, 2 for invalid
input or filesystem errors, and 130 for keyboard interruption.
