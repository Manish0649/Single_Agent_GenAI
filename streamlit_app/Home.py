"""
Home.py -- Entry point for the RewardSphere RAG Knowledge Assistant Streamlit frontend.

Run with:
    streamlit run streamlit_app/Home.py
"""
import streamlit as st
import requests

st.set_page_config(
    page_title="RewardSphere AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "api_base_url" not in st.session_state:
    st.session_state["api_base_url"] = "http://localhost:8000"

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center;padding:1rem 0 0.5rem 0;'>
            <span style='font-size:2.5rem;'>🤖</span>
            <h2 style='margin:0;font-size:1.2rem;font-weight:700;color:#6C63FF;'>RewardSphere AI</h2>
            <p style='margin:0;font-size:0.75rem;color:#888;'>Single-Agent GenAI Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("### ⚙️ API Configuration")
    api_url = st.text_input("Backend URL", value=st.session_state["api_base_url"])
    st.session_state["api_base_url"] = api_url.rstrip("/")

    if st.button("🔄 Check Health", use_container_width=True):
        try:
            resp = requests.get(f"{st.session_state['api_base_url']}/health", timeout=5)
            data = resp.json()
            if data.get("status") == "ok":
                st.success("✅ API is healthy")
            else:
                st.warning("⚠️ API is degraded")
            for comp, sv in data.get("components", {}).items():
                icon = "✅" if sv.startswith("ok") else "❌"
                st.caption(f"{icon} {comp}: {sv}")
        except Exception as e:
            st.error(f"❌ Cannot reach API: {e}")

    st.divider()
    st.caption("Navigate using the pages in the sidebar above")

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.hero{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);border-radius:20px;padding:3rem 2rem;text-align:center;margin-bottom:2rem;}
.hero-title{font-size:2.6rem;font-weight:800;background:linear-gradient(90deg,#6C63FF,#48CAE4,#90E0EF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.hero-sub{color:#adb5bd;font-size:1rem;font-weight:300;}
.badge{display:inline-block;background:rgba(108,99,255,0.2);border:1px solid rgba(108,99,255,0.5);color:#a89cff;border-radius:999px;padding:.15rem .75rem;font-size:.75rem;margin:.2rem;}
.feat{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(108,99,255,0.3);border-radius:16px;padding:1.5rem;text-align:center;height:100%;}
.feat-icon{font-size:2rem;margin-bottom:.75rem;}
.feat-title{font-size:1rem;font-weight:600;color:#e0e0e0;}
.feat-desc{font-size:.82rem;color:#888;line-height:1.5;}
.scard{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(72,202,228,0.3);border-radius:12px;padding:1.2rem;text-align:center;}
.snum{font-size:2rem;font-weight:800;color:#48CAE4;}
.slbl{font-size:.8rem;color:#888;}
</style>
""", unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-title">🤖 RewardSphere AI Knowledge Assistant</div>
  <div class="hero-sub">Secure · Observable · Context-Aware RAG over your customer dataset</div>
  <br/>
  <span class="badge">FastAPI</span>
  <span class="badge">LangChain</span>
  <span class="badge">Milvus</span>
  <span class="badge">Pydantic AI</span>
  <span class="badge">Langfuse</span>
  <span class="badge">RAG</span>
</div>
""", unsafe_allow_html=True)

# ── Stats ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
for col, (num, lbl) in zip(
    [c1, c2, c3, c4],
    [("10","Golden Test Cases"), ("10","Security Scenarios"), ("6","API Endpoints"), ("5","Retrieval Top-K")],
):
    with col:
        st.markdown(
            f'<div class="scard"><div class="snum">{num}</div><div class="slbl">{lbl}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br/>", unsafe_allow_html=True)
st.markdown("### 🚀 What can you do?")
f1, f2, f3 = st.columns(3)
for col, (icon, title, desc) in zip(
    [f1, f2, f3],
    [
        ("💬", "Chat Assistant", "Ask natural-language questions about any customer. Powered by RAG with Milvus retrieval and guardrail protection."),
        ("👤", "Customer Lookup", "Browse structured customer profiles: subscription, payments, risk events, and revenue all in one view."),
        ("📊", "Model Accuracy", "Run the full evaluation suite (golden questions + security test cases) live against the API and see accuracy metrics."),
    ],
):
    with col:
        st.markdown(
            f'<div class="feat"><div class="feat-icon">{icon}</div><div class="feat-title">{title}</div><div class="feat-desc">{desc}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br/>", unsafe_allow_html=True)

with st.expander("🏗️ System Architecture"):
    st.code("""
Streamlit Frontend  (Chat | Customer | Evaluation)
         |
     FastAPI Backend
         |
   Input Guardrails  (validate / rate-limit / injection check)
         |
   Agent Orchestrator
      /       \\
LangChain    Pydantic AI
(RAG/Milvus) (Typed tools)
      \\       /
   Context Builder
         |
  Output Validation  (schema + business rules + safety)
         |
      Langfuse  (traces, metrics, evaluation)
""", language="text")

with st.expander("🛡️ Security Controls"):
    controls = {
        "Input": "UserID regex | Query length limit | Rate limiting",
        "Injection": "Regex pattern matching (direct + indirect)",
        "Retrieval": "Milvus metadata filter: user_id == authorized_user_id",
        "Tools": "Access control check per tool call",
        "Output": "Schema validation | Business rule checks | Content safety",
        "Logging": "Sensitive fields redacted | No full customer records in logs",
    }
    for layer, ctrl in controls.items():
        a, b = st.columns([1, 3])
        a.markdown(f"**{layer}**")
        b.code(ctrl)

st.divider()
st.caption("Built with ❤️ using Streamlit | FastAPI | LangChain | Milvus")
