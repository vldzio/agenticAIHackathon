"""Shared training routine for the two classifiers.

The reported training metrics come from stratified 5-fold cross-validation on
the training data (every row is scored by a model that never saw it); the saved
model is then fitted on all of the training data.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder, StandardScaler

from ml.evaluation.evaluate_models import CLASS_ORDER, compute_metrics

RANDOM_STATE = 42


def build_model() -> HistGradientBoostingClassifier:
    # Settings chosen by cross-validation on the training data only (not the evaluation set).
    return HistGradientBoostingClassifier(
        learning_rate=0.03,
        max_iter=600,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=RANDOM_STATE,
    )


def train_classifier(
    training_data_path: str,
    feature_columns: list,
    categorical_features: list,
    target_column: str,
    model_output_path: str,
    scaler_output_path: str,
    encoder_output_path: str,
) -> dict:
    df = pd.read_csv(training_data_path)

    x = df[feature_columns].copy()
    feature_encoders = {}
    for col in categorical_features:
        encoder = LabelEncoder()
        x[col] = encoder.fit_transform(x[col])
        feature_encoders[col] = encoder

    target_encoder = LabelEncoder()
    y = target_encoder.fit_transform(df[target_column])

    # Tree models do not need scaling; the scaler is kept so the saved artifacts
    # keep the same three-file layout the app and the evaluation code load.
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x.to_numpy(dtype=float))

    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_proba = cross_val_predict(build_model(), x_scaled, y, cv=folds, method="predict_proba")
    cv_metrics = compute_metrics(
        df[target_column], cv_proba, target_encoder.classes_, CLASS_ORDER[target_column]
    )

    model = build_model().fit(x_scaled, y)
    importance = permutation_importance(
        model, x_scaled, y, n_repeats=3, random_state=RANDOM_STATE, scoring="accuracy"
    )

    Path(model_output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(model_output_path, "wb") as f:
        pickle.dump(model, f)
    with open(scaler_output_path, "wb") as f:
        pickle.dump(scaler, f)
    with open(encoder_output_path, "wb") as f:
        pickle.dump(
            {
                "target_encoder": target_encoder,
                "feature_encoders": feature_encoders,
                "feature_columns": feature_columns,
            },
            f,
        )

    return {
        "model_accuracy": cv_metrics["eval_accuracy"],
        "validation": "stratified 5-fold cross-validation on the training data",
        "cv_metrics": cv_metrics,
        "total_samples": len(df),
        "classes": cv_metrics["classes"],
        "feature_importance": dict(zip(feature_columns, np.round(importance.importances_mean, 4).tolist())),
        "classification_report": cv_metrics["classification_report"],
        "confusion_matrix": cv_metrics["confusion_matrix"],
    }
