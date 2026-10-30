from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.ml import router as ml_router
from app.api.routes.rca import router as rca_router
from app.api.routes.services import router as services_router
from app.api.routes.settings import router as settings_router
from app.api.routes.telemetry import logs_router, metrics_router
from app.core.config import settings


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


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.APP_NAME, "docs": "/docs", "status": "ok"}
