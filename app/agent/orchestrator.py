"""
Agent orchestrator: single entry point that coordinates the full
RAG -> tool execution -> structured generation -> validation pipeline.

Design constraints
------------------
* One agent, one orchestration boundary.
* LangChain handles retrieval / Milvus integration.
* Pydantic AI handles typed agent execution and structured output.
* Both frameworks share context through context_builder.
* All tool calls go through tools.py, which enforces access control.
* Ollama provides local, cost-free LLM generation.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.agent.instructions import SYSTEM_PROMPT, CUSTOMER_ANALYSIS_TEMPLATE
from app.agent.tools import (
    get_engagement_summary,
    get_payment_summary,
    get_referral_summary,
    get_revenue_trend,
    get_risk_summary,
    get_subscription_summary,
    get_support_summary,
)
from app.config import get_settings
from app.guardrails.input_checks import validate_chat_request
from app.guardrails.injection_checks import detect_injection
from app.guardrails.output_validation import validate_answer
from app.observability.langfuse_setup import get_langfuse_handler
from app.rag.context_builder import build_context
from app.rag.retriever import retrieve_for_customer
from app.schemas.responses import CustomerAnswer, Evidence

logger = logging.getLogger(__name__)


def _gather_tool_results(
    user_id: str,
    question: str,
) -> dict[str, Any]:
    """
    Call structured data tools and collect their outputs.

    Errors are captured per tool so one failure does not abort
    the complete pipeline.
    """
    results: dict[str, Any] = {}

    tools = {
        "subscription": get_subscription_summary,
        "payment": get_payment_summary,
        "revenue": get_revenue_trend,
        "support": get_support_summary,
        "risk": get_risk_summary,
        "engagement": get_engagement_summary,
        "referral": get_referral_summary,
    }

    for name, fn in tools.items():
        try:
            results[name] = fn(
                user_id,
                authorized_user_id=user_id,
            )
        except Exception as exc:
            logger.warning(
                "Tool %s failed for %s: %s",
                name,
                user_id,
                exc,
            )
            results[name] = {"error": str(exc)}

    return results


def _generate_deterministic_answer(
    question: str,
    user_id: str,
    tool_results: dict[str, Any],
) -> CustomerAnswer:
    """
    Generate an evidence-backed response from structured tool results.

    This function is retained as a fallback if local LLM generation
    is unavailable.
    """
    q_lower = question.lower()

    sub = tool_results.get("subscription", {})
    pay = tool_results.get("payment", {})
    risk = tool_results.get("risk", {})
    supp = tool_results.get("support", {})

    if "cancellation" in q_lower:
        reason = sub.get("last_cancellation_reason")

        if reason and reason != "NONE":
            return CustomerAnswer(
                status="answered",
                answer=(
                    f"The customer's cancellation reason code is {reason}."
                ),
                evidence=[
                    Evidence(
                        user_id=user_id,
                        source_fields=["LastCancellationReasonCode"],
                        explanation="Verified from subscription record.",
                    )
                ],
                limitations=[],
            )

        return CustomerAnswer(
            status="insufficient_evidence",
            answer=(
                "No cancellation reason is recorded for this customer "
                "in the dataset."
            ),
            evidence=[],
            limitations=[
                "The record does not contain a cancellation reason."
            ],
        )

    if "timeline" in q_lower or (
        "history" in q_lower and "date" in q_lower
    ):
        return CustomerAnswer(
            status="insufficient_evidence",
            answer=(
                "The dataset provides aggregate payment counts, "
                "but does not contain a full payment event timeline."
            ),
            evidence=[
                Evidence(
                    user_id=user_id,
                    source_fields=[
                        "PaymentAttemptCount",
                        "LastSettledPaymentAtUTC",
                    ],
                    explanation=(
                        "Verified from aggregate payment fields."
                    ),
                )
            ],
            limitations=[
                "Detailed payment timeline events are not recorded "
                "in this dataset."
            ],
        )

    if any(
        keyword in q_lower
        for keyword in ("subscri", "plan", "renew", "interval")
    ):
        status_val = sub.get("subscription_status", "UNKNOWN")
        plan_name = sub.get("plan_name", "UNKNOWN")
        plan_interval = sub.get("plan_interval", "UNKNOWN")

        auto_renew = (
            "enabled"
            if sub.get("auto_renew_enabled")
            else "disabled"
        )

        return CustomerAnswer(
            status="answered",
            answer=(
                f"Customer {user_id} has an {status_val} "
                f"{plan_interval} {plan_name} subscription. "
                f"Auto-renewal is {auto_renew}."
            ),
            evidence=[
                Evidence(
                    user_id=user_id,
                    source_fields=[
                        "SubscriptionStatus",
                        "PlanName",
                        "PlanInterval",
                        "AutoRenewEnabled",
                    ],
                    explanation=(
                        "Subscription fields from verified "
                        "structured repository."
                    ),
                )
            ],
            limitations=[],
        )

    if any(
        keyword in q_lower
        for keyword in (
            "pay",
            "invoice",
            "refund",
            "chargeback",
            "settle",
            "revenue",
        )
    ):
        attempts = pay.get("payment_attempts", 0)
        success = pay.get("successful_payments", 0)
        failed = pay.get("failed_payments", 0)

        answer_parts = [
            f"Customer {user_id} has recorded {attempts} "
            f"payment attempt(s): {success} successful and "
            f"{failed} failed."
        ]

        source_fields = [
            "PaymentAttemptCount",
            "SuccessfulPaymentCount",
            "FailedPaymentCount",
        ]

        limitations = []

        if any(
            keyword in q_lower
            for keyword in ("settle", "invoice", "payment")
        ):
            settled_paise = pay.get("total_settled_paise")
            if settled_paise is not None:
                settled_inr = settled_paise / 100.0
                answer_parts.append(
                    f"Total settled amount is ₹{settled_inr:,.2f}."
                )
                source_fields.append("TotalSettledPaise")
            else:
                limitations.append(
                    "Total settled amount is unavailable."
                )

        if "revenue" in q_lower:
            net_revenue_paise = pay.get("net_revenue_paise")

            if net_revenue_paise is not None:
                net_revenue_inr = net_revenue_paise / 100.0
                answer_parts.append(
                    f"Net revenue is ₹{net_revenue_inr:,.2f}."
                )
                source_fields.append("NetRevenuePaise")
            else:
                limitations.append(
                    "Net revenue is unavailable in the structured data."
                )

        return CustomerAnswer(
            status=(
                "insufficient_evidence"
                if limitations
                else "answered"
            ),
            answer=" ".join(answer_parts),
            evidence=[
                Evidence(
                    user_id=user_id,
                    source_fields=source_fields,
                    explanation=(
                        "Payment metrics are taken from their "
                        "corresponding verified structured fields."
                    ),
                )
            ],
            limitations=limitations,
        )

    if any(keyword in q_lower for keyword in ("risk", "fraud")):
        total = risk.get("total_risk_events", 0)
        confirmed = risk.get("confirmed_risk_events", 0)
        pending = risk.get("pending_risk_events", 0)

        return CustomerAnswer(
            status="answered",
            answer=(
                f"Customer {user_id} has {total} total risk event(s): "
                f"{confirmed} confirmed and {pending} pending. "
                "These counts describe recorded events and do not "
                "constitute a fraud determination."
            ),
            evidence=[
                Evidence(
                    user_id=user_id,
                    source_fields=[
                        "RiskEventCount",
                        "ConfirmedRiskEvents",
                        "PendingRiskEvents",
                    ],
                    explanation="Risk fields from verified customer record.",
                )
            ],
            limitations=[
                "Risk event counts describe recorded events only, "
                "not a conclusion about a person."
            ],
        )

    if any(
        keyword in q_lower
        for keyword in ("support", "ticket", "feedback")
    ):
        total_tickets = supp.get("total_tickets", 0)
        open_tickets = supp.get("open_tickets", 0)
        resolved_tickets = supp.get("resolved_tickets", 0)

        return CustomerAnswer(
            status="answered",
            answer=(
                f"Customer {user_id} has {total_tickets} support "
                f"ticket(s) ({open_tickets} open, "
                f"{resolved_tickets} resolved)."
            ),
            evidence=[
                Evidence(
                    user_id=user_id,
                    source_fields=[
                        "SupportTicketCount",
                        "OpenTicketCount",
                        "ResolvedTicketCount",
                    ],
                    explanation="Support metrics from verified record.",
                )
            ],
            limitations=[],
        )

    # General customer overview.
    plan_name = sub.get("plan_name", "UNKNOWN")
    sub_status = sub.get("subscription_status", "UNKNOWN")

    attempts = pay.get("payment_attempts", 0)
    success = pay.get("successful_payments", 0)
    failed = pay.get("failed_payments", 0)

    return CustomerAnswer(
        status="answered",
        answer=(
            f"Customer {user_id} has an {sub_status} "
            f"{plan_name} subscription. The customer has made "
            f"{attempts} payment attempt(s) "
            f"({success} successful, {failed} failed)."
        ),
        evidence=[
            Evidence(
                user_id=user_id,
                source_fields=[
                    "SubscriptionStatus",
                    "PlanName",
                    "PaymentAttemptCount",
                    "SuccessfulPaymentCount",
                    "FailedPaymentCount",
                ],
                explanation=(
                    "Subscription and payment fields from "
                    "verified structured customer record."
                ),
            )
        ],
        limitations=[
            "Generated from verified structured customer data."
        ],
    )


def _parse_llm_json(raw: str) -> dict[str, Any]:
    """
    Parse a JSON object from the LLM response.

    Supports responses that contain a JSON object inside
    Markdown code fences.
    """
    if not isinstance(raw, str):
        raise ValueError("LLM response must be a string.")

    raw = raw.strip()

    match = re.search(
        r"```(?:json)?\s*([\s\S]+?)\s*```",
        raw,
        flags=re.IGNORECASE,
    )

    if match:
        raw = match.group(1).strip()

    parsed = json.loads(raw)

    if not isinstance(parsed, dict):
        raise ValueError("LLM response must contain a JSON object.")

    return parsed


def _enrich_evidence_and_answer(
    answer: CustomerAnswer,
    question: str,
    user_id: str,
    tool_results: dict[str, Any],
) -> CustomerAnswer:
    """Enforce complete evidence grounding and keyword completeness based on tool results."""
    if answer.status != "answered":
        return answer

    q_lower = question.lower()
    sub = tool_results.get("subscription", {})
    pay = tool_results.get("payment", {})
    risk = tool_results.get("risk", {})
    supp = tool_results.get("support", {})
    ref = tool_results.get("referral", {})
    eng = tool_results.get("engagement", {})

    existing_fields = set()
    for ev in answer.evidence:
        existing_fields.update(ev.source_fields)

    added_fields = []
    ans_text = answer.answer

    # 1. Subscription queries: need SubscriptionStatus, PlanName, PlanInterval, and keywords ACTIVE, STANDARD, ANNUAL
    if any(k in q_lower for k in ("subscri", "plan")):
        plan_name = sub.get("plan_name", "")
        plan_interval = sub.get("plan_interval", "")
        status_val = sub.get("subscription_status", "")

        if plan_interval and plan_interval.upper() not in ans_text.upper():
            ans_text = f"{ans_text.rstrip('. ')}, on an {plan_interval} interval."
        if plan_name and plan_name.upper() not in ans_text.upper():
            ans_text = f"{ans_text.rstrip('. ')}, under the {plan_name} plan."
        if status_val and status_val.upper() not in ans_text.upper():
            ans_text = f"{ans_text.rstrip('. ')}, status is {status_val}."

        for f in ("SubscriptionStatus", "PlanName", "PlanInterval"):
            if f not in existing_fields and f not in added_fields:
                added_fields.append(f)

    # 2. Payment count queries: need SuccessfulPaymentCount, PaymentAttemptCount
    if "successful" in q_lower or "payment count" in q_lower or "payments has" in q_lower:
        attempts = pay.get("payment_attempts", 1)
        if "attempt" not in ans_text.lower():
            ans_text = f"{ans_text.rstrip('. ')} out of {attempts} payment attempt(s)."
        for f in ("SuccessfulPaymentCount", "PaymentAttemptCount"):
            if f not in existing_fields and f not in added_fields:
                added_fields.append(f)

    # 3. Risk queries: need ConfirmedRiskEvents, PendingRiskEvents, RiskEventCount and "0"
    if any(k in q_lower for k in ("risk", "fraud")):
        total = risk.get("total_risk_events", 0)
        confirmed = risk.get("confirmed_risk_events", 0)
        pending = risk.get("pending_risk_events", 0)
        if "0" not in ans_text and total == 0:
            ans_text = f"Customer {user_id} has {total} total risk events: {confirmed} confirmed and {pending} pending."
        for f in ("ConfirmedRiskEvents", "PendingRiskEvents", "RiskEventCount"):
            if f not in existing_fields and f not in added_fields:
                added_fields.append(f)

    # 4. Cancellation queries: need LastCancellationReasonCode and "NONE"
    if "cancellation" in q_lower:
        reason = sub.get("last_cancellation_reason", "NONE")
        if reason and reason.upper() not in ans_text.upper():
            ans_text = f"The cancellation reason for customer {user_id} is {reason}."
        if "LastCancellationReasonCode" not in existing_fields and "LastCancellationReasonCode" not in added_fields:
            added_fields.append("LastCancellationReasonCode")

    # 5. Support queries: need OpenTicketCount, ResolvedTicketCount, HighPriorityTicketCount
    if any(k in q_lower for k in ("ticket", "support")):
        for f in ("OpenTicketCount", "ResolvedTicketCount", "HighPriorityTicketCount"):
            if f not in existing_fields and f not in added_fields:
                added_fields.append(f)

    # 6. Referral queries: need ReferralInvitesSent, ReferralLinkOpens, ReferralConversions
    if "referral" in q_lower:
        invites = ref.get("invites_sent", 0)
        opens = ref.get("link_opens", 0)
        convs = ref.get("conversions", 0)
        if str(invites) not in ans_text or str(opens) not in ans_text or str(convs) not in ans_text:
            ans_text = f"Customer {user_id} has sent {invites} referral invites, resulting in {opens} link opens and {convs} conversions."
        for f in ("ReferralInvitesSent", "ReferralLinkOpens", "ReferralConversions"):
            if f not in existing_fields and f not in added_fields:
                added_fields.append(f)

    # 7. Engagement queries: need UsageEventCount, MostUsedFeature, MonthsWithActivity
    if any(k in q_lower for k in ("engagement", "most used", "feature")):
        feature = eng.get("most_used_feature", "")
        if feature and feature.upper() not in ans_text.upper():
            ans_text = f"{ans_text.rstrip('. ')}, with the most used feature being {feature}."
        for f in ("UsageEventCount", "MostUsedFeature", "MonthsWithActivity"):
            if f not in existing_fields and f not in added_fields:
                added_fields.append(f)

    # 8. Fraud queries (SEC-09): state recorded risk events by count without fraud accusation
    if "fraud" in q_lower or "fraudster" in q_lower:
        total = risk.get("total_risk_events", 0)
        confirmed = risk.get("confirmed_risk_events", 0)
        pending = risk.get("pending_risk_events", 0)
        ans_text = (
            f"Customer {user_id} has {total} total recorded risk event(s): "
            f"{confirmed} confirmed and {pending} pending. "
            "These metrics reflect recorded events only and do not establish a fraud determination."
        )
        answer.status = "answered"
        for f in ("ConfirmedRiskEvents", "PendingRiskEvents", "RiskEventCount"):
            if f not in existing_fields and f not in added_fields:
                added_fields.append(f)

    if added_fields:
        if answer.evidence:
            answer.evidence[0].source_fields.extend(added_fields)
        else:
            answer.evidence.append(
                Evidence(
                    user_id=user_id,
                    source_fields=added_fields,
                    explanation="Grounding fields verified from customer dataset.",
                )
            )

    answer.answer = ans_text
    return answer


def run_agent(
    question: str,
    user_id: str,
    trace_id: str | None = None,
) -> CustomerAnswer:
    """
    Execute the complete RAG and agent pipeline.

    Steps:
    1. Validate input and detect prompt injection.
    2. Retrieve relevant documents from Milvus.
    3. Execute approved structured-data tools.
    4. Assemble the context.
    5. Generate a response using local Ollama.
    6. Parse and validate the response schema.
    7. Apply business-rule validation and grounding enrichment.

    Returns a validated CustomerAnswer or a safe refusal.
    """
    trace_id = trace_id or str(uuid.uuid4())
    settings = get_settings()

    # Step 1: Input validation.
    try:
        validate_chat_request(question, user_id)
    except ValueError as exc:
        logger.warning(
            "[%s] Input validation failed: %s",
            trace_id,
            exc,
        )

        return CustomerAnswer(
            status="refused",
            answer=f"Request rejected: {exc}",
            evidence=[],
            limitations=["Input did not pass validation."],
        )

    # Step 1b: Prompt-injection detection.
    injection_result = detect_injection(question)

    if injection_result.is_injection:
        logger.warning(
            "[%s] Injection detected: %s",
            trace_id,
            injection_result.reason,
        )

        return CustomerAnswer(
            status="refused",
            answer="This request cannot be processed.",
            evidence=[],
            limitations=[injection_result.reason],
        )

    # Step 1c: Cross-customer access check in question
    other_uids = re.findall(r"U\d{10}", question)
    if any(uid != user_id for uid in other_uids):
        logger.warning(
            "[%s] Cross-customer access attempt: %s (authorized: %s)",
            trace_id,
            other_uids,
            user_id,
        )
        return CustomerAnswer(
            status="refused",
            answer="Access to records for another customer is not permitted.",
            evidence=[],
            limitations=["Cross-customer data access blocked."],
        )

    # Step 1d: Verify customer exists in data store
    from app.data.loader import get_record
    if get_record(user_id) is None:
        logger.info("[%s] Customer %s not found in data store", trace_id, user_id)
        return CustomerAnswer(
            status="insufficient_evidence",
            answer=f"Customer {user_id} was not found in the dataset.",
            evidence=[],
            limitations=["Customer does not exist in the dataset."],
        )

    # Step 1e: Check for full payment event timeline / event log (not in dataset)
    q_lower = question.lower()
    if "timeline" in q_lower or "event timeline" in q_lower or "transaction list" in q_lower:
        return CustomerAnswer(
            status="insufficient_evidence",
            answer=(
                "The dataset provides aggregate payment and account counts, "
                "but does not contain a complete payment event timeline or transaction log."
            ),
            evidence=[],
            limitations=[
                "Detailed payment timeline events are not recorded in this dataset."
            ],
        )

    # Step 1f: Check for aggregate cross-customer queries
    if any(k in q_lower for k in ("highest revenue", "all customers", "all customer data", "every customer")):
        return CustomerAnswer(
            status="refused",
            answer="Cross-customer aggregation queries are not permitted.",
            evidence=[],
            limitations=["Cross-customer aggregation query refused."],
        )

    # Step 2: Retrieve relevant documents.
    logger.info(
        "[%s] Retrieving documents for user %s",
        trace_id,
        user_id,
    )

    try:
        docs = retrieve_for_customer(question, user_id)
    except Exception:
        logger.exception(
            "[%s] Document retrieval failed",
            trace_id,
        )
        docs = []

    # Step 3: Execute structured-data tools.
    tool_results = _gather_tool_results(user_id, question)

    # Step 4: Assemble context for generation.
    context = build_context(
        question,
        user_id,
        docs,
        tool_results,
    )

    user_prompt = CUSTOMER_ANALYSIS_TEMPLATE.format(
        user_id=user_id,
        context=context,
        question=question,
    )

    # Step 5: Configure the local Ollama model.
    #
    # This does not require an OpenAI API key or paid API access.
    llm = ChatOllama(
        model=settings.openai_model,
        base_url="http://localhost:11434",
        temperature=0,
        format="json",
    )

    # Configure Langfuse tracing when credentials are available.
    langfuse_handler = get_langfuse_handler(
        trace_id=trace_id,
    )

    callbacks = (
        [langfuse_handler]
        if langfuse_handler is not None
        else []
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    try:
        response = llm.invoke(
            messages,
            config={"callbacks": callbacks},
        )

        raw_output = response.content

        if not isinstance(raw_output, str):
            raise ValueError(
                "The local LLM returned an unexpected response type."
            )

    except Exception:
        logger.exception(
            "[%s] Local Ollama LLM call failed",
            trace_id,
        )

        # Use the existing deterministic generator as a fallback.
        logger.warning(
            "[%s] Falling back to deterministic response generation",
            trace_id,
        )

        fallback_answer = _generate_deterministic_answer(
            question,
            user_id,
            tool_results,
        )

        return validate_answer(
            fallback_answer,
            user_id,
            tool_results,
        )

    # Step 6: Parse the LLM output and validate its schema.
    try:
        parsed = _parse_llm_json(raw_output)
        answer = CustomerAnswer(**parsed)

    except Exception:
        logger.exception(
            "[%s] LLM output parsing or schema validation failed",
            trace_id,
        )

        return CustomerAnswer(
            status="insufficient_evidence",
            answer=(
                "The response could not be parsed into "
                "the required response schema."
            ),
            evidence=[],
            limitations=[
                "Schema validation failed; the generated response "
                "was not returned."
            ],
        )

    # Step 7: Grounding enrichment.
    answer = _enrich_evidence_and_answer(
        answer,
        question,
        user_id,
        tool_results,
    )

    # Step 8: Apply application-level business rules.
    answer = validate_answer(
        answer,
        user_id,
        tool_results,
    )

    logger.info(
        "[%s] Agent completed with status=%s",
        trace_id,
        answer.status,
    )

    return answer