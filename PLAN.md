# AetherFit AI — Plan to a Fully Functional Application

_Based on a code review plus a hands-on run of the repo (fresh venv, Mock mode, Streamlit AppTest, model evaluation, and the training pipeline in a scratch copy)._

## 1. Where the project stands

**What works today**
- `streamlit run main.py` boots. In Mock mode the 7-node LangGraph pipeline runs end to end and fills all four tabs.
- The bundled models load. Evaluation on the bundled CSVs gives ~98.1% accuracy for fitness level and ~74.6% for injury risk.
- The Dockerfile and devcontainer exist, and the code layout is clean (`agents/` for logic, `nodes/` for graph adapters, `ml/` for training).

**What is not yet a "real" application** (verified findings, highest impact first)

| # | Finding | Evidence | Severity |
|---|---|---|---|
| 1 | **Invalid input crashes the graph.** The form parser flags errors but the graph has no conditional edge, so the flow continues. With `age=5` the run dies with `INVALID_CONCURRENT_GRAPH_UPDATE` on `error_messages`. | Reproduced | Critical |
| 2 | **The same crash happens if any parallel branch fails.** `error_messages` (and the other list fields) have no reducer, so two parallel nodes writing it in one step fails. Real Gemini failures will hit this too. | Reproduced; see `state.py` | Critical |
| 3 | **Race condition between the two ML branches.** `injury_assessor` runs in parallel with `fitness_scorer` but reads `fitness_level_class` from state, and `Fitness_Level` is a model feature. It silently falls back to `"Beginner"`, so injury predictions are wrong or non-deterministic. | `nodes/injury_assessor_node.py` | Critical |
| 4 | **Errors are swallowed and shown as success.** Nodes return fake defaults (`"Beginner"`, `"Low Risk"`, 0.0 confidence) on failure. `graph.py` hardcodes `parsing_complete: True` and `error: False`, and the UI still says "Assessment generated". | `nodes/*`, `graph.py` | High |
| 5 | **Mock mode ignores the user's input.** The mock is keyed on words in the prompt and returns fixed JSON: always "Beginner / 4 h" and always Mon/Wed workouts. Reported frequency is 3 but only 2 days are scheduled. Mock demos are therefore not representative. | `utils/gemini_client.py` | High |
| 6 | **The live Gemini path is untested.** There are no tests and no retries, timeouts or rate-limit handling. Schema validation checks only top-level keys. The normalizer prompt asks for `"condtions"` (typo) while the mock uses `"conditions"`. `google-generativeai` is deprecated in favour of `google-genai`. | Review | High |
| 7 | **Health-safety data is collected but never used.** `normalized_health_conditions` (limitations, `cleared_for_exercise`, severity) is never passed to the workout, nutrition or recovery planners. Someone with "severe" conditions still gets a normal plan and no medical disclaimer or block. | Review | High |
| 8 | **Train/serve skew in the injury model.** `Flexibility_Score`, `Strength_Imbalance_Score`, `Training_Frequency_Hours` and `Previous_Injury` are not asked of the user. They are guessed from experience level via hard-coded lookups, or from a substring search for "injury". Reported accuracy therefore does not describe what users get. | `agents/injury_assessor_ml.py` | High |
| 9 | **Fitness-model sanity.** A default "Beginner, 4 h/week" profile is classified as **Athlete** (85% confidence). The labels look synthetic and only weakly related to experience: in the training CSV, about 1/3 of "Never Exercised" rows are not Beginner and "Advanced" experience is labelled Athlete only about 55% of the time. This needs a data-provenance review and a rule-based sanity guardrail. | Reproduced | High |
| 10 | **Broken cleaning code.** In `clean_injury_data.py` the filtering block and `return` are indented inside the `for col in numeric_cols` loop, so only the first column (Age) is filtered and the function returns after one iteration. Also `fillna(inplace=True)` on a column slice is deprecated. | Code review | High |
| 11 | **Training pipeline is broken.** `run_training_pipeline` fails with `FileNotFoundError` because `eval_dir` points at `data/` instead of `data/evaluation_dataset/` (the README admits this). `max_features=1000` on a 12-feature RandomForest is invalid. `__main__` blocks in the trainers use fragile relative paths. | Reproduced | Medium |
| 12 | **Environment reproducibility.** The pickles were written with scikit-learn 1.8.0, but `requirements.txt` has `scikit-learn>=1.3`. A fresh install gets 1.9.1 and emits `InconsistentVersionWarning` on every load, with no guarantee of correctness. Models are also reloaded from disk on every node call. There are also 78 committed `__pycache__/*.pyc` files. | Reproduced; `git ls-files` | Medium |
| 13 | **Dependency bloat and drift.** `langchain`, `langchain-community`, `langchain-google-genai`, `pydantic-settings`, `loguru`, `rouge-score`, `python-dotenv`, `email-validator`, `requests`, `scipy` and `importlib-metadata` are never imported. `langgraph==0.2.50` is old and `pytest` is a runtime dependency. | `grep` | Medium |
| 14 | **Not yet a product.** There is no persistence (plans vanish on refresh), no user accounts or history, no progress tracking, no backend API, no tests or CI, and no logging or monitoring. The UI is raw `st.write` dumps of dicts. | Review | Product gap |

## 2. Target definition ("fully functional")

A user can:
1. Enter a profile, or return to a saved one.
2. Get a **validated, safe, personalized** assessment plus workout, nutrition and recovery plan. This works in Mock or Live Gemini mode and fails gracefully on any error.
3. **Save, revisit, compare and export** plans (PDF and JSON), and **log workouts** against the plan.

A developer can clone, run one command, run tests in CI, retrain models reproducibly, and deploy with Docker.

**Decisions (confirmed):** the app becomes a **FastAPI backend plus a separate frontend**, and Live mode stays **bring-your-own-key (BYOK)**. See "Architecture decisions" below; Phase 4 is written for this architecture.

## Architecture decisions
- **Backend:** FastAPI, Pydantic v2 schemas, the existing LangGraph pipeline behind a service layer. Endpoints: `POST /api/assessments` (optionally streamed via SSE per graph node), `GET /api/assessments/{id}`, `GET /api/models/evaluation`, `GET /api/health`. OpenAPI docs come free and the frontend gets generated types.
- **Frontend:** separate app (proposed: React + Vite + TypeScript + Tailwind) that talks only to the API. Streamlit is retired once the new UI reaches parity.
- **BYOK:** the user's Gemini key is sent per request in an `X-Gemini-Api-Key` header over HTTPS. The server keeps it in memory for that request only. It is never persisted or logged, and is redacted from logs and error messages. The frontend keeps it in `sessionStorage` (or memory only), never in the database. Mock mode needs no key. Add CORS allow-listing, per-IP rate limiting and request-size limits.
- **Persistence:** SQLite for plans and workout logs (Postgres-ready via SQLAlchemy). No API keys in the DB.
- **Deploy:** two containers (`api`, `web`) via `docker-compose`, with a reverse proxy in production.

## 3. Phased plan

### Phase 0 — Hygiene and reproducibility (½ day)
- Remove tracked `__pycache__/` and `*.pyc` (`git rm -r --cached`). `.gitignore` already covers them.
- Pin exact versions in `requirements.txt` (`scikit-learn==1.8.0` to match the pickles, or retrain and re-pin). Move `pytest`, `ruff` and `mypy` to `requirements-dev.txt`. Drop unused packages (item 13). Standardise on Python 3.12 (Dockerfile) and update the devcontainer, which uses 3.11.
- Add `pyproject.toml` (ruff config, pytest config), a `Makefile` (`run`, `test`, `lint`, `train`, `docker`) and a `.env.example`.
- Load model artifacts once (`functools.lru_cache` or a `ModelRegistry`) instead of unpickling on every node call. Add a model-metadata file (sklearn version, training date, data hash, metrics) and check it at load time.

### Phase 1 — Make the pipeline correct and robust (1–2 days) *(fixes 1–4, 7)*
1. **State:** add `Annotated[List[str], operator.add]` reducers for `error_messages` and other list fields written by parallel nodes. Add a typed `warnings` field.
2. **Graph topology:** the fitness model must run before the injury model, so make it `normalizer → fitness_scorer → injury_assessor → workout_planner` (or pass the fitness class explicitly). This removes the race. Add a **conditional edge after `form_parser`** that routes to a terminal `validation_failed` node when `error_occurred` is set.
3. **Honest failures:** nodes raise or return `*_complete=False` plus a structured error, with no fake "Beginner / Low Risk" defaults. `assess_fitness` builds `error` and `parsing_complete` from real state. The UI shows partial results with per-section "couldn't generate, retry" banners.
4. **Pydantic models** for the input profile and for each LLM response (`WorkoutPlan`, `NutritionPlan`, `RecoveryPlan`, `NormalizedInputs`), used for validation and coercion instead of top-level key checks. Allow one automatic repair or retry on schema failure.
5. **Safety layer:**
   - Feed `normalized_health_conditions` (limitations, severity, `cleared_for_exercise`) into all three planners.
   - Add a rules-based guardrail node. If `cleared_for_exercise` is false, severity is severe, age is over 60 with cardiac-type keywords, or BMI is extreme, then require a "consult a clinician first" gate and generate only a light or conservative plan.
   - Add a visible disclaimer, and always enforce the calorie floor (already 1200) with sex-specific minimums.
   - Verify that the schedule matches `frequency_per_week` (the mock currently violates this).

### Phase 2 — LLM layer (1–2 days) *(fixes 5, 6)*
- Migrate to the supported `google-genai` SDK. Add timeouts, exponential-backoff retries, 429 handling, token and cost logging, a configurable model, and safe error messages (never echo the API key). Try Gemini `response_schema` / structured output where available.
- Fix the prompt typo (`condtions` → `conditions`) and make prompts return exactly the Pydantic schema. Move prompts out of the agent files into `prompts/` templates.
- Rewrite `MockGeminiClient` to be **input-aware and deterministic**. It should derive experience, years and hours from the text with simple regex, honour `frequency_per_week`, and vary plans by goal and fitness level. It must stay clearly labelled "simulated" in the UI. This also makes it the test double.
- Add an opt-in "sanity" test against real Gemini (marked `@pytest.mark.live`, skipped without `GEMINI_API_KEY`).

### Phase 3 — ML quality and retraining (2–3 days) *(fixes 8–12)*
1. **Fix `clean_injury_data.py`** (dedent the filters and return out of the loop, and clip outliers correctly). Fix `clean_fitness_data.py` if it has the same pattern. Also fix the unused `fillna(inplace=True)`.
2. **Fix the training pipeline:** correct `eval_dir`, remove `max_features=1000` (use `"sqrt"`), replace relative-path `__main__` blocks with a single CLI (`python -m ml.train_pipeline --seed 42`), and write a metrics JSON plus model card into `ml/models/`.
3. **Close the train/serve gap for injury risk** (choose one):
   - (a) Ask users the missing questions (previous injury, flexibility self-test, training days per week) and use the real features, or
   - (b) Retrain using only features the app can actually observe.

   Then report the accuracy of the model as deployed. Add a leakage check: verify `Overtraining_Risk_Score` and `Activity_Score` are not label proxies.
4. **Investigate the fitness labels** (item 9). Document data provenance. If the data is synthetic, say so in the UI and README. Add cross-validation, calibration (`CalibratedClassifierCV`), a fitness-model check against a hand-written set of persona test cases, and a sanity guardrail (e.g. "Never Exercised" cannot be classified Athlete).
5. **Serialization:** switch to `joblib` with pinned versions, or export to ONNX / skops to avoid the pickle-trust caveat. Add a `make train` step in CI that checks the model still meets a minimum-metric threshold.
6. **Explainability:** surface the top feature contributions (SHAP or `feature_importances_`) instead of the four hard-coded "risk factors".

### Phase 4 — API and frontend (1–2 weeks)
- **Backend package layout:** `backend/app/{api,services,schemas,graph,ml,db}`. `services/assessment_service.py` owns profile → plan and is the only thing routes call.
- **API:** routes listed in "Architecture decisions", plus versioned `/api/v1`, typed error responses (`{code, message, field_errors}`), request IDs, and a BYOK dependency that validates the key format and maps Gemini auth/quota errors to clear 401/429 responses.
- **Persistence:** SQLAlchemy models `assessments`, `workout_logs` (and `users` if auth is added). Anonymous device-scoped IDs first; real auth (OAuth or email link) later.
- **Frontend pages:** Assess (form with inline validation, Mock/BYOK toggle with a "simulated" badge, per-node progress), Results (overview with risk gauge and confidence bars, workout per-day tables and weekly calendar, nutrition macro charts, recovery), My Plans, Progress, Model Info (evaluation and provenance).
- **Export:** PDF and JSON from the API, plus an iCal schedule.
- **Progress tracking:** log sessions, weight and adherence. "Re-plan" regenerates the next block using logged history, with a deload trigger.
- **Contract:** the frontend uses types generated from the OpenAPI schema, so the two sides cannot silently drift.

### Phase 5 — Quality, CI and deployment (1–2 days)
- **Tests** (`tests/`), with mock-mode as the default double:
  - Unit: form parser boundaries, BMI and calorie maths, macro totals, JSON extraction, guardrail rules.
  - Graph: invalid input short-circuits, a failing node yields partial results and no concurrent-update error, injury runs after fitness.
  - ML: artifacts load, `predict` returns valid classes, metrics ≥ threshold, persona cases behave sensibly.
  - UI: `streamlit.testing.v1.AppTest` smoke test for generate, error and export flows.
  - Contract: Pydantic schemas against recorded sample Gemini responses.
- **CI (GitHub Actions):** ruff, mypy (lenient), pytest with coverage, Docker build, and a nightly optional live-Gemini test.
- **Docker:** multi-stage build, non-root user, `HEALTHCHECK` against `/_stcore/health`, `.dockerignore` covering `data/` (or a mounted volume), `docker-compose.yml` with a volume for SQLite. Rename `dockerfile` → `Dockerfile`.
- **Observability:** structured logging (use stdlib or loguru consistently), a per-run trace id (`plan_id`), and an error-reporting hook.
- **Docs:** update the README (stop claiming things the code doesn't do), and add an architecture diagram, model card and `CONTRIBUTING.md`.
- **Deploy** to Streamlit Community Cloud, Hugging Face Spaces or Cloud Run. Add rate limiting or a per-session request cap when using a shared key. Keep the current BYOK design.

## 4. Suggested order and milestones

| Milestone | Contents | Exit criteria |
|---|---|---|
| **M1 – Stable core** | Phases 0 + 1 | No crash on any input or node failure; injury/fitness ordering fixed; the 4 core graph tests pass |
| **M2 – Trustworthy AI** | Phases 2 + 3 | Live Gemini works with retries and schema validation; retraining runs from one command; deployed-feature metrics documented |
| **M3 – Usable product** | Phase 4 | FastAPI + separate frontend: save, view, export and track plans |
| **M4 – Shippable** | Phase 5 | CI green; Docker image healthy; README accurate; deployed demo |

**Quick wins to do first (about 2–3 hours, highest payoff):** items 1, 2, 3, 4 (state reducers, conditional edge, ordering, honest errors), the `clean_injury_data` indentation bug, the `eval_dir` typo, pinning scikit-learn, and untracking `__pycache__`.

## 5. Risks and open questions
- **Data provenance:** are the CSVs synthetic? If yes, the accuracy numbers are not real-world validity. Say so, and avoid presenting the output as clinical screening.
- **Medical liability:** injury-risk and nutrition advice needs guardrails and disclaimers (Phase 1.5) before any public deployment.
- **Frontend stack:** React + Vite + TypeScript is proposed. Say so if you prefer another framework.
- **Auth:** BYOK is decided. Still open: anonymous device-scoped plans vs real user accounts.
- **Retrain vs pin:** retrain on scikit-learn 1.9 (cleaner long-term, and needed anyway after the Phase 3 data fixes) vs pin 1.8.0 (fastest).
