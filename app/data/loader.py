"""
Data loader and quality checker.

Loads the CSV dataset, validates it, and exposes a dictionary-based
in-memory store keyed by UserID for exact structured lookups.

Important parsing notes
-----------------------
* RegistrationAtUTC and similar 14-digit columns are YYYYMMDDHHmmSS strings
  stored as int64 – NOT Unix timestamps.
* Financial fields are in integer paise (1 INR = 100 paise).
* Missing / null values are represented by pandas NA; they must not be
  silently coerced to zero.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import get_settings

logger = logging.getLogger(__name__)

# Columns that encode timestamps as YYYYMMDDHHmmSS int64
_TIMESTAMP_COLS = [
    "RegistrationAtUTC",
    "SubscriptionStartAtUTC",
    "LastSettledPaymentAtUTC",
    "LatestActivityAtUTC",
]

# Financial columns stored in integer paise
_PAISE_COLS = [
    "PlanPricePaise",
    "TotalInvoicedPaise",
    "TotalDiscountPaise",
    "TotalTaxPaise",
    "TotalSettledPaise",
    "RefundAmountPaise",
    "ChargebackAmountPaise",
    "CreditNoteAmountPaise",
    "NetRevenuePaise",
    "HistoricalRewardValuePaise",
]

# Monthly revenue columns: SettledRevenue202510Paise … SettledRevenue202609Paise
_MONTH_REVENUE_COLS: list[str] = []  # populated after load

# Store loaded once; keyed by UserID
_STORE: dict[str, dict[str, Any]] = {}
_DF: pd.DataFrame | None = None


def _parse_yyyymmddhhmmss(series: pd.Series) -> pd.Series:
    """Parse a 14-digit integer column as datetime using YYYYMMDDHHmmSS."""
    return pd.to_datetime(
        series.astype(str).str.zfill(14),
        format="%Y%m%d%H%M%S",
        errors="coerce",
    )


def load_dataset(path: Path | None = None) -> pd.DataFrame:
    """
    Load and lightly validate the CSV.  Returns a cleaned DataFrame and
    populates the in-memory store.
    """
    global _DF, _STORE, _MONTH_REVENUE_COLS

    settings = get_settings()
    csv_path = path or settings.dataset_path

    logger.info("Loading dataset from %s", csv_path)
    df = pd.read_csv(csv_path, low_memory=False)

    # Identify monthly revenue columns
    _MONTH_REVENUE_COLS = [
        c for c in df.columns if c.startswith("SettledRevenue") and c.endswith("Paise")
    ]

    # Parse timestamp columns
    for col in _TIMESTAMP_COLS:
        if col in df.columns:
            df[col] = _parse_yyyymmddhhmmss(df[col])

    # Ensure paise columns are nullable int (no silent float coercion)
    for col in _PAISE_COLS + _MONTH_REVENUE_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if "UserID" in df.columns:
        df = df.set_index("UserID", drop=False)

    _DF = df
    _STORE = {}
    logger.info("Dataset loaded: %d records, %d columns", len(df), len(df.columns))
    return df


def get_dataframe() -> pd.DataFrame:
    """Return the loaded DataFrame, loading if necessary."""
    if _DF is None:
        load_dataset()
    return _DF  # type: ignore[return-value]


def get_record(user_id: str) -> dict[str, Any] | None:
    """Return the raw record for a UserID, or None if not found."""
    global _DF
    if _DF is None:
        load_dataset()
    if _DF is None or user_id not in _DF.index:
        return None
    row = _DF.loc[user_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return row.to_dict()


def month_revenue_cols() -> list[str]:
    """Return the list of monthly settled-revenue column names."""
    if _DF is None:
        load_dataset()
    return _MONTH_REVENUE_COLS
