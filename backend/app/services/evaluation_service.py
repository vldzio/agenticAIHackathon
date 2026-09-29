from __future__ import annotations

import threading
from typing import Any

import pandas as pd

from app.ml import paths
from app.ml.features import SPECS
from app.ml.registry import get_registry
from ml_pipeline.cleaning import clean_dataset
from ml_pipeline.metrics import compute_metrics

_cache: dict[str, Any] = {}
_lock = threading.Lock()


def model_info() -> dict[str, Any]:
    meta = get_registry().metadata
    models = {}
    for name, m in meta["models"].items():
        models[name] = {
            "classes": m["classes"],
            "features": m["features"],
            "training_ranges": m["training_ranges"],
            "global_feature_importance": m["global_feature_importance"],
            "cross_validation": m["cross_validation"],
            "training_evaluation": m["evaluation"],
            "data": {k: v for k, v in m["data"].items() if not k.endswith("sha256")},
            "artifact_bytes": m["artifact_bytes"],
        }
    return {
        "trained_at": meta["trained_at"],
        "environment": meta["environment"],
        "models": models,
        "guardrails": [
            "Predicted fitness level is capped by the level implied by your stated training history.",
            "Predictions for inputs outside the training ranges are flagged as extrapolations.",
            "Safety rules (not the ML models) decide when medical clearance is recommended.",
        ],
        "limitations": [
            "The training data appears synthetic and is not clinically validated.",
            "Cross-validation on the training file is noticeably higher than accuracy on the separate "
            "evaluation file for injury risk, which indicates the two files are not identically distributed.",
            "The injury model only sees observable inputs (age, BMI, sex, experience, conditions, previous injury, weekly hours).",
        ],
    }


def evaluate(force: bool = False) -> dict[str, Any]:
    """Live evaluation on the bundled evaluation CSVs (cached; falls back to stored metrics)."""
    with _lock:
        if _cache and not force:
            return _cache
        registry = get_registry()
        result: dict[str, Any] = {"source": "live", "models": {}}
        for name, spec in SPECS.items():
            eval_file = paths.EVAL_DIR / paths.DATASET_FILES[name][1]
            if eval_file.exists():
                df, _ = clean_dataset(pd.read_csv(eval_file), spec)
                result["models"][name] = compute_metrics(registry.get(name).pipeline, df, spec)
            else:
                result["source"] = "stored"
                result["models"][name] = registry.metadata["models"][name]["evaluation"]
        _cache.clear()
        _cache.update(result)
        return _cache
