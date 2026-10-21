"""
Application configuration loaded from environment variables.
All secrets and credentials must be set in a .env file (never committed).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # ── LLM ──────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", validation_alias="OPENAI_EMBEDDING_MODEL"
    )
    openai_base_url: str = Field(default="", validation_alias="OPENAI_BASE_URL")

    # ── Milvus ────────────────────────────────────────────────────────────────
    milvus_uri: str = Field(default="http://localhost:19530", validation_alias="MILVUS_URI")
    milvus_token: str = Field(default="", validation_alias="MILVUS_TOKEN")
    milvus_collection: str = Field(default="customer_summaries", validation_alias="MILVUS_COLLECTION")

    # ── Langfuse ──────────────────────────────────────────────────────────────
    langfuse_public_key: str = Field(default="", validation_alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", validation_alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", validation_alias="LANGFUSE_HOST")

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    api_secret_key: str = Field(default="change-me", validation_alias="API_SECRET_KEY")
    ingest_api_key: str = Field(default="ingest-secret-key", validation_alias="INGEST_API_KEY")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # ── Data ──────────────────────────────────────────────────────────────────
    dataset_path: Path = Field(
        default=Path("dataset/RewardSphere_1M_Customers.csv"), validation_alias="DATASET_PATH"
    )

    # ── RAG ───────────────────────────────────────────────────────────────────
    retrieval_top_k: int = 5
    max_context_tokens: int = 4096
    embedding_batch_size: int = 256

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
