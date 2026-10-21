"""
Pydantic request and response schemas for the FastAPI layer.

All model-generated content must pass through these schemas before being
returned to callers.  Schema validation is not a substitute for factual
or security checks; those are enforced separately.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.requests import ChatRequest, IngestRequest


# ─── Response schemas ─────────────────────────────────────────────────────────

class Evidence(BaseModel):
    """A single piece of supporting evidence for a factual claim."""

    user_id: str
    source_fields: list[str] = Field(min_length=1)
    explanation: str


class CustomerAnswer(BaseModel):
    """
    Structured answer returned by the agent.

    status:
        answered             – the question is fully supported by evidence.
        insufficient_evidence – relevant record found but fields are missing/null.
        refused              – request is out of scope, unauthorized, or unsafe.
    """

    status: Literal["answered", "insufficient_evidence", "refused"]
    answer: str
    evidence: list[Evidence]
    limitations: list[str]

    @field_validator("evidence")
    @classmethod
    def evidence_required_when_answered(
        cls, v: list[Evidence], info  # noqa: ANN001
    ) -> list[Evidence]:
        status = (info.data or {}).get("status")
        if status == "answered" and not v:
            raise ValueError(
                "evidence must not be empty when status is 'answered'."
            )
        return v


class CustomerSummaryResponse(BaseModel):
    """Structured summary returned by GET /customers/{user_id}/summary."""

    user_id: str
    name: str
    segment: str
    account_status: str
    region: str
    city: str
    acquisition_channel: str
    preferred_language: str
    tenure_days: int
    subscription_plan: str
    subscription_interval: str
    subscription_status: str
    auto_renew: bool
    plan_price_paise: int
    payment_attempts: int
    successful_payments: int
    failed_payments: int
    total_settled_paise: int
    open_tickets: int
    resolved_tickets: int
    risk_events: int
    confirmed_risk_events: int
    pending_risk_events: int


class RevenueResponse(BaseModel):
    """Monthly settled revenue returned by GET /customers/{user_id}/revenue."""

    user_id: str
    total_invoiced_paise: int
    total_settled_paise: int
    net_revenue_paise: int
    refund_amount_paise: int
    chargeback_amount_paise: int
    credit_note_amount_paise: int
    monthly_settled: dict[str, int]  # key: "YYYY-MM", value: paise


class IngestResponse(BaseModel):
    """Response from POST /ingest."""

    status: Literal["ok", "error"]
    records_indexed: int
    message: str


class HealthResponse(BaseModel):
    """Response from GET /health."""

    status: Literal["ok", "degraded"]
    version: str = "1.0.0"
    components: dict[str, str]


class ErrorResponse(BaseModel):
    """Controlled error shape returned on failures."""

    error: str
    detail: str | None = None
    trace_id: str | None = None
