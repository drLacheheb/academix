import os
from contextlib import asynccontextmanager
from time import time

from core.infrastructure.logging.logger import get_logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from api.limiter_config import limiter
from api.routers import (
    embedding,
    jobs,
    matching,
    profiles,
    refinement,
    status,
    translation,
)

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing API application lifespan...")
    try:
        from api.dependencies import get_repo

        repo = get_repo()
        repo.init_db()
        logger.success("Database connection and tables initialized.")
    except Exception as e:
        logger.warning(f"Database initialization warning on startup: {e}")

    logger.info("Verifying storage backend connection...")
    try:
        from api.dependencies import get_storage_service

        storage = get_storage_service()
        storage.verify_connection()
        logger.success("Storage backend connection verified successfully.")
    except Exception as e:
        logger.critical(f"Failed to verify storage connection backend: {e}")
        raise RuntimeError(
            f"FastAPI startup aborted due to storage verification failure: {e}"
        ) from e

    yield


app = FastAPI(title="Job Sourcing API", version="1.0.0", lifespan=lifespan)

# Parse allowed CORS origins from environment with secure defaults
raw_origins = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "https://drlacheheb.github.io,http://localhost:8000,http://127.0.0.1:8000",
)
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

# Setup CORS middleware with restricted origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
)


# Setup Security Response Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Setup HTTP Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    duration = time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)")
    return response


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
app.include_router(translation.router)
app.include_router(refinement.router)
app.include_router(embedding.router)
app.include_router(profiles.router)
app.include_router(matching.router)
