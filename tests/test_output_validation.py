"""Tests for output validation business rules."""
from __future__ import annotations

import pytest

from app.guardrails.output_validation import validate_answer
from app.schemas.responses import CustomerAnswer, Evidence


def _make_answer(**kwargs) -> CustomerAnswer:
    defaults = dict(
        status="answered",
        answer="The customer has an active subscription.",
        evidence=[
            Evidence(
                user_id="U0000000001",
                source_fields=["SubscriptionStatus", "PlanName"],
                explanation="Subscription fields support the answer.",
            )
        ],
        limitations=[],
    )
    defaults.update(kwargs)
    return CustomerAnswer(**defaults)


class TestSchemaValidation:
    def test_answered_requires_evidence(self):
        with pytest.raises(Exception):
            CustomerAnswer(
                status="answered",
                answer="Some answer",
                evidence=[],  # must not be empty for 'answered'
                limitations=[],
            )

    def test_refused_allows_empty_evidence(self):
        ans = CustomerAnswer(
            status="refused",
            answer="Cannot answer.",
            evidence=[],
            limitations=["Out of scope."],
        )
        assert ans.status == "refused"

    def test_insufficient_evidence_allows_empty_evidence(self):
        ans = CustomerAnswer(
            status="insufficient_evidence",
            answer="Field not available.",
            evidence=[],
            limitations=["Field missing."],
        )
        assert ans.status == "insufficient_evidence"

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            CustomerAnswer(
                status="made_up_status",
                answer="Whatever",
                evidence=[],
                limitations=[],
            )


class TestCrossCustomerValidation:
    def test_evidence_for_different_user_blocked(self):
        answer = _make_answer(
            evidence=[
                Evidence(
                    user_id="U0000000002",  # different from authorized
                    source_fields=["SubscriptionStatus"],
                    explanation="Subscription fields.",
                )
            ]
        )
        result = validate_answer(answer, authorized_user_id="U0000000001")
        assert result.status == "refused"
        assert "unauthorized" in result.answer.lower()


class TestBusinessRules:
    def test_pending_risk_events_noted_in_limitations(self):
        answer = _make_answer(
            answer="The customer has some risk events.",
            evidence=[
                Evidence(
                    user_id="U0000000001",
                    source_fields=["RiskEventCount"],
                    explanation="Risk event count.",
                )
            ],
        )
        tool_results = {
            "risk": {
                "confirmed_risk_events": 2,
                "pending_risk_events": 3,  # pending > 0, not mentioned in answer
            },
            "subscription": {"subscription_status": "ACTIVE"},
            "payment": {"failed_payments": 0, "total_invoiced_paise": 100000, "total_settled_paise": 90000},
        }
        result = validate_answer(answer, "U0000000001", tool_results)
        # Should add a limitation about pending events
        limitations_text = " ".join(result.limitations)
        assert "pending" in limitations_text.lower()

    def test_failed_payment_with_active_subscription_noted(self):
        answer = _make_answer(
            answer="There is one failed payment.",
        )
        tool_results = {
            "risk": {"confirmed_risk_events": 0, "pending_risk_events": 0},
            "subscription": {"subscription_status": "ACTIVE"},
            "payment": {
                "failed_payments": 1,
                "total_invoiced_paise": 100000,
                "total_settled_paise": 90000,
            },
        }
        result = validate_answer(answer, "U0000000001", tool_results)
        limitations_text = " ".join(result.limitations)
        assert "active" in limitations_text.lower() or "separate" in limitations_text.lower()

    def test_credential_in_output_blocked(self):
        answer = _make_answer(
            answer="The api_key is sk-abc123. Customer is active.",
        )
        result = validate_answer(answer, "U0000000001")
        assert result.status == "refused"

    def test_fraud_accusation_blocked(self):
        answer = _make_answer(
            answer="This customer is confirmed a fraudster based on events.",
        )
        result = validate_answer(answer, "U0000000001")
        assert result.status == "refused"


class TestUnknownFieldCitation:
    def test_unknown_field_adds_limitation(self):
        answer = _make_answer(
            evidence=[
                Evidence(
                    user_id="U0000000001",
                    source_fields=["NonExistentField"],
                    explanation="This field doesn't exist in schema.",
                )
            ]
        )
        result = validate_answer(answer, "U0000000001")
        limitations_text = " ".join(result.limitations)
        assert "not in the known schema" in limitations_text


class TestFinancialEvidenceValidation:
    def test_net_revenue_requires_correct_source_field(self):
        answer = _make_answer(
            answer="The customer's net revenue is ₹6,370.94.",
            evidence=[
                Evidence(
                    user_id="U0000000001",
                    source_fields=["PaymentAttemptCount", "TotalSettledPaise"],
                    explanation="Payment attempts and settled amount.",
                )
            ],
        )

        result = validate_answer(answer, "U0000000001")

        assert result.status == "insufficient_evidence"
        assert "NetRevenuePaise" in " ".join(result.limitations)
        
    def test_net_revenue_with_correct_source_field(self):
        answer = _make_answer(
            answer="The customer's net revenue is ₹6,370.94.",
            evidence=[
                Evidence(
                    user_id="U0000000001",
                    source_fields=["NetRevenuePaise"],
                    explanation="Net revenue from the payment data.",
                )
            ],
        )

        result = validate_answer(answer, "U0000000001")

        limitations_text = " ".join(result.limitations)

        assert "net revenue: NetRevenuePaise" not in limitations_text

    def test_payment_attempts_require_correct_source_field(self):
        answer = _make_answer(
            answer="The customer made 1 payment attempt.",
            evidence=[
                Evidence(
                    user_id="U0000000001",
                    source_fields=["TotalSettledPaise"],
                    explanation="Total settled payment amount.",
                )
            ],
        )

        result = validate_answer(answer, "U0000000001")

        assert result.status == "insufficient_evidence"
        assert "PaymentAttemptCount" in " ".join(result.limitations)