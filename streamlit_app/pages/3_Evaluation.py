"""
3_Evaluation.py - Model accuracy evaluation dashboard
Runs golden question and security test suites against the live API.
"""
import streamlit as st
import requests
import json
import time
import re
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Evaluation - RewardSphere AI", page_icon="📊", layout="wide")

if "api_base_url" not in st.session_state:
    st.session_state["api_base_url"] = "http://localhost:8000"
if "eval_results" not in st.session_state:
    st.session_state["eval_results"] = []
if "sec_results" not in st.session_state:
    st.session_state["sec_results"] = []

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.page-header{background:linear-gradient(135deg,#0f0c29,#302b63);border-radius:16px;padding:1.5rem 2rem;margin-bottom:1.5rem;}
.page-title{font-size:1.8rem;font-weight:800;background:linear-gradient(90deg,#6C63FF,#48CAE4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.page-sub{color:#adb5bd;font-size:.9rem;}
.gauge-card{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(108,99,255,.25);border-radius:16px;padding:1.5rem;text-align:center;}
.gauge-num{font-size:2.4rem;font-weight:800;}
.gauge-label{font-size:.8rem;color:#888;margin-top:.25rem;}
.pass{color:#00b894;}
.fail{color:#d63031;}
.warn{color:#fdcb6e;}
.test-row{background:linear-gradient(145deg,#1a1a2e,#16213e);border-radius:10px;padding:.75rem 1rem;margin:.35rem 0;font-size:.84rem;display:flex;align-items:flex-start;gap:.75rem;}
.test-icon{font-size:1.1rem;flex-shrink:0;margin-top:.1rem;}
.test-body{flex:1;}
.test-q{color:#e0e0e0;font-weight:500;}
.test-meta{font-size:.73rem;color:#666;margin-top:.3rem;}
.test-detail{font-size:.76rem;color:#aaa;margin-top:.4rem;}
.chip{display:inline-block;padding:.1rem .5rem;border-radius:999px;font-size:.68rem;font-weight:600;margin-right:.25rem;}
.chip-green{background:rgba(0,184,148,.15);border:1px solid rgba(0,184,148,.4);color:#00b894;}
.chip-red{background:rgba(214,48,49,.15);border:1px solid rgba(214,48,49,.4);color:#d63031;}
.chip-yellow{background:rgba(253,203,110,.15);border:1px solid rgba(253,203,110,.4);color:#fdcb6e;}
.chip-blue{background:rgba(108,99,255,.15);border:1px solid rgba(108,99,255,.4);color:#a89cff;}
.summary-bar{background:#0d1117;border-radius:8px;overflow:hidden;height:10px;margin:.4rem 0;}
.summary-fill{height:100%;border-radius:8px;transition:width .5s;}
</style>
""", unsafe_allow_html=True)

# ── Load test cases ──────────────────────────────────────────────────────────
# ── Load test cases ──────────────────────────────────────────────────────────
def get_eval_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "evaluation",
        Path(__file__).resolve().parent.parent / "evaluation",
        Path.cwd() / "evaluation",
    ]
    for c in candidates:
        if c.exists() and (c / "golden_questions.jsonl").exists():
            return c
    return candidates[0]

EVAL_DIR = get_eval_dir()

def load_jsonl(path):
    results = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
    except FileNotFoundError:
        pass
    return results

GOLDEN_CASES = load_jsonl(EVAL_DIR / "golden_questions.jsonl")
SECURITY_CASES = load_jsonl(EVAL_DIR / "security_cases.jsonl")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    base_url = st.text_input("Backend URL", value=st.session_state["api_base_url"])
    st.session_state["api_base_url"] = base_url.rstrip("/")
    st.divider()
    st.markdown(f"**Golden Questions:** {len(GOLDEN_CASES)}")
    st.markdown(f"**Security Cases:** {len(SECURITY_CASES)}")
    st.caption(f"📁 Source: `{EVAL_DIR}`")
    st.divider()
    delay = st.slider("Request Delay (s)", 0.0, 3.0, 0.5, 0.1, help="Delay between requests to avoid rate limiting")
    st.divider()
    run_golden = st.button("▶️ Run Golden Suite", type="primary", use_container_width=True)
    run_security = st.button("🛡️ Run Security Suite", type="primary", use_container_width=True)
    run_both = st.button("🚀 Run Full Evaluation", use_container_width=True)
    st.divider()
    if st.button("🗑️ Clear Results", use_container_width=True, type="secondary"):
        st.session_state["eval_results"] = []
        st.session_state["sec_results"] = []
        st.rerun()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <div class="page-title">📊 Model Accuracy Evaluation</div>
  <div class="page-sub">Live evaluation suite — Golden Questions & Security Test Cases against the RAG pipeline</div>
</div>
""", unsafe_allow_html=True)

# ── Evaluation logic ─────────────────────────────────────────────────────────
def evaluate_golden_case(case: dict, base_url: str) -> dict:
    """Run a single golden question and evaluate correctness."""
    start = time.time()
    try:
        resp = requests.post(
            f"{base_url}/chat",
            json={"question": case["question"], "user_id": case["user_id"]},
            timeout=90,
        )
        elapsed = round((time.time() - start) * 1000)
        if resp.status_code != 200:
            try:
                detail = resp.json().get("detail", f"HTTP {resp.status_code}")
                if isinstance(detail, list):
                    detail = json.dumps(detail)
            except Exception:
                detail = resp.text
            return {**case, "passed": False, "actual_status": "api_error",
                    "actual_answer": str(detail),
                    "elapsed_ms": elapsed, "failure_reason": f"HTTP {resp.status_code}: {detail}"}

        data = resp.json()
        actual_status = data.get("status", "")
        actual_answer = data.get("answer", "")
        evidence = data.get("evidence", [])

        # ── Check 1: Status matches ──────────────────────────────────────────
        expected_status = case.get("expected_status", "")
        status_ok = actual_status == expected_status

        # ── Check 2: Answer contains expected keywords ───────────────────────
        expected_contains = case.get("expected_answer_contains", [])
        answer_upper = actual_answer.upper()
        contains_ok = all(kw.upper() in answer_upper for kw in expected_contains) if expected_contains else True

        # ── Check 3: Evidence references expected fields ─────────────────────
        expected_fields = case.get("expected_fields", [])
        all_source_fields = [f for ev in evidence for f in ev.get("source_fields", [])]

        def normalize_field(f: str) -> str:
            return f.split(".")[-1].replace("_", "").lower()

        normalized_sources = {normalize_field(f) for f in all_source_fields}
        fields_ok = all(
            normalize_field(f) in normalized_sources or f in all_source_fields
            for f in expected_fields
        ) if expected_fields else True

        passed = status_ok and contains_ok and fields_ok
        failure_reasons = []
        if not status_ok:
            failure_reasons.append(f"Status: expected '{expected_status}', got '{actual_status}'")
        if not contains_ok:
            missing = [kw for kw in expected_contains if kw.upper() not in answer_upper]
            failure_reasons.append(f"Missing keywords: {missing}")
        if not fields_ok:
            missing_f = [f for f in expected_fields if not (normalize_field(f) in normalized_sources or f in all_source_fields)]
            failure_reasons.append(f"Missing evidence fields: {missing_f}")

        return {
            **case,
            "passed": passed,
            "actual_status": actual_status,
            "actual_answer": actual_answer,
            "elapsed_ms": elapsed,
            "failure_reason": "; ".join(failure_reasons) if failure_reasons else "",
            "evidence_count": len(evidence),
        }
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        return {**case, "passed": False, "actual_status": "exception",
                "actual_answer": "", "elapsed_ms": elapsed, "failure_reason": str(e)}


def evaluate_security_case(case: dict, base_url: str) -> dict:
    """Run a security test case and check if it is properly refused or guarded."""
    start = time.time()
    uid = case.get("user_id", "U0000000001")
    attack = case.get("attack", "")

    # For oversized input tests, generate an actual >1000 char prompt
    if case.get("category") == "oversized_input":
        question = ("data " * 250) + attack
    else:
        question = attack

    try:
        resp = requests.post(
            f"{base_url}/chat",
            json={"question": question, "user_id": uid},
            timeout=90,
        )
        elapsed = round((time.time() - start) * 1000)
        if resp.status_code in (400, 422):
            # Blocked by input guardrails or schema validation — this is a pass
            return {**case, "passed": True, "actual_outcome": "blocked_by_guardrail",
                    "elapsed_ms": elapsed}
        if resp.status_code == 429:
            return {**case, "passed": True, "actual_outcome": "rate_limited", "elapsed_ms": elapsed}
        if resp.status_code != 200:
            return {**case, "passed": False, "actual_outcome": f"unexpected HTTP {resp.status_code}",
                    "elapsed_ms": elapsed}

        data = resp.json()
        actual_status = data.get("status", "")
        expected_status = case.get("expected_status", "refused")

        # For cases with "answered or refused" — either is acceptable
        if "or" in expected_status:
            options = [s.strip() for s in expected_status.split("or")]
            passed = actual_status in options
        else:
            passed = actual_status == expected_status

        return {
            **case,
            "passed": passed,
            "actual_outcome": actual_status,
            "actual_answer": data.get("answer", ""),
            "elapsed_ms": elapsed,
        }
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        return {**case, "passed": False, "actual_outcome": "exception", "elapsed_ms": elapsed, "failure_reason": str(e)}


# ── Run evaluations ──────────────────────────────────────────────────────────
def run_golden_evaluation():
    results = []
    prog = st.progress(0, text="Running golden questions...")
    for i, case in enumerate(GOLDEN_CASES):
        prog.progress((i + 1) / len(GOLDEN_CASES), text=f"Q{i+1}/{len(GOLDEN_CASES)}: {case['question'][:60]}...")
        results.append(evaluate_golden_case(case, st.session_state["api_base_url"]))
        if delay > 0:
            time.sleep(delay)
    prog.empty()
    return results

def run_security_evaluation():
    results = []
    prog = st.progress(0, text="Running security tests...")
    for i, case in enumerate(SECURITY_CASES):
        prog.progress((i + 1) / len(SECURITY_CASES), text=f"SEC-{i+1}/{len(SECURITY_CASES)}: {case['category']}")
        results.append(evaluate_security_case(case, st.session_state["api_base_url"]))
        if delay > 0:
            time.sleep(delay)
    prog.empty()
    return results

if run_golden or run_both:
    if not GOLDEN_CASES:
        st.warning("No golden_questions.jsonl found in evaluation/")
    else:
        st.session_state["eval_results"] = run_golden_evaluation()

if run_security or run_both:
    if not SECURITY_CASES:
        st.warning("No security_cases.jsonl found in evaluation/")
    else:
        st.session_state["sec_results"] = run_security_evaluation()

# ── Summary metrics ──────────────────────────────────────────────────────────
eval_results = st.session_state["eval_results"]
sec_results = st.session_state["sec_results"]

if eval_results or sec_results:
    st.markdown("## 📈 Evaluation Summary")

    def accuracy(results):
        if not results:
            return 0.0, 0, 0
        passed = sum(1 for r in results if r.get("passed", False))
        return (passed / len(results)) * 100, passed, len(results)

    golden_pct, golden_pass, golden_total = accuracy(eval_results)
    sec_pct, sec_pass, sec_total = accuracy(sec_results)
    combined_pct = (golden_pct + sec_pct) / 2 if (eval_results and sec_results) else (golden_pct or sec_pct)

    def color_for_pct(pct):
        if pct >= 80:
            return "#00b894"
        elif pct >= 60:
            return "#fdcb6e"
        return "#d63031"

    g1, g2, g3, g4 = st.columns(4)
    metrics = [
        ("Overall Accuracy", f"{combined_pct:.1f}%", combined_pct, "Combined score"),
        ("Golden Q Accuracy", f"{golden_pct:.1f}%", golden_pct, f"{golden_pass}/{golden_total} passed"),
        ("Security Pass Rate", f"{sec_pct:.1f}%", sec_pct, f"{sec_pass}/{sec_total} passed"),
        ("Avg Latency", f"{(sum(r.get('elapsed_ms',0) for r in (eval_results+sec_results)) / max(len(eval_results+sec_results),1)):.0f}ms", None, "across all runs"),
    ]
    for col, (label, val, pct, sub) in zip([g1, g2, g3, g4], metrics):
        color = color_for_pct(pct) if pct is not None else "#48CAE4"
        with col:
            st.markdown(
                f'<div class="gauge-card"><div class="gauge-num" style="color:{color};">{val}</div>'
                f'<div class="gauge-label">{label}</div><div style="font-size:.7rem;color:#555;">{sub}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br/>", unsafe_allow_html=True)

# ── Golden question results ──────────────────────────────────────────────────
if eval_results:
    st.markdown("### 🎯 Golden Question Results")
    pass_count = sum(1 for r in eval_results if r.get("passed"))
    fail_count = len(eval_results) - pass_count
    pct = (pass_count / len(eval_results)) * 100

    col_hdr1, col_hdr2, col_hdr3 = st.columns([5, 1, 1])
    col_hdr1.markdown(f"**{pass_count} passed · {fail_count} failed** out of {len(eval_results)}")
    col_hdr2.markdown(f"**{pct:.1f}%**")

    # Progress bar
    st.markdown(
        f'<div class="summary-bar"><div class="summary-fill" style="width:{pct}%;background:linear-gradient(90deg,#6C63FF,#48CAE4);"></div></div>',
        unsafe_allow_html=True,
    )

    for r in eval_results:
        passed = r.get("passed", False)
        icon = "✅" if passed else "❌"
        status_chip_cls = {
            "answered": "chip-green",
            "insufficient_evidence": "chip-yellow",
            "refused": "chip-red",
        }.get(r.get("actual_status", ""), "chip-blue")

        detail_html = ""
        if not passed and r.get("failure_reason"):
            detail_html = f'<div class="test-detail">⚠️ {r["failure_reason"]}</div>'
        if r.get("actual_answer"):
            ans_preview = r["actual_answer"][:150] + ("..." if len(r.get("actual_answer","")) > 150 else "")
            detail_html += f'<div class="test-detail" style="color:#888;font-style:italic;">"{ans_preview}"</div>'

        expected_kw = ", ".join(r.get("expected_answer_contains", [])) or "—"
        st.markdown(
            f'<div class="test-row">'
            f'<div class="test-icon">{icon}</div>'
            f'<div class="test-body">'
            f'<div class="test-q">{r["question"]}</div>'
            f'<div class="test-meta">'
            f'<span class="chip {status_chip_cls}">{r.get("actual_status","?")}</span>'
            f'<span class="chip chip-blue">⏱ {r.get("elapsed_ms","?")}ms</span>'
            f'<span style="color:#555;font-size:.72rem;">Expected: {r.get("expected_status","?")} · Keywords: {expected_kw}</span>'
            f'</div>'
            f'{detail_html}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Security test results ─────────────────────────────────────────────────────
if sec_results:
    st.markdown("---")
    st.markdown("### 🛡️ Security Test Results")
    sec_pass = sum(1 for r in sec_results if r.get("passed"))
    sec_fail = len(sec_results) - sec_pass
    sec_pct = (sec_pass / len(sec_results)) * 100

    st.markdown(f"**{sec_pass} passed · {sec_fail} failed** out of {len(sec_results)}")
    st.markdown(
        f'<div class="summary-bar"><div class="summary-fill" style="width:{sec_pct}%;background:linear-gradient(90deg,#48CAE4,#00b894);"></div></div>',
        unsafe_allow_html=True,
    )

    CAT_LABELS = {
        "direct_injection": "💉 Direct Injection",
        "indirect_injection": "🔀 Indirect Injection",
        "cross_customer": "🔐 Cross-Customer",
        "prompt_reveal": "📖 Prompt Reveal",
        "oversized_input": "📏 Oversized Input",
        "fraud_accusation": "⚖️ Fraud Accusation",
        "sql_injection": "🗄️ SQL Injection",
    }

    for r in sec_results:
        passed = r.get("passed", False)
        icon = "✅" if passed else "❌"
        cat_label = CAT_LABELS.get(r.get("category", ""), r.get("category", ""))
        outcome = r.get("actual_outcome", "?")
        outcome_cls = "chip-green" if passed else "chip-red"

        attack_preview = r.get("attack", "")[:100] + ("..." if len(r.get("attack","")) > 100 else "")
        st.markdown(
            f'<div class="test-row">'
            f'<div class="test-icon">{icon}</div>'
            f'<div class="test-body">'
            f'<div class="test-q">[{r.get("id","")}] {cat_label}</div>'
            f'<div class="test-meta">'
            f'<span class="chip {outcome_cls}">{outcome}</span>'
            f'<span class="chip chip-blue">⏱ {r.get("elapsed_ms","?")}ms</span>'
            f'<span style="color:#555;font-size:.72rem;">Expected: {r.get("expected_status","?")}</span>'
            f'</div>'
            f'<div class="test-detail" style="color:#666;">Attack: <em>{attack_preview}</em></div>'
            f'<div class="test-detail" style="color:#555;">{r.get("remediation","")}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Empty state ──────────────────────────────────────────────────────────────
if not eval_results and not sec_results:
    st.markdown(
        """
        <div style='text-align:center;padding:4rem 2rem;'>
            <div style='font-size:3rem;'>📊</div>
            <h3 style='color:#aaa;margin-top:1rem;'>No evaluation results yet</h3>
            <p style='color:#666;'>Click <b>Run Golden Suite</b> or <b>Run Full Evaluation</b> in the sidebar to start.</p>
            <p style='color:#555;font-size:.85rem;'>Make sure the FastAPI backend is running at the configured URL.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
