"""
Output validation pipeline.

Validates generated CustomerAnswer objects against:
1. Schema correctness.
2. Evidence references and known dataset fields.
3. Business-rule consistency.
4. Cross-customer access violations.
5. Content safety.
"""

from __future__ import annotations

import logging
from typing import Any

from app.guardrails.content_safety import check_output_safety
from app.schemas.responses import CustomerAnswer

logger = logging.getLogger(__name__)


# Actual field names in the source dataset.
_KNOWN_FIELDS = {
    "UserID",
    "SyntheticName",
    "RegistrationAtUTC",
    "RegionCode",
    "CityCode",
    "CustomerSegment",
    "AccountStatus",
    "RegistrationPlatform",
    "AcquisitionChannel",
    "PreferredLanguage",
    "ConsentStatus",
    "ReferrerUserID",
    "TenureDays",
    "FirstCampaignID",
    "AcquisitionTouchCount",
    "DirectReferralsRegistered",
    "DirectReferralsPaid",
    "ReferralInvitesSent",
    "ReferralLinkOpens",
    "ReferralConversions",
    "SubscriptionID",
    "PlanID",
    "PlanName",
    "PlanInterval",
    "PlanPricePaise",
    "SubscriptionStatus",
    "AutoRenewEnabled",
    "SubscriptionStartAtUTC",
    "RenewalEvents",
    "LastCancellationReasonCode",
    "InvoiceCount",
    "TotalInvoicedPaise",
    "TotalDiscountPaise",
    "TotalTaxPaise",
    "PaymentAttemptCount",
    "SuccessfulPaymentCount",
    "FailedPaymentCount",
    "PaymentRetryCount",
    "TotalSettledPaise",
    "RefundAmountPaise",
    "ChargebackAmountPaise",
    "CreditNoteAmountPaise",
    "NetRevenuePaise",
    "MainPaymentMethod",
    "LastSettledPaymentAtUTC",
    "UsageEventCount",
    "TotalUsageUnits",
    "TotalEngagementSeconds",
    "MonthsWithActivity",
    "LatestActivityAtUTC",
    "MostUsedFeature",
    "LoginEventCount",
    "SupportTicketCount",
    "OpenTicketCount",
    "ResolvedTicketCount",
    "HighPriorityTicketCount",
    "FeedbackCount",
    "AverageFeedbackScoreX100",
    "RiskEventCount",
    "ConfirmedRiskEvents",
    "PendingRiskEvents",
    "HistoricalRewardCount",
    "HistoricalRewardValuePaise",
    "EverFulfilledReward",
    "LatestRewardMonth",
}


# Maps common LLM-generated aliases to actual dataset field names.
_FIELD_ALIASES = {
    "user_id": "UserID",
    "customer_id": "UserID",
    "name": "SyntheticName",
    "subscription.plan_name": "PlanName",
    "plan_name": "PlanName",
    "subscription.subscription_status": "SubscriptionStatus",
    "subscription_status": "SubscriptionStatus",
    "subscription.plan_interval": "PlanInterval",
    "plan_interval": "PlanInterval",
    "subscription.auto_renew_enabled": "AutoRenewEnabled",
    "auto_renew_enabled": "AutoRenewEnabled",
    "subscription.plan_price_paise": "PlanPricePaise",
    "plan_price_paise": "PlanPricePaise",
    "subscription.last_cancellation_reason": "LastCancellationReasonCode",
    "last_cancellation_reason": "LastCancellationReasonCode",
    "last_cancellation_reason_code": "LastCancellationReasonCode",
    "lastcancellationreasoncode": "LastCancellationReasonCode",
    "cancellation_reason": "LastCancellationReasonCode",
    "cancellation_reason_code": "LastCancellationReasonCode",
    "cancellationreason": "LastCancellationReasonCode",
    "payment.payment_attempts": "PaymentAttemptCount",
    "payment_attempts": "PaymentAttemptCount",
    "paymentattempts": "PaymentAttemptCount",
    "paymentattemptcount": "PaymentAttemptCount",
    "successful_payments": "SuccessfulPaymentCount",
    "successfulpaymentcount": "SuccessfulPaymentCount",
    "payment.successful_payments": "SuccessfulPaymentCount",
    "failed_payments": "FailedPaymentCount",
    "failedpaymentcount": "FailedPaymentCount",
    "payment_retries": "PaymentRetryCount",
    "payment.total_settled_paise": "TotalSettledPaise",
    "total_settled_paise": "TotalSettledPaise",
    "totalsettledpaise": "TotalSettledPaise",
    "payment.net_revenue_paise": "NetRevenuePaise",
    "net_revenue_paise": "NetRevenuePaise",
    "netrevenuepaise": "NetRevenuePaise",
    "engagement.usage_events": "UsageEventCount",
    "usage_events": "UsageEventCount",
    "usageeventcount": "UsageEventCount",
    "total_usage_units": "TotalUsageUnits",
    "total_engagement_seconds": "TotalEngagementSeconds",
    "months_with_activity": "MonthsWithActivity",
    "monthswithactivity": "MonthsWithActivity",
    "latest_activity_at_utc": "LatestActivityAtUTC",
    "most_used_feature": "MostUsedFeature",
    "mostusedfeature": "MostUsedFeature",
    "login_events": "LoginEventCount",
    "login_event_count": "LoginEventCount",
    "support_tickets": "SupportTicketCount",
    "supportticketcount": "SupportTicketCount",
    "total_tickets": "SupportTicketCount",
    "open_tickets": "OpenTicketCount",
    "openticketcount": "OpenTicketCount",
    "resolved_tickets": "ResolvedTicketCount",
    "resolvedticketcount": "ResolvedTicketCount",
    "high_priority_tickets": "HighPriorityTicketCount",
    "highpriorityticketcount": "HighPriorityTicketCount",
    "feedback_count": "FeedbackCount",
    "risk.total_risk_events": "RiskEventCount",
    "total_risk_events": "RiskEventCount",
    "risk_event_count": "RiskEventCount",
    "riskeventcount": "RiskEventCount",
    "risk.confirmed_risk_events": "ConfirmedRiskEvents",
    "confirmed_risk_events": "ConfirmedRiskEvents",
    "confirmedriskevents": "ConfirmedRiskEvents",
    "risk.pending_risk_events": "PendingRiskEvents",
    "pending_risk_events": "PendingRiskEvents",
    "pendingriskevents": "PendingRiskEvents",
    "referral.invites_sent": "ReferralInvitesSent",
    "invites_sent": "ReferralInvitesSent",
    "referral_invites_sent": "ReferralInvitesSent",
    "referralinvitessent": "ReferralInvitesSent",
    "referral.link_opens": "ReferralLinkOpens",
    "link_opens": "ReferralLinkOpens",
    "referral_link_opens": "ReferralLinkOpens",
    "referrallinkopens": "ReferralLinkOpens",
    "referral.conversions": "ReferralConversions",
    "conversions": "ReferralConversions",
    "referral_conversions": "ReferralConversions",
    "referralconversions": "ReferralConversions",
    "direct_referrals_registered": "DirectReferralsRegistered",
    "direct_referrals_paid": "DirectReferralsPaid",
    "referrer_user_id": "ReferrerUserID",
    "refund_amount_paise": "RefundAmountPaise",
    "chargeback_amount_paise": "ChargebackAmountPaise",
    "credit_note_amount_paise": "CreditNoteAmountPaise",
    "total_invoiced_paise": "TotalInvoicedPaise",
    "historical_reward_count": "HistoricalRewardCount",
    "historical_reward_value_paise": "HistoricalRewardValuePaise",
}


def _add_limitation(
    answer: CustomerAnswer,
    message: str,
) -> CustomerAnswer:
    """Return a copy with an additional limitation message."""
    if message in answer.limitations:
        return answer

    return CustomerAnswer(
        status=answer.status,
        answer=answer.answer,
        evidence=answer.evidence,
        limitations=[*answer.limitations, message],
    )


def _normalize_field_name(field: str) -> str:
    """Normalize an LLM field alias to its dataset column name."""

    stripped = field.strip()

    # Exact dataset field names should remain unchanged.
    if stripped in _KNOWN_FIELDS:
        return stripped

    # Match aliases without case sensitivity.
    normalized = stripped.lower()

    # Handle malformed field names generated by the LLM.
    malformed_aliases = {
        "paymentpaymentattemptcount": "PaymentAttemptCount",
        "revenuenetrevenuepaise": "NetRevenuePaise",
    }

    if normalized in malformed_aliases:
        return malformed_aliases[normalized]

    # Match existing aliases.
    return _FIELD_ALIASES.get(normalized, stripped)

def _check_financial_evidence(answer: CustomerAnswer) -> CustomerAnswer:
    """Check whether financial claims cite the appropriate source fields."""
    answer_text = answer.answer.lower()

    cited_fields = {
        field
        for item in answer.evidence
        for field in item.source_fields
    }

    required_fields = {}

    if "net revenue" in answer_text:
        required_fields["net revenue"] = "NetRevenuePaise"

    if "settled amount" in answer_text or "settled revenue" in answer_text:
        required_fields["settled amount"] = "TotalSettledPaise"

    if "payment attempt" in answer_text:
        required_fields["payment attempts"] = "PaymentAttemptCount"

    missing_fields = [
        f"{claim}: {field}"
        for claim, field in required_fields.items()
        if field not in cited_fields
    ]

    if not missing_fields:
        return answer

    limitation = (
        "Evidence validation failed: the following claims lack "
        "their expected source fields: " + ", ".join(missing_fields)
    )

    limitations = [*answer.limitations, limitation]

    return CustomerAnswer(
        status="insufficient_evidence",
        answer=(
            "The answer cannot be verified because the required "
            "financial evidence is missing."
        ),
        evidence=answer.evidence,
        limitations=limitations,
    )

def validate_answer(
    answer: CustomerAnswer,
    authorized_user_id: str,
    tool_results: dict[str, Any] | None = None,
) -> CustomerAnswer:
    """
    Validate an answer against access-control, evidence, safety,
    and business rules.

    Returns a validated or annotated CustomerAnswer.
    """

    # 1. Content safety.
    safety = check_output_safety(answer.answer)

    if not safety.is_safe:
        logger.error(
            "Content safety violations: %s",
            safety.violations,
        )

        return CustomerAnswer(
            status="refused",
            answer="This response was blocked by the content safety policy.",
            evidence=[],
            limitations=safety.violations,
        )

    # 2. Cross-customer access protection.
    for evidence_item in answer.evidence:
        if (
            evidence_item.user_id
            and evidence_item.user_id != authorized_user_id
        ):
            logger.error(
                "Evidence references unauthorized user %s; authorized user is %s",
                evidence_item.user_id,
                authorized_user_id,
            )

            return CustomerAnswer(
                status="refused",
                answer=(
                    "Response blocked: evidence referenced "
                    "an unauthorized customer."
                ),
                evidence=[],
                limitations=[
                    "Cross-customer data access detected."
                ],
            )

    # 3. Normalize and validate evidence field names.
    for evidence_item in answer.evidence:
        normalized_fields = [
            _normalize_field_name(field)
            for field in evidence_item.source_fields
        ]

        evidence_item.source_fields = normalized_fields

        unknown_fields = [
            field
            for field in normalized_fields
            if field not in _KNOWN_FIELDS
        ]

        if unknown_fields:
            logger.warning(
                "Evidence cites unknown fields: %s",
                unknown_fields,
            )

            answer = _add_limitation(
                answer,
                (
                    "Some cited source fields are not in the known "
                    f"schema: {unknown_fields}"
                ),
            )

    # 4. Business-rule consistency checks.
    if tool_results:
        risk = tool_results.get("risk") or {}
        payment = tool_results.get("payment") or {}
        subscription = tool_results.get("subscription") or {}

        # Risk events: pending events are not confirmed events.
        if (
            "confirmed_risk_events" in risk
            and "pending_risk_events" in risk
        ):
            confirmed = risk.get("confirmed_risk_events") or 0
            pending = risk.get("pending_risk_events") or 0

            if (
                pending > 0
                and confirmed != pending
                and "pending" not in answer.answer.lower()
            ):
                answer = _add_limitation(
                    answer,
                    (
                        f"Note: {pending} risk event(s) are pending "
                        "and have not been confirmed."
                    ),
                )

        # Failed payments do not automatically mean cancellation.
        if payment and subscription:
            failed = payment.get("failed_payments", 0) or 0
            subscription_status = subscription.get(
                "subscription_status",
                "",
            )

            if failed > 0 and subscription_status == "ACTIVE":
                answer = _add_limitation(
                    answer,
                    (
                        "Failed payments are recorded, but the "
                        "subscription remains ACTIVE. These are "
                        "separate states."
                    ),
                )

        # Flag unexpected financial totals for review.
        if payment:
            invoiced = payment.get("total_invoiced_paise") or 0
            settled = payment.get("total_settled_paise") or 0

            if invoiced and settled and settled > invoiced:
                answer = _add_limitation(
                    answer,
                    (
                        "Total settled amount exceeds total invoiced "
                        "amount. Verify the source data."
                    ),
                )

    answer = _check_financial_evidence(answer)
    return answer