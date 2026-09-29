"""Data cleaning for both datasets.

Replaces the previous IQR-based row dropping (which, in the injury script, was accidentally applied
to a single column because of an indentation bug, and would have deleted every positive value of
the binary columns had it run on all of them). Cleaning now is:

1. drop duplicate ``User_ID`` rows;
2. coerce numerics; drop rows whose value falls outside a *plausible physical range*;
3. median-impute remaining missing numeric values;
4. recompute derived columns (BMI, categories) from raw values with the same functions the API uses;
5. drop rows with missing/invalid categoricals or target.

Every step is counted in the returned report.
"""

from __future__ import annotations

import pandas as pd

from app.domain.profile_metrics import age_category, bmi_category, hours_category
from app.ml.features import FITNESS_SPEC, INJURY_SPEC, ModelSpec

PLAUSIBLE_RANGES = {
    "Age": (18, 100),
    "Height_CM": (100, 250),
    "Weight_KG": (30, 300),
    "BMI": (12, 60),
    "Available_Hours_Per_Week": (0, 40),
    "Training_Frequency_Hours": (0, 40),
}
BINARY_COLUMNS = ["Has_Health_Conditions", "Previous_Injury"]
DATASET_NUMERIC = {
    "fitness_level": ["Age", "Height_CM", "Weight_KG", "BMI", "Available_Hours_Per_Week"],
    "injury_risk": ["Age", "BMI", "Training_Frequency_Hours"],
}


def clean_dataset(df: pd.DataFrame, spec: ModelSpec, dedupe: bool = True) -> tuple[pd.DataFrame, dict]:
    report: dict[str, int] = {"rows_in": len(df)}
    df = df.copy()
    if dedupe and "User_ID" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["User_ID"], keep="first")
        report["dropped_duplicates"] = before - len(df)

    numeric_cols = [c for c in DATASET_NUMERIC[spec.name] if c in df.columns]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Out-of-range (but present) values are invalid records, not "outliers" to be trimmed.
    before = len(df)
    for col in numeric_cols:
        lo, hi = PLAUSIBLE_RANGES[col]
        df = df[df[col].isna() | df[col].between(lo, hi)]
    report["dropped_out_of_range"] = before - len(df)

    if spec.name == "fitness_level":
        both = df["Height_CM"].notna() & df["Weight_KG"].notna()
        calc = (df["Weight_KG"] / (df["Height_CM"] / 100) ** 2).round(1)
        df.loc[df["BMI"].isna() & both, "BMI"] = calc[df["BMI"].isna() & both]
    report["imputed_numeric_cells"] = int(df[numeric_cols].isna().sum().sum())
    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].median())

    for col in BINARY_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    before = len(df)
    for col in [c for c in BINARY_COLUMNS if c in df.columns]:
        df = df[df[col].isin([0, 1])]
    report["dropped_invalid_binary"] = before - len(df)

    # Derived columns (kept in the cleaned CSV for transparency; the models do not need them).
    df["Age_Category"] = df["Age"].map(age_category)
    df["BMI_Category"] = df["BMI"].map(bmi_category)
    if "Available_Hours_Per_Week" in df.columns:
        df["Hours_Category"] = df["Available_Hours_Per_Week"].map(hours_category)

    before = len(df)
    for col, allowed in {**spec.allowed, spec.target: spec.classes}.items():
        df = df[df[col].isin(allowed)]
    report["dropped_invalid_categorical"] = before - len(df)

    df = df.reset_index(drop=True)
    report["rows_out"] = len(df)
    return df, report


def clean_fitness_data(df: pd.DataFrame, dedupe: bool = True) -> tuple[pd.DataFrame, dict]:
    return clean_dataset(df, FITNESS_SPEC, dedupe)


def clean_injury_data(df: pd.DataFrame, dedupe: bool = True) -> tuple[pd.DataFrame, dict]:
    return clean_dataset(df, INJURY_SPEC, dedupe)
