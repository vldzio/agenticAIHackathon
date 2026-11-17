#!/bin/sh
# Render web service: private FreeLLMAPI gateway (127.0.0.1:3001) + public Streamlit on $PORT.
set -e
( cd /app && HOST=127.0.0.1 PORT=3001 exec node server/dist/index.js ) &
if [ -n "$LANGSMITH_API_KEY" ]; then export LANGSMITH_TRACING=true; fi
cd /srv/app
exec /opt/venv/bin/python -m streamlit run main.py \
  --server.port "${PORT:-10000}" --server.address 0.0.0.0 --server.headless true \
  --browser.gatherUsageStats false
