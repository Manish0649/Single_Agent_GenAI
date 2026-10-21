"""
Data quality report generator.

Run standalone:   python -m app.data.quality_checks
Or call produce_report() programmatically.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.loader import get_dataframe, month_revenue_cols

logger = logging.getLogger(__name__)


def produce_report() -> dict[str, Any]:
    """Run all quality checks and return a structured report dict."""
    df = get_dataframe()
    report: dict[str, Any] = {}

    # ── 1. Basic shape ────────────────────────────────────────────────────────
    report["total_rows"] = int(len(df))
    report["total_columns"] = int(len(df.columns))

    # ── 2. UserID uniqueness ──────────────────────────────────────────────────
    report["user_id_unique"] = bool(df["UserID"].is_unique)
    report["duplicate_user_ids"] = int(df["UserID"].duplicated().sum())

    # ── 3. Null / missing values ───────────────────────────────────────────────
    null_counts = df.isnull().sum()
    report["columns_with_nulls"] = {
        col: int(cnt) for col, cnt in null_counts.items() if cnt > 0
    }

    # ── 4. Categorical distributions ─────────────────────────────────────────
    for col in [
        "AccountStatus",
        "ConsentStatus",
        "SubscriptionStatus",
        "CustomerSegment",
    ]:
        if col in df.columns:
            report[f"{col}_distribution"] = df[col].value_counts().to_dict()

    # ── 5. Financial field sanity ─────────────────────────────────────────────
    # Settled <= Invoiced
    mismatch = (df["TotalSettledPaise"] > df["TotalInvoicedPaise"]).sum()
    report["settled_exceeds_invoiced_count"] = int(mismatch)

    # Net revenue = Settled - Refund - Chargeback - CreditNote
    df["_computed_net"] = (
        df["TotalSettledPaise"]
        - df["RefundAmountPaise"]
        - df["ChargebackAmountPaise"]
        - df["CreditNoteAmountPaise"]
    )
    net_mismatch = (df["_computed_net"] != df["NetRevenuePaise"]).sum()
    report["net_revenue_formula_mismatches"] = int(net_mismatch)
    df.drop(columns=["_computed_net"], inplace=True)

    # ── 6. Monthly revenue consistency ───────────────────────────────────────
    rev_cols = month_revenue_cols()
    if rev_cols:
        df["_monthly_sum"] = df[rev_cols].sum(axis=1)
        report["monthly_revenue_cols_count"] = len(rev_cols)
        report["monthly_revenue_sum_range"] = {
            "min": int(df["_monthly_sum"].min()),
            "max": int(df["_monthly_sum"].max()),
        }
        df.drop(columns=["_monthly_sum"], inplace=True)

    # ── 7. Risk field consistency ─────────────────────────────────────────────
    risk_sum_mismatch = (
        df["ConfirmedRiskEvents"] + df["PendingRiskEvents"] > df["RiskEventCount"]
    ).sum()
    report["risk_sum_exceeds_total"] = int(risk_sum_mismatch)

    # ── 8. Timestamp availability ──────────────────────────────────────────────
    for col in [
        "RegistrationAtUTC",
        "SubscriptionStartAtUTC",
        "LastSettledPaymentAtUTC",
        "LatestActivityAtUTC",
    ]:
        if col in df.columns:
            report[f"{col}_null_count"] = int(df[col].isnull().sum())

    logger.info("Data quality report complete: %s", json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    import pprint

    from app.data.loader import load_dataset

    load_dataset()
    pprint.pprint(produce_report())
