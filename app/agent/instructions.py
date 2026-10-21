"""
Agent system instructions – loaded at runtime.

Kept as a Python string so the orchestrator can version and swap it without
touching the main application code.
"""
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

SYSTEM_PROMPT: str = (_PROMPT_DIR / "system_prompt.txt").read_text(encoding="utf-8")
CUSTOMER_ANALYSIS_TEMPLATE: str = (
    _PROMPT_DIR / "customer_analysis.txt"
).read_text(encoding="utf-8")
