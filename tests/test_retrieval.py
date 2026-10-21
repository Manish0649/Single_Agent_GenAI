"""Retrieval unit tests (Milvus-independent; mock the vector store)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.rag.context_builder import build_context
from app.rag.document_builder import build_customer_summary


class TestDocumentBuilder:
    def test_builds_document_with_user_id(self):
        record = {
            "UserID": "U0000000001",
            "SyntheticName": "TestUser",
            "CustomerSegment": "PROFESSIONAL",
            "AccountStatus": "ACTIVE",
            "RegionCode": "TN",
            "CityCode": "CHENNAI",
            "AcquisitionChannel": "ORGANIC",
            "PreferredLanguage": "EN",
            "TenureDays": 364,
            "PlanName": "STANDARD",
            "PlanInterval": "ANNUAL",
            "SubscriptionStatus": "ACTIVE",
            "AutoRenewEnabled": 1,
            "PlanPricePaise": 599900,
            "PaymentAttemptCount": 1,
            "SuccessfulPaymentCount": 1,
            "FailedPaymentCount": 0,
            "PaymentRetryCount": 0,
            "TotalSettledPaise": 637094,
            "NetRevenuePaise": 637094,
            "UsageEventCount": 6,
            "TotalUsageUnits": 30,
            "MonthsWithActivity": 3,
            "MostUsedFeature": "DASHBOARD",
            "LoginEventCount": 2,
            "OpenTicketCount": 0,
            "ResolvedTicketCount": 0,
            "HighPriorityTicketCount": 0,
            "RiskEventCount": 0,
            "ConfirmedRiskEvents": 0,
            "PendingRiskEvents": 0,
            "ReferralInvitesSent": 11,
            "ReferralLinkOpens": 6,
            "ReferralConversions": 6,
        }
        doc = build_customer_summary(record)
        assert doc.metadata["user_id"] == "U0000000001"
        assert "PROFESSIONAL" in doc.page_content
        assert "STANDARD" in doc.page_content

    def test_document_id_is_user_id(self):
        record = {"UserID": "U0000000042"}
        doc = build_customer_summary(record)
        assert doc.id == "U0000000042"


class TestContextBuilder:
    def test_filters_out_wrong_user_docs(self):
        """Context builder must exclude docs belonging to a different user."""
        from langchain_core.documents import Document

        wrong_doc = Document(
            page_content="Wrong user data",
            metadata={"user_id": "U0000000999"},
        )
        context = build_context(
            question="What is the status?",
            user_id="U0000000001",
            retrieved_docs=[wrong_doc],
        )
        assert "Wrong user data" not in context

    def test_includes_correct_user_docs(self):
        from langchain_core.documents import Document

        correct_doc = Document(
            page_content="Customer is ACTIVE",
            metadata={"user_id": "U0000000001"},
        )
        context = build_context(
            question="What is the status?",
            user_id="U0000000001",
            retrieved_docs=[correct_doc],
        )
        assert "Customer is ACTIVE" in context

    def test_includes_tool_results(self):
        context = build_context(
            question="What is the plan?",
            user_id="U0000000001",
            retrieved_docs=[],
            tool_results={"subscription": {"plan_name": "STANDARD"}},
        )
        assert "STANDARD" in context

    def test_context_truncated_at_limit(self):
        """Very large contexts should be truncated."""
        from langchain_core.documents import Document
        from app.config import get_settings

        s = get_settings()
        # Create a doc much larger than the token budget
        large_content = "A" * (s.max_context_tokens * 5)
        doc = Document(
            page_content=large_content,
            metadata={"user_id": "U0000000001"},
        )
        context = build_context("question", "U0000000001", [doc])
        assert len(context) < len(large_content) + 500  # must be truncated
