from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from langchain_milvus import Milvus

from app.config import get_settings
from app.rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)

_VECTOR_STORE: Milvus | None = None


def _connection_args() -> dict[str, Any]:
    """Build Milvus connection arguments."""
    settings = get_settings()

    args: dict[str, Any] = {
        "uri": settings.milvus_uri,
    }

    if settings.milvus_token:
        args["token"] = settings.milvus_token

    return args


def _create_vector_store(
    *,
    drop_old: bool = False,
    timeout: float | None = None,
) -> Milvus:
    """Create a Milvus vector store with consistent field configuration."""
    settings = get_settings()

    logger.info(
        "Connecting to Milvus: uri=%s, collection=%s",
        settings.milvus_uri,
        settings.milvus_collection,
    )

    enable_dynamic = True
    if not drop_old:
        try:
            from pymilvus import Collection, connections, utility
            connections.connect(
                alias="schema_check",
                uri=settings.milvus_uri,
                token=settings.milvus_token or "",
            )
            if utility.has_collection(settings.milvus_collection, using="schema_check"):
                col = Collection(settings.milvus_collection, using="schema_check")
                enable_dynamic = bool(col.schema.enable_dynamic_field)
            connections.disconnect("schema_check")
        except Exception:
            enable_dynamic = False

    return Milvus(
        embedding_function=get_embeddings(),
        collection_name=settings.milvus_collection,
        connection_args=_connection_args(),
        drop_old=drop_old,
        auto_id=False,
        primary_field="pk",
        text_field="text",
        vector_field="vector",
        enable_dynamic_field=enable_dynamic,
        timeout=timeout,
    )


def get_vector_store(
    drop_old: bool = False,
    timeout: float | None = 2.0,
) -> Milvus:
    """Return the cached Milvus vector store.

    Use drop_old=True only when intentionally recreating a collection.
    """
    global _VECTOR_STORE

    if _VECTOR_STORE is None or drop_old:
        _VECTOR_STORE = _create_vector_store(
            drop_old=drop_old,
            timeout=timeout,
        )

    return _VECTOR_STORE


def ingest_documents(
    docs: list[Document],
    batch_size: int = 256,
    drop_old: bool = False,
) -> int:
    """Embed and store documents in Milvus in batches.

    Each document must contain a unique user_id in its metadata.
    The user_id is also used as the document's primary key.
    """
    global _VECTOR_STORE

    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")

    if not docs:
        logger.info("No documents supplied for ingestion.")
        return 0

    for doc in docs:
        user_id = doc.metadata.get("user_id")

        if user_id is None or not str(user_id).strip():
            raise ValueError(
                "Every document must contain a non-empty 'user_id' "
                "in its metadata."
            )

    user_ids = [str(doc.metadata["user_id"]) for doc in docs]

    if len(user_ids) != len(set(user_ids)):
        raise ValueError(
            "Duplicate user_id values found. Each customer must have "
            "a unique primary key."
        )

    total = len(docs)

    try:
        for start in range(0, total, batch_size):
            batch = docs[start : start + batch_size]

            # Recreate the collection only for the first batch when explicitly
            # requested. Subsequent batches must preserve the new collection.
            recreate_collection = drop_old and start == 0

            vector_store = _create_vector_store(
                drop_old=recreate_collection,
            )

            batch_ids = [
                str(doc.metadata["user_id"])
                for doc in batch
            ]

            vector_store.add_documents(
                documents=batch,
                ids=batch_ids,
            )

            logger.info(
                "Indexed batch: %d/%d documents",
                min(start + len(batch), total),
                total,
            )

    finally:
        # Ensure subsequent retrieval obtains a fresh vector-store instance.
        _VECTOR_STORE = None

    logger.info("Document ingestion completed: %d documents", total)

    return total