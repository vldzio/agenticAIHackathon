# AetherFit AI

**A fitness-planning app that combines supervised ML with an agentic planning workflow.** AetherFit takes a user profile, predicts fitness level and injury risk, and produces workout, nutrition, and recovery guidance through a seven-node LangGraph pipeline. A Streamlit interface presents the full assessment and exports it as JSON.

**Live demo:** [aetherfit-ai.onrender.com](https://aetherfit-ai.onrender.com)

Two generation modes are built in: **Mock Demo**, which needs no API key, and **live Gemini generation** with your own API key.

## Features

- Profile form for age, height, weight, fitness goal, experience, available training time, and health conditions.
- Random Forest classifiers for fitness level and injury risk, with class probabilities and the risk factors behind them.
- A LangGraph workflow that coordinates input normalization, classification, workout planning, nutrition guidance, and recovery recommendations.
- Results across **Overview**, **Workout**, **Nutrition**, and **Recovery** tabs, with JSON export.
- A **Run Model Evaluation** button that reports accuracy and confusion matrices for both classifiers on the held-out evaluation sets.

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

## Run locally

Requires Python 3.12 (the Docker base image version). Pretrained models are included. Run commands from the repository root.

```bash
git clone https://github.com/vldzio/agenticAIHackathon.git
cd agenticAIHackathon
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run main.py
```

Open the address Streamlit prints (normally `http://localhost:8501`). **Mock Demo** works out of the box; for live generation, choose **Use My Gemini API Key** in the sidebar and paste your key. The key is kept only in the Streamlit session.

### Docker

```bash
docker build -f dockerfile -t aetherfit-ai .
docker run --rm -p 8501:8501 aetherfit-ai
```

Then open `http://localhost:8501`.

## Models and evaluation

- `ml/models/` holds the trained fitness-level and injury-risk classifiers, scalers, and encoders.
- `data/training_dataset/` and `data/processed/` hold raw and cleaned training data; `data/evaluation_dataset/` holds the held-out evaluation sets.
- `ml/data_cleaning/` and `ml/train_model/` contain preprocessing and training code; `ml/evaluation/evaluate_models.py` computes accuracy, per-class precision/recall/F1, and confusion matrices.
- `ml/train_pipeline.py` runs cleaning, training, and evaluation end to end.

On 8,000 held-out rows of synthetic data, the classifiers reach **81.7% accuracy for fitness level** and **69.0% for injury risk**.

## Project structure

| Path | Purpose |
| --- | --- |
| `main.py` | Streamlit form, result tabs, evaluation button, JSON download |
| `workflow/workflow.py` | Seven-node LangGraph topology |
| `graph.py`, `state.py` | Assessment orchestration and shared typed state |
| `nodes/`, `agents/` | ML prediction and planning components |
| `utils/gemini_client.py` | Mock and Gemini client helpers |
| `ml/`, `data/` | Training, model artifacts, and datasets |
| `dockerfile` | Containerized Streamlit app on port 8501 |

## Disclaimer

AetherFit's guidance is for general fitness planning and is not medical advice.
