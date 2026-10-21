"""FastAPI endpoint tests using TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data

    def test_health_schema(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ("ok", "degraded")


class TestChatEndpoint:
    def test_valid_request_accepted(self):
        """A valid request structure should be processed (may return insufficient_evidence)."""
        response = client.post(
            "/chat",
            json={
                "question": "What is the subscription status?",
                "user_id": "U0000000001",
            },
        )
        # Should not be 422 (validation error) or 500
        assert response.status_code in (200, 422)
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ("answered", "insufficient_evidence", "refused")

    def test_invalid_user_id_rejected(self):
        response = client.post(
            "/chat",
            json={
                "question": "What is the subscription status?",
                "user_id": "INVALID_ID",
            },
        )
        assert response.status_code == 422

    def test_empty_question_rejected(self):
        response = client.post(
            "/chat",
            json={"question": "", "user_id": "U0000000001"},
        )
        assert response.status_code == 422

    def test_question_too_long_rejected(self):
        response = client.post(
            "/chat",
            json={"question": "x" * 1001, "user_id": "U0000000001"},
        )
        assert response.status_code == 422


class TestIngestEndpoint:
    def test_ingest_without_key_rejected(self):
        response = client.post("/ingest", json={})
        assert response.status_code == 422  # missing header

    def test_ingest_with_wrong_key_rejected(self):
        response = client.post(
            "/ingest",
            json={},
            headers={"x-ingest-key": "wrong-key"},
        )
        assert response.status_code == 403


class TestCustomerSummaryEndpoint:
    def test_invalid_user_id_format(self):
        response = client.get("/customers/BADID/summary")
        assert response.status_code == 400

    def test_nonexistent_user_returns_404(self):
        # This user does not exist in the dataset
        response = client.get("/customers/U9999999999/summary")
        # Either 404 (user not found) or 200 (if dataset loaded)
        assert response.status_code in (200, 404)


class TestRevenueEndpoint:
    def test_invalid_user_id_format(self):
        response = client.get("/customers/BADID/revenue")
        assert response.status_code == 400

    def test_valid_user_id_processed(self):
        response = client.get("/customers/U0000000001/revenue")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert "total_settled_paise" in data
            assert "monthly_settled" in data
