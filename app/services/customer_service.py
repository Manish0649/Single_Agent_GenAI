"""
Customer service layer: wraps repository access with business logic.
"""
from __future__ import annotations

from typing import Any

from app.data.repository import get_repository
from app.schemas.responses import CustomerSummaryResponse, RevenueResponse


def get_customer_summary(user_id: str) -> CustomerSummaryResponse | None:
    repo = get_repository()
    rec = repo.get_customer_record(user_id)
    if rec is None:
        return None
    sub = repo.get_subscription_summary(user_id) or {}
    pay = repo.get_payment_summary(user_id) or {}
    risk = repo.get_risk_summary(user_id) or {}

    def _i(d: dict[str, Any], k: str, default: Any = 0) -> Any:
        v = d.get(k, default)
        return v if v is not None else default

    import pandas as pd

    def _s(v: Any, default: str = "UNKNOWN") -> str:
        try:
            if pd.isna(v):
                return default
        except (TypeError, ValueError):
            pass
        return str(v) if v is not None else default

    return CustomerSummaryResponse(
        user_id=user_id,
        name=_s(rec.get("SyntheticName")),
        segment=_s(rec.get("CustomerSegment")),
        account_status=_s(rec.get("AccountStatus")),
        region=_s(rec.get("RegionCode")),
        city=_s(rec.get("CityCode")),
        acquisition_channel=_s(rec.get("AcquisitionChannel")),
        preferred_language=_s(rec.get("PreferredLanguage")),
        tenure_days=int(_i(rec, "TenureDays")),
        subscription_plan=_s(sub.get("plan_name")),
        subscription_interval=_s(sub.get("plan_interval")),
        subscription_status=_s(sub.get("subscription_status")),
        auto_renew=bool(sub.get("auto_renew_enabled", False)),
        plan_price_paise=int(_i(sub, "plan_price_paise")),
        payment_attempts=int(_i(pay, "payment_attempts")),
        successful_payments=int(_i(pay, "successful_payments")),
        failed_payments=int(_i(pay, "failed_payments")),
        total_settled_paise=int(_i(pay, "total_settled_paise")),
        open_tickets=int(_i(repo.get_support_summary(user_id) or {}, "open_tickets")),
        resolved_tickets=int(
            _i(repo.get_support_summary(user_id) or {}, "resolved_tickets")
        ),
        risk_events=int(_i(risk, "total_risk_events")),
        confirmed_risk_events=int(_i(risk, "confirmed_risk_events")),
        pending_risk_events=int(_i(risk, "pending_risk_events")),
    )


def get_revenue_response(user_id: str) -> RevenueResponse | None:
    repo = get_repository()
    rev = repo.get_revenue_trend(user_id)
    if rev is None:
        return None
    pay = repo.get_payment_summary(user_id) or {}

    def _i(d: dict[str, Any], k: str) -> int:
        v = d.get(k, 0)
        return int(v) if v is not None else 0

    return RevenueResponse(
        user_id=user_id,
        total_invoiced_paise=_i(pay, "total_invoiced_paise"),
        total_settled_paise=_i(pay, "total_settled_paise"),
        net_revenue_paise=_i(pay, "net_revenue_paise"),
        refund_amount_paise=_i(pay, "refund_amount_paise"),
        chargeback_amount_paise=_i(pay, "chargeback_amount_paise"),
        credit_note_amount_paise=_i(pay, "credit_note_amount_paise"),
        monthly_settled=rev.get("monthly_settled_paise", {}),
    )
