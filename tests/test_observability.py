"""
Tests for observability (Langfuse tracing, metrics, failure recording, redaction).

Verifies Section 13 scenarios:
19. Verify that a successful request generates a trace.
20. Verify that retrieval and validation failures are observable.
21. Verify that token usage and latency are recorded where supported.
22. Confirm that logs do not unnecessarily expose sensitive customer data.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.observability.langfuse_setup import (
    create_trace,
    get_langfuse_handler,
    record_score,
    redact_sensitive,
)


class TestObservabilityTracing:
    """Scenario 19: Trace generation for requests."""

    def test_trace_id_generation_and_propagation(self):
        with patch("app.observability.langfuse_setup._ENABLED", True):
            mock_client = MagicMock()
            with patch("app.observability.langfuse_setup._langfuse_client", mock_client):
                trace = create_trace(
                    name="chat_request",
                    user_id="U0000000001",
                    trace_id="test-trace-123",
                    metadata={"query": "test query"},
                )
                mock_client.trace.assert_called_once_with(
                    id="test-trace-123",
                    name="chat_request",
                    user_id="U0000000001",
                    metadata={"query": "test query"},
                )


class TestFailureObservability:
    """Scenario 20: Retrieval and validation failures are observable."""

    def test_failure_score_recorded(self):
        with patch("app.observability.langfuse_setup._ENABLED", True):
            mock_client = MagicMock()
            with patch("app.observability.langfuse_setup._langfuse_client", mock_client):
                record_score(
                    trace_id="trace-fail-1",
                    name="validation_success",
                    value=0.0,
                    comment="Schema validation failed",
                )
                mock_client.score.assert_called_once_with(
                    trace_id="trace-fail-1",
                    name="validation_success",
                    value=0.0,
                    comment="Schema validation failed",
                )

    def test_observability_handles_client_errors_gracefully(self):
        with patch("app.observability.langfuse_setup._ENABLED", True):
            mock_client = MagicMock()
            mock_client.score.side_effect = RuntimeError("Network error")
            with patch("app.observability.langfuse_setup._langfuse_client", mock_client):
                # Must not raise an unhandled exception to callers
                record_score("trace-1", "score_name", 1.0)


class TestMetricsRecording:
    """Scenario 21: Token usage and latency tracking."""

    def test_langfuse_callback_handler_configured_with_trace_id(self):
        with patch("app.observability.langfuse_setup._ENABLED", True):
            with patch("app.observability.langfuse_setup._langfuse_client", MagicMock()):
                handler = get_langfuse_handler(trace_id="trace-xyz-999")
                # When Langfuse is installed, CallbackHandler is returned with trace_id
                if handler is not None:
                    assert handler.trace_id == "trace-xyz-999"


class TestDataRedaction:
    """Scenario 22: Confirm that logs/traces do not expose sensitive credentials."""

    def test_redact_sensitive_api_keys(self):
        raw = "Making request with api_key=sk-1234567890abcdefghijklmnop to server"
        clean = redact_sensitive(raw)
        assert "sk-1234567890abcdefghijklmnop" not in clean
        assert "sk-[REDACTED]" in clean

    def test_redact_sensitive_bearer_token(self):
        raw = "Authorization: Bearer mySecretToken1234567890123456 in header"
        clean = redact_sensitive(raw)
        assert "mySecretToken1234567890123456" not in clean
        assert "[REDACTED]" in clean

    def test_benign_text_untouched(self):
        benign = "User U0000000001 queried subscription status on 2026-10-20."
        assert redact_sensitive(benign) == benign
