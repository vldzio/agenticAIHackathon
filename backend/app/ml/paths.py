from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
TRAIN_DIR = DATA_DIR / "training_dataset"
EVAL_DIR = DATA_DIR / "evaluation_dataset"
PROCESSED_DIR = DATA_DIR / "processed"  # generated; git-ignored
ARTIFACT_DIR = BACKEND_DIR / "artifacts"
METADATA_FILE = ARTIFACT_DIR / "metadata.json"

DATASET_FILES = {
    "fitness_level": ("fitness_level_training.csv", "fitness_level_evaluation.csv"),
    "injury_risk": ("injury_risk_training.csv", "injury_risk_evaluation.csv"),
}
