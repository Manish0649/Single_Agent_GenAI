"""
Pydantic request models for the FastAPI layer.

Validates all incoming requests before processing by guardrails, tools, or agents.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Body for POST /chat."""

    question: Annotated[
        str,
        Field(
            min_length=3,
            max_length=1000,
            description="The user's natural-language question.",
        ),
    ]
    user_id: Annotated[
        str,
        Field(
            pattern=r"^U\d{10}$",
            description="The customer UserID being queried (e.g. U0000000001).",
        ),
    ]

    @field_validator("question")
    @classmethod
    def strip_question(cls, v: str) -> str:
        return v.strip()


class IngestRequest(BaseModel):
    """Body for POST /ingest (admin-only)."""

    dataset_path: str | None = Field(
        None,
        description="Override path to the CSV dataset. Defaults to the configured path.",
    )
    batch_size: int = Field(
        256,
        ge=1,
        le=2048,
        description="Number of records per embedding batch.",
    )
    force_recreate: bool = Field(
        False,
        description="If true, drop and recreate the Milvus collection.",
    )
