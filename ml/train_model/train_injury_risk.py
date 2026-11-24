"""Train the injury risk classifier."""

from ml.train_model.common import train_classifier

# Only what the app collects from the user. Flexibility_Score,
# Strength_Imbalance_Score and Overtraining_Risk_Score are measurements the app
# does not have; the old model was fed invented values for them at prediction time.
# Fitness_Level is left out too: the workflow runs this model in parallel with the
# fitness model, so its prediction is not available here (the old code always sent
# "Beginner"), and feeding a predicted level back in adds no accuracy.
FEATURE_COLUMNS = [
    "Age",
    "BMI",
    "Gender",
    "Fitness_Experience",
    "Has_Health_Conditions",
    "Previous_Injury",
    "Training_Frequency_Hours",
]
CATEGORICAL_FEATURES = ["Gender", "Fitness_Experience"]
TARGET_COLUMN = "Injury_Risk_Class"


def train_injury_risk_model(
    training_data_path: str,
    model_output_path: str,
    scaler_output_path: str,
    encoder_output_path: str,
) -> dict:
    return train_classifier(
        training_data_path,
        FEATURE_COLUMNS,
        CATEGORICAL_FEATURES,
        TARGET_COLUMN,
        model_output_path,
        scaler_output_path,
        encoder_output_path,
    )
