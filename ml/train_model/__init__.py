"""Model training functions for ML pipeline."""

from ml.train_model.train_fitness_level import train_fitness_level_model
from ml.train_model.train_injury_risk import train_injury_risk_model

__all__ = [
    "train_fitness_level_model",
    "train_injury_risk_model",
]
