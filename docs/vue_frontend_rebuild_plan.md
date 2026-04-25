# Vue Frontend Rebuild Plan

> For Hermes: use this as the migration baseline when replacing the Streamlit UI with a real frontend + API split.

Goal: replace the blocking Streamlit console with a Vue single-page app and a FastAPI backend that exposes explicit task, log, settings, curriculum and publishing endpoints.

Architecture:
- Keep the existing Python learning/publishing agents as the domain layer.
- Add a thin FastAPI API layer in `src/webapi/` so long-running work is triggered as background tasks instead of blocking page rendering.
- Add a Vue/Vite frontend in `frontend/` focused on observability: log viewer, task queue, curriculum control, materials browsing, settings editing and publish triggers.

Tech stack:
- Backend: FastAPI + uvicorn
- Frontend: Vue 3 + vue-router + Vite
- Existing domain layer: `src/student/*`, `src/publisher_v2/*`, `src/core/*`

## Implemented in this iteration

1. `src/webapi/app.py`
   - REST endpoints for curriculum, study, publish, logs, settings, tasks, materials and knowledge base.
2. `src/webapi/task_runtime.py`
   - in-process background task registry for long-running jobs.
3. `src/webapi/services.py`
   - wrappers around existing agents and storage.
4. `run_api.py`
   - uvicorn entrypoint.
5. `frontend/`
   - Vue SPA with pages for Dashboard / Study / Materials / Publish / Logs / Settings.
6. `requirements.txt`
   - added FastAPI and uvicorn.

## Why this is better than Streamlit here

- Logs are explicit API data, not hidden in server stdout.
- Long tasks are visible in a task panel instead of freezing one request.
- Frontend state is separate from backend execution state.
- The UI can evolve independently from agent orchestration.

## Current limitations

- Background tasks are process-local; restarting the API server loses in-memory task registry entries.
- There is no persistent queue yet.
- The new frontend currently targets functional control/visibility first, not polished visual design.
- Streamlit is still present in the repo for backward compatibility, but the new API + Vue stack is the preferred direction.

## Next recommended steps

1. Add persistent task storage (`data/tasks/*.json` or SQLite) so restart recovery is possible.
2. Add SSE/WebSocket streaming for live log/task updates.
3. Move business logic currently embedded in `app.py` into reusable service modules so the Streamlit file can be retired entirely.
4. Add auth if the app will be exposed beyond localhost.
5. Add frontend build integration and static serving from FastAPI for one-command startup.

## Run locally

Backend:
```bash
pip install -r requirements.txt
python run_api.py
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

API default: `http://127.0.0.1:8000`
Frontend default: `http://127.0.0.1:5173`
