"""
FastAPI route dependencies: authentication and authorization.
"""
from __future__ import annotations

import logging

from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)


def require_ingest_key(x_ingest_key: str = Header(...)) -> None:
    """Protect the /ingest endpoint with a static API key."""
    s = get_settings()
    if x_ingest_key != s.ingest_api_key:
        logger.warning("Ingest endpoint called with invalid key.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid ingest API key.",
        )


def get_client_id(x_forwarded_for: str | None = Header(None)) -> str:
    """Return a simple client identifier for rate limiting."""
    return x_forwarded_for or "local"
