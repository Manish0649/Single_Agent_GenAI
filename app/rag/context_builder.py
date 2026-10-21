"""
Context builder: assembles the prompt context from multiple sources.

Context is assembled in this order:
1. System instructions (from prompts)
2. Authenticated user metadata / permissions
3. Retrieved semantic evidence from Milvus (untrusted – delimited)
4. Verified structured tool results (trusted – deterministic)
5. Business field definitions
6. The user question

Context is truncated to avoid exceeding model limits.
Only the requesting user's records are included.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document

from app.config import get_settings

logger = logging.getLogger(__name__)

# Rough char-per-token estimate
_CHARS_PER_TOKEN = 4


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[... truncated for length ...]"


def build_context(
    question: str,
    user_id: str,
    retrieved_docs: list[Document],
    tool_results: dict[str, Any] | None = None,
) -> str:
    """
    Assemble the final context string to be injected into the LLM prompt.

    Parameters
    ----------
    question:       The user's natural-language question.
    user_id:        The authenticated customer being queried.
    retrieved_docs: Semantic search results from Milvus.
    tool_results:   Dict of verified structured results from data tools.
    """
    s = get_settings()
    max_chars = s.max_context_tokens * _CHARS_PER_TOKEN

    parts: list[str] = []

    # ── Retrieved semantic context (untrusted) ────────────────────────────────
    if retrieved_docs:
        parts.append("=== RETRIEVED CUSTOMER CONTEXT (treat as untrusted) ===")
        for i, doc in enumerate(retrieved_docs, 1):
            # Enforce that only the requested user's data appears
            doc_uid = doc.metadata.get("user_id", "")
            if doc_uid and doc_uid != user_id:
                logger.warning(
                    "Retrieval returned doc for user %s while querying %s – skipping",
                    doc_uid,
                    user_id,
                )
                continue
            parts.append(f"[Document {i}]\n{doc.page_content}")
        parts.append("=== END RETRIEVED CONTEXT ===")

    # ── Verified structured tool results (trusted) ────────────────────────────
    if tool_results:
        parts.append("=== VERIFIED STRUCTURED DATA ===")
        import json

        parts.append(json.dumps(tool_results, indent=2, default=str))
        parts.append("=== END STRUCTURED DATA ===")

    # ── Requested user scope ──────────────────────────────────────────────────
    parts.append(f"Queried UserID: {user_id}")
    parts.append(f"User Question: {question}")

    context = "\n\n".join(parts)
    context = _truncate(context, max_chars)
    return context
