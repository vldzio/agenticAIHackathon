"""Data cleaning for fitness level training dataset."""

import pandas as pd
from pathlib import Path

VALID_VALUES = {
  "Gender": ["Male", "Female", "Other"],
  "Fitness_Goal": ["Weight Loss", "Muscle Building", "Endurance/Cardio", "General Fitness"],
  "Fitness_Experience": ["Never Exercised", "Beginner", "Some Experience", "Advanced"],
  "Fitness_Level_Class": ["Beginner", "Intermediate", "Advanced", "Athlete"],
}
NUMERIC_COLS = ["Age", "Height_CM", "Weight_KG", "BMI", "Available_Hours_Per_Week", "Activity_Score"]


def clean_fitness_data(input_path: str, output_path: str = None) -> pd.DataFrame:
  df = pd.read_csv(input_path)
  df = df.drop_duplicates(subset=["User_ID"], keep="first")

  for col in NUMERIC_COLS:
    df[col] = pd.to_numeric(df[col], errors="coerce")

  # Rows with a missing or unknown category or label cannot be repaired, so drop them.
  for col, valid in VALID_VALUES.items():
    df = df[df[col].isin(valid)]

  # BMI and weight follow from each other and height, so recover them exactly.
  height_m = df["Height_CM"] / 100
  df["BMI"] = df["BMI"].fillna((df["Weight_KG"] / height_m**2).round(1))
  df["Weight_KG"] = df["Weight_KG"].fillna((df["BMI"] * height_m**2).round(1))

  # Other numeric gaps stay empty: the classifier handles missing values itself.
  # No outlier filter: every value in the raw file is inside its valid range, and
  # the old IQR rule threw away everyone training more than about 13 hours a week.

  df.reset_index(drop=True, inplace=True)

  if output_path:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Cleaned fitness dataset saved to {output_path}")

  return df
