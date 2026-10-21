"""
Prompt injection detection.

Detects both direct injection (from user input) and indirect injection
(from text that could be in a retrieved document or tool output).

These are layered mitigations, not a guarantee that every attack is detected.
Authorization is enforced in Python, not by the LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns indicating an attempt to override or extract system instructions
_DIRECT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+.{0,40}(instructions|prompt|rules)",
    r"forget\s+(your\s+)?(instructions|system\s+prompt|role)",
    r"you\s+are\s+now\s+(?:an?\s+)?(?:different|unrestricted|evil|jailbroken|DAN)",
    r"act\s+as\s+(if\s+you\s+are\s+)?(?:an?\s+)?(?:different|unrestricted)",
    r"(?:what\s+(?:is|are)\s+|reveal\s+|show\s+|give\s+me\s+|tell\s+me\s+|print\s+)(?:the\s+|your\s+)?(?:system\s+prompt|api[_\s-]?key|credentials?|secrets?|passwords?|instructions)",
    r"reveal\s+(the\s+|your\s+)?(system\s+prompt|api\s+key|credentials?|secrets?|password)",
    r"print\s+(the\s+|your\s+)?(system\s+prompt|instructions)",
    r"your\s+(real\s+)?instructions\s+(are|say)",
    r"new\s+instructions?\s*[:–—\-\s]",
    r"expose\s+all\s+customer\s+data",
    r"print\s+every\s+customer\s+record",
    r"override\s+(the\s+)?system",
    r"sudo\s+",
    r"<\s*(?:script|iframe|svg|object)",       # HTML/JS injection
    r"\/\*.*?\*\/",                             # comment injection
    r"\bexec\s*\(",                             # code injection
    r"\beval\s*\(",
    r"DROP\s+TABLE",                            # SQL injection
    r"UNION\s+SELECT",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _DIRECT_INJECTION_PATTERNS]


@dataclass
class InjectionResult:
    is_injection: bool
    reason: str = ""


def detect_injection(text: str) -> InjectionResult:
    """
    Check *text* for known injection patterns.

    Returns InjectionResult with is_injection=True and a reason string
    if any pattern matches.
    """
    for pattern in _COMPILED:
        if pattern.search(text):
            return InjectionResult(
                is_injection=True,
                reason=f"Suspicious pattern detected: {pattern.pattern[:60]}",
            )
    return InjectionResult(is_injection=False)


def sanitize_for_context(text: str) -> str:
    """
    Return a sanitized copy of *text* safe to include in prompt context.

    Strips HTML tags and removes null bytes.
    """
    # Strip HTML-like tags
    text = re.sub(r"<[^>]{0,200}>", "", text)
    # Remove null bytes
    text = text.replace("\x00", "")
    return text
