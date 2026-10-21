"""Tests for data loading and quality checks."""
from __future__ import annotations

import pandas as pd
import pytest

from app.data.loader import _parse_yyyymmddhhmmss


class TestTimestampParsing:
    """14-digit timestamps are YYYYMMDDHHmmSS, NOT Unix timestamps."""

    def test_valid_timestamp(self):
        s = pd.Series([20251001000029])
        result = _parse_yyyymmddhhmmss(s)
        assert result.dt.year[0] == 2025
        assert result.dt.month[0] == 10
        assert result.dt.day[0] == 1

    def test_invalid_timestamp_coerces_to_nat(self):
        s = pd.Series([99999999999999])
        result = _parse_yyyymmddhhmmss(s)
        assert pd.isna(result[0])


class TestRepositoryNullHandling:
    """Missing values must not silently become verified zeros."""

    def test_safe_handles_na(self):
        import pandas as pd
        from app.data.repository import _safe

        record = {"col": pd.NA}
        assert _safe(record, "col", default="MISSING") == "MISSING"

    def test_safe_returns_value_when_present(self):
        from app.data.repository import _safe

        record = {"col": 12345}
        assert _safe(record, "col") == 12345

    def test_safe_returns_default_for_missing_key(self):
        from app.data.repository import _safe

        assert _safe({}, "nonexistent", default=0) == 0


class TestQualityChecks:
    def test_produce_report(self):
        from app.data.quality_checks import produce_report

        report = produce_report()
        assert report["total_rows"] > 0
        assert "user_id_unique" in report
        assert "settled_exceeds_invoiced_count" in report
        assert "columns_with_nulls" in report
