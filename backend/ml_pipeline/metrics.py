"""Metric computation shared by training and the live evaluation endpoint."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
)

from app.ml.features import ModelSpec


def expected_calibration_error(proba: np.ndarray, y_idx: np.ndarray, bins: int = 10) -> float:
    conf = proba.max(axis=1)
    correct = (proba.argmax(axis=1) == y_idx).astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (conf > lo) & (conf <= hi)
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
    return float(ece)


def compute_metrics(model: Any, df: pd.DataFrame, spec: ModelSpec) -> dict[str, Any]:
    x = df[spec.features]
    y = df[spec.target].to_numpy()
    classes = list(model.classes_)
    order = spec.classes
    proba = model.predict_proba(x)
    # Re-order probability columns into the canonical (ordinal) class order.
    proba = proba[:, [classes.index(c) for c in order]]
    y_idx = np.array([order.index(v) for v in y])
    pred_idx = proba.argmax(axis=1)
    pred = np.array(order)[pred_idx]

    report = classification_report(y, pred, labels=order, output_dict=True, zero_division=0)
    return {
        "samples": len(df),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, labels=order, average="macro", zero_division=0)),
        "within_one_class_accuracy": float(np.mean(np.abs(pred_idx - y_idx) <= 1)),
        "log_loss": float(log_loss(y_idx, proba, labels=list(range(len(order))))),
        "expected_calibration_error": expected_calibration_error(proba, y_idx),
        "classes": order,
        "precision_per_class": {c: float(report[c]["precision"]) for c in order},
        "recall_per_class": {c: float(report[c]["recall"]) for c in order},
        "f1_per_class": {c: float(report[c]["f1-score"]) for c in order},
        "support_per_class": {c: int(report[c]["support"]) for c in order},
        "confusion_matrix": confusion_matrix(y, pred, labels=order).tolist(),
    }
