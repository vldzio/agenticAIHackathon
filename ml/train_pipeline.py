"""Master orchestrator for ML training pipeline."""

import sys
from pathlib import Path

# Add project root to sys.path to ensure imports work in all scenarios
# (script execution, module import, and pytest)
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try relative imports first (when imported as module), fall back to absolute
try:
    from .data_cleaning.clean_fitness_data import clean_fitness_data
    from .data_cleaning.clean_injury_data import clean_injury_data
    from .train_model.train_fitness_level import train_fitness_level_model
    from .train_model.train_injury_risk import train_injury_risk_model
    from .evaluation.evaluate_models import evaluate_fitness_level_model, evaluate_injury_risk_model
except ImportError:
    # Fall back to absolute imports when run as a script
    from ml.data_cleaning.clean_fitness_data import clean_fitness_data
    from ml.data_cleaning.clean_injury_data import clean_injury_data
    from ml.train_model.train_fitness_level import train_fitness_level_model
    from ml.train_model.train_injury_risk import train_injury_risk_model
    from ml.evaluation.evaluate_models import evaluate_fitness_level_model, evaluate_injury_risk_model


def run_training_pipeline(project_root: str = None) -> dict:
    try:
        if project_root is None:
            project_root = Path.cwd()
        else:
            project_root = Path(project_root)

        data_dir = project_root / "data"
        training_dir = data_dir / "training_dataset"
        processed_dir = data_dir / "processed"
        eval_dir = data_dir

        models_dir = project_root / "ml" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)

        fitness_train_raw = training_dir / "fitness_level_training.csv"
        injury_train_raw = training_dir / "injury_risk_training.csv"

        fitness_train_clean = processed_dir / "fitness_level_training_cleaned.csv"
        injury_train_clean = processed_dir / "injury_risk_training_cleaned.csv"

        fitness_eval = eval_dir / "fitness_level_evaluation.csv"
        injury_eval = eval_dir / "injury_risk_evaluation.csv"

        fitness_model = models_dir / "fitness_level_model.pkl"
        fitness_scaler = models_dir / "fitness_level_scaler.pkl"
        fitness_encoder = models_dir / "fitness_level_encoder.pkl"

        injury_model = models_dir / "injury_risk_model.pkl"
        injury_scaler = models_dir / "injury_risk_scaler.pkl"
        injury_encoder = models_dir / "injury_risk_encoder.pkl"

        clean_fitness_data(str(fitness_train_raw), str(fitness_train_clean))
        clean_injury_data(str(injury_train_raw), str(injury_train_clean))

        fitness_training = train_fitness_level_model(
            str(fitness_train_clean),
            str(fitness_model),
            str(fitness_scaler),
            str(fitness_encoder),
        )

        injury_training = train_injury_risk_model(
            str(injury_train_clean),
            str(injury_model),
            str(injury_scaler),
            str(injury_encoder),
        )

        fitness_evaluation = evaluate_fitness_level_model(
            str(fitness_eval),
            str(fitness_model),
            str(fitness_scaler),
            str(fitness_encoder),

        )

        injury_evaluation = evaluate_injury_risk_model(
            str(injury_eval),
            str(injury_model),
            str(injury_scaler),
            str(injury_encoder),
        )

        return {
            "pipeline_status": "success",
            "fitness_training" : fitness_training,
            "injury_training" : injury_training,
            "fitness_evaluation" : fitness_evaluation,
            "injury_evaluation" : injury_evaluation,
        }
    except Exception as e:
        return {
            "pipeline_status": "failed",
            "error":str(e),
        }


if __name__ == "__main__":
    # Run from AetherFit root directory
    project_root = str(Path(__file__).parent.parent)
    results = run_training_pipeline(project_root)
    sys.exit(0 if results['pipeline_status'] == 'success' else 1)
