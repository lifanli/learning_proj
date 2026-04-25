# Learning Code Project

Learning Code Project is a local-first AI learning workspace for building a personal knowledge base from a learning goal. It connects curriculum planning, source collection, material analysis, knowledge-base browsing, long-form publishing, and background task tracking into one runnable project.

## Features

- Curriculum generation: create a structured learning plan from a goal, then approve it before execution.
- Automated study workflow: collect and analyze web pages, GitHub repositories, ArXiv papers, and course pages.
- Knowledge-base browser: view local Markdown knowledge-base folders and files from the web UI.
- Publishing workflow: generate chapters, sections, and quality reports from collected materials.
- Background tasks: track progress, retry failures, cancel cooperative long-running tasks, and inspect task details.
- Integrated web app: FastAPI backend with a Vue/Vite frontend.

## Tech Stack

- Backend: Python, FastAPI, Pydantic, PyYAML
- Frontend: Vue 3, Vite
- LLM: OpenAI-compatible APIs, including DashScope/Qwen-compatible endpoints
- Storage: local files, Markdown, SQLite, and JSON runtime state

## Requirements

- Python 3.11 or newer is recommended.
- Node.js 18 or newer is recommended for building the frontend.
- An OpenAI-compatible API key if you want to run LLM-backed workflows.

Create and activate your own Python environment with your preferred tool, then install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Install and build the frontend:

```bash
cd frontend
npm install
npm run build
cd ..
```

Create a local environment file for secrets:

```bash
cp .env.example .env
```

Set `DASHSCOPE_API_KEY` or the environment variable referenced by `llm.api_key_env` in `config/settings.yaml`. Do not commit real API keys.

## Run

Start the integrated API and web frontend with Python:

```bash
python run_api.py
```

Open:

```text
http://localhost:8000
```

By default the service listens on `127.0.0.1`. If you intentionally need LAN access, set `STUDY_PROJ_HOST=0.0.0.0` before starting the app.

## Configuration

Main configuration lives in `config/settings.yaml`.

- `llm.api_key_env` names the environment variable used for the LLM API key.
- `llm.base_url` points to the OpenAI-compatible API endpoint.
- `models.fast`, `models.deep`, and `models.vision` select model names used by different workflows.
- API keys should stay in local environment variables or `.env`, not in committed YAML files.

## Tests

Run the backend test suite:

```bash
python -m pytest -q
```

The live LLM smoke test is skipped by default. Run it only when you explicitly want to make a real API call:

```bash
RUN_LIVE_LLM_TEST=1 python -m pytest tests/test_llm.py -q
```

On Windows PowerShell:

```powershell
$env:RUN_LIVE_LLM_TEST="1"
python -m pytest tests/test_llm.py -q
```

## Repository Hygiene

The repository intentionally ignores local runtime data and personal outputs:

- `.env` and other local secret files
- logs and task runtime state
- collected materials and generated knowledge-base content
- frontend build output
- local notes and process documents

Only `README.md` is tracked as public-facing Markdown documentation.

## Branches

- `main`: public-facing stable branch with a clear project README.
- `study-proj-current`: development branch for ongoing code history.

## Security Notes

- `/api/settings` is restricted to localhost and does not return or persist plaintext secrets.
- `/api/system/state` returns redacted diagnostic settings.
- Log and knowledge-base file reads validate path containment to prevent traversal.
- Task lists return compact error summaries; full tracebacks are available only in task detail responses.
