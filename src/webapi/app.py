from __future__ import annotations

from ipaddress import ip_address
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .services import (
    approve_curriculum,
    generate_curriculum,
    get_curriculum,
    get_dashboard_summary,
    get_knowledge_tree,
    get_material,
    get_system_state,
    list_log_files,
    list_materials,
    load_settings_text,
    read_knowledge_file,
    read_log_file,
    run_auto_study,
    run_manual_study,
    run_publish,
    save_settings_text,
)
from .task_runtime import registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
LOCAL_CLIENT_HOSTS = {"localhost", "testclient"}


class CurriculumGenerateRequest(BaseModel):
    goal: str = Field(min_length=1)
    depth: str = Field(default="comprehensive")


class ManualStudyRequest(BaseModel):
    mode: str
    value: str
    max_pages: int = 50


class PublishRequest(BaseModel):
    topic: str
    parent_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class SettingsUpdateRequest(BaseModel):
    content: str


def _require_local_client(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host in LOCAL_CLIENT_HOSTS:
        return
    try:
        if ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise HTTPException(status_code=403, detail="Settings API is only available from localhost.")


def _mount_frontend(app: FastAPI) -> None:
    index_path = FRONTEND_DIST / "index.html"
    if not index_path.is_file():
        return

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_app(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")

        if full_path:
            dist_root = FRONTEND_DIST.resolve()
            target = (dist_root / full_path).resolve()
            try:
                target.relative_to(dist_root)
            except ValueError:
                raise HTTPException(status_code=404, detail="Frontend asset not found")
            if target.is_file():
                return FileResponse(target)

        return FileResponse(index_path)


def _register_task_handlers() -> None:
    registry.register("curriculum.generate", generate_curriculum)
    registry.register("curriculum.auto_study", run_auto_study)
    registry.register("study.manual", run_manual_study)
    registry.register("publish.book", run_publish)


def create_app() -> FastAPI:
    _register_task_handlers()
    app = FastAPI(title="study-proj API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/dashboard")
    def dashboard():
        return get_dashboard_summary()

    @app.get("/api/system/state")
    def system_state():
        return get_system_state()

    @app.get("/api/materials")
    def materials(source_type: Optional[str] = None, keyword: Optional[str] = None, limit: int = 100):
        return {"items": list_materials(source_type=source_type, keyword=keyword, limit=limit)}

    @app.get("/api/materials/{material_id}")
    def material_detail(material_id: str):
        material = get_material(material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        return material

    @app.get("/api/curriculum")
    def curriculum():
        data = get_curriculum()
        return {"curriculum": data}

    @app.post("/api/curriculum/generate")
    def curriculum_generate(payload: CurriculumGenerateRequest):
        task = registry.submit("curriculum.generate", generate_curriculum, payload.goal, payload.depth)
        return {"task": registry.to_dict(task)}

    @app.post("/api/curriculum/approve")
    def curriculum_approve():
        return {"curriculum": approve_curriculum()}

    @app.post("/api/curriculum/auto-study")
    def curriculum_auto_study():
        task = registry.submit("curriculum.auto_study", run_auto_study)
        return {"task": registry.to_dict(task)}

    @app.post("/api/study/manual")
    def manual_study(payload: ManualStudyRequest):
        task = registry.submit("study.manual", run_manual_study, payload.mode, payload.value, payload.max_pages)
        return {"task": registry.to_dict(task)}

    @app.post("/api/publish")
    def publish(payload: PublishRequest):
        task = registry.submit("publish.book", run_publish, payload.topic, payload.parent_id, payload.tags)
        return {"task": registry.to_dict(task)}

    @app.get("/api/logs")
    def logs():
        return {"files": list_log_files()}

    @app.get("/api/logs/{name}")
    def log_detail(name: str, limit: int = 300):
        try:
            return read_log_file(name, limit=limit)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Log file not found")

    @app.get("/api/settings")
    def settings(request: Request):
        _require_local_client(request)
        return {"content": load_settings_text()}

    @app.put("/api/settings")
    def settings_update(payload: SettingsUpdateRequest, request: Request):
        _require_local_client(request)
        try:
            parsed = save_settings_text(payload.content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"saved": True, "settings": parsed}

    @app.get("/api/tasks")
    def tasks():
        return {"items": registry.list()}

    @app.get("/api/tasks/{task_id}")
    def task_detail(task_id: str):
        task = registry.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return registry.to_dict(task)

    @app.post("/api/tasks/{task_id}/cancel")
    def task_cancel(task_id: str):
        task = registry.cancel(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"task": registry.to_dict(task)}

    @app.post("/api/tasks/{task_id}/retry")
    def task_retry(task_id: str):
        try:
            task = registry.retry(task_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Task not found")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return {"task": registry.to_dict(task)}

    @app.get("/api/knowledge-base")
    def knowledge_base():
        return {"items": get_knowledge_tree()}

    @app.get("/api/knowledge-base/file")
    def knowledge_file(path: str):
        try:
            return read_knowledge_file(path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Knowledge file not found")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    _mount_frontend(app)
    return app


app = create_app()
