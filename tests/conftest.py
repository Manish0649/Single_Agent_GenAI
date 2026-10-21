"""Pytest configuration and shared fixtures."""
from __future__ import annotations

import os

import pytest


# Set a dummy OpenAI key so imports don't fail in tests that don't call the LLM
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")
os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
os.environ.setdefault("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
os.environ.setdefault("MILVUS_URI", "http://localhost:19530")
os.environ["DATASET_PATH"] = "tests/sample_customers.csv"
os.environ.setdefault("INGEST_API_KEY", "test-ingest-key")
os.environ.setdefault("API_SECRET_KEY", "test-secret")
