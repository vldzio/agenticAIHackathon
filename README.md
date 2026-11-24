# AetherFit AI

**A fitness-planning app that combines supervised ML with an agentic planning workflow.** AetherFit takes a user profile, predicts fitness level and injury risk with trained classifiers, and produces workout, nutrition, and recovery guidance through a seven-node LangGraph pipeline. A Streamlit interface presents the full assessment and exports it as JSON.

**Live demo:** [aetherfit-ai.onrender.com](https://aetherfit-ai.onrender.com)

## Features

- Profile form for age, height, weight, gender, fitness goal, experience, weekly training time, and health conditions.
- Gradient-boosted classifiers (scikit-learn `HistGradientBoostingClassifier`) for fitness level and injury risk, with class probabilities and the risk factors behind them.
- A LangGraph workflow that coordinates input normalization, classification, workout planning, nutrition guidance, and recovery recommendations.
- Results across **Overview**, **Workout**, **Nutrition**, and **Recovery** tabs, with JSON export.
- A **Run Model Evaluation** button that scores both classifiers on the held-out evaluation sets.

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

### Generation modes

| Mode | What it uses |
| --- | --- |
| **Free Demo (live LLM)** (default) | Free-tier models through a private OpenAI-compatible gateway, with a small daily allowance per visitor |
| **Use My Gemini API Key** | Your own Gemini key, kept only in the session |
| **Use My OpenAI-Compatible Key** | Your own key for any OpenAI-compatible provider |
| **Mock Demo** | Offline placeholder output for development, enabled with `ENABLE_MOCK=1` |

LLM steps are schema-checked with one corrective retry, and every assessment can be traced in LangSmith.

## Run locally

Requires Python 3.11+. Pretrained models are included. Run commands from the repository root.

```bash
git clone https://github.com/vldzio/agenticAIHackathon.git
cd agenticAIHackathon
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run main.py
```

Open the address Streamlit prints (normally `http://localhost:8501`) and choose a mode in the sidebar. For the Free Demo mode, set `LLM_BASE_URL` and `LLM_API_KEY` to an OpenAI-compatible endpoint; the key modes need nothing beyond your own key.

```bash
pytest tests    # drives the real Streamlit app, workflow and models with a stubbed LLM endpoint
```

### Docker

```bash
docker build -f dockerfile -t aetherfit-ai .
docker run --rm -p 8501:8501 aetherfit-ai
```

Deployment recipes for the hosted demo are in `deploy/render/` (with `render.yaml`) and `deploy/space/`.

## Data and models

The classifiers are trained on synthetic fitness datasets bundled in `data/`:

| Dataset | Rows | Target |
| --- | --- | --- |
| `data/training_dataset/fitness_level_training.csv` | 30,000 | `Fitness_Level_Class` (Beginner, Intermediate, Advanced, Athlete) |
| `data/training_dataset/injury_risk_training.csv` | 30,000 | `Injury_Risk_Class` (four risk levels) |
| `data/evaluation_dataset/fitness_level_evaluation.csv` | 8,000 | held-out evaluation |
| `data/evaluation_dataset/injury_risk_evaluation.csv` | 8,000 | held-out evaluation |

The models use only the inputs the app's form collects. `python ml/train_pipeline.py` cleans the data, retrains both models, evaluates them on the held-out sets, and records the run in `ml/models/metrics.json`.

### Recorded results

From `ml/models/metrics.json`, scored once on the 8,000 held-out rows per task:

| Metric | Fitness level | Injury risk |
| --- | --- | --- |
| Accuracy (95% bootstrap interval) | 81.7% (80.8 to 82.5) | 69.0% (67.9 to 70.0) |
| Majority-class baseline | 27.9% | 30.0% |
| Macro F1 | 0.807 | 0.694 |
| Within one class of the true label | 100.0% | 99.7% |
| Quadratic weighted kappa | 0.932 | 0.861 |

## Project structure

| Path | Purpose |
| --- | --- |
| `main.py` | Streamlit form, modes, result tabs, evaluation button, JSON download |
| `workflow/workflow.py` | Seven-node LangGraph topology |
| `graph.py`, `state.py` | Assessment orchestration and shared typed state |
| `nodes/`, `agents/` | ML prediction and planning components |
| `utils/` | Gemini and OpenAI-compatible clients, gateway helper, rate limiting |
| `ml/` | Data cleaning, training, evaluation, and trained models |
| `data/` | Training and evaluation datasets |
| `tests/` | App and model tests |
| `deploy/` | Render and Hugging Face Space deployment recipes |

## Disclaimer

AetherFit's guidance is for general fitness planning and is not medical advice.
