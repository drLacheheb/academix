from contextlib import asynccontextmanager
import logging
import os
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from api.limiter_config import limiter
from api.routers import status, jobs, detection, translation, refinement

logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running database migrations on startup...")
    try:
        from alembic.config import Config
        from alembic import command

        ini_path = "packages/api/alembic.ini"
        if not os.path.exists(ini_path):
            ini_path = "alembic.ini"

        if os.path.exists(ini_path):
            alembic_cfg = Config(ini_path)
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations completed successfully.")
        else:
            logger.warning(f"Alembic config not found at {ini_path}, skipping migrations.")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")
    yield


app = FastAPI(title="Job Sourcing API", version="1.0.0", lifespan=lifespan)

# Setup Rate Limiting State & Handler
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
    )


# Include Routers
app.include_router(status.router)
app.include_router(jobs.router)
app.include_router(detection.router)
app.include_router(translation.router)
app.include_router(refinement.router)
