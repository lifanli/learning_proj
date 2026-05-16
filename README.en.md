# AI Learning and Knowledge Base Publishing System

[中文](README.md) | Default language: Chinese

This project is a local AI workspace for personal learning and technical knowledge building. It collects material from courses, webpages, GitHub, ArXiv, WeChat articles, and other sources, stores the processed material locally, then generates structured Markdown knowledge-base books from that material.

Current development branch: `study-proj-current`

## Core Capabilities

- Curriculum generation: create domains, topics, search queries, and recommended sources from a learning goal.
- Automated study: process a curriculum or manually submitted topics and URLs.
- Material store: persist full text, images, code blocks, tags, terms, references, and metadata with SQLite plus filesystem storage.
- Automated publishing: retrieve material, plan book chapters, write sections, and assemble Markdown books.
- Web console: manage study tasks, publishing, materials, logs, settings, and generated knowledge files through FastAPI + Vue.
- Background tasks: track progress, inspect results, cancel, retry, and preserve task history.
- OpenAI-compatible models: Xiaomi MiMo is the default provider, with presets for custom OpenAI-compatible endpoints, DashScope/Qwen, and Anthropic Claude.

## Project Layout

```text
.
├── config/                 # Settings, curriculum, and curated source registry
├── frontend/               # Vue web console
├── src/
│   ├── core/               # LLM client, task DAG engine, material store
│   ├── student/            # Student agent: search, fetch, translate, tag, enrich
│   ├── publisher_v2/       # Publisher agent: outline, write, review, assemble
│   ├── researchers/        # ArXiv, WeChat, and document researchers
│   ├── tools/              # Web, search, PDF, GitHub, and utility tools
│   └── webapi/             # FastAPI service and background task runtime
├── tests/                  # Unit, integration, and smoke tests
├── data/                   # Local runtime data; only .gitkeep is tracked
└── knowledge_base/         # Generated books; only .gitkeep is tracked
```

## Quick Start

### 1. Prepare the Environment

The existing scripts assume a Conda environment named `study-proj`:

```powershell
conda create -n study-proj python=3.11
conda activate study-proj
python -m pip install -r requirements.txt
```

Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

### 2. Configure the API Key

The default provider is Xiaomi MiMo through its OpenAI-compatible endpoint:

```text
https://token-plan-cn.xiaomimimo.com/v1
```

Create a local `.env` file:

```powershell
Copy-Item .env.example .env
notepad .env
```

The file should contain:

```text
XIAOMI_MIMO_API_KEY=your_api_key_here
```

Do not put real secrets in `config/settings.yaml`, and do not commit `.env`.

### 3. Start the App

Build the frontend and start the integrated service:

```powershell
.\start.bat
```

Default URL:

```text
http://localhost:8000
```

API-only startup:

```powershell
python run_api.py
```

## Common Commands

Run backend tests:

```powershell
python -m pytest -q
```

Run the live LLM smoke test:

```powershell
$env:RUN_LIVE_LLM_TEST="1"
python -m pytest tests/test_llm.py -q
```

Run the standalone OpenAI-compatible smoke script:

```powershell
python test-openai.py
```

Build the frontend:

```powershell
cd frontend
npm run build
```

## Local Data and Git Rules

The following files are intentionally not committed:

- `.env` and local secret files
- databases, logs, PDFs, task history, and material store files under `data/`
- generated books, Markdown files, and archives under `knowledge_base/`
- frontend build output under `frontend/dist/`
- local notes, process documents, and temporary tool state

The repository should contain source code, configuration templates, tests, and minimal directory placeholders only.

## Main Workflow

1. Enter a learning goal in the Study page and generate a curriculum.
2. Review and approve the curriculum, then start automated study.
3. Inspect collected material in the Materials page.
4. Submit a publishing topic to generate a Markdown knowledge-base book.
5. Preview generated files in the Knowledge Base page.

## Notes

- Long-running tasks call external model and data-source APIs, which may incur cost or hit rate limits.
- ArXiv, GitHub, and web search failures are handled with best-effort fallbacks where possible.
- The default setup is intended for local single-user usage; settings APIs are restricted to local clients.
- Generated knowledge-base content is runtime output, not repository source.
