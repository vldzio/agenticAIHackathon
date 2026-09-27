# AetherFit AI

**A fitness-planning prototype that combines supervised ML with an agentic planning workflow.** AetherFit takes a user profile, estimates fitness-level and injury-risk categories, and produces workout, nutrition, and recovery guidance through a seven-node LangGraph pipeline. A Streamlit interface makes the complete assessment explorable and exportable as JSON.

AetherFit supports two generation modes: a **no-key Mock Demo** for exploring the experience and **live Gemini-backed generation** with a visitor-provided API key. The user-facing UI labels the mock mode as simulated rather than passing it off as a live model response.

## What it does

- Collects age, height, weight, fitness goal, experience, available training time, and health conditions in a Streamlit sidebar.
- Loads trained Random Forest models to classify fitness level and injury risk, including class probabilities and surfaced risk factors.
- Uses LangGraph to coordinate input normalization, classification, workout planning, nutrition guidance, and recovery recommendations.
- Presents results across **Overview**, **Workout**, **Nutrition**, and **Recovery** tabs; supports JSON export.
- Exposes a **Run Model Evaluation** action that reports evaluation accuracy and confusion matrices for both classifiers using the repository's evaluation datasets.

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
- `ml/train_model/` and `ml/data_cleaning/` contain training/preprocessing code; `ml/evaluation/evaluate_models.py` computes accuracy, per-class precision/recall/F1, and confusion matrices.

Click **Run Model Evaluation** in the Streamlit UI to inspect the metrics on the bundled evaluation CSVs. This README does not claim a particular score without a recorded run and documented data provenance. **If retraining**, note that `ml/train_pipeline.py` currently points its evaluation files at `data/` rather than `data/evaluation_dataset/`; correct `eval_dir` before using that orchestrator. Only load serialized `.pkl` model files from sources you trust.

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
