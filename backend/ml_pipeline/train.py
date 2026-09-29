"""Reproducible training CLI.

    python -m ml_pipeline.train            # clean -> train -> cross-validate -> evaluate -> write artifacts
    python -m ml_pipeline.train --seed 7 --min-accuracy 0.6

Outputs (``backend/artifacts``): ``fitness_level.joblib``, ``injury_risk.joblib``, ``metadata.json``.
``metadata.json`` records library versions, data hashes, feature lists, training ranges, metrics and the
artifact SHA-256, which the API verifies at load time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.ml import paths
from app.ml.features import SPECS, ModelSpec
from ml_pipeline.cleaning import clean_dataset
from ml_pipeline.metrics import compute_metrics


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_pipeline(spec: ModelSpec, seed: int) -> Pipeline:
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), spec.categorical)],
        remainder="passthrough",
        verbose_feature_names_out=False,
    ).set_output(transform="pandas")
    forest = RandomForestClassifier(
        n_estimators=60,
        max_depth=12,
        min_samples_leaf=8,
        class_weight="balanced",
        n_jobs=-1,
        random_state=seed,
    )
    # Sigmoid calibration so the reported "confidence" is closer to a real probability.
    calibrated = CalibratedClassifierCV(forest, method="sigmoid", cv=3)
    return Pipeline([("pre", pre), ("clf", calibrated)])


def global_importance(model: Pipeline, spec: ModelSpec) -> dict[str, float]:
    """Mean impurity importance of the calibrated forests, summed back onto the original features."""
    names = list(model.named_steps["pre"].get_feature_names_out())
    calibrated = model.named_steps["clf"].calibrated_classifiers_
    importances = np.mean([c.estimator.feature_importances_ for c in calibrated], axis=0)
    out = dict.fromkeys(spec.features, 0.0)
    for name, value in zip(names, importances, strict=True):
        owner = next((f for f in spec.categorical if name.startswith(f + "_")), name)
        out[owner] += float(value)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def _load(spec: ModelSpec, train: bool) -> pd.DataFrame:
    train_file, eval_file = paths.DATASET_FILES[spec.name]
    return pd.read_csv((paths.TRAIN_DIR if train else paths.EVAL_DIR) / (train_file if train else eval_file))


def train_one(spec: ModelSpec, seed: int, cv_folds: int = 5) -> tuple[Pipeline, dict[str, Any]]:
    raw_train = _load(spec, train=True)
    train_df, train_report = clean_dataset(raw_train, spec)
    paths.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(paths.PROCESSED_DIR / f"{spec.name}_training_cleaned.csv", index=False)

    raw_eval = _load(spec, train=False)
    eval_df, eval_report = clean_dataset(raw_eval, spec, dedupe=True)

    print(f"[{spec.name}] cleaning report (train): {train_report}")
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    cv_scores = cross_val_score(
        build_pipeline(spec, seed), train_df[spec.features], train_df[spec.target], cv=cv, scoring="accuracy"
    )
    print(f"[{spec.name}] {cv_folds}-fold CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    model = build_pipeline(spec, seed)
    model.fit(train_df[spec.features], train_df[spec.target])
    metrics = compute_metrics(model, eval_df, spec)
    print(f"[{spec.name}] held-out eval accuracy: {metrics['accuracy']:.4f}, macro-F1 {metrics['macro_f1']:.4f}")

    ranges = {col: {"min": float(train_df[col].min()), "max": float(train_df[col].max())} for col in spec.numeric}
    baseline: dict[str, Any] = {col: float(train_df[col].median()) for col in spec.numeric}
    baseline.update({col: str(train_df[col].mode().iloc[0]) for col in spec.categorical})
    meta = {
        "name": spec.name,
        "target": spec.target,
        "classes": spec.classes,
        "features": {"numeric": spec.numeric, "categorical": spec.categorical},
        "training_ranges": ranges,
        "baseline": baseline,
        "global_feature_importance": global_importance(model, spec),
        "data": {
            "training_file": paths.DATASET_FILES[spec.name][0],
            "training_sha256": sha256_file(paths.TRAIN_DIR / paths.DATASET_FILES[spec.name][0]),
            "evaluation_file": paths.DATASET_FILES[spec.name][1],
            "evaluation_sha256": sha256_file(paths.EVAL_DIR / paths.DATASET_FILES[spec.name][1]),
            "cleaning_report_training": train_report,
            "cleaning_report_evaluation": eval_report,
            "provenance": "Bundled CSVs of unknown origin whose statistics indicate a synthetic generator; "
            "not clinically validated.",
        },
        "cross_validation": {
            "folds": cv_folds,
            "accuracy_mean": float(cv_scores.mean()),
            "accuracy_std": float(cv_scores.std()),
        },
        "evaluation": metrics,
    }
    return model, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument("--min-accuracy", type=float, default=0.0, help="fail (exit 1) if held-out accuracy is lower")
    parser.add_argument("--out", type=Path, default=paths.ARTIFACT_DIR)
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": args.seed,
        "environment": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        "models": {},
    }
    ok = True
    for spec in SPECS.values():
        model, meta = train_one(spec, args.seed, args.cv_folds)
        artifact = args.out / f"{spec.name}.joblib"
        joblib.dump(model, artifact, compress=3)
        meta["artifact"] = artifact.name
        meta["artifact_sha256"] = sha256_file(artifact)
        meta["artifact_bytes"] = artifact.stat().st_size
        metadata["models"][spec.name] = meta
        if meta["evaluation"]["accuracy"] < args.min_accuracy:
            print(f"FAIL: {spec.name} accuracy below {args.min_accuracy}", file=sys.stderr)
            ok = False

    (args.out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote artifacts to {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
