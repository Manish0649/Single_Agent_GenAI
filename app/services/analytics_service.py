"""
Analytics service layer: high-level analytics and deterministic aggregations.

Provides verified analytical summaries for:
- Engagement (usage events, active months, most-used feature)
- Referrals (invites, opens, registrations, conversions)
- Support (open, resolved, high-priority ticket distribution)
- Risk metrics (strictly preserving distinction between confirmed and pending)
- Financial sanity checks and deterministic revenue metrics
"""
from __future__ import annotations

from typing import Any

from app.data.repository import get_repository


def get_engagement_metrics(user_id: str) -> dict[str, Any] | None:
    """Return verified engagement metrics for a customer."""
    repo = get_repository()
    return repo.get_engagement_summary(user_id)


def get_referral_metrics(user_id: str) -> dict[str, Any] | None:
    """Return verified referral activity metrics for a customer."""
    repo = get_repository()
    return repo.get_referral_summary(user_id)


def get_support_metrics(user_id: str) -> dict[str, Any] | None:
    """Return verified customer support metrics."""
    repo = get_repository()
    return repo.get_support_summary(user_id)


def get_risk_profile(user_id: str) -> dict[str, Any] | None:
    """
    Return risk profile separating confirmed from pending events.
    
    A count of risk events does NOT constitute a fraud determination.
    """
    repo = get_repository()
    return repo.get_risk_summary(user_id)


def verify_revenue_consistency(user_id: str) -> dict[str, Any] | None:
    """
    Verify mathematical consistency between billing fields for a customer:
    - Checks: TotalSettled <= TotalInvoiced
    - Checks: NetRevenue == TotalSettled - Refund - Chargeback - CreditNote
    - Compares monthly sum against TotalSettled only where valid.
    """
    repo = get_repository()
    rec = repo.get_customer_record(user_id)
    if rec is None:
        return None

    pay = repo.get_payment_summary(user_id) or {}
    rev = repo.get_revenue_trend(user_id) or {}

    invoiced = pay.get("total_invoiced_paise", 0) or 0
    settled = pay.get("total_settled_paise", 0) or 0
    refund = pay.get("refund_amount_paise", 0) or 0
    chargeback = pay.get("chargeback_amount_paise", 0) or 0
    credit_note = pay.get("credit_note_amount_paise", 0) or 0
    recorded_net = pay.get("net_revenue_paise", 0) or 0

    computed_net = settled - refund - chargeback - credit_note
    monthly_settled = rev.get("monthly_settled_paise", {})
    monthly_sum = sum(monthly_settled.values()) if monthly_settled else 0

    return {
        "user_id": user_id,
        "total_invoiced_paise": invoiced,
        "total_settled_paise": settled,
        "recorded_net_revenue_paise": recorded_net,
        "computed_net_revenue_paise": computed_net,
        "net_revenue_matches": recorded_net == computed_net,
        "settled_le_invoiced": settled <= invoiced,
        "monthly_sum_paise": monthly_sum,
        "monthly_sum_matches_settled": monthly_sum == settled,
    }
