import pandas as pd

from ml_pipeline.cleaning import clean_fitness_data, clean_injury_data


def _injury_rows():
    return pd.DataFrame(
        {
            "User_ID": ["a", "a", "b", "c", "d", "e"],
            "Age": [30, 30, 40, 200, 35, None],
            "BMI": [22.0, 22.0, 25.0, 24.0, 26.0, 23.0],
            "Gender": ["Male", "Male", "Female", "Male", "Robot", "Other"],
            "Fitness_Level": ["Beginner"] * 6,
            "Fitness_Experience": ["Beginner"] * 6,
            "Has_Health_Conditions": [0, 0, 1, 0, 0, 1],
            "Previous_Injury": [1, 1, 0, 0, 0, 1],
            "Training_Frequency_Hours": [3, 3, 5, 4, 4, 6],
            "Injury_Risk_Class": ["Low Risk", "Low Risk", "High Risk", "Low Risk", "Low Risk", "Moderate Risk"],
        }
    )


def test_injury_cleaning_keeps_binary_positives_and_drops_invalid():
    """Regression: the old script returned inside the loop and IQR-filtering would have deleted all 1s."""
    df, report = clean_injury_data(_injury_rows())
    assert report["dropped_duplicates"] == 1
    assert report["dropped_out_of_range"] == 1  # age 200
    assert report["dropped_invalid_categorical"] == 1  # gender Robot
    assert set(df["User_ID"]) == {"a", "b", "e"}
    assert df["Previous_Injury"].sum() == 2 and df["Has_Health_Conditions"].sum() == 2
    assert df["Age"].notna().all()  # missing age imputed
    assert {"Age_Category", "BMI_Category"} <= set(df.columns)


def test_fitness_cleaning_recomputes_bmi_and_categories():
    raw = pd.DataFrame(
        {
            "User_ID": ["a"],
            "Age": [50],
            "Height_CM": [180.0],
            "Weight_KG": [81.0],
            "BMI": [None],
            "Gender": ["Male"],
            "Fitness_Goal": ["General Fitness"],
            "Available_Hours_Per_Week": [7.0],
            "Fitness_Experience": ["Advanced"],
            "Fitness_Level_Class": ["Advanced"],
        }
    )
    df, _ = clean_fitness_data(raw)
    assert df.loc[0, "BMI"] == 25.0
    assert df.loc[0, "BMI_Category"] == "Overweight"
    assert df.loc[0, "Age_Category"] == "Middle Aged"
    assert df.loc[0, "Hours_Category"] == "High"
