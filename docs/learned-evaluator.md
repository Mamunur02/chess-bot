# Train and run our linear evaluator

The first supervised bot is implemented. It learns a piece-square/tempo correction
to material and uses the same plain alpha-beta search. Read the
[frozen pilot and amendment](research/linear-evaluator-pilot-v1.md) and
[measured report](../experiments/summaries/linear-evaluator-pilot-v1.md).

## Reproduction

Use the already pinned local Stockfish executable and prepared puzzle splits
referenced in the manifest. Exclusion files are hash-checked and read for position
identity only. The dataset generator never reads old puzzle solution labels as
targets. All output paths must be fresh:

```powershell
uv run python -m chesslab.learning experiments/manifests/linear-evaluator-pilot-v1.json artifacts/linear-data-new
```

Generation freezes source trajectories, identities/splits and source snapshots
before labels. The teacher receives full trajectory history; learned features
encode the board and turn only. Labels are incremental, with no automatic retries.
An invocation cap or failed label prevents training. Grouped splits and exclusion
rules reduce leakage; they do not make artificial rollouts representative of
human or strong-engine games.

Training needs NumPy in an isolated environment. The completed run reused the
existing ignored `artifacts/plot-env/` with NumPy 2.5.4. No production dependency
or lockfile was changed. For that existing environment:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
artifacts/plot-env/Scripts/python.exe scripts/train_linear_evaluator.py self-test
artifacts/plot-env/Scripts/python.exe scripts/train_linear_evaluator.py train artifacts/linear-data-new artifacts/linear-model-new
uv run python scripts/train_linear_evaluator.py assess artifacts/linear-data-new artifacts/linear-model-new artifacts/linear-model-new/test-assessment.json
```

The trainer never opens `test.json`. It selects lambda on validation RMSE, saves
the checkpoint and selection record, and does not refit. Assessment requires that
frozen model/data identity and reads test labels separately. Predictions are
clipped and rounded to integer cp; validation selection uses the same convention.
No test outcome authorizes another hyperparameter search on that test set.
Default tests require neither NumPy nor an external engine. The NumPy analytic
ridge self-test is a separate optional training-environment check.

Models are JSON, not pickle: schema, dimensions, finite coefficients, score
perspective, material prior and clipping are validated. Hash the actual model
file before configuring it. The native agent configuration is:

```json
{"kind":"linear_alpha_beta","path":"artifacts/linear-evaluator-model-v1/model.json","sha256":"93adbed58f5b19e4835d37526cb7218b51a707c60286e2635944afa3b1475b3e"}
```

This kind works in match and tactical manifests. It has plain search switches
fixed to match the material control. Model loading/pin validation belongs to
setup; inference is inside the decision timer. Match startup failures preserve
active-game identity and coverage, while tactical setup failures are per-case
records. Terminal mate/draw utility always precedes model evaluation.

## Serve the learned bot over UCI

```powershell
uv run chesslab-uci --model artifacts/linear-evaluator-model-v1/model.json --model-sha256 93adbed58f5b19e4835d37526cb7218b51a707c60286e2635944afa3b1475b3e
```

Without these flags the existing material engine remains the default. The flags
must be paired; missing/corrupt weights fail before the UCI session starts.
`uv run python -m chesslab.uci` supports the same arguments. This remains the
existing minimal synchronous UCI server, with its existing time-control limits.

## Audit and artifacts

`scripts/audit_linear_pilot.py` recomputes split/label metrics, production features,
model pins, source snapshots, exclusions, and tactical/match outcomes. The pilot
invocation is recorded in the compact summary. Raw data, model checkpoints,
original training script, teacher diagnostics and search/game logs remain under
ignored `artifacts/linear-*` paths. Only recipes, source, manifests and compact
results are committed. Reproducing labels requires the local pinned teacher;
model inference does not require that teacher, NumPy or internet access.
