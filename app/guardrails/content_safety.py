"""
Content safety module.

Evaluates whether a request or response violates application policies:
* No credential or secret disclosure.
* No cross-customer data exposure.
* No unsupported fraud accusations.
* No sensitive PII inference beyond what is recorded.
* Distinguishes recorded risk events from fraud conclusions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_CREDENTIAL_PATTERNS = [
    r"api[\s_-]?key",
    r"secret[\s_-]?key",
    r"password",
    r"bearer\s+token",
    r"authorization:\s*bearer",
    r"sk-[a-zA-Z0-9]{20,}",     # OpenAI-style key
    r"pk-lf-[a-zA-Z0-9]{20,}",  # Langfuse key
    r"MILVUS_TOKEN",
]
_FRAUD_ACCUSATION_PATTERNS = [
    r"(?<!not\s)(?<!not\s\ba\s)(?<!cannot\s)\b(is|confirmed|proven|clearly)\s+(a\s+)?fraud(ster|ulent)?\b",
    r"\b(definitely|certainly)\s+(committed|did)\s+(fraud|theft|crime)\b",
]

_CREDENTIAL_RE = [re.compile(p, re.IGNORECASE) for p in _CREDENTIAL_PATTERNS]
_FRAUD_RE = [re.compile(p, re.IGNORECASE) for p in _FRAUD_ACCUSATION_PATTERNS]


@dataclass
class SafetyResult:
    is_safe: bool
    violations: list[str]


def check_output_safety(text: str) -> SafetyResult:
    """Check a generated text string for policy violations."""
    violations: list[str] = []

    for pattern in _CREDENTIAL_RE:
        if pattern.search(text):
            violations.append(f"Possible credential exposure: {pattern.pattern}")

    for pattern in _FRAUD_RE:
        if pattern.search(text):
            violations.append(
                "Unsupported fraud accusation detected. Risk events must be "
                "described by their recorded status, not declared as fraud."
            )

    return SafetyResult(is_safe=len(violations) == 0, violations=violations)


def redact_sensitive_fields(record: dict) -> dict:  # type: ignore[type-arg]
    """
    Return a copy of *record* with sensitive fields redacted for logging.

    NEVER log full customer records in plaintext.
    """
    sensitive = {
        "SyntheticName",
        "ReferrerUserID",
        "MainPaymentMethod",
        "FirstCampaignID",
    }
    return {
        k: ("***REDACTED***" if k in sensitive else v)
        for k, v in record.items()
    }
