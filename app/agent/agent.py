"""
Pydantic AI typed agent implementation.

Enforces:
- Single agent with bounded execution and typed tools
- Structured output conforming to CustomerAnswer
- Access-control verification inside each tool via RunContext dependencies
- Strict separation between retrieval (LangChain/Milvus) and agent execution (Pydantic AI)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext

from app.agent.instructions import SYSTEM_PROMPT
from app.agent import tools as tool_impl
from app.config import get_settings
from app.schemas.responses import CustomerAnswer


@dataclass
class CustomerAgentDeps:
    """Runtime dependencies passed to the agent and verified by each tool."""
    authorized_user_id: str
    retrieved_context: str = ""


def get_agent_model():
    """Return the configured local Ollama model through its OpenAI-compatible API."""
    from pydantic_ai.models.openai import OpenAIModel

    settings = get_settings()

    return OpenAIModel(
        settings.openai_model,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key or "ollama",
    )


def create_customer_agent(model_override: Any = None) -> Agent[CustomerAgentDeps, CustomerAnswer]:
    """Create and configure the Pydantic AI Customer Agent."""
    model = model_override or get_agent_model()

    agent: Agent[CustomerAgentDeps, CustomerAnswer] = Agent(
        model=model,
        output_type=CustomerAnswer,
        deps_type=CustomerAgentDeps,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    @agent.system_prompt
    def add_retrieved_context(ctx: RunContext[CustomerAgentDeps]) -> str:
        if ctx.deps.retrieved_context:
            return f"\n--- RETRIEVED EVIDENCE FROM VECTOR STORE ---\n{ctx.deps.retrieved_context}\n--- END EVIDENCE ---\n"
        return ""

    @agent.tool
    def get_customer_record(ctx: RunContext[CustomerAgentDeps], user_id: str) -> dict[str, Any]:
        """Return the customer profile for an authorized user."""
        try:
            return tool_impl.get_customer_record(user_id, authorized_user_id=ctx.deps.authorized_user_id)
        except (ValueError, PermissionError) as exc:
            return {"error": str(exc)}

    @agent.tool
    def get_subscription_summary(ctx: RunContext[CustomerAgentDeps], user_id: str) -> dict[str, Any]:
        """Return verified subscription details and status."""
        try:
            return tool_impl.get_subscription_summary(user_id, authorized_user_id=ctx.deps.authorized_user_id)
        except (ValueError, PermissionError) as exc:
            return {"error": str(exc)}

    @agent.tool
    def get_payment_summary(ctx: RunContext[CustomerAgentDeps], user_id: str) -> dict[str, Any]:
        """Return verified payment attempt counts, settlements, and dispute metrics."""
        try:
            return tool_impl.get_payment_summary(user_id, authorized_user_id=ctx.deps.authorized_user_id)
        except (ValueError, PermissionError) as exc:
            return {"error": str(exc)}

    @agent.tool
    def get_revenue_trend(ctx: RunContext[CustomerAgentDeps], user_id: str) -> dict[str, Any]:
        """Return verified monthly settled revenue trend."""
        try:
            return tool_impl.get_revenue_trend(user_id, authorized_user_id=ctx.deps.authorized_user_id)
        except (ValueError, PermissionError) as exc:
            return {"error": str(exc)}

    @agent.tool
    def get_support_summary(ctx: RunContext[CustomerAgentDeps], user_id: str) -> dict[str, Any]:
        """Return customer support ticket counts and feedback metrics."""
        try:
            return tool_impl.get_support_summary(user_id, authorized_user_id=ctx.deps.authorized_user_id)
        except (ValueError, PermissionError) as exc:
            return {"error": str(exc)}

    @agent.tool
    def get_risk_summary(ctx: RunContext[CustomerAgentDeps], user_id: str) -> dict[str, Any]:
        """
        Return confirmed and pending risk events separately.
        Never conflate confirmed with pending risk events.
        """
        try:
            return tool_impl.get_risk_summary(user_id, authorized_user_id=ctx.deps.authorized_user_id)
        except (ValueError, PermissionError) as exc:
            return {"error": str(exc)}

    return agent
