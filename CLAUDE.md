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
- `workflow/`, `nodes/`, `agents/`, `ml/` - original LangGraph pipeline and models (`ml/models/*.pkl`). `deploy/space/` - Dockerfile, start.sh, README.

## Run and test
- `python -m venv .venv && .venv\Scripts\pip install -r requirements.txt && .venv\Scripts\pytest tests/test_demo.py` (8 tests drive the real Streamlit app via `AppTest`, the real workflow and ML models; only the LLM HTTP endpoint is stubbed).
- Local run: `streamlit run main.py` (set `LLM_BASE_URL`/`LLM_API_KEY` for Free mode, or use BYO key modes).

## Rules and gotchas
- `requirements.txt` pins `scikit-learn==1.8.0` (the pickles were saved with it) and `pyarrow==18.1.0` (newer pyarrow needs NumPy 2, which langchain 0.3 forbids; without the pin the app crashed at import in testing).
- The hosted app must not offer simulated output: Mock mode stays behind `ENABLE_MOCK=1`. Client IP = LAST `X-Forwarded-For` entry. Never log API keys.
- LangSmith: set `LANGSMITH_API_KEY` and `start.sh` turns tracing on; project `aetherfit-demo`.

## Deploy facts
- Space `aetherfit-ai` (Docker, `app_port: 7860`). Secrets: `ENCRYPTION_KEY` (64 hex), `FREEAPI_CONFIG_JSON`, `LANGSMITH_API_KEY`, `UPSTASH_REDIS_REST_URL/TOKEN`; optional `RL_PER_IP_DAILY`, `RL_GLOBAL_DAILY`. The Space clones branch `demo-ready`.
- Steps: `hf auth login`, create the Space from `deploy/space/` (Docker SDK), set the secrets, wait for the build, open the Space URL.

## Status
Verified: 8 tests pass (real workflow, real ML models). NOT verified: Space Docker build, real provider calls, Streamlit behind the Spaces iframe/proxy (start.sh disables CORS/XSRF checks for it), live LangSmith traces.
