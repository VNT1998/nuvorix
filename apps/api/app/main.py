import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.api.v1.agents import router as agents_router
from apps.api.app.api.v1.audit import router as audit_router
from apps.api.app.api.v1.deployments import router as deployments_router
from apps.api.app.api.v1.evaluations import router as evaluations_router
from apps.api.app.api.v1.gateway import router as gateway_router
from apps.api.app.api.v1.health import router as health_router
from apps.api.app.api.v1.incidents import router as incidents_router
from apps.api.app.api.v1.knowledge import router as knowledge_router
from apps.api.app.api.v1.models import router as models_router
from apps.api.app.api.v1.projects import router as projects_router
from apps.api.app.api.v1.workloads import router as workloads_router
from apps.api.app.core.config import settings
from apps.api.app.core.telemetry import record_http_request
from apps.api.app.db.session import AsyncSessionLocal, init_db
from apps.api.app.seed import seed_demo_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    await init_db()
    # Seed initial demo data
    async with AsyncSessionLocal() as session:
        await seed_demo_data(session)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Nuvorix AI/ML Production Platform Control Plane API",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HTTP Request Metrics Middleware
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Avoid recording /metrics to avoid self-amplifying metrics
    if not request.url.path.startswith("/metrics"):
        record_http_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_sec=duration,
        )
    return response


# Mount Health & Telemetry Routes
app.include_router(health_router)

# Mount API v1 Routers
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(workloads_router, prefix=settings.API_V1_STR)
app.include_router(models_router, prefix=settings.API_V1_STR)
app.include_router(evaluations_router, prefix=settings.API_V1_STR)
app.include_router(deployments_router, prefix=settings.API_V1_STR)
app.include_router(knowledge_router, prefix=settings.API_V1_STR)
app.include_router(agents_router, prefix=settings.API_V1_STR)
app.include_router(gateway_router, prefix=settings.API_V1_STR)
app.include_router(incidents_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "platform": "Nuvorix AI/ML Production Platform",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_url": "/health",
        "api_v1_prefix": settings.API_V1_STR,
    }
