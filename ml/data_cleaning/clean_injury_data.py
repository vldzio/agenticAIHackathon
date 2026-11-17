"""Data cleaning for injury risk training dataset."""

import pandas as pd
from pathlib import Path

VALID_VALUES = {
    "Gender": ["Male", "Female", "Other"],
    "Fitness_Level": ["Beginner", "Intermediate", "Advanced", "Athlete"],
    "Fitness_Experience": ["Never Exercised", "Beginner", "Some Experience", "Advanced"],
    "Injury_Risk_Class": ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"],
}
NUMERIC_COLS = [
    "Age",
    "BMI",
    "Flexibility_Score",
    "Strength_Imbalance_Score",
    "Training_Frequency_Hours",
    "Overtraining_Risk_Score",
    "Has_Health_Conditions",
    "Previous_Injury",
]


def clean_injury_data(input_path: str, output_path: str = None) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    df = df.drop_duplicates(subset=["User_ID"], keep="first")

    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Rows with a missing or unknown category or label cannot be repaired, so drop them.
    for col, valid in VALID_VALUES.items():
        df = df[df[col].isin(valid)]

    # The two yes/no flags are the strongest predictors; a missing flag is not
    # guessed (the old median fill turned every gap into "no"), the row is dropped.
    for col in ["Has_Health_Conditions", "Previous_Injury"]:
        df = df[df[col].isin([0, 1])]

    # Other numeric gaps stay empty: the classifier handles missing values itself.
    # No outlier filter: every value in the raw file is inside its valid range.

    df.reset_index(drop=True, inplace=True)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Cleaned injury dataset saved to {output_path}")

    return df
