import logging
import subprocess
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import AsyncSessionLocal
from app.routers import auth, health, media, questions, results, sessions, tests, users

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
)
logger = logging.getLogger("quizbee")

app = FastAPI(
    title="Quizbee API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000)
    logger.info(
        '{"method": "%s", "path": "%s", "status": %d, "duration_ms": %d}',
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


api_v1 = FastAPI(title="Quizbee API v1")
api_v1.include_router(health.router, tags=["health"])
api_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1.include_router(users.router, prefix="/users", tags=["users"])
api_v1.include_router(questions.router, prefix="/questions", tags=["questions"])
api_v1.include_router(tests.router, prefix="/tests", tags=["tests"])
api_v1.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_v1.include_router(results.router, prefix="/results", tags=["results"])
api_v1.include_router(media.router, prefix="/media", tags=["media"])

app.mount("/api/v1", api_v1)


@app.on_event("startup")
async def startup():
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True, cwd="/app", capture_output=True)
        logger.info("Migrations applied")
    except Exception as e:
        logger.warning("Migration warning: %s", e)

    async with AsyncSessionLocal() as db:
        from app.seed import seed_admin
        await seed_admin(db)
