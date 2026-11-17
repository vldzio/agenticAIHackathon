#!/bin/sh
# Starts the private gateway, then the public Streamlit app. Runs as the unprivileged `node` user.
set -e

# Gateway: localhost only. Provider keys / admin account come from FREEAPI_CONFIG_JSON (Space secret).
( cd /app && HOST=127.0.0.1 PORT=3001 exec node server/dist/index.js ) &

# LangSmith: trace LangGraph runs automatically once a key is configured.
if [ -n "$LANGSMITH_API_KEY" ]; then export LANGSMITH_TRACING=true; fi

# Streamlit: public port 7860. CORS/XSRF are relaxed because Spaces embed the app in an iframe.
cd /srv/app
exec /opt/venv/bin/python -m streamlit run main.py \
  --server.port 7860 --server.address 0.0.0.0 --server.headless true \
  --server.enableCORS false --server.enableXsrfProtection false --browser.gatherUsageStats false
