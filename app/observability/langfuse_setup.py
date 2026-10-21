"""
Langfuse observability setup.

Captures the full request lifecycle including retrieval, LLM calls,
validation failures, latency, and token usage.

Sensitive customer identifiers are redacted from logs where appropriate.
"""
from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_langfuse_client = None
_ENABLED = False


def _init_langfuse():
    global _langfuse_client, _ENABLED
    s = get_settings()
    if not s.langfuse_public_key or not s.langfuse_secret_key:
        logger.info("Langfuse keys not configured; tracing disabled.")
        return
    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host,
        )
        _ENABLED = True
        logger.info("Langfuse tracing enabled.")
    except ImportError:
        logger.warning("langfuse package not installed; tracing disabled.")
    except Exception as exc:
        logger.warning("Langfuse init failed: %s", exc)


_init_langfuse()


def get_langfuse_handler(trace_id: str | None = None):
    """
    Return a LangChain-compatible Langfuse callback handler,
    or None if Langfuse is not configured.
    """
    if not _ENABLED or _langfuse_client is None:
        return None
    try:
        from langfuse.callback import CallbackHandler

        return CallbackHandler(
            public_key=get_settings().langfuse_public_key,
            secret_key=get_settings().langfuse_secret_key,
            host=get_settings().langfuse_host,
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.warning("Could not create Langfuse handler: %s", exc)
        return None


def record_score(trace_id: str, name: str, value: float, comment: str = "") -> None:
    """Record an evaluation score against a trace."""
    if not _ENABLED or _langfuse_client is None:
        return
    try:
        _langfuse_client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
        )
    except Exception as exc:
        logger.warning("Langfuse score failed: %s", exc)


def create_trace(
    name: str,
    user_id: str,
    trace_id: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    """Create a root trace object if Langfuse is enabled."""
    if not _ENABLED or _langfuse_client is None:
        return None
    try:
        return _langfuse_client.trace(
            id=trace_id,
            name=name,
            user_id=user_id,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.warning("Could not create Langfuse trace: %s", exc)
        return None


def redact_sensitive(text: str) -> str:
    """Redact API keys, tokens, and credentials from log strings."""
    import re

    text = re.sub(r"sk-[a-zA-Z0-9]{15,}", "sk-[REDACTED]", text)
    text = re.sub(
        r"(bearer\s+)[a-zA-Z0-9_\-\.]{15,}", r"\1[REDACTED]", text, flags=re.IGNORECASE
    )
    return text


def flush() -> None:
    """Flush pending Langfuse events (call at shutdown)."""
    if _ENABLED and _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception as exc:
            logger.warning("Langfuse flush failed: %s", exc)
