from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import actors, artifacts, big_bangs, case_studies, emotion_observability, frontend, god_agent, graphs, initialization, jobs, multiverses, sample, scenario_bank, settings, sociology, ticks, workspace
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import engine

settings_obj = get_settings()
app = FastAPI(title=settings_obj.app_name)
repo_root = Path(__file__).resolve().parents[2]
frontend_root = repo_root / "frontend"
frontend_dist_root = frontend_root / "dist"
frontend_assets_root = frontend_dist_root / "assets"
frontend_public_root = frontend_root / "public"

if settings_obj.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings_obj.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
def startup() -> None:
    if settings_obj.auto_create_tables:
        Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


def _frontend_index_response():
    index_path = frontend_dist_root / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"status": "frontend not built", "dev": "cd frontend && npm install && npm run dev", "build": "cd frontend && npm run build"}


@app.get("/")
def frontend_index():
    return _frontend_index_response()


@app.get("/big-bangs", include_in_schema=False)
@app.get("/big-bangs/new", include_in_schema=False)
@app.get("/workspace/{big_bang_id}", include_in_schema=False)
@app.get("/reports", include_in_schema=False)
@app.get("/reports/report/{report_id}", include_in_schema=False)
@app.get("/reports/version/{report_version_id}", include_in_schema=False)
@app.get("/jobs", include_in_schema=False)
@app.get("/settings", include_in_schema=False)
def frontend_spa_route():
    return _frontend_index_response()


prefix = settings_obj.api_prefix
app.include_router(big_bangs.router, prefix=prefix)
app.include_router(frontend.router, prefix=prefix)
app.include_router(workspace.router, prefix=prefix)
app.include_router(multiverses.router, prefix=prefix)
app.include_router(ticks.router, prefix=prefix)
app.include_router(actors.router, prefix=prefix)
app.include_router(graphs.router, prefix=prefix)
app.include_router(emotion_observability.router, prefix=prefix)
app.include_router(sociology.router, prefix=prefix)
app.include_router(god_agent.router, prefix=prefix)
app.include_router(settings.router, prefix=prefix)
app.include_router(jobs.router, prefix=prefix)
app.include_router(artifacts.router, prefix=prefix)
app.include_router(sample.router, prefix=prefix)
app.include_router(initialization.router, prefix=prefix)
app.include_router(case_studies.router, prefix=prefix)
app.include_router(scenario_bank.router, prefix=prefix)

if frontend_assets_root.exists():
    app.mount("/assets", StaticFiles(directory=frontend_assets_root), name="assets")
if frontend_public_root.exists():
    app.mount("/static", StaticFiles(directory=frontend_public_root), name="static")
