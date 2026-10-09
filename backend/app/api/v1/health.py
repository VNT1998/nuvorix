import datetime

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.telemetry import get_metrics_payload
from backend.app.db.session import get_db
from backend.app.schemas.domain import HealthResponse, ReadyResponse

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e!s}"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version=settings.VERSION,
        database=db_status,
        timestamp=datetime.datetime.now(datetime.UTC),
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    import os

    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    storage_ok = os.path.exists(settings.ARTIFACT_STORE_PATH) and os.access(
        settings.ARTIFACT_STORE_PATH, os.W_OK
    )

    is_ready = db_ok and storage_ok

    return ReadyResponse(
        ready=is_ready,
        dependencies={
            "database": "connected" if db_ok else "disconnected",
            "artifact_store": "ready" if storage_ok else "unreachable_or_readonly",
            "telemetry": "active",
        },
    )


@router.get("/metrics")
async def metrics():
    content = get_metrics_payload()
    return Response(content=content, media_type=CONTENT_TYPE_LATEST)


@router.get("/telemetry/traces")
async def get_telemetry_traces():
    """Retrieve live distributed trace spans recorded by OpenTelemetry."""
    from backend.app.core.telemetry import get_recent_spans

    return {"spans": get_recent_spans(), "count": len(get_recent_spans())}
