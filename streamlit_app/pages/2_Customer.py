"""
2_Customer.py - Customer lookup and structured profile view
"""
import streamlit as st
import requests

st.set_page_config(page_title="Customer - RewardSphere AI", page_icon="👤", layout="wide")

if "api_base_url" not in st.session_state:
    st.session_state["api_base_url"] = "http://localhost:8000"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.page-header{background:linear-gradient(135deg,#0f0c29,#302b63);border-radius:16px;padding:1.5rem 2rem;margin-bottom:1.5rem;}
.page-title{font-size:1.8rem;font-weight:800;background:linear-gradient(90deg,#6C63FF,#48CAE4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.page-sub{color:#adb5bd;font-size:.9rem;}
.info-card{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(108,99,255,.25);border-radius:14px;padding:1.25rem;margin-bottom:1rem;}
.info-section{font-size:.75rem;font-weight:600;color:#6C63FF;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.75rem;}
.kv-row{display:flex;justify-content:space-between;padding:.3rem 0;border-bottom:1px solid rgba(255,255,255,.05);}
.kv-key{color:#888;font-size:.82rem;}
.kv-val{color:#e0e0e0;font-size:.82rem;font-weight:500;text-align:right;}
.pill{display:inline-block;padding:.15rem .65rem;border-radius:999px;font-size:.72rem;font-weight:600;}
.pill-green{background:rgba(0,184,148,.15);border:1px solid rgba(0,184,148,.4);color:#00b894;}
.pill-red{background:rgba(214,48,49,.15);border:1px solid rgba(214,48,49,.4);color:#d63031;}
.pill-yellow{background:rgba(253,203,110,.15);border:1px solid rgba(253,203,110,.4);color:#fdcb6e;}
.pill-blue{background:rgba(108,99,255,.15);border:1px solid rgba(108,99,255,.4);color:#a89cff;}
.metric-big{font-size:1.8rem;font-weight:800;color:#48CAE4;}
.metric-label{font-size:.75rem;color:#888;margin-top:.2rem;}
.rev-card{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(72,202,228,.25);border-radius:14px;padding:1.25rem;margin-bottom:1rem;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    base_url = st.text_input("Backend URL", value=st.session_state["api_base_url"])
    st.session_state["api_base_url"] = base_url.rstrip("/")
    st.divider()
    st.markdown("#### 🔖 Quick User IDs")
    for uid in ["U0000000001", "U0000000002", "U0000000003", "U0000000010", "U0000000100"]:
        if st.button(uid, key=f"cu_{uid}", use_container_width=True):
            st.session_state["cu_selected"] = uid
            st.rerun()

st.markdown("""
<div class="page-header">
  <div class="page-title">👤 Customer Lookup</div>
  <div class="page-sub">Structured customer profile — subscription, payments, risk events and revenue</div>
</div>
""", unsafe_allow_html=True)

import re
col1, col2 = st.columns([3, 1])
with col1:
    user_id = st.text_input(
        "Customer User ID",
        value=st.session_state.get("cu_selected", "U0000000001"),
        placeholder="e.g. U0000000001",
    )
with col2:
    st.markdown("<br/>", unsafe_allow_html=True)
    lookup = st.button("🔍 Lookup", type="primary", use_container_width=True)

# ── Data fetch ───────────────────────────────────────────────────────────────
summary_data = None
revenue_data = None
error_msg = None

if lookup or "cu_selected" in st.session_state:
    uid = user_id.strip()
    if not re.match(r"^U\d{10}$", uid):
        st.error("❌ Invalid User ID format (U + 10 digits)")
    else:
        col_s, col_r = st.columns(2)
        with col_s:
            with st.spinner("Fetching summary..."):
                try:
                    resp = requests.get(f"{st.session_state['api_base_url']}/customers/{uid}/summary", timeout=15)
                    if resp.status_code == 200:
                        summary_data = resp.json()
                    elif resp.status_code == 404:
                        error_msg = "Customer not found."
                    else:
                        error_msg = resp.json().get("detail", "Error fetching summary.")
                except Exception as e:
                    error_msg = str(e)
        with col_r:
            with st.spinner("Fetching revenue..."):
                try:
                    resp2 = requests.get(f"{st.session_state['api_base_url']}/customers/{uid}/revenue", timeout=15)
                    if resp2.status_code == 200:
                        revenue_data = resp2.json()
                except Exception:
                    pass  # revenue is optional display

if error_msg:
    st.error(f"❌ {error_msg}")

# ── Summary display ──────────────────────────────────────────────────────────
def paise_to_inr(p):
    return f"₹{p/100:,.2f}" if p is not None else "N/A"

def pill(val, mapping):
    cls = mapping.get(str(val).upper(), "pill-blue")
    return f'<span class="pill {cls}">{val}</span>'

if summary_data:
    s = summary_data
    st.markdown("---")

    # ── Quick metric row ─────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    metrics = [
        ("Payment Attempts", s.get("payment_attempts", 0)),
        ("Successful Payments", s.get("successful_payments", 0)),
        ("Failed Payments", s.get("failed_payments", 0)),
        ("Open Tickets", s.get("open_tickets", 0)),
        ("Risk Events", s.get("risk_events", 0)),
    ]
    for col, (label, val) in zip([m1, m2, m3, m4, m5], metrics):
        with col:
            st.markdown(
                f'<div style="background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(108,99,255,.25);border-radius:12px;padding:1rem;text-align:center;">'
                f'<div class="metric-big">{val}</div><div class="metric-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br/>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    # ── Profile card ─────────────────────────────────────────────────────────
    with col_a:
        sub_status = s.get("subscription_status", "")
        acct_status = s.get("account_status", "")
        sub_pill = pill(sub_status, {"ACTIVE": "pill-green", "CANCELLED": "pill-red", "TRIAL": "pill-yellow"})
        acct_pill = pill(acct_status, {"ACTIVE": "pill-green", "SUSPENDED": "pill-red", "CLOSED": "pill-red"})

        st.markdown(f"""
        <div class="info-card">
          <div class="info-section">👤 Profile</div>
          <div class="kv-row"><span class="kv-key">User ID</span><span class="kv-val"><code>{s.get("user_id","")}</code></span></div>
          <div class="kv-row"><span class="kv-key">Name</span><span class="kv-val">{s.get("name","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Segment</span><span class="kv-val">{s.get("segment","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Account Status</span><span class="kv-val">{acct_pill}</span></div>
          <div class="kv-row"><span class="kv-key">Region</span><span class="kv-val">{s.get("region","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">City</span><span class="kv-val">{s.get("city","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Acquisition Channel</span><span class="kv-val">{s.get("acquisition_channel","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Preferred Language</span><span class="kv-val">{s.get("preferred_language","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Tenure</span><span class="kv-val">{s.get("tenure_days","N/A")} days</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="info-card">
          <div class="info-section">💳 Subscription</div>
          <div class="kv-row"><span class="kv-key">Plan</span><span class="kv-val">{s.get("subscription_plan","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Interval</span><span class="kv-val">{s.get("subscription_interval","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Status</span><span class="kv-val">{sub_pill}</span></div>
          <div class="kv-row"><span class="kv-key">Auto-Renew</span><span class="kv-val">{"✅ Yes" if s.get("auto_renew") else "❌ No"}</span></div>
          <div class="kv-row"><span class="kv-key">Plan Price</span><span class="kv-val">{paise_to_inr(s.get("plan_price_paise"))}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ── Payments & Risk card ──────────────────────────────────────────────────
    with col_b:
        st.markdown(f"""
        <div class="info-card">
          <div class="info-section">💰 Payments</div>
          <div class="kv-row"><span class="kv-key">Payment Attempts</span><span class="kv-val">{s.get("payment_attempts","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Successful Payments</span><span class="kv-val" style="color:#00b894;">{s.get("successful_payments","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Failed Payments</span><span class="kv-val" style="color:#d63031;">{s.get("failed_payments","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Total Settled</span><span class="kv-val">{paise_to_inr(s.get("total_settled_paise"))}</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="info-card">
          <div class="info-section">🎫 Support Tickets</div>
          <div class="kv-row"><span class="kv-key">Open Tickets</span><span class="kv-val" style="color:#fdcb6e;">{s.get("open_tickets","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Resolved Tickets</span><span class="kv-val" style="color:#00b894;">{s.get("resolved_tickets","N/A")}</span></div>
        </div>
        """, unsafe_allow_html=True)

        risk_color = "#d63031" if (s.get("risk_events", 0) or 0) > 0 else "#00b894"
        st.markdown(f"""
        <div class="info-card">
          <div class="info-section">⚠️ Risk Events</div>
          <div class="kv-row"><span class="kv-key">Total Risk Events</span><span class="kv-val" style="color:{risk_color};">{s.get("risk_events","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Confirmed Risk Events</span><span class="kv-val" style="color:#d63031;">{s.get("confirmed_risk_events","N/A")}</span></div>
          <div class="kv-row"><span class="kv-key">Pending Risk Events</span><span class="kv-val" style="color:#fdcb6e;">{s.get("pending_risk_events","N/A")}</span></div>
        </div>
        """, unsafe_allow_html=True)

# ── Revenue display ──────────────────────────────────────────────────────────
if revenue_data:
    r = revenue_data
    st.markdown("### 📈 Revenue Metrics")
    rc1, rc2, rc3 = st.columns(3)
    rev_metrics = [
        ("Total Invoiced", paise_to_inr(r.get("total_invoiced_paise")), "#6C63FF"),
        ("Total Settled", paise_to_inr(r.get("total_settled_paise")), "#00b894"),
        ("Net Revenue", paise_to_inr(r.get("net_revenue_paise")), "#48CAE4"),
    ]
    for col, (label, val, color) in zip([rc1, rc2, rc3], rev_metrics):
        with col:
            st.markdown(
                f'<div style="background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(108,99,255,.2);border-radius:12px;padding:1.2rem;text-align:center;">'
                f'<div style="font-size:1.6rem;font-weight:800;color:{color};">{val}</div>'
                f'<div style="font-size:.78rem;color:#888;">{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br/>", unsafe_allow_html=True)
    rc4, rc5, rc6 = st.columns(3)
    rev_metrics2 = [
        ("Refunds", paise_to_inr(r.get("refund_amount_paise")), "#fdcb6e"),
        ("Chargebacks", paise_to_inr(r.get("chargeback_amount_paise")), "#d63031"),
        ("Credit Notes", paise_to_inr(r.get("credit_note_amount_paise")), "#a89cff"),
    ]
    for col, (label, val, color) in zip([rc4, rc5, rc6], rev_metrics2):
        with col:
            st.markdown(
                f'<div style="background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(108,99,255,.2);border-radius:12px;padding:1.2rem;text-align:center;">'
                f'<div style="font-size:1.6rem;font-weight:800;color:{color};">{val}</div>'
                f'<div style="font-size:.78rem;color:#888;">{label}</div></div>',
                unsafe_allow_html=True,
            )

    monthly = r.get("monthly_settled", {})
    if monthly:
        st.markdown("<br/>### 📅 Monthly Settled Revenue")
        import pandas as pd
        df_monthly = pd.DataFrame(
            [(k, v / 100) for k, v in sorted(monthly.items())],
            columns=["Month", "Settled (₹)"],
        )
        st.bar_chart(df_monthly.set_index("Month"))
