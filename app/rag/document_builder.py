"""
Document builder: converts structured customer records into
searchable, human-readable text summaries suitable for vector embedding.

Only selected fields are included in the searchable summary.
The full structured record remains in the data repository for exact queries.
"""
from __future__ import annotations

from typing import Any

from langchain_core.documents import Document


def _paise_to_inr(paise: int | None) -> str:
    if paise is None:
        return "UNKNOWN"
    return f"₹{paise / 100:.2f}"


def build_customer_summary(record: dict[str, Any]) -> Document:
    """
    Create a LangChain Document containing a human-readable customer summary.

    The document id is set to UserID for deterministic lookup and deduplication.
    """
    uid = record.get("UserID", "UNKNOWN")
    rev_cols = [k for k in record if k.startswith("SettledRevenue") and k.endswith("Paise")]

    monthly_lines = []
    for col in sorted(rev_cols):
        raw = col.replace("SettledRevenue", "").replace("Paise", "")
        if len(raw) == 6:
            label = f"{raw[:4]}-{raw[4:]}"
        else:
            label = raw
        val = record.get(col)
        monthly_lines.append(f"  {label}: {_paise_to_inr(val)}")

    monthly_block = "\n".join(monthly_lines) if monthly_lines else "  No monthly data"

    text = f"""Customer ID: {uid}
Name: {record.get('SyntheticName', 'UNKNOWN')}
Segment: {record.get('CustomerSegment', 'UNKNOWN')}
Account Status: {record.get('AccountStatus', 'UNKNOWN')}
Region: {record.get('RegionCode', 'UNKNOWN')}
City: {record.get('CityCode', 'UNKNOWN')}
Acquisition Channel: {record.get('AcquisitionChannel', 'UNKNOWN')}
Preferred Language: {record.get('PreferredLanguage', 'UNKNOWN')}
Tenure Days: {record.get('TenureDays', 'UNKNOWN')}

Subscription:
  Plan: {record.get('PlanName', 'UNKNOWN')}
  Interval: {record.get('PlanInterval', 'UNKNOWN')}
  Status: {record.get('SubscriptionStatus', 'UNKNOWN')}
  Auto-Renew: {'Enabled' if record.get('AutoRenewEnabled') else 'Disabled'}
  Price: {_paise_to_inr(record.get('PlanPricePaise'))}

Payments:
  Attempts: {record.get('PaymentAttemptCount', 'UNKNOWN')}
  Successful: {record.get('SuccessfulPaymentCount', 'UNKNOWN')}
  Failed: {record.get('FailedPaymentCount', 'UNKNOWN')}
  Retries: {record.get('PaymentRetryCount', 'UNKNOWN')}
  Total Settled: {_paise_to_inr(record.get('TotalSettledPaise'))}
  Net Revenue: {_paise_to_inr(record.get('NetRevenuePaise'))}

Engagement:
  Usage Events: {record.get('UsageEventCount', 'UNKNOWN')}
  Total Usage Units: {record.get('TotalUsageUnits', 'UNKNOWN')}
  Months with Activity: {record.get('MonthsWithActivity', 'UNKNOWN')}
  Most Used Feature: {record.get('MostUsedFeature', 'UNKNOWN')}
  Login Events: {record.get('LoginEventCount', 'UNKNOWN')}

Support:
  Open Tickets: {record.get('OpenTicketCount', 'UNKNOWN')}
  Resolved Tickets: {record.get('ResolvedTicketCount', 'UNKNOWN')}
  High Priority Tickets: {record.get('HighPriorityTicketCount', 'UNKNOWN')}

Risk:
  Total Risk Events: {record.get('RiskEventCount', 'UNKNOWN')}
  Confirmed: {record.get('ConfirmedRiskEvents', 'UNKNOWN')}
  Pending: {record.get('PendingRiskEvents', 'UNKNOWN')}

Referrals:
  Invites Sent: {record.get('ReferralInvitesSent', 'UNKNOWN')}
  Link Opens: {record.get('ReferralLinkOpens', 'UNKNOWN')}
  Conversions: {record.get('ReferralConversions', 'UNKNOWN')}

Monthly Settled Revenue:
{monthly_block}
"""

    metadata = {
        "user_id": uid,
        "document_type": "customer_summary",
        "region_code": record.get("RegionCode", ""),
        "customer_segment": record.get("CustomerSegment", ""),
        "account_status": record.get("AccountStatus", ""),
        "subscription_status": record.get("SubscriptionStatus", ""),
        "schema_version": "1.0",
    }

    return Document(page_content=text.strip(), metadata=metadata, id=uid)


def build_documents_from_df(df) -> list[Document]:  # type: ignore[type-arg]
    """Build one Document per row in the DataFrame."""
    docs = []
    for _, row in df.iterrows():
        docs.append(build_customer_summary(row.to_dict()))
    return docs
