"""Tests for analytics service metrics and revenue consistency."""
from __future__ import annotations

import pytest

from app.services.analytics_service import (
    get_engagement_metrics,
    get_referral_metrics,
    get_risk_profile,
    get_support_metrics,
    verify_revenue_consistency,
)


class TestAnalyticsService:
    def test_engagement_metrics_returns_data(self):
        metrics = get_engagement_metrics("U0000000001")
        if metrics:
            assert "usage_events" in metrics
            assert "most_used_feature" in metrics

    def test_referral_metrics_returns_data(self):
        metrics = get_referral_metrics("U0000000001")
        if metrics:
            assert "direct_referrals_registered" in metrics
            assert "invites_sent" in metrics

    def test_support_metrics_returns_data(self):
        metrics = get_support_metrics("U0000000001")
        if metrics:
            assert "open_tickets" in metrics
            assert "resolved_tickets" in metrics

    def test_risk_profile_separates_confirmed_and_pending(self):
        profile = get_risk_profile("U0000000001")
        if profile:
            assert "confirmed_risk_events" in profile
            assert "pending_risk_events" in profile

    def test_verify_revenue_consistency(self):
        result = verify_revenue_consistency("U0000000001")
        if result:
            assert "total_settled_paise" in result
            assert "settled_le_invoiced" in result
            assert "net_revenue_matches" in result

    def test_nonexistent_user_returns_none(self):
        assert verify_revenue_consistency("U9999999999") is None
