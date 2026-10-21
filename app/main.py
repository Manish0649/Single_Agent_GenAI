"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.observability.langfuse_setup import flush


# ─── Logging ─────────────────────────────────────────────────────────────────

settings = get_settings()

log_level = getattr(
    logging,
    settings.log_level.upper(),
    logging.INFO,
)

logging.basicConfig(level=log_level)

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(log_level)
)

logger = logging.getLogger(__name__)


# ─── Application Lifespan ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""

    logger.info("Starting Single-Agent GenAI Knowledge Assistant")

    # Do not load the complete dataset automatically at startup.
    # The data layer will load it when required.

    yield

    try:
        flush()
    except Exception:
        logger.exception("Failed to flush Langfuse events during shutdown")

    logger.info("Application shut down cleanly.")


# ─── FastAPI Application ─────────────────────────────────────────────────────

app = FastAPI(
    title="Single-Agent GenAI Knowledge Assistant",
    description=(
        "A secure, observable, context-aware RAG application over the "
        "RewardSphere customer dataset. Built with FastAPI, LangChain, "
        "Milvus, Pydantic AI, and Langfuse."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─── CORS Configuration ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
    ],
)


# ─── Register API Routes ─────────────────────────────────────────────────────

app.include_router(router)


# ─── Global Exception Handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected errors without exposing internal details."""

    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please check the server logs.",
        },
    )