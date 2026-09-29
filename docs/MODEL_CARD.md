# Model card – AetherFit fitness-level and injury-risk classifiers

Numbers below come from `backend/artifacts/metadata.json` (seed 42; scikit-learn 1.9.1). Regenerate with `make train`.

## Intended use

Give a *rough, explainable* orientation to a fitness-planning app: an estimated fitness level (Beginner → Athlete) and injury-risk band (Low → Very High) that shape the generated plan. **Not** a clinical screening tool, diagnosis, or substitute for a professional. Users are told this in the UI, exports and this document.

## Data

| | Fitness model | Injury model |
|---|---|---|
| Training rows (raw → cleaned) | 30,000 → 29,009 | 30,000 → 28,768 |
| Evaluation rows | 8,000 | 8,000 |
| Provenance | Bundled CSVs of unknown origin; statistics (labels banded by a proxy feature, age dominating the label) indicate a **synthetic generator** | same |
| Age range seen | 18–70 | 18–70 |

Cleaning (`ml_pipeline/cleaning.py`): plausible-range validation, median imputation of missing numerics, de-duplication, invalid category/binary rows dropped, derived columns recomputed. (Interquartile-range filtering was **not** used – on binary columns it would delete every positive row.)

## Features

| Model | Numeric | Categorical |
|---|---|---|
| Fitness | Age, BMI, Weight_KG, Available_Hours_Per_Week | Gender, Fitness_Experience, Fitness_Goal |
| Injury | Age, BMI, Has_Health_Conditions, Previous_Injury, Training_Frequency_Hours | Gender, Fitness_Level, Fitness_Experience |

Deliberately **excluded**:

- `Activity_Score` (fitness) – it is banded by the label, i.e. a proxy for it. With it accuracy was 98.3 %, without it 80.9 %. The old app also computed it differently from the dataset, so the reported 98 % never applied to real inputs.
- `Flexibility` / `Strength_Imbalance` (injury) – present in the data but never measured by the app; guessing them at serving time made predictions arbitrary.

Serving and training share `app/ml/features.py`, so feature construction cannot drift.

## Model

`Pipeline(ColumnTransformer(OneHotEncoder(handle_unknown="ignore")), CalibratedClassifierCV(RandomForestClassifier(class_weight="balanced")))`, sigmoid calibration with 3 folds. Artifacts are stored with joblib and verified by SHA-256 and library versions on load.

## Performance (held-out evaluation CSVs, 8,000 rows each)

| | Fitness level | Injury risk |
|---|---|---|
| Accuracy | **79.2 %** | **69.2 %** |
| Within one class | 99.7 % | 99.96 % |
| Macro-F1 | 0.782 | 0.682 |
| Log-loss | 0.529 | 0.774 |
| Expected calibration error | 0.053 | 0.099 |
| 5-fold CV accuracy (train) | 73.9 % ± 0.5 | 80.4 % ± 0.6 |

Per-class precision – fitness: Beginner 0.88, Intermediate 0.67, Advanced 0.67, Athlete 0.91. Injury: Low 0.97, Moderate 0.60, High 0.71, Very High 0.72.

These are far lower than the previously advertised 98 % (fitness) because the label-proxy feature was removed. That is the honest figure.

### Known behaviours

- **Distribution shift on injury risk.** CV accuracy (80 %) is much higher than accuracy on the evaluation CSV (69 %). On that set the model has high precision but low recall for *Low Risk* (0.36): it tends to err toward **overstating** risk. For a safety feature this is the preferable direction, but it is still an error.
- **Fitness labels are mostly a function of age** in this synthetic data, and about 35 % of "Beginner" and 20 % of "Never Exercised" rows carry higher labels. Predictions for young users therefore skew high.
- **Ages outside 18–70** (the app accepts up to 100) are outside the training range; the app warns rather than trusting the number.

## Guardrails around the models

- **Experience ceiling** – the predicted fitness level is capped by stated experience (Never Exercised → at most Beginner, Beginner → Intermediate, Some Experience → Advanced; ≤ 2 h/week can't be Athlete), and the cap is recorded in the result notes.
- **Safety rules** (`app/domain/safety.py`) override model output: high injury risk, age ≥ 60, extreme BMI, previous injury, or reported conditions push the plan to conservative; red-flag symptoms, severe conditions or "not cleared" produce **clinician-first** (light intensity, ≤ 3 sessions, clearance required).
- The LLM's reading of free text is merged with deterministic heuristics as a floor – the LLM can add caution but never downgrade a detected condition. Free-text is wrapped in delimiters and a self-declared "Advanced/Athlete" with no stated years is capped, to blunt prompt injection.

## Explanations

"What influenced this" bars come from single-feature occlusion: each input is replaced by a typical training value and the change in the predicted-class probability is reported. They describe influence on this prediction, not causation.

## Ethical and safety considerations

Health inputs (conditions, injuries) are sensitive. They are stored only in the device-scoped plan record, never sent anywhere except (in Live mode) to Google Gemini using the user's own key. The nutrition and workout advice is generic; users with medical conditions must seek professional guidance, which the UI, PDF and API responses state.

## Future work

Replace the synthetic dataset with real, consented data; validate with clinicians; add proper calibration checks by subgroup; add Alembic migrations and user accounts.
