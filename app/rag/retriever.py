"""
Retriever: performs metadata-filtered semantic search against Milvus.

IMPORTANT: Retrieval results are treated as untrusted supporting context.
Access control is enforced by filtering on user_id in metadata so that
a similarity search cannot surface another customer's record.
"""
from __future__ import annotations

import logging

from langchain_core.documents import Document

from app.config import get_settings
from app.rag.milvus_store import get_vector_store

logger = logging.getLogger(__name__)


def retrieve_for_customer(
    query: str,
    user_id: str,
    top_k: int | None = None,
) -> list[Document]:
    """
    Retrieve documents relevant to *query* that belong to *user_id* only.

    The metadata filter `user_id == user_id` prevents cross-customer leakage
    even if the similarity score would otherwise rank another record higher.
    """
    s = get_settings()
    k = top_k or s.retrieval_top_k
    try:
        store = get_vector_store(timeout=1.0)
        results = store.similarity_search(
            query,
            k=k,
            expr=f'user_id == "{user_id}"',
            timeout=1.0,
        )
        logger.info(
            "Retrieval for user %s returned %d docs (query=%r)",
            user_id,
            len(results),
            query[:80],
        )
        return results
    except Exception as exc:
        logger.warning("Milvus retrieval unavailable (proceeding with tools): %s", exc)
        return []
