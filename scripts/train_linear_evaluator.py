"""Train in an isolated NumPy environment; assess a frozen model separately.

The train command never opens test.json. Inference and assessment need only the
standard library. Checkpoints/data stay in ignored artifacts, not the repository.
"""

import argparse
import hashlib
import json
import math
import os
import platform
from datetime import UTC, datetime
from pathlib import Path

FEATURES = 385
SCHEMA = "signed-piece-square-tempo-v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def load_split(directory, split):
    metadata = json.loads((directory / "metadata.json").read_text())
    if metadata["status"] != "completed":
        raise ValueError("training/assessment requires a completed label run")
    path = directory / f"{split}.json"
    if digest(path) != metadata["split_sha256"][split]:
        raise ValueError("split SHA-256 mismatch")
    rows = json.loads(path.read_text())
    if not rows:
        raise ValueError("empty labelled split")
    for row in rows:
        if row["split"] != split or row["error"] is not None:
            raise ValueError("invalid row split/status")
        if len(row["features"]) != FEATURES or any(
            type(x) not in (int, float) or not math.isfinite(x) for x in row["features"]
        ):
            raise ValueError("invalid feature vector")
        if type(row["target_cp"]) is not int or type(row["material_cp"]) is not int:
            raise ValueError("integer targets and material required")
    return rows


def load_plan(directory):
    plan = json.loads((directory / "plan.json").read_text())
    metadata = json.loads((directory / "metadata.json").read_text())
    actual = hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if actual != metadata["manifest_digest"]:
        raise ValueError("dataset plan differs from its frozen digest")
    return plan


def check_disjoint(left, right):
    for key in ("group", "identity"):
        if {r[key] for r in left} & {r[key] for r in right}:
            raise ValueError(f"{key} overlap between data splits")


def predict(row, weights, clip):
    value = row["material_cp"] + sum(
        a * b for a, b in zip(row["features"], weights, strict=True)
    )
    return round(max(-clip, min(clip, value)))


def metrics(rows, weights, clip):
    errors = [predict(row, weights, clip) - row["target_cp"] for row in rows]
    return {
        "positions": len(rows),
        "source_groups": len({r["group"] for r in rows}),
        "rmse_cp": math.sqrt(sum(e * e for e in errors) / len(errors)),
        "mae_cp": sum(abs(e) for e in errors) / len(errors),
    }


def fit_numpy(rows, regularization):
    import numpy as np

    x = np.array([r["features"] for r in rows], dtype=np.float64)
    y = np.array([r["target_cp"] - r["material_cp"] for r in rows], dtype=np.float64)
    weights = np.linalg.solve(
        x.T @ x / len(rows) + regularization * np.eye(FEATURES), x.T @ y / len(rows)
    )
    if not np.all(np.isfinite(weights)):
        raise ValueError("nonfinite fitted weights")
    return weights.tolist()


def select_model(train, validation, lambdas, clip, fitter=fit_numpy):
    """Select solely on validation RMSE; ties prefer greater regularization."""
    check_disjoint(train, validation)
    candidates = []
    weights_by_lambda = {}
    for regularization in lambdas:
        weights = fitter(train, regularization)
        weights_by_lambda[regularization] = weights
        candidates.append(
            {
                "lambda": regularization,
                "train": metrics(train, weights, clip),
                "validation": metrics(validation, weights, clip),
            }
        )
    chosen = min(candidates, key=lambda c: (c["validation"]["rmse_cp"], -c["lambda"]))
    return weights_by_lambda[chosen["lambda"]], chosen, candidates


def train(directory, output):
    import numpy as np

    plan = load_plan(directory)
    if plan["feature_schema"] != SCHEMA:
        raise ValueError("unsupported feature schema")
    rows = load_split(directory, "train")
    validation = load_split(directory, "validation")
    weights, selected, candidates = select_model(
        rows, validation, plan["lambdas"], plan["clip_cp"]
    )
    output.mkdir(parents=True, exist_ok=False)
    model = {
        "schema_version": 1,
        "feature_schema": SCHEMA,
        "coefficients": weights,
        "clip_cp": plan["clip_cp"],
        "prior": "material-v1",
        "perspective": "white",
    }
    write_new(output / "model.json", model)
    record = {
        "selected": selected,
        "candidates": candidates,
        "model_sha256": digest(output / "model.json"),
        "dataset_metadata_sha256": digest(directory / "metadata.json"),
        "dataset_plan_sha256": digest(directory / "plan.json"),
        "train_sha256": digest(directory / "train.json"),
        "validation_sha256": digest(directory / "validation.json"),
        "script_sha256": digest(Path(__file__)),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "thread_env": {
            key: os.environ.get(key)
            for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
        },
        "trained_at": datetime.now(UTC).isoformat(),
        "selection": "validation RMSE only; no refit; test split unopened",
        "train_material": metrics(rows, [0.0] * FEATURES, plan["clip_cp"]),
        "validation_material": metrics(validation, [0.0] * FEATURES, plan["clip_cp"]),
    }
    write_new(output / "selection.json", record)
    (output / "train-script.py").write_bytes(Path(__file__).read_bytes())


def assess(directory, model_directory, output):
    record = json.loads((model_directory / "selection.json").read_text())
    if digest(model_directory / "model.json") != record["model_sha256"]:
        raise ValueError("selected model SHA-256 mismatch")
    if digest(directory / "metadata.json") != record["dataset_metadata_sha256"]:
        raise ValueError("dataset differs from selection")
    # Check split disjointness without using test outcomes for model selection.
    test = load_split(directory, "test")
    check_disjoint(test, load_split(directory, "train"))
    check_disjoint(test, load_split(directory, "validation"))
    model = json.loads((model_directory / "model.json").read_text())
    result = {
        "assessed_at": datetime.now(UTC).isoformat(),
        "model_sha256": record["model_sha256"],
        "selection_sha256": digest(model_directory / "selection.json"),
        "test_sha256": digest(directory / "test.json"),
        "learned": metrics(test, model["coefficients"], model["clip_cp"]),
        "material": metrics(test, [0.0] * FEATURES, model["clip_cp"]),
        "interpretation": "Clipped teacher-label fidelity, not playing strength.",
        "script_sha256": digest(Path(__file__)),
    }
    write_new(output, result)


def self_test():
    rows = [
        {"features": [1.0] + [0.0] * (FEATURES - 1), "target_cp": 2, "material_cp": 0}
        for _ in range(2)
    ]
    weights = fit_numpy(rows, 1.0)
    assert abs(weights[0] - 1.0) < 1e-12
    assert all(abs(w) < 1e-12 for w in weights[1:])
    print("NumPy ridge analytic self-test passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    training = sub.add_parser("train")
    training.add_argument("data", type=Path)
    training.add_argument("output", type=Path)
    assessment = sub.add_parser("assess")
    assessment.add_argument("data", type=Path)
    assessment.add_argument("model", type=Path)
    assessment.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "train":
        train(args.data, args.output)
    elif args.command == "assess":
        assess(args.data, args.model, args.output)
    else:
        self_test()


if __name__ == "__main__":
    main()
