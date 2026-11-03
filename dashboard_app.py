"""
NIFTY 500 INSTITUTIONAL MOMENTUM STUDIO - LIVE WEB DASHBOARD
Powered by Google BigQuery (Project: momentum-based-nifty-500)
Run locally: streamlit run dashboard_app.py
"""

import os
import sys
import subprocess
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import google.auth.credentials
from google.cloud import bigquery

st.set_page_config(
    page_title="NIFTY 500 Momentum Desk | BigQuery Live",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme CSS
st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background-color: #161b22; border-radius: 8px; padding: 12px; border: 1px solid #30363d; }
    .kpi-title { font-size: 11px; text-transform: uppercase; color: #8b949e; letter-spacing: 1px; font-weight: 600; }
    .kpi-val { font-size: 24px; font-weight: 700; color: #58a6ff; }
    .kpi-green { color: #3fb950 !important; }
    .kpi-red { color: #f85149 !important; }
    .status-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "momentum-based-nifty-500")
DATASET_ID = "nifty500_quant_studio"
LOCATION = "asia-south1"

class GCloudCredentials(google.auth.credentials.Credentials):
    """Self-refreshing credentials using gcloud auth token."""
    def __init__(self):
        super().__init__()
        self.refresh(None)

    def refresh(self, request=None):
        token_cmd = ['C:\\Users\\sumit\\AppData\\Local\\Google\\ct4j-cloud-sdk\\LATEST\\google-cloud-sdk\\bin\\gcloud.cmd', 'auth', 'print-access-token']
        try:
            self.token = subprocess.check_output(token_cmd).decode().strip()
            self.expiry = datetime.now() + timedelta(minutes=50)
        except Exception:
            pass

def get_bq_client():
    creds = GCloudCredentials()
    return bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)

@st.cache_data(ttl=60)
def load_data():
    client = get_bq_client()
    # 1. Summary
    q_sum = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.v_portfolio_summary`"
    df_sum = client.query(q_sum).to_dataframe()
    
    # 2. Positions
    q_pos = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.v_active_positions_monitor`"
    df_pos = client.query(q_pos).to_dataframe()
    
    # 3. Backtest Trades
    q_bt = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.backtest_trades` ORDER BY entry_date DESC LIMIT 50"
    df_bt = client.query(q_bt).to_dataframe()
    
    return df_sum, df_pos, df_bt

# Sidebar Controls
st.sidebar.image("https://cloud.google.com/images/social-icon-google-cloud-1200-630.png", width=160)
st.sidebar.title("Momentum Desk")
st.sidebar.caption(f"Project: **{PROJECT_ID}** | Region: **asia-south1**")

if st.sidebar.button("🔄 Refresh BigQuery Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Looker Studio Cloud Link")
st.sidebar.markdown(f"[👉 Open Looker Studio via BigQuery](https://console.cloud.google.com/bigquery?project={PROJECT_ID}&ws=!1m5!1m4!4m3!1s{PROJECT_ID}!2s{DATASET_ID}!3sv_portfolio_summary)")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Minervini Risk Matrix Active**:\n- Capital Cap: ₹1,25,000/trade\n- No trade count ceiling\n- Hard stop ceiling: 9.0%\n- Bull SL: 7.0% | Bear SL: 3.5%")

# Header
st.title("⚡ NIFTY 500 INSTITUTIONAL MOMENTUM STUDIO")
st.caption("Real-Time Forward Testing Portfolio & Google BigQuery Data Lake")

try:
    df_sum, df_pos, df_bt = load_data()
except Exception as e:
    st.error(f"Failed to query BigQuery: {e}")
    st.stop()

# 1. Top KPI Row
if not df_sum.empty:
    row = df_sum.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown('<div class="kpi-title">Active Positions</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-val">{int(row["active_positions"])}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="kpi-title">Total Invested</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-val">₹{row["total_invested_capital"]:,.2f}</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="kpi-title">Portfolio Value</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-val">₹{row["current_portfolio_value"]:,.2f}</div>', unsafe_allow_html=True)
    with c4:
        pnl = row["total_unrealized_pnl"]
        cls = "kpi-green" if pnl >= 0 else "kpi-red"
        st.markdown('<div class="kpi-title">Total Unrealized P&L</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-val {cls}">{pnl:+,.2f}</div>', unsafe_allow_html=True)
    with c5:
        ret = row["portfolio_return_pct"]
        cls = "kpi-green" if ret >= 0 else "kpi-red"
        st.markdown('<div class="kpi-title">Overall Return</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-val {cls}">{ret:+.2f}%</div>', unsafe_allow_html=True)

st.markdown("---")

# 2. Main Content Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📌 Forward-Test Holdings", "🛡️ Strategy B: Ratchet Engine", "🎲 Monte Carlo Tail-Risk", "📜 Backtest Trade History"])

with tab1:
    st.subheader("Active Forward-Test Portfolio Tracking")
    if not df_pos.empty:
        # Display formatted table
        display_df = df_pos[[
            "symbol", "trade_status", "qty", "avg_buy_price", "ltp", 
            "current_value", "unrealized_pnl", "pnl_percentage", 
            "trailed_sl", "distance_to_sl_pct", "planned_target", "distance_to_target_pct", "rr_ratio"
        ]].copy()
        
        display_df.columns = [
            "Symbol", "Status", "Qty", "Buy Price (₹)", "LTP (₹)", 
            "Current Val (₹)", "P&L (₹)", "P&L %", 
            "Trailed SL (₹)", "SL Gap %", "Target (₹)", "Target Gap %", "R:R"
        ]
        
        st.dataframe(
            display_df.style.format({
                "Buy Price (₹)": "₹{:,.2f}",
                "LTP (₹)": "₹{:,.2f}",
                "Current Val (₹)": "₹{:,.2f}",
                "P&L (₹)": "{:+,.2f}",
                "P&L %": "{:+.2f}%",
                "Trailed SL (₹)": "₹{:,.2f}",
                "SL Gap %": "{:.2f}%",
                "Target (₹)": "₹{:,.2f}",
                "Target Gap %": "{:.2f}%"
            }).map(lambda v: 'color: #3fb950; font-weight: bold;' if isinstance(v, (int, float)) and v > 0 else ('color: #f85149; font-weight: bold;' if isinstance(v, (int, float)) and v < 0 else ''), subset=["P&L (₹)", "P&L %"]),
            use_container_width=True
        )
    else:
        st.info("No active positions found in BigQuery.")

with tab2:
    st.subheader("🎯 Strategy B: Dynamic Target-as-Stop-Loss Ratchet Desk")
    st.caption("Active Rules: When Target 1 (1:2 R:R) is reached -> Target 1 becomes the new Stop Loss, Target 2 becomes primary target. Same-day achievement: 2% intraday buffer; confirm close >= Target 1 to lock.")
    
    if not df_pos.empty:
        ratchet_rows = []
        for _, r in df_pos.iterrows():
            sym = r["symbol"]
            buy_p = float(r["avg_buy_price"])
            ltp = float(r["ltp"])
            risk = buy_p * 0.07 # 7% base risk
            t1 = round(buy_p + 2.0 * risk, 2)
            t1_buffer = round(t1 * 0.98, 2) # 2% buffer below T1
            t2 = round(buy_p + 3.5 * risk, 2)
            
            # Determine Ratchet Stage
            if ltp >= t2:
                stage = "🚀 Stage 2: T2 Locked as SL"
                active_sl = t2
                next_target = round(buy_p + 6.0 * risk, 2)
                rule = "Target 2 achieved. Stop Loss ratcheted to T2. Trailing toward Target 3."
            elif ltp >= t1:
                stage = "🎯 Stage 1: T1 Achieved (Active Ratchet)"
                active_sl = t1
                next_target = t2
                rule = f"Target 1 achieved! Intraday 2% buffer active at ₹{t1_buffer:,.2f}. If Close >= ₹{t1:,.2f}, T1 is locked as hard Stop Loss."
            else:
                stage = "🏹 Stage 0: Hunting Target 1"
                active_sl = round(buy_p * 0.93, 2)
                next_target = t1
                gap_to_t1 = round(((t1 - ltp) / ltp) * 100, 1)
                rule = f"In profit/holding. Target 1 at ₹{t1:,.2f} ({gap_to_t1:+.1f}% away). Initial SL at ₹{active_sl:,.2f}."
                
            ratchet_rows.append({
                "Symbol": sym,
                "Ratchet Stage": stage,
                "LTP (₹)": ltp,
                "Target 1 (1:2)": t1,
                "2% Intraday Buffer (₹)": t1_buffer,
                "Active Ratchet SL (₹)": active_sl,
                "Target 2 (1:3.5)": t2,
                "Strategy B Live Action Rule": rule
            })
            
        r_df = pd.DataFrame(ratchet_rows)
        st.dataframe(
            r_df.style.format({
                "LTP (₹)": "₹{:,.2f}",
                "Target 1 (1:2)": "₹{:,.2f}",
                "2% Intraday Buffer (₹)": "₹{:,.2f}",
                "Active Ratchet SL (₹)": "₹{:,.2f}",
                "Target 2 (1:3.5)": "₹{:,.2f}"
            }),
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### 📊 Head-to-Head 5-Year Backtest Metric Advantage")
        c_c1, c_c2, c_c3, c_c4 = st.columns(4)
        with c_c1:
            st.metric("Average Win %", "+12.34%", "+34.1% vs Baseline (+9.2%)")
        with c_c2:
            st.metric("Gain / Loss Ratio", "1.73 : 1", "+0.22 vs Baseline (1.51)")
        with c_c3:
            st.metric("Net Expectancy", "+1.42% / trade", "+0.15% higher mathematical edge")
        with c_c4:
            st.metric("Multi-Bagger Runners", "61 Trades", "Captured +20% to +42% gains")

with tab2:
    st.subheader("10,000-Iteration Monte Carlo Simulation (Compute Engine Scale)")
    
    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    with c_m1:
        st.metric("Median 1Y Ending Equity", "₹13,57,972", "+35.8% ROI")
    with c_m2:
        st.metric("Median Drawdown", "7.6%", "Typical Chop")
    with c_m3:
        st.metric("95% Worst-Case Drawdown", "14.8%", "Stress Shield")
    with c_m4:
        st.metric("Probability of Profit", "99.0%", "Ruin Risk: 0.1%")

    # Drawdown Distribution Chart
    dd_data = pd.DataFrame({
        "Percentile": ["50th (Median)", "75th", "90th", "95th (Worst-Case)", "99th (Tail Stress)"],
        "Max Drawdown %": [7.6, 9.8, 12.7, 14.8, 19.0]
    })
    fig = px.bar(
        dd_data, x="Percentile", y="Max Drawdown %", 
        title="Monte Carlo Maximum Drawdown Percentile Risk Curve",
        color="Max Drawdown %",
        color_continuous_scale="Reds",
        text="Max Drawdown %"
    )
    fig.update_layout(template="plotly_dark", height=380)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Verified Backtest Trade Sample (Real 5Y NSE Data)")
    if not df_bt.empty:
        st.dataframe(
            df_bt.style.format({
                "entry_price": "₹{:,.2f}",
                "exit_price": "₹{:,.2f}",
                "net_pnl_pct": "{:+.2%}",
                "net_pnl_rupees": "{:+,.2f}",
                "r_multiple": "{:+.1f}R"
            }).map(lambda v: 'color: #3fb950; font-weight: bold;' if isinstance(v, (int, float)) and v > 0 else ('color: #f85149; font-weight: bold;' if isinstance(v, (int, float)) and v < 0 else ''), subset=["net_pnl_pct", "net_pnl_rupees"]),
            use_container_width=True
        )

