---
title: AetherFit AI
emoji: 🏋️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: Fitness planning with ML classifiers and a LangGraph agent workflow
---

# AetherFit AI (Hugging Face Space)

Streamlit app: pretrained scikit-learn classifiers + a seven-node LangGraph workflow whose LLM steps run
live through a **private** [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) gateway in the same
container. Every run is traced to LangSmith project `aetherfit-demo`.
Source: <https://github.com/vldzio/agenticAIHackathon>.

## Space secrets (Settings → Variables and secrets)

| Name | Value |
| --- | --- |
| `ENCRYPTION_KEY` | 64 hex chars (`openssl rand -hex 32`); required by the gateway |
| `FREEAPI_CONFIG_JSON` | gateway config with your free-tier provider keys, see `freellmapi.config.example.json` |
| `LANGSMITH_API_KEY` | LangSmith key (tracing switches on automatically) |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | per-IP and global daily limits |
| `RL_PER_IP_DAILY` / `RL_GLOBAL_DAILY` | optional, default 20 / 1000 credits per UTC day (one assessment = 4 credits) |
