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
from api.routers import status, jobs, detection, translation, refinement, profiles, matching

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
            # Dynamically set the absolute migrations path relative to alembic.ini location
            ini_dir = os.path.dirname(os.path.abspath(ini_path))
            migrations_dir = os.path.abspath(os.path.join(ini_dir, "src", "api", "migrations"))
            alembic_cfg.set_main_option("script_location", migrations_dir)
            
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations completed successfully.")
        else:
            logger.warning(f"Alembic config not found at {ini_path}, skipping migrations.")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")

    logger.info("Verifying storage backend connection...")
    try:
        from api.dependencies import get_storage_service
        storage = get_storage_service()
        storage.verify_connection()
        logger.info("Storage backend connection verified successfully.")
    except Exception as e:
        logger.critical(f"Failed to verify storage connection backend: {e}")
        raise RuntimeError(f"FastAPI startup aborted due to storage verification failure: {e}") from e

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
app.include_router(profiles.router)
app.include_router(matching.router)
