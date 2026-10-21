"""
Input guardrails: validate query length, format, user-id patterns,
and apply basic rate-limit bookkeeping.

These checks run BEFORE any LLM or retrieval call.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict

_RATE_LIMIT_WINDOW_S = 60
_RATE_LIMIT_MAX_REQUESTS = 20

# Simple in-process rate limiter (replace with Redis in production)
_request_timestamps: dict[str, list[float]] = defaultdict(list)

USER_ID_RE = re.compile(r"^U\d{10}$")

# Patterns that suggest the question contains injected instructions
_SUSPICIOUS_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+.{0,30}instructions",
    r"forget\s+your\s+(instructions|system\s+prompt)",
    r"reveal\s+(the\s+)?(system\s+prompt|secret|credentials?|api\s+key)",
    r"act\s+as\s+(?:if\s+you\s+are|a\s+different)",
    r"you\s+are\s+now\s+(?:a\s+)?(?:different|unrestricted|jailbroken)",
]
_SUSPICIOUS_RE = [re.compile(p, re.IGNORECASE) for p in _SUSPICIOUS_PATTERNS]


def validate_user_id(user_id: str) -> None:
    """Raise ValueError if user_id does not match expected format."""
    if not USER_ID_RE.match(user_id):
        raise ValueError(
            f"UserID must match pattern U + 10 digits (got {user_id!r})."
        )


def validate_chat_request(question: str, user_id: str) -> None:
    """Run all input validation checks; raise ValueError on failure."""
    if not question or not question.strip():
        raise ValueError("Question must not be empty.")
    if len(question) > 1000:
        raise ValueError("Question exceeds maximum length of 1000 characters.")
    validate_user_id(user_id)


def check_rate_limit(client_id: str) -> None:
    """Raise ValueError if the client has exceeded the request rate limit."""
    now = time.monotonic()
    window_start = now - _RATE_LIMIT_WINDOW_S
    timestamps = _request_timestamps[client_id]
    # Purge old entries
    _request_timestamps[client_id] = [t for t in timestamps if t > window_start]
    if len(_request_timestamps[client_id]) >= _RATE_LIMIT_MAX_REQUESTS:
        raise ValueError(
            f"Rate limit exceeded: max {_RATE_LIMIT_MAX_REQUESTS} requests per minute."
        )
    _request_timestamps[client_id].append(now)
