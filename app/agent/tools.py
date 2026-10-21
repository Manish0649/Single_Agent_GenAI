"""
Agent tools: bounded, typed data-access functions used by the Pydantic AI agent.

Each tool:
  - Validates its input.
  - Enforces that the requested user_id matches the authorised scope.
  - Returns typed data; never raw SQL or unrestricted filesystem access.
  - Does NOT perform free-form generation or arithmetic on financial fields.
"""
from __future__ import annotations

import logging
from typing import Any

from app.data.repository import get_repository

logger = logging.getLogger(__name__)


def _validate_user_id(user_id: str) -> None:
    import re
    if not re.match(r"^U\d{10}$", user_id):
        raise ValueError(f"Invalid UserID format: {user_id!r}")


def get_customer_record(user_id: str, authorized_user_id: str) -> dict[str, Any]:
    """Return the full structured record for *user_id* if authorized."""
    _validate_user_id(user_id)
    if user_id != authorized_user_id:
        raise PermissionError(
            f"Access denied: requested {user_id}, authorized {authorized_user_id}"
        )
    repo = get_repository()
    record = repo.get_customer_record(user_id)
    if record is None:
        return {"error": f"No record found for UserID {user_id}"}
    # Return a subset of safe fields (exclude raw timestamps stored as int)
    safe_fields = [
        "UserID", "SyntheticName", "RegionCode", "CityCode",
        "CustomerSegment", "AccountStatus", "RegistrationPlatform",
        "AcquisitionChannel", "PreferredLanguage", "ConsentStatus",
        "TenureDays",
    ]
    return {k: record.get(k) for k in safe_fields}


def get_subscription_summary(user_id: str, authorized_user_id: str) -> dict[str, Any]:
    """Return subscription details for *user_id*."""
    _validate_user_id(user_id)
    if user_id != authorized_user_id:
        raise PermissionError(f"Access denied: requested {user_id}")
    result = get_repository().get_subscription_summary(user_id)
    return result or {"error": f"No record for {user_id}"}


def get_payment_summary(user_id: str, authorized_user_id: str) -> dict[str, Any]:
    """Return payment and billing summary for *user_id*."""
    _validate_user_id(user_id)
    if user_id != authorized_user_id:
        raise PermissionError(f"Access denied: requested {user_id}")
    result = get_repository().get_payment_summary(user_id)
    return result or {"error": f"No record for {user_id}"}


def get_revenue_trend(user_id: str, authorized_user_id: str) -> dict[str, Any]:
    """Return monthly settled revenue trend for *user_id*."""
    _validate_user_id(user_id)
    if user_id != authorized_user_id:
        raise PermissionError(f"Access denied: requested {user_id}")
    result = get_repository().get_revenue_trend(user_id)
    return result or {"error": f"No record for {user_id}"}


def get_support_summary(user_id: str, authorized_user_id: str) -> dict[str, Any]:
    """Return support ticket summary for *user_id*."""
    _validate_user_id(user_id)
    if user_id != authorized_user_id:
        raise PermissionError(f"Access denied: requested {user_id}")
    result = get_repository().get_support_summary(user_id)
    return result or {"error": f"No record for {user_id}"}


def get_risk_summary(user_id: str, authorized_user_id: str) -> dict[str, Any]:
    """
    Return risk event summary for *user_id*.

    IMPORTANT: confirmed and pending events must be reported separately.
    A count of risk events does not constitute a fraud determination.
    """
    _validate_user_id(user_id)
    if user_id != authorized_user_id:
        raise PermissionError(f"Access denied: requested {user_id}")
    result = get_repository().get_risk_summary(user_id)
    return result or {"error": f"No record for {user_id}"}


def get_engagement_summary(user_id: str, authorized_user_id: str) -> dict[str, Any]:
    """Return engagement and usage summary for *user_id*."""
    _validate_user_id(user_id)
    if user_id != authorized_user_id:
        raise PermissionError(f"Access denied: requested {user_id}")
    result = get_repository().get_engagement_summary(user_id)
    return result or {"error": f"No record for {user_id}"}


def get_referral_summary(user_id: str, authorized_user_id: str) -> dict[str, Any]:
    """Return referral activity summary for *user_id*."""
    _validate_user_id(user_id)
    if user_id != authorized_user_id:
        raise PermissionError(f"Access denied: requested {user_id}")
    result = get_repository().get_referral_summary(user_id)
    return result or {"error": f"No record for {user_id}"}
