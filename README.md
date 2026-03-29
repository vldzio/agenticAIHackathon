# AetherFit AI

This app is configured for public demo use with two runtime modes:

- `Mock Demo` is the default and does not require any API key.
- `Use My Gemini API Key` lets a visitor run live Gemini-backed generation with their own key.

Deployment notes:

- Do not configure a shared `GEMINI_API_KEY` for the hosted app.
- User-provided Gemini keys are stored only in Streamlit session state for the active session.
- User-provided keys are not persisted to disk, `.env`, downloads, or repo-tracked files.
