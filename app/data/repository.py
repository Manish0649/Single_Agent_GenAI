"""
Structured data repository.

All customer data access goes through this module.
Access control is enforced here – NOT delegated to the LLM.
"""
from __future__ import annotations

import logging
from typing import Any

from app.data.loader import get_record, month_revenue_cols

logger = logging.getLogger(__name__)

_MISSING = object()  # sentinel for truly absent values


def _safe(record: dict[str, Any], key: str, default: Any = None) -> Any:
    """Return record[key] if present and not NA-ish; else default."""
    val = record.get(key, _MISSING)
    if val is _MISSING:
        return default
    # pandas NA / NaT / NaN
    try:
        import pandas as pd

        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    return val


class CustomerRepository:
    """Access-controlled repository for structured customer records."""

    def get_customer_record(self, user_id: str) -> dict[str, Any] | None:
        """Return the full raw record or None if not found."""
        return get_record(user_id)

    def get_subscription_summary(self, user_id: str) -> dict[str, Any] | None:
        rec = get_record(user_id)
        if rec is None:
            return None
        return {
            "user_id": user_id,
            "subscription_id": _safe(rec, "SubscriptionID"),
            "plan_id": _safe(rec, "PlanID"),
            "plan_name": _safe(rec, "PlanName"),
            "plan_interval": _safe(rec, "PlanInterval"),
            "plan_price_paise": _safe(rec, "PlanPricePaise"),
            "subscription_status": _safe(rec, "SubscriptionStatus"),
            "auto_renew_enabled": _safe(rec, "AutoRenewEnabled"),
            "subscription_start": str(_safe(rec, "SubscriptionStartAtUTC", "UNKNOWN")),
            "renewal_events": _safe(rec, "RenewalEvents", 0),
            "last_cancellation_reason": _safe(rec, "LastCancellationReasonCode", "NONE"),
        }

    def get_payment_summary(self, user_id: str) -> dict[str, Any] | None:
        rec = get_record(user_id)
        if rec is None:
            return None
        return {
            "user_id": user_id,
            "invoice_count": _safe(rec, "InvoiceCount", 0),
            "total_invoiced_paise": _safe(rec, "TotalInvoicedPaise", 0),
            "total_discount_paise": _safe(rec, "TotalDiscountPaise", 0),
            "total_tax_paise": _safe(rec, "TotalTaxPaise", 0),
            "payment_attempts": _safe(rec, "PaymentAttemptCount", 0),
            "successful_payments": _safe(rec, "SuccessfulPaymentCount", 0),
            "failed_payments": _safe(rec, "FailedPaymentCount", 0),
            "payment_retries": _safe(rec, "PaymentRetryCount", 0),
            "total_settled_paise": _safe(rec, "TotalSettledPaise", 0),
            "refund_amount_paise": _safe(rec, "RefundAmountPaise", 0),
            "chargeback_amount_paise": _safe(rec, "ChargebackAmountPaise", 0),
            "credit_note_amount_paise": _safe(rec, "CreditNoteAmountPaise", 0),
            "net_revenue_paise": _safe(rec, "NetRevenuePaise", 0),
            "main_payment_method": _safe(rec, "MainPaymentMethod"),
            "last_settled_payment": str(
                _safe(rec, "LastSettledPaymentAtUTC", "UNKNOWN")
            ),
        }

    def get_revenue_trend(self, user_id: str) -> dict[str, Any] | None:
        rec = get_record(user_id)
        if rec is None:
            return None
        rev_cols = month_revenue_cols()
        monthly: dict[str, int] = {}
        for col in rev_cols:
            # col pattern: SettledRevenue202510Paise  → key: 2025-10
            raw = col.replace("SettledRevenue", "").replace("Paise", "")
            if len(raw) == 6:
                key = f"{raw[:4]}-{raw[4:]}"
            else:
                key = raw
            val = _safe(rec, col, 0)
            monthly[key] = int(val) if val is not None else 0
        return {
            "user_id": user_id,
            "total_settled_paise": _safe(rec, "TotalSettledPaise", 0),
            "net_revenue_paise": _safe(rec, "NetRevenuePaise", 0),
            "monthly_settled_paise": monthly,
        }

    def get_engagement_summary(self, user_id: str) -> dict[str, Any] | None:
        rec = get_record(user_id)
        if rec is None:
            return None
        return {
            "user_id": user_id,
            "usage_events": _safe(rec, "UsageEventCount", 0),
            "total_usage_units": _safe(rec, "TotalUsageUnits", 0),
            "total_engagement_seconds": _safe(rec, "TotalEngagementSeconds", 0),
            "months_with_activity": _safe(rec, "MonthsWithActivity", 0),
            "latest_activity": str(_safe(rec, "LatestActivityAtUTC", "UNKNOWN")),
            "most_used_feature": _safe(rec, "MostUsedFeature"),
            "login_events": _safe(rec, "LoginEventCount", 0),
        }

    def get_support_summary(self, user_id: str) -> dict[str, Any] | None:
        rec = get_record(user_id)
        if rec is None:
            return None
        return {
            "user_id": user_id,
            "total_tickets": _safe(rec, "SupportTicketCount", 0),
            "open_tickets": _safe(rec, "OpenTicketCount", 0),
            "resolved_tickets": _safe(rec, "ResolvedTicketCount", 0),
            "high_priority_tickets": _safe(rec, "HighPriorityTicketCount", 0),
            "feedback_count": _safe(rec, "FeedbackCount", 0),
            "avg_feedback_score_x100": _safe(rec, "AverageFeedbackScoreX100"),
        }

    def get_risk_summary(self, user_id: str) -> dict[str, Any] | None:
        rec = get_record(user_id)
        if rec is None:
            return None
        return {
            "user_id": user_id,
            "total_risk_events": _safe(rec, "RiskEventCount", 0),
            # IMPORTANT: confirmed and pending are distinct; do not combine
            "confirmed_risk_events": _safe(rec, "ConfirmedRiskEvents", 0),
            "pending_risk_events": _safe(rec, "PendingRiskEvents", 0),
        }

    def get_referral_summary(self, user_id: str) -> dict[str, Any] | None:
        rec = get_record(user_id)
        if rec is None:
            return None
        return {
            "user_id": user_id,
            "referrer_user_id": _safe(rec, "ReferrerUserID"),
            "direct_referrals_registered": _safe(rec, "DirectReferralsRegistered", 0),
            "direct_referrals_paid": _safe(rec, "DirectReferralsPaid", 0),
            "invites_sent": _safe(rec, "ReferralInvitesSent", 0),
            "link_opens": _safe(rec, "ReferralLinkOpens", 0),
            "conversions": _safe(rec, "ReferralConversions", 0),
        }


# Singleton
_repo = CustomerRepository()


def get_repository() -> CustomerRepository:
    return _repo
