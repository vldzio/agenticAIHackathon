# AetherFit AI (agenticAIHackathon) - project context

## What this is
Streamlit fitness-planning app: pretrained scikit-learn classifiers (fitness level, injury risk) + a seven-node LangGraph workflow whose LLM steps write workout, nutrition and recovery plans. The `demo-ready` branch makes a LIVE LLM the default for the hosted demo. The Space itself is the UI (no Vercel):

```text
Hugging Face Docker Space (public :7860 Streamlit `main.py`) -> private FreeLLMAPI gateway (127.0.0.1:3001, same container) -> free-tier LLMs
   modes: Free Demo (default, rate-limited) | My Gemini key | My OpenAI-compatible key | Mock (only with ENABLE_MOCK=1)
```

## Layout
- `main.py` - UI and modes (`MODE_*`), gateway start (`_start_gateway`), per-IP admission via `utils/demo_guard.py` (4 credits per assessment). `main.py` uses CRLF; keep it.
- `utils/openai_compat_client.py` - OpenAI-compatible client with `GeminiClient`'s interface (`generate_structured_json`, one corrective retry, LangSmith-wrapped). `utils/gateway.py` reads the gateway's unified key from its local SQLite DB. `utils/gemini_client.py` is original (its mock payloads are used only by tests and `ENABLE_MOCK`).
- `workflow/`, `nodes/`, `agents/` - LangGraph pipeline. `ml/` - cleaning, training (`ml/train_model/common.py`), evaluation and models (`ml/models/*.pkl`); `python ml/train_pipeline.py` retrains both models and records `ml/models/metrics.json`.
- `deploy/render/` + `render.yaml` - Render web service `aetherfit-ai` (live at https://aetherfit-ai.onrender.com, free plan, auto-deploys `demo-ready`). `deploy/space/` - earlier Hugging Face Space files.

## Run and test
- `python -m venv .venv && .venv\Scripts\pip install -r requirements.txt && .venv\Scripts\pytest tests` (14 tests: `test_demo.py` drives the real Streamlit app via `AppTest` with the real workflow and ML models, only the LLM HTTP endpoint is stubbed; `test_models.py` checks the classifiers on the evaluation CSVs). Needs Python 3.11+ (scikit-learn 1.8.0 has no 3.10 build).
- Local run: `streamlit run main.py` (set `LLM_BASE_URL`/`LLM_API_KEY` for Free mode, or use BYO key modes).

## Rules and gotchas
- `requirements.txt` pins `scikit-learn==1.8.0` (the pickles were saved with it) and `pyarrow==18.1.0` (newer pyarrow needs NumPy 2, which langchain 0.3 forbids; without the pin the app crashed at import in testing).
- The ML models may only use inputs the form collects (no `Activity_Score`, flexibility, strength-imbalance, overtraining or `Fitness_Level` columns); `test_models.py` enforces it. Model classes are in LabelEncoder (alphabetical) order, so always decode with the saved encoder. The injury evaluation set is labelled on a shifted scale, which caps exact accuracy near 70% (see README).
- The hosted app must not offer simulated output: Mock mode stays behind `ENABLE_MOCK=1`. Client IP = `CF-Connecting-IP` (Render sits behind Cloudflare), else the LAST `X-Forwarded-For` entry. Never log API keys.
- Free mode uses a pinned model chain (`LLM_MODELS`, default `DEFAULT_FREE_MODELS` in `utils/openai_compat_client.py`): fast models first, the gateway's `auto` route last, 25 s per try, a failed model rests 60 s. Do not make `auto` the first choice; it picked slow or rate-limited models and one assessment took minutes. Own-key modes never use the chain.
- LangSmith: set `LANGSMITH_API_KEY` and `start.sh` turns tracing on; project `aetherfit-demo`.

## Deploy facts
- Space `aetherfit-ai` (Docker, `app_port: 7860`). Secrets: `ENCRYPTION_KEY` (64 hex), `FREEAPI_CONFIG_JSON`, `LANGSMITH_API_KEY`, `UPSTASH_REDIS_REST_URL/TOKEN`; optional `RL_PER_IP_DAILY`, `RL_GLOBAL_DAILY`. The Space clones branch `demo-ready`.
- Steps: `hf auth login`, create the Space from `deploy/space/` (Docker SDK), set the secrets, wait for the build, open the Space URL.

## Status
Verified: 14 tests pass (real workflow, real ML models); held-out accuracy 81.7% fitness and 69.0% injury (`ml/models/metrics.json`); local run through a live FreeLLMAPI gateway. Render deploy with a live assessment and the Upstash limiter keyed on the visitor's real IP. NOT verified: Space Docker build, real provider calls, Streamlit behind the Spaces iframe/proxy (start.sh disables CORS/XSRF checks for it), live LangSmith traces.
