import datetime

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.core.telemetry import get_metrics_payload
from apps.api.app.db.session import get_db
from apps.api.app.schemas.domain import HealthResponse, ReadyResponse

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
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return ReadyResponse(
        ready=db_ok,
        dependencies={
            "database": "connected" if db_ok else "disconnected",
            "artifact_store": "ready",
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
    from apps.api.app.core.telemetry import get_recent_spans
    return {"spans": get_recent_spans(), "count": len(get_recent_spans())}

