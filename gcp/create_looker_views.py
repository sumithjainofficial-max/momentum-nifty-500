"""
Creates Looker Studio Analytical Views in Google BigQuery.
These views power the real-time web & mobile Looker Studio Dashboard.
"""

import os
import sys
import subprocess
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "momentum-based-nifty-500")
DATASET_ID = "nifty500_quant_studio"
LOCATION = "asia-south1"

def get_bq_client():
    token_cmd = ['C:\\Users\\sumit\\AppData\\Local\\Google\\ct4j-cloud-sdk\\LATEST\\google-cloud-sdk\\bin\\gcloud.cmd', 'auth', 'print-access-token']
    try:
        token = subprocess.check_output(token_cmd).decode().strip()
        creds = Credentials(token)
        return bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)
    except Exception:
        return bigquery.Client(project=PROJECT_ID, location=LOCATION)

def create_views():
    client = get_bq_client()
    
    # View 1: v_portfolio_summary (KPI Top Cards)
    v1_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_portfolio_summary` AS
    SELECT 
        CURRENT_DATE('Asia/Kolkata') AS report_date,
        COUNT(DISTINCT symbol) AS active_positions,
        SUM(total_invested) AS total_invested_capital,
        SUM(current_value) AS current_portfolio_value,
        SUM(unrealized_pnl) AS total_unrealized_pnl,
        ROUND((SUM(unrealized_pnl) / NULLIF(SUM(total_invested), 0)) * 100, 2) AS portfolio_return_pct
    FROM `{PROJECT_ID}.{DATASET_ID}.forward_portfolio_tracking`
    WHERE as_of_date = (SELECT MAX(as_of_date) FROM `{PROJECT_ID}.{DATASET_ID}.forward_portfolio_tracking`);
    """

    # View 2: v_active_positions_monitor (Holdings Table with Risk Gaps)
    v2_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_active_positions_monitor` AS
    SELECT 
        symbol,
        trade_status,
        qty,
        avg_buy_price,
        total_invested,
        ltp,
        current_value,
        unrealized_pnl,
        ROUND(pnl_pct * 100, 2) AS pnl_percentage,
        trailed_sl,
        ROUND(((ltp - trailed_sl) / NULLIF(ltp, 0)) * 100, 2) AS distance_to_sl_pct,
        planned_target,
        ROUND(((planned_target - ltp) / NULLIF(ltp, 0)) * 100, 2) AS distance_to_target_pct,
        daily_rsi,
        weekly_rsi,
        rr_ratio,
        updated_at
    FROM `{PROJECT_ID}.{DATASET_ID}.forward_portfolio_tracking`
    WHERE as_of_date = (SELECT MAX(as_of_date) FROM `{PROJECT_ID}.{DATASET_ID}.forward_portfolio_tracking`);
    """

    # View 3: v_daily_breakout_candidates (Top Scanner Alerts)
    v3_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_daily_breakout_candidates` AS
    SELECT 
        scan_date,
        symbol,
        signal_status,
        cmp,
        volume_expansion_pct,
        daily_rsi,
        weekly_rsi,
        stop_loss_price,
        stop_loss_pct,
        recommended_qty,
        total_investment,
        target_1_days,
        target_2_weeks,
        rr_ratio
    FROM `{PROJECT_ID}.{DATASET_ID}.daily_signals`
    WHERE scan_date >= DATE_SUB(CURRENT_DATE('Asia/Kolkata'), INTERVAL 7 DAY)
    ORDER BY volume_expansion_pct DESC;
    """

    views = [
        ("v_portfolio_summary", v1_sql),
        ("v_active_positions_monitor", v2_sql),
        ("v_daily_breakout_candidates", v3_sql)
    ]

    for name, query in views:
        try:
            job = client.query(query)
            job.result()
            print(f"[✓] Looker Studio View created: {DATASET_ID}.{name}")
        except Exception as e:
            print(f"[!] Error creating view {name}: {e}")

if __name__ == "__main__":
    create_views()

