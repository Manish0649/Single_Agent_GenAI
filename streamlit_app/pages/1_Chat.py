"""
1_Chat.py - Chat interface for RewardSphere RAG Knowledge Assistant
"""
import streamlit as st
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Chat - RewardSphere AI", page_icon="💬", layout="wide")

if "api_base_url" not in st.session_state:
    st.session_state["api_base_url"] = "http://localhost:8000"
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "selected_user_id" not in st.session_state:
    st.session_state["selected_user_id"] = "U0000000001"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.page-header{background:linear-gradient(135deg,#0f0c29,#302b63);border-radius:16px;padding:1.5rem 2rem;margin-bottom:1.5rem;}
.page-title{font-size:1.8rem;font-weight:800;background:linear-gradient(90deg,#6C63FF,#48CAE4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.page-sub{color:#adb5bd;font-size:.9rem;}
.msg-user{background:linear-gradient(135deg,rgba(108,99,255,0.13),rgba(48,43,99,0.26));border:1px solid rgba(108,99,255,0.27);border-radius:12px 12px 4px 12px;padding:1rem;margin:0.5rem 0;}
.msg-bot{background:linear-gradient(135deg,#16213e,#1a1a2e);border:1px solid rgba(72,202,228,0.27);border-radius:12px 12px 12px 4px;padding:1rem;margin:0.5rem 0;}
.msg-meta{font-size:.7rem;color:#666;margin-top:.3rem;}
.status-answered{color:#00b894;font-weight:600;}
.status-insufficient{color:#fdcb6e;font-weight:600;}
.status-refused{color:#d63031;font-weight:600;}
.evidence-card{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:.75rem;margin:.5rem 0;font-size:.82rem;}
.field-chip{display:inline-block;background:rgba(108,99,255,.15);border:1px solid rgba(108,99,255,.4);color:#a89cff;border-radius:999px;padding:.1rem .5rem;font-size:.7rem;margin:.15rem;}
.latency-badge{background:rgba(72,202,228,.1);border:1px solid rgba(72,202,228,.3);color:#48CAE4;border-radius:6px;padding:.1rem .5rem;font-size:.72rem;float:right;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    base_url = st.text_input("Backend URL", value=st.session_state["api_base_url"])
    st.session_state["api_base_url"] = base_url.rstrip("/")
    st.divider()
    st.markdown("#### 🔖 Quick User IDs")
    for uid in ["U0000000001", "U0000000002", "U0000000003", "U0000000010"]:
        if st.button(uid, key=f"quick_{uid}", use_container_width=True):
            st.session_state["selected_user_id"] = uid
            st.rerun()
    st.divider()
    st.markdown("#### 💡 Sample Questions")
    samples = [
        "What is the subscription status?",
        "How many successful payments were made?",
        "What is the risk status?",
        "Summarize the referral activity.",
        "What is the most used feature?",
        "What are the support ticket counts?",
        "What is the engagement profile?",
    ]
    for q in samples:
        label = q[:38] + ("..." if len(q) > 38 else "")
        if st.button(label, key=f"sq_{hash(q)}", use_container_width=True):
            st.session_state["prefill_question"] = q
            st.rerun()
    st.divider()
    if st.button("🗑️ Clear Chat History", use_container_width=True, type="secondary"):
        st.session_state["chat_history"] = []
        st.rerun()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <div class="page-title">💬 Chat Assistant</div>
  <div class="page-sub">Ask natural-language questions about any customer — powered by RAG + guardrails</div>
</div>
""", unsafe_allow_html=True)

# ── Input area ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])
with col1:
    user_id = st.text_input(
        "Customer User ID",
        value=st.session_state.get("selected_user_id", "U0000000001"),
        placeholder="e.g. U0000000001",
        help="Format: U followed by exactly 10 digits",
    )
    st.session_state["selected_user_id"] = user_id
with col2:
    st.markdown("<br/>", unsafe_allow_html=True)
    import re
    valid_uid = bool(re.match(r"^U\d{10}$", user_id.strip()))
    if valid_uid:
        st.success("✅ Valid User ID format")
    else:
        st.error("❌ Invalid format (U + 10 digits)")

question = st.text_area(
    "Your Question",
    value=st.session_state.pop("prefill_question", ""),
    placeholder="What is the subscription status and plan for this customer?",
    height=80,
)

btn_col1, _ = st.columns([1, 4])
with btn_col1:
    send = st.button("🚀 Send", type="primary", use_container_width=True, disabled=not valid_uid)

# ── Handle send ──────────────────────────────────────────────────────────────
if send and question.strip():
    uid = user_id.strip()
    q = question.strip()
    st.session_state["chat_history"].append({
        "role": "user",
        "user_id": uid,
        "question": q,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    with st.spinner("🔍 Retrieving context and generating answer..."):
        t0 = time.time()
        try:
            resp = requests.post(
                f"{st.session_state['api_base_url']}/chat",
                json={"question": q, "user_id": uid},
                timeout=60,
            )
            elapsed = round((time.time() - t0) * 1000)
            if resp.status_code == 200:
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "data": resp.json(),
                    "elapsed_ms": elapsed,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                })
            else:
                st.session_state["chat_history"].append({
                    "role": "error",
                    "detail": resp.json().get("detail", "Unknown error"),
                    "status_code": resp.status_code,
                    "elapsed_ms": elapsed,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                })
        except Exception as e:
            elapsed = round((time.time() - t0) * 1000)
            st.session_state["chat_history"].append({
                "role": "error",
                "detail": str(e),
                "elapsed_ms": elapsed,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            })
    st.rerun()

# ── Chat display ─────────────────────────────────────────────────────────────
st.markdown("---")

if not st.session_state["chat_history"]:
    st.markdown(
        "<div style='text-align:center;color:#555;padding:3rem;font-size:1rem;'>💬 No messages yet. Ask a question above!</div>",
        unsafe_allow_html=True,
    )

for msg in reversed(st.session_state["chat_history"]):
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="msg-user">
            <b>🧑 You</b> &nbsp; <code style='background:rgba(108,99,255,.15);padding:.1rem .4rem;border-radius:4px;font-size:.8rem;'>{msg["user_id"]}</code>
            <br/><br/>{msg["question"]}
            <div class="msg-meta">🕐 {msg["timestamp"]}</div>
        </div>""", unsafe_allow_html=True)

    elif msg["role"] == "assistant":
        d = msg["data"]
        status = d.get("status", "unknown")
        status_cls = {
            "answered": "status-answered",
            "insufficient_evidence": "status-insufficient",
            "refused": "status-refused",
        }.get(status, "")
        status_icon = {"answered": "✅", "insufficient_evidence": "⚠️", "refused": "🚫"}.get(status, "❓")

        st.markdown(f"""
        <div class="msg-bot">
            <span class="latency-badge">⏱ {msg["elapsed_ms"]}ms</span>
            <b>🤖 Assistant</b> &nbsp; <span class="{status_cls}">{status_icon} {status.upper()}</span>
            <br/><br/>{d.get("answer", "")}
            <div class="msg-meta">🕐 {msg["timestamp"]}</div>
        </div>""", unsafe_allow_html=True)

        evidence = d.get("evidence", [])
        limitations = d.get("limitations", [])

        if evidence:
            with st.expander(f"📎 Evidence ({len(evidence)} source(s))"):
                for ev in evidence:
                    fields_html = "".join(
                        f'<span class="field-chip">{f}</span>'
                        for f in ev.get("source_fields", [])
                    )
                    st.markdown(f"""
                    <div class="evidence-card">
                        <b>User:</b> {ev.get("user_id", "")} &nbsp; {fields_html}
                        <br/><span style="color:#888;font-size:.8rem;">{ev.get("explanation", "")}</span>
                    </div>""", unsafe_allow_html=True)

        if limitations:
            with st.expander(f"⚠️ Limitations ({len(limitations)})"):
                for lim in limitations:
                    st.warning(lim)

    elif msg["role"] == "error":
        sc = msg.get("status_code", "")
        st.markdown(f"""
        <div style="background:#2d0000;border:1px solid rgba(214,48,49,.4);border-radius:12px;padding:1rem;margin:.5rem 0;">
            ❌ <b>Error</b>{f" (HTTP {sc})" if sc else ""}: {msg.get("detail", "Unknown error")}
            <div style="font-size:.7rem;color:#666;">🕐 {msg["timestamp"]}</div>
        </div>""", unsafe_allow_html=True)
