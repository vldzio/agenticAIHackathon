"""Data cleaning for fitness level training dataset."""

import pandas as pd
from pathlib import Path


def clean_fitness_data(input_path: str, output_path: str = None) -> pd.DataFrame:
  df = pd.read_csv(input_path)
  df = df.drop_duplicates(subset=["User_ID"], keep="first")

  numeric_cols = [
    "Age",
    "Height_CM",
    "Weight_KG",
    "BMI",
    "Available_Hours_Per_Week",
    "Activity_Score"
  ]
  for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df[col].fillna(df[col].median(), inplace=True)

  for col in numeric_cols:

    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    df = df[(df[col] >= lower) & (df[col] <= upper)]

  valid_gender = ["Male", "Female", "Other"]
  valid_fitness_class = ["Beginner", "Intermediate", "Advanced", "Athlete"]
  valid_experience = ["Never Exercised", "Beginner", "Some Experience", "Advanced"]

  df = df[df["Gender"].isin(valid_gender)]
  df = df[df["Fitness_Level_Class"].isin(valid_fitness_class)]
  df = df[df["Fitness_Experience"].isin(valid_experience)]

  df.reset_index(drop=True, inplace=True)

  if output_path:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Cleaned fitness dataset saved to {output_path}")

  return df
