"""Evaluate trained ML models on evaluation datasets."""

from datetime import datetime, timezone
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


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


def _evaluate(eval_data_path: str, target_column: str, model_path: str, scaler_path: str, encoder_path: str) -> dict:
    df = pd.read_csv(eval_data_path)
    model, scaler, encoder_data = _load_artifacts(model_path, scaler_path, encoder_path)

    x = df[encoder_data["feature_columns"]].copy()
    y = df[target_column].copy()

    for col, encoder in encoder_data["feature_encoders"].items():
        x[col] = encoder.transform(x[col])

    y_encoded = encoder_data["target_encoder"].transform(y)
    y_pred = model.predict(scaler.transform(x))
    report = classification_report(y_encoded, y_pred, target_names=encoder_data["target_encoder"].classes_, output_dict=True)
    cm = confusion_matrix(y_encoded, y_pred)
    classes = list(encoder_data["target_encoder"].classes_)

    return {
        "eval_accuracy": accuracy_score(y_encoded, y_pred),
        "total_samples": len(df),
        "classes": classes,
        "class_counts": dict(zip(classes, np.bincount(y_encoded))),
        "precision_per_class": {cls: report[cls]["precision"] for cls in classes},
        "recall_per_class": {cls: report[cls]["recall"] for cls in classes},
        "f1_per_class": {cls: report[cls]["f1-score"] for cls in classes},
        "support_per_class": {cls: report[cls]["support"] for cls in classes},
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }


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
