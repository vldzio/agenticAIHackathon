"""Train the fitness level classifier."""

from ml.train_model.common import train_classifier

# Only what the app collects from the user. Activity_Score is excluded on purpose:
# its ranges barely overlap between classes (it nearly encodes the label) and the
# app cannot measure it, so a model that leans on it scores well offline and
# poorly in the app. The *_Category columns are dropped because they are derived
# from Age, BMI and hours, which the model already sees.
FEATURE_COLUMNS = [
    "Age",
    "BMI",
    "Weight_KG",
    "Available_Hours_Per_Week",
    "Gender",
    "Fitness_Experience",
    "Fitness_Goal",
]
CATEGORICAL_FEATURES = ["Gender", "Fitness_Experience", "Fitness_Goal"]
TARGET_COLUMN = "Fitness_Level_Class"


def train_fitness_level_model(
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
