from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.health import router as health_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.ml import router as ml_router
from app.api.routes.rca import router as rca_router
from app.api.routes.services import router as services_router
from app.api.routes.settings import router as settings_router
from app.api.routes.telemetry import logs_router, metrics_router
from app.core.config import PROJECT_ROOT, settings


app = FastAPI(
    title=settings.APP_NAME,
    description="AIOps service monitoring, anomaly detection, and incident analysis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(health_router)
app.include_router(services_router)
app.include_router(metrics_router)
app.include_router(logs_router)
app.include_router(ml_router)
app.include_router(rca_router)
app.include_router(incidents_router)
app.include_router(settings_router)
app.include_router(dashboard_router)

frontend_dist = PROJECT_ROOT / "frontend" / "dist"
frontend_assets = frontend_dist / "assets"
if frontend_assets.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="frontend-assets")


@app.get("/", response_model=None)
def root() -> FileResponse | dict[str, str]:
    index_file = frontend_dist / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {"name": settings.APP_NAME, "docs": "/docs", "status": "ok"}


@app.get("/{frontend_path:path}", include_in_schema=False)
def frontend_route(frontend_path: str) -> FileResponse:
    if not frontend_dist.is_dir() or frontend_path.startswith(
        ("api/", "health/", "docs", "redoc", "openapi.json")
    ):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(frontend_dist / "index.html")
