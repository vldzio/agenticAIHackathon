"""Evaluate trained ML models on the held-out evaluation datasets.

Both targets are ordered classes, so besides plain accuracy the report includes
ordinal metrics (within-one-class accuracy, quadratic weighted kappa), a
majority-class baseline, a bootstrap confidence interval and calibration.
"""

from datetime import datetime, timezone
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    log_loss,
)

# Lowest to highest. Confusion matrices and per-class tables use this order.
CLASS_ORDER = {
    "Fitness_Level_Class": ["Beginner", "Intermediate", "Advanced", "Athlete"],
    "Injury_Risk_Class": ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"],
}


def _load_artifacts(model_path: str, scaler_path: str, encoder_path: str):
    with open(model_path, "rb") as model_file:
        model = pickle.load(model_file)
    if hasattr(model, "n_jobs"):
        model.n_jobs = 1
    with open(scaler_path, "rb") as scaler_file:
        scaler = pickle.load(scaler_file)
    with open(encoder_path, "rb") as encoder_file:
        encoder_data = pickle.load(encoder_file)
    return model, scaler, encoder_data


def _expected_calibration_error(confidence: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    which = np.clip(np.digitize(confidence, edges[1:-1]), 0, bins - 1)
    ece = 0.0
    for b in range(bins):
        mask = which == b
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - confidence[mask].mean())
    return float(ece)


def compute_metrics(y_true, proba: np.ndarray, proba_classes, order, n_bootstrap: int = 1000) -> dict:
    """Metrics for an ordered multi-class target.

    y_true: true class names. proba: (n, k) probabilities whose columns follow
    proba_classes. order: class names from lowest to highest.
    """
    order = list(order)
    rank = {name: i for i, name in enumerate(order)}
    columns = [list(proba_classes).index(name) for name in order]
    proba = np.asarray(proba)[:, columns]
    y = np.array([rank[name] for name in y_true])
    pred = proba.argmax(axis=1)
    correct = (pred == y).astype(float)

    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(y), size=(n_bootstrap, len(y)))
    low, high = np.percentile(correct[idx].mean(axis=1), [2.5, 97.5])

    labels = list(range(len(order)))
    report = classification_report(y, pred, labels=labels, target_names=order, output_dict=True, zero_division=0)
    counts = np.bincount(y, minlength=len(order))

    return {
        "eval_accuracy": float(accuracy_score(y, pred)),
        "accuracy_ci95": [float(low), float(high)],
        "majority_baseline_accuracy": float(counts.max() / len(y)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro", labels=labels, zero_division=0)),
        "weighted_f1": float(f1_score(y, pred, average="weighted", labels=labels, zero_division=0)),
        "within_one_class_accuracy": float(np.mean(np.abs(pred - y) <= 1)),
        "quadratic_weighted_kappa": float(cohen_kappa_score(y, pred, weights="quadratic", labels=labels)),
        "log_loss": float(log_loss(y, proba, labels=labels)),
        "expected_calibration_error": _expected_calibration_error(proba.max(axis=1), correct),
        "mean_confidence": float(proba.max(axis=1).mean()),
        "total_samples": int(len(y)),
        "classes": order,
        "class_counts": {name: int(counts[i]) for i, name in enumerate(order)},
        "predicted_counts": {name: int(n) for name, n in zip(order, np.bincount(pred, minlength=len(order)))},
        "precision_per_class": {name: report[name]["precision"] for name in order},
        "recall_per_class": {name: report[name]["recall"] for name in order},
        "f1_per_class": {name: report[name]["f1-score"] for name in order},
        "support_per_class": {name: report[name]["support"] for name in order},
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y, pred, labels=labels).tolist(),
    }


def _evaluate(eval_data_path: str, target_column: str, model_path: str, scaler_path: str, encoder_path: str) -> dict:
    df = pd.read_csv(eval_data_path)
    model, scaler, encoder_data = _load_artifacts(model_path, scaler_path, encoder_path)

    x = df[encoder_data["feature_columns"]].copy()
    for col, encoder in encoder_data["feature_encoders"].items():
        x[col] = encoder.transform(x[col])

    proba = model.predict_proba(scaler.transform(x.to_numpy(dtype=float)))
    proba_classes = encoder_data["target_encoder"].inverse_transform(model.classes_)
    result = compute_metrics(df[target_column], proba, proba_classes, CLASS_ORDER[target_column])
    result["feature_columns"] = list(encoder_data["feature_columns"])
    return result


def evaluate_fitness_level_model(eval_data_path: str, model_path: str, scaler_path: str, encoder_path: str) -> dict:
    result = _evaluate(eval_data_path, "Fitness_Level_Class", model_path, scaler_path, encoder_path)
    result["model"] = "fitness_level"
    return result


def evaluate_injury_risk_model(eval_data_path: str, model_path: str, scaler_path: str, encoder_path: str) -> dict:
    result = _evaluate(eval_data_path, "Injury_Risk_Class", model_path, scaler_path, encoder_path)
    result["model"] = "injury_risk"
    return result


def evaluate_all_models(project_root: str = None) -> dict:
    root = Path(project_root) if project_root else Path.cwd()
    eval_dir = root / "data" / "evaluation_dataset"
    models_dir = root / "ml" / "models"
    results = {"timestamp": datetime.now(timezone.utc).isoformat()}

    try:
        results["fitness_evaluation"] = evaluate_fitness_level_model(
            str(eval_dir / "fitness_level_evaluation.csv"),
            str(models_dir / "fitness_level_model.pkl"),
            str(models_dir / "fitness_level_scaler.pkl"),
            str(models_dir / "fitness_level_encoder.pkl"),
        )
    except Exception as exc:
        results["fitness_evaluation"] = {"error": str(exc)}

    try:
        results["injury_evaluation"] = evaluate_injury_risk_model(
            str(eval_dir / "injury_risk_evaluation.csv"),
            str(models_dir / "injury_risk_model.pkl"),
            str(models_dir / "injury_risk_scaler.pkl"),
            str(models_dir / "injury_risk_encoder.pkl"),
        )
    except Exception as exc:
        results["injury_evaluation"] = {"error": str(exc)}

    return results
