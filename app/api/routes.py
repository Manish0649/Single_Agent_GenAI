"""
FastAPI routes.

All endpoints validate requests through Pydantic schemas.
Ingestion requires an API key, and unexpected errors are logged
without exposing internal exception details to clients.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent.orchestrator import run_agent
from app.api.dependencies import get_client_id, require_ingest_key
from app.guardrails.input_checks import check_rate_limit, validate_user_id
from app.rag.document_builder import build_documents_from_df
from app.rag.milvus_store import ingest_documents
from app.schemas.responses import (
    ChatRequest,
    CustomerAnswer,
    CustomerSummaryResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    RevenueResponse,
)
from app.services.customer_service import (
    get_customer_summary,
    get_revenue_response,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Health Check ─────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    tags=["ops"],
)
def health() -> HealthResponse:
    """Check the availability of Milvus and the local data store."""

    components: dict[str, str] = {}

    # Check Milvus.
    try:
        from app.rag.milvus_store import get_vector_store

        get_vector_store()
        components["milvus"] = "ok"

    except Exception:
        logger.exception("Milvus health check failed")
        components["milvus"] = "degraded"

    # Check the local data store.
    try:
        from app.data.loader import get_dataframe

        df = get_dataframe()
        components["data_store"] = f"ok ({len(df)} records)"

    except Exception:
        logger.exception("Data store health check failed")
        components["data_store"] = "degraded"

    overall_status = (
        "ok"
        if all(
            component.startswith("ok")
            for component in components.values()
        )
        else "degraded"
    )

    return HealthResponse(
        status=overall_status,
        components=components,
    )


# ─── Dataset Ingestion ───────────────────────────────────────────────────────

@router.post(
    "/ingest",
    response_model=IngestResponse,
    dependencies=[Depends(require_ingest_key)],
    summary="Ingest customer data into the vector store",
    tags=["admin"],
)
def ingest(body: IngestRequest) -> IngestResponse:
    """
    Load the dataset, build customer summaries, and index them in Milvus.

    Requires the configured ingestion API key.

    Note:
    The current implementation loads the dataset and builds documents
    in memory. Optimize the pipeline before ingesting the complete
    million-row dataset.
    """

    try:
        from app.data.loader import load_dataset

        dataset_path = (
            Path(body.dataset_path)
            if body.dataset_path
            else None
        )

        df = load_dataset(dataset_path)

        documents = build_documents_from_df(df)

        indexed_count = ingest_documents(
            documents,
            batch_size=body.batch_size,
            drop_old=body.force_recreate,
        )

        logger.info(
            "Ingestion completed successfully: %d documents indexed",
            indexed_count,
        )

        return IngestResponse(
            status="ok",
            records_indexed=indexed_count,
            message=f"Successfully indexed {indexed_count} documents.",
        )

    except Exception:
        logger.exception("Dataset ingestion failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Dataset ingestion failed. "
                "Check the server logs for details."
            ),
        ) from None


# ─── Chat ────────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=CustomerAnswer,
    summary="Ask a question using the single-agent RAG pipeline",
    tags=["chat"],
)
def chat(
    body: ChatRequest,
    client_id: str = Depends(get_client_id),
) -> CustomerAnswer:
    """Process a natural-language question about a customer."""

    # Apply rate limiting.
    try:
        check_rate_limit(client_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    # Validate the requested customer ID.
    try:
        validate_user_id(body.user_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    trace_id = str(uuid.uuid4())

    logger.info(
        "[%s] Chat request received: user_id=%s question_length=%d",
        trace_id,
        body.user_id,
        len(body.question),
    )

    try:
        return run_agent(
            question=body.question,
            user_id=body.user_id,
            trace_id=trace_id,
        )

    except Exception:
        logger.exception(
            "[%s] Chat processing failed for user_id=%s",
            trace_id,
            body.user_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process the question. Please try again later.",
        ) from None


# ─── Customer Summary ─────────────────────────────────────────────────────────

@router.get(
    "/customers/{user_id}/summary",
    response_model=CustomerSummaryResponse,
    summary="Retrieve a structured customer summary",
    tags=["customers"],
)
def customer_summary(user_id: str) -> CustomerSummaryResponse:
    """Return the structured summary for a customer."""

    try:
        validate_user_id(user_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        result = get_customer_summary(user_id)

    except Exception:
        logger.exception(
            "Failed to retrieve customer summary for user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve the customer summary.",
        ) from None

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    return result


# ─── Customer Revenue ─────────────────────────────────────────────────────────

@router.get(
    "/customers/{user_id}/revenue",
    response_model=RevenueResponse,
    summary="Retrieve verified revenue metrics for a customer",
    tags=["customers"],
)
def customer_revenue(user_id: str) -> RevenueResponse:
    """Return verified revenue metrics for a customer."""

    try:
        validate_user_id(user_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        result = get_revenue_response(user_id)

    except Exception:
        logger.exception(
            "Failed to retrieve revenue metrics for user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve the customer's revenue metrics.",
        ) from None

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    return result