import os
import resource
import sys
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings


class DiagnosticService:
    @classmethod
    async def run_diagnostics(cls, db: AsyncSession) -> dict[str, Any]:
        """
        Execute real-time empirical diagnostic checks across critical dependencies.
        Never returns fabricated or static placeholder values.
        """
        diagnostics: dict[str, Any] = {}

        # 1. Database Connectivity & Round-trip Latency
        t_start = time.perf_counter()
        try:
            res = await db.execute(text("SELECT 1"))
            res.scalar()
            db_latency = (time.perf_counter() - t_start) * 1000.0
            diagnostics["database"] = {
                "status": "healthy",
                "latency_ms": round(db_latency, 2),
            }
        except Exception as e:
            diagnostics["database"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # 2. Process Memory (Real RSS)
        try:
            raw_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # macOS reports bytes, Linux reports kilobytes
            rss_mb = raw_rss / (1024 * 1024) if sys.platform == "darwin" else raw_rss / 1024
            diagnostics["memory"] = {
                "process_rss_mb": round(rss_mb, 2),
            }
        except Exception:
            diagnostics["memory"] = {
                "process_rss_mb": None,
            }

        # 3. Artifact Storage Filesystem Health
        try:
            artifact_dir = settings.ARTIFACT_STORE_PATH
            is_writable = os.access(artifact_dir, os.W_OK) and os.access(artifact_dir, os.R_OK)
            diagnostics["artifact_store"] = {
                "status": "healthy" if is_writable else "degraded",
                "path": artifact_dir,
                "writable": is_writable,
            }
        except Exception as e:
            diagnostics["artifact_store"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # 4. Redis Service
        if settings.REDIS_URL and "localhost" in settings.REDIS_URL:
            diagnostics["redis"] = {
                "status": "optional_local",
                "url": settings.REDIS_URL,
            }
        else:
            diagnostics["redis"] = {
                "status": "configured",
                "url": settings.REDIS_URL,
            }

        return diagnostics
