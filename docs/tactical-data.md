# Tactical data preparation and pilot

The first source is the [CC0 Lichess puzzle export](https://database.lichess.org/#puzzles).
It is mutable: retain the exact source bytes or a content-identical archive,
download headers, retrieval date and SHA-256. Generated data and raw runs belong
under ignored `data/` and `artifacts/`, not in Git. The checked-in data manifest
identifies the first snapshot; no large dataset or engine binary is committed.

## Prepare

Download `https://database.lichess.org/lichess_db_puzzle.csv.zst` to
`data/lichess/lichess_db_puzzle.csv.zst` and retain HTTP response headers. The
2026-10-17 download was 307,234,795 bytes compressed; the CSV is larger. Standard
Zstandard tools may decompress it. Alternatively Node 24+ can run the included
PZstandard adapter without a new Python dependency:

```powershell
node scripts/decompress-puzzles.mjs data/lichess/lichess_db_puzzle.csv.zst data/lichess/lichess_db_puzzle.csv
uv run python -m chesslab.puzzles data/lichess/lichess_db_puzzle.csv data/lichess/prepared-v1
```

Both tools protect existing outputs. The Node adapter specifically supports
PZstandard metadata/data frame pairs used by this snapshot, not every possible
Zstandard stream. The adapter removes a newly created partial output on failure.
Its optional offline integration check is:

```powershell
node --test scripts/decompress-puzzles.test.mjs
```

Preparation uses only the project's existing Python dependencies. It scans all
CSV rows with a seeded 1,200-row reservoir, validates each sampled full solution
line using `python-chess`, and reconstructs the solver position after the setup
move. It accepts all legal immediate mates and rejects inconsistent mate labels.
It groups connected source-game, normalized-position and puzzle-ID duplicates,
retains one representative per component, then shuffles into disjoint 50/50/200
development/validation/test splits. The output retains original rows, normalized
positions, accepted moves, split hashes, rejection reasons and provenance.

Sampling is uniform over source rows before filtering and component reduction,
not uniform over all valid or all independent puzzles. No rating filter is used.
The resulting tactical distribution is not representative of ordinary gameplay.

## Development pilot

```powershell
uv run python scripts/run_tactical_pilot.py data/lichess/prepared-v1 artifacts/tactical-pilot-new --positions 10 --max-seconds 600
```

This checks the first ten development positions at three node budgets through
the existing experiment runner, with warmup, raw artifacts and failure records.
Its fixed variant ordering and single timing pass are suitable for capacity
planning, not a formal speed claim. Validation and test splits are never loaded
by this pilot. The cap is checked between budget grids; one grid may overrun it.

## Counterbalanced runs

The new runner supports per-case persistence, rotation of variant order,
alternating budget order, explicit split selection and timing repeats:

```powershell
uv run python -m chesslab.tactical data/lichess/prepared-v1 artifacts/tactical-validation-new --split validation --budgets 1000 --repeats 1 --max-seconds 180
```

After finalizing the protocol and arranging a quiet run window, the proposed
three-pass held-out command is:

```powershell
uv run python -m chesslab.tactical data/lichess/prepared-v1 artifacts/tactical-test-v1 --split test --budgets 1000 5000 20000 --repeats 3 --max-seconds 18000 --protocol docs/research/tactical-evaluation-protocol.md
```

The user subsequently authorized three passes and an immediate quiet window.
The actual run uses `data/lichess/prepared-v1-verified`, a 14,400-second cap, and
the frozen protocol. Repeats are timing measurements on the same
200 positions, not 600 independent quality observations. A runtime cap is a
checkpoint boundary between searches, not a hard per-search deadline. Add
`--resume` with the same data, code, protocol and experiment settings to
continue a capped/interrupted run. Recorded failures are retained rather than
automatically retried. Existing outputs require explicit resume.

The artifact directory contains plan/protocol hashes, source snapshots, positions,
versions and lock hash, Git state, per-case JSON, and current status/active case.
No source-code change can be resumed into the same experiment directory.

## Active full study and automatic analysis

On 2026-10-17 at 13:51 UTC (14:51 Europe/London), the hidden local study process
started after a development warmup. `scripts/run_tactical_study.py` runs the
three-pass study, retains stdout/stderr and session notes under `artifacts/`,
and temporarily inhibits Windows sleep without changing the power plan. The
runner invocation is capped at four hours between searches; a capped or failed
run preserves checkpoints and requires attention rather than silently changing
the experiment.

Current run status is in `artifacts/tactical-test-v1/metadata.json`;
session status is in `artifacts/tactical-test-v1-session.json` and additional
hardware/setup notes in `artifacts/tactical-test-v1-run-notes.json`. Each completed
case appears under `artifacts/tactical-test-v1/cases/`. Avoid changing frozen
`src/`, `pyproject.toml`, `uv.lock` or the protocol while it runs.

The initial run stopped at 15:11 BST after 891 saved searches when Windows
denied replacement of `metadata.json`. Verified checkpoints were resumed at
15:16 BST by `scripts/resume_tactical_study.py`. The recovery wrapper preserves
the initial failure/session records in `recovery-v1/`, retries only progress-file
WinError 5 failures (at most eight), and retains the original 18:51 BST deadline.
It does not alter frozen search code, protocol or recorded decisions. A failed
recorded search is never automatically rerun. This interruption and recovery
must accompany the timing findings.

On successful completion, `scripts/analyse_tactical.py` checks run identities,
source snapshots, legal recorded decisions, labels, budgets and repeated-search
consistency. It writes first-pass quality, paired bootstrap summaries, repeated
median timings, failure examples and a generated memo to
`reports/tactical-study-v1/`. The analysis refuses unfinished runs and flags
repeat disagreements. Reproduction after a completed run, using a fresh output:

```powershell
uv run python scripts/analyse_tactical.py artifacts/tactical-test-v1 --output reports/tactical-study-reanalysis
```

Figures use Matplotlib 3.10.8 in a separate ignored environment at
`artifacts/plot-env/`. This is an analysis tool, not a project/agent dependency;
the frozen project lockfile and installed engine environment are unchanged.
The figure script writes PNG, SVG and PDF plus the plotting package versions.
Analysis/plot sources are copied and hashed in the report directory. Recreate
the optional isolated plotting environment with:

```powershell
uv venv artifacts/plot-env --python .venv/Scripts/python.exe
uv pip install --python artifacts/plot-env/Scripts/python.exe matplotlib==3.10.8
```

Development of analysis scripts, one plotting-tool installation and verification
checks briefly overlapped early first-pass timings. The run notes record that
interval. No trials are discarded for it; per-position three-pass medians reduce
transient timing effects but do not eliminate that limitation.

## Windows sandbox execution used in this session

The default uv cache and pytest temporary directory were not writable in the
sandbox. A workspace cache, explicit existing interpreter and fresh workspace
pytest base directory worked without changing system configuration:

```powershell
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-new
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src tests
```

Use a fresh pytest base directory: pytest manages and may clean its contents.
`--no-sync` uses the already installed environment. A subsequent
`uv --cache-dir artifacts/uv-cache sync --locked --offline --python .venv/Scripts/python.exe`
confirmed that all 18 installed packages match the lock without downloads.
Installed versions are also recorded in run artifacts. The regular `uv run`
commands remain the normal workflow where interpreter/cache permissions work.
