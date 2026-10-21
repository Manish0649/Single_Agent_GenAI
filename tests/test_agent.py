"""Tests for agent tools – permissions and bounded access."""
from __future__ import annotations

import pytest

from app.agent.tools import (
    get_customer_record,
    get_payment_summary,
    get_risk_summary,
    get_subscription_summary,
)


class TestToolAccessControl:
    """Tools must block cross-customer access."""

    def test_get_customer_record_wrong_auth_raises(self):
        with pytest.raises(PermissionError):
            get_customer_record(
                "U0000000002",
                authorized_user_id="U0000000001",
            )

    def test_get_subscription_wrong_auth_raises(self):
        with pytest.raises(PermissionError):
            get_subscription_summary(
                "U0000000002",
                authorized_user_id="U0000000001",
            )

    def test_get_payment_wrong_auth_raises(self):
        with pytest.raises(PermissionError):
            get_payment_summary(
                "U0000000002",
                authorized_user_id="U0000000001",
            )

    def test_get_risk_wrong_auth_raises(self):
        with pytest.raises(PermissionError):
            get_risk_summary(
                "U0000000002",
                authorized_user_id="U0000000001",
            )


class TestToolInputValidation:
    """Tools must reject malformed UserIDs."""

    def test_invalid_user_id_format_raises(self):
        with pytest.raises(ValueError):
            get_customer_record(
                "NOT_VALID",
                authorized_user_id="NOT_VALID",
            )

    def test_empty_user_id_raises(self):
        with pytest.raises(ValueError):
            get_customer_record("", authorized_user_id="")


class TestRiskToolSemantics:
    """Risk events: confirmed != pending; do not conflate."""

    def test_risk_summary_returns_separate_fields(self):
        from unittest.mock import patch

        mock_risk = {
            "user_id": "U0000000001",
            "total_risk_events": 5,
            "confirmed_risk_events": 2,
            "pending_risk_events": 3,
        }

        with patch(
            "app.data.repository.CustomerRepository.get_risk_summary",
            return_value=mock_risk,
        ):
            result = get_risk_summary(
                "U0000000001",
                authorized_user_id="U0000000001",
            )

        assert result["confirmed_risk_events"] == 2
        assert result["pending_risk_events"] == 3
        assert result["confirmed_risk_events"] != result["pending_risk_events"]


class TestPydanticAIAgent:
    """Tests for the typed Pydantic AI agent workflow."""

    def test_agent_initialization_and_tool_registration(self):
        from app.agent.agent import create_customer_agent
        from app.schemas.responses import CustomerAnswer

        agent = create_customer_agent("test")

        # Verify structured output schema.
        assert agent._result_schema is not None
        assert "final_result" in agent._result_schema.tools

        # Verify the schema accepts CustomerAnswer.
        expected_answer = CustomerAnswer(
            status="answered",
            answer="Test answer",
            evidence=[
                {
                    "user_id": "U0000000001",
                    "source_fields": ["SubscriptionStatus"],
                    "explanation": "Test evidence",
                }
            ],
            limitations=[],
        )

        result_tool = agent._result_schema.tools["final_result"]
        validated_answer = result_tool.type_adapter.validate_python(
            expected_answer.model_dump()
        )

        assert validated_answer == expected_answer

        # Pydantic AI 0.0.14 stores registered function tools in _function_tools.
        registered_tools = list(agent._function_tools.keys())

        expected_tools = [
            "get_customer_record",
            "get_subscription_summary",
            "get_payment_summary",
            "get_revenue_trend",
            "get_support_summary",
            "get_risk_summary",
        ]

        for tool_name in expected_tools:
            assert tool_name in registered_tools

    def test_agent_run_sync_produces_structured_output(self):
        from app.agent.agent import (
            CustomerAgentDeps,
            create_customer_agent,
        )
        from app.schemas.responses import CustomerAnswer

        agent = create_customer_agent("test")

        result = agent.run_sync(
            "Summarize subscription for customer",
            deps=CustomerAgentDeps(
                authorized_user_id="U0000000001",
                retrieved_context="Active subscription plan STANDARD",
            ),
        )

        assert isinstance(result.data, CustomerAnswer)
        assert result.data.status in (
            "answered",
            "insufficient_evidence",
            "refused",
        )