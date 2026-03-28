"""Train injury risk classifier using RandomForest."""

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score


def train_injury_risk_model(
    training_data_path: str,
    model_output_path: str,
    scaler_output_path: str,
    encoder_output_path: str
) -> dict:

    df = pd.read_csv(training_data_path)

    feature_columns = [
        "Age",
        "BMI",
        "Fitness_Level",
        "Gender",
        "Fitness_Experience",
        "Age_Category",
        "BMI_Category",
        "Has_Health_Conditions",
        "Previous_Injury",
        "Flexibility_Score",
        "Strength_Imbalance_Score",
        "Training_Frequency_Hours"
    ]

    target_column = "Injury_Risk_Class"

    x = df[feature_columns].copy()
    y = df[target_column].copy()

    categorical_features = [
        "Fitness_Level",
        "Gender",
        "Fitness_Experience",
        "Age_Category",
        "BMI_Category"
    ]

    feature_encoders = {}

    for col in categorical_features:
        encoder = LabelEncoder()
        x[col] = encoder.fit_transform(x[col])
        feature_encoders[col] = encoder
    
    target_encoder = LabelEncoder()
    y = target_encoder.fit_transform(y)

    x_train,x_test,y_train,y_test = train_test_split(x,y,test_size=0.2,random_state=42,stratify=y)

    scaler = StandardScaler()

    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
        max_features=1000
    )

    model.fit(x_train_scaled, y_train)

    predictions = model.predict(x_test_scaled)

    accuarcy = accuracy_score(y_test, predictions)

    report = classification_report(y_test, predictions, output_dict=True)

    cm = confusion_matrix(y_test, predictions)

    Path(model_output_path).parent.mkdir(parents=True,exist_ok=True)

    with open(model_output_path, "wb") as f:
        pickle.dump(model,f)

    with open(scaler_output_path, "wb") as f:
        pickle.dump(scaler,f)

    encoder_data = {
        "target_encoder": target_encoder,
        "feature_encoders": feature_encoders,
        "feature_columns": feature_columns
    }

    with open(encoder_output_path, "wb") as f:
        pickle.dump(encoder_data,f)

    feature_importance = dict(zip(feature_columns, model.feature_importances_))

    return {
        "model_accuracy": accuarcy,
        "total_samples": len(df),
        "train_samples": len(x_train),
        "test_samples": len(x_test),
        "classes": list(target_encoder.classes_),
        "feature_importance": feature_importance,
        "classification_report": report,
        "confusion_matrix": cm.tolist()
    }

if __name__ == "__main__":
    train_injury_risk_model(
        "../../data/processed/injury_risk_training_cleaned.csv",
        "../models/injury_risk_model.pkl",
        "../models/injury_risk_scaler.pkl",
        "../models/injury_risk_encoder.pkl",
    )
