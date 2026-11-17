# AetherFit AI

**A fitness-planning prototype that combines supervised ML with an agentic planning workflow.** AetherFit takes a user profile, estimates fitness-level and injury-risk categories, and produces workout, nutrition, and recovery guidance through a seven-node LangGraph pipeline. A Streamlit interface makes the complete assessment explorable and exportable as JSON.

AetherFit supports two generation modes: a **no-key Mock Demo** for exploring the experience and **live Gemini-backed generation** with a visitor-provided API key. The user-facing UI labels the mock mode as simulated rather than passing it off as a live model response.

## What it does

- Collects age, height, weight, fitness goal, experience, available training time, and health conditions in a Streamlit sidebar.
- Loads trained gradient-boosted classifiers to estimate fitness level and injury risk from the answers on the form, including class probabilities and surfaced risk factors.
- Uses LangGraph to coordinate input normalization, classification, workout planning, nutrition guidance, and recovery recommendations.
- Presents results across **Overview**, **Workout**, **Nutrition**, and **Recovery** tabs; supports JSON export.
- Exposes a **Run Model Evaluation** action that scores both classifiers on the repository's held-out evaluation datasets: accuracy with a confidence interval, macro F1, ordinal metrics, calibration, per-class precision and recall, and confusion matrices.

```text
Profile form
    ↓
Parse → normalize ┬→ fitness classifier ────┐
                  └→ injury-risk classifier ─┤
                                             ↓
                         workout plan → nutrition plan → recovery guidance
                                             ↓
                                  Streamlit tabs + JSON export
```

The fitness and injury branches feed the downstream workout planner; LLM-backed steps use either the mock generator or the selected Gemini client.

## Run locally

**Requirements:** Python 3.12 is the project's Docker base image; use a comparable supported Python version for local runs. Dependencies and pretrained model artifacts are included in this repository. Run commands from the repository root.

```bash
git clone https://github.com/vldzio/agenticAIHackathon.git
cd agenticAIHackathon
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run main.py
```

Open the address printed by Streamlit (normally `http://localhost:8501`). Keep **Mock Demo** selected to try the flow without an API key. To use live generation, choose **Use My Gemini API Key** in the sidebar and enter your own key there. The README does **not** require a shared key in `.env` or in the hosted deployment. A user-provided key is held in Streamlit session state for that session; avoid submitting sensitive profile details to a model unless you are comfortable with that provider's processing.

### Docker

The repository includes a lowercase `dockerfile`; pass it explicitly on case-sensitive hosts:

```bash
docker build -f dockerfile -t aetherfit-ai .
docker run --rm -p 8501:8501 aetherfit-ai
```

Then open `http://localhost:8501`. The container defaults to Mock Demo; visitors can opt into their own Gemini key in the UI.

## ML artifacts and evaluation

- `ml/models/` contains serialized fitness-level and injury-risk classifiers, scalers, and encoders used by the app.
- `data/training_dataset/` and `data/processed/` contain training inputs and cleaned datasets; `data/evaluation_dataset/` contains separate evaluation CSVs.
- `ml/train_model/` and `ml/data_cleaning/` contain training/preprocessing code; `ml/evaluation/evaluate_models.py` computes the metrics below.
- `python ml/train_pipeline.py` cleans the data, retrains both models, evaluates them and records the run in `ml/models/metrics.json`.

### Recorded results

Both models are trained on `data/training_dataset/` only and scored once on the 8,000 separate rows in `data/evaluation_dataset/`. The datasets are synthetic, so these numbers describe how well the models reproduce the datasets' labelling rules, not real-world medical or coaching accuracy.

| Metric (held-out evaluation set) | Fitness level | Injury risk |
| --- | --- | --- |
| Accuracy (95% bootstrap interval) | 81.7% (80.8 to 82.5) | 69.0% (67.9 to 70.0) |
| Majority-class baseline | 27.9% | 30.0% |
| Macro F1 | 0.807 | 0.694 |
| Within one class of the true label | 100.0% | 99.7% |
| Quadratic weighted kappa | 0.932 | 0.861 |
| Expected calibration error | 0.064 | 0.086 |
| 5-fold cross-validation accuracy on training data | 76.0% | 78.1% |

Things to know when reading them:

- **The models only use what the form collects.** The fitness model does not use the dataset's `Activity_Score` column, and the injury model does not use `Flexibility_Score`, `Strength_Imbalance_Score`, `Overtraining_Risk_Score` or `Fitness_Level`. An earlier version scored 98% and 75% offline with those columns, but the app cannot measure them and fed the models invented values, so the predictions users saw were far less accurate than the report claimed.
- **Injury risk: the evaluation set is labelled on a shifted scale.** Each dataset assigns its four risk classes by rank within that dataset (exactly 25/30/25/20%), and the evaluation population is older and heavier, so the same person tends to get a lower class there than in the training data. The model ranks people well (kappa 0.86, almost never more than one class off) but its fixed class boundaries come from the training data, which caps exact-match accuracy on this set.
- **Fitness level: training rows are noisier than evaluation rows** (missing values), which is why cross-validation accuracy is lower than evaluation accuracy.
- **Fitness level: the labels follow age, BMI and hours more than stated experience.** The app's default profile (30-year-old man, BMI 24.2, "Beginner, training 3 times per week", 4-5 hours) is classed Advanced at about 71% confidence. This is not a pipeline bug: the LLM normaliser returns Beginner, 0 years, 4.5 hours, those values reach the model unchanged, and the label is decoded with the saved encoder. In the training data, self-described beginners aged 25-35 with BMI 22.5-26 and 3.5-5.5 hours are labelled Advanced 58% of the time and Beginner 5% (149 rows); across all rows, the Beginner class averages age 46.5 and BMI 27.5. Clearly different profiles still move sensibly (once a week, 1.5 hours, never exercised: Beginner; 8 years, 10 hours: Athlete), but the model can only be as good as these synthetic labels, so the app shows its result as a rough estimate. Retraining on the same data would not change this.

Click **Run Model Evaluation** in the Streamlit UI to recompute these metrics from the bundled evaluation CSVs. Only load serialized `.pkl` model files from sources you trust.

## Repository map

| Path | Purpose |
| --- | --- |
| `main.py` | Streamlit input form, tabs, evaluation button, JSON download |
| `workflow/workflow.py` | Seven-node LangGraph topology |
| `graph.py`, `state.py` | Assessment orchestration and shared typed state |
| `nodes/`, `agents/` | ML prediction and planning components |
| `utils/gemini_client.py` | Mock and Gemini client helpers |
| `ml/`, `data/` | Training, model artifacts, and evaluation datasets |
| `dockerfile` | Containerized Streamlit startup on port 8501 |

## Intended use

AetherFit demonstrates how tabular ML predictions and LLM-assisted planning can work together in an interactive assessment. **It is an exploratory fitness/wellness prototype, not a clinically validated injury-screening, medical, or nutrition service.** Treat any guidance as illustrative and consult qualified professionals for individual health decisions.

## Live demo deployment

The hosted app runs as one Hugging Face Docker Space ([`deploy/space/`](deploy/space)) containing the Streamlit app plus a **private** [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) gateway:

* **Free Demo (live LLM)** is the default mode: the normaliser, workout, nutrition and recovery steps are generated live by a free-tier model through the gateway (`utils/openai_compat_client.py`, schema-checked with one corrective retry). Each visitor gets a small daily allowance (4 credits per assessment, per-IP and global caps in Upstash Redis).
* **Use My Gemini API Key** / **Use My OpenAI-Compatible Key** bypass the shared allowance and use the visitor's own provider account (kept in the session only).
* **Mock Demo** returns simulated placeholder output, so it is **not offered on the hosted app**; it exists for offline development and appears only when `ENABLE_MOCK=1`.
* Every assessment is traced to LangSmith (project `aetherfit-demo`): the LangGraph nodes and each model call.
* `requirements.txt` now pins `scikit-learn==1.8.0` (the version the shipped `ml/models/*.pkl` were saved with) and `pyarrow==18.1.0` (newer pyarrow needs NumPy 2, which LangChain 0.3 forbids).
* Tests: `pip install -r requirements.txt && pytest tests/test_demo.py` (drives the real Streamlit app, LangGraph workflow and ML models against a stub LLM endpoint).
