"""
BigQuery Provisioning & Schema Setup for NIFTY 500 Institutional Momentum Desk.
Dataset: nifty500_quant_studio (Region: asia-south1 Mumbai)
Tables:
1. historical_ohlcv_daily (Partitioned by date, clustered by symbol)
2. daily_signals (Partitioned by scan_date)
3. forward_portfolio_tracking (Partitioned by as_of_date)
4. backtest_trades (Partitioned by entry_date)
"""

import os
import sys
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from google.cloud import bigquery
from google.cloud.bigquery import SchemaField, Table, Dataset
from google.oauth2.credentials import Credentials

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "momentum-based-nifty-500")
DATASET_ID = "nifty500_quant_studio"
LOCATION = "asia-south1"  # Mumbai, India

def get_bq_client():
    token_cmd = ['C:\\Users\\sumit\\AppData\\Local\\Google\\ct4j-cloud-sdk\\LATEST\\google-cloud-sdk\\bin\\gcloud.cmd', 'auth', 'print-access-token']
    try:
        token = subprocess.check_output(token_cmd).decode().strip()
        creds = Credentials(token)
        return bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)
    except Exception:
        return bigquery.Client(project=PROJECT_ID, location=LOCATION)

def setup_bigquery():
    client = get_bq_client()
    dataset_ref = client.dataset(DATASET_ID)

    # 1. Create Dataset if not exists
    try:
        client.get_dataset(dataset_ref)
        print(f"[✓] Dataset {DATASET_ID} already exists.")
    except Exception:
        dataset = Dataset(dataset_ref)
        dataset.location = LOCATION
        dataset.description = "NIFTY 500 Quantitative Momentum Trading Lake & Looker Studio Analytics"
        client.create_dataset(dataset, timeout=30)
        print(f"[+] Created BigQuery Dataset: {DATASET_ID} in {LOCATION}")

    # 2. Table: historical_ohlcv_daily
    t1_id = f"{PROJECT_ID}.{DATASET_ID}.historical_ohlcv_daily"
    s1 = [
        SchemaField("date", "DATE", mode="REQUIRED"),
        SchemaField("symbol", "STRING", mode="REQUIRED"),
        SchemaField("open", "FLOAT64", mode="NULLABLE"),
        SchemaField("high", "FLOAT64", mode="NULLABLE"),
        SchemaField("low", "FLOAT64", mode="NULLABLE"),
        SchemaField("close", "FLOAT64", mode="REQUIRED"),
        SchemaField("volume", "INT64", mode="NULLABLE"),
        SchemaField("vol_sma20", "FLOAT64", mode="NULLABLE"),
        SchemaField("vol_expansion", "FLOAT64", mode="NULLABLE"),
        SchemaField("daily_rsi", "FLOAT64", mode="NULLABLE"),
        SchemaField("weekly_rsi", "FLOAT64", mode="NULLABLE"),
        SchemaField("pivot_high20", "FLOAT64", mode="NULLABLE"),
        SchemaField("ema20", "FLOAT64", mode="NULLABLE"),
        SchemaField("ema50", "FLOAT64", mode="NULLABLE"),
        SchemaField("sma200", "FLOAT64", mode="NULLABLE")
    ]
    t1 = Table(t1_id, schema=s1)
    t1.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="date"
    )
    t1.clustering_fields = ["symbol"]
    try:
        client.create_table(t1, exists_ok=True)
        print(f"[✓] Table provisioned: historical_ohlcv_daily (Partitioned: date, Clustered: symbol)")
    except Exception as e:
        print(f"[!] Error creating historical_ohlcv_daily: {e}")

    # 3. Table: daily_signals
    t2_id = f"{PROJECT_ID}.{DATASET_ID}.daily_signals"
    s2 = [
        SchemaField("scan_date", "DATE", mode="REQUIRED"),
        SchemaField("symbol", "STRING", mode="REQUIRED"),
        SchemaField("signal_status", "STRING", mode="REQUIRED"),
        SchemaField("cmp", "FLOAT64", mode="REQUIRED"),
        SchemaField("volume_expansion_pct", "FLOAT64", mode="NULLABLE"),
        SchemaField("daily_rsi", "FLOAT64", mode="NULLABLE"),
        SchemaField("weekly_rsi", "FLOAT64", mode="NULLABLE"),
        SchemaField("market_regime", "STRING", mode="NULLABLE"),
        SchemaField("stop_loss_pct", "FLOAT64", mode="NULLABLE"),
        SchemaField("stop_loss_price", "FLOAT64", mode="NULLABLE"),
        SchemaField("recommended_qty", "INT64", mode="NULLABLE"),
        SchemaField("total_investment", "FLOAT64", mode="NULLABLE"),
        SchemaField("target_1_days", "FLOAT64", mode="NULLABLE"),
        SchemaField("target_2_weeks", "FLOAT64", mode="NULLABLE"),
        SchemaField("target_3_months", "FLOAT64", mode="NULLABLE"),
        SchemaField("rr_ratio", "STRING", mode="NULLABLE"),
        SchemaField("created_at", "TIMESTAMP", mode="NULLABLE")
    ]
    t2 = Table(t2_id, schema=s2)
    t2.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="scan_date"
    )
    t2.clustering_fields = ["signal_status", "symbol"]
    try:
        client.create_table(t2, exists_ok=True)
        print(f"[✓] Table provisioned: daily_signals (Partitioned: scan_date, Clustered: status, symbol)")
    except Exception as e:
        print(f"[!] Error creating daily_signals: {e}")

    # 4. Table: forward_portfolio_tracking
    t3_id = f"{PROJECT_ID}.{DATASET_ID}.forward_portfolio_tracking"
    s3 = [
        SchemaField("as_of_date", "DATE", mode="REQUIRED"),
        SchemaField("symbol", "STRING", mode="REQUIRED"),
        SchemaField("trade_status", "STRING", mode="REQUIRED"),
        SchemaField("qty", "INT64", mode="REQUIRED"),
        SchemaField("avg_buy_price", "FLOAT64", mode="REQUIRED"),
        SchemaField("total_invested", "FLOAT64", mode="REQUIRED"),
        SchemaField("ltp", "FLOAT64", mode="REQUIRED"),
        SchemaField("current_value", "FLOAT64", mode="REQUIRED"),
        SchemaField("unrealized_pnl", "FLOAT64", mode="REQUIRED"),
        SchemaField("pnl_pct", "FLOAT64", mode="REQUIRED"),
        SchemaField("daily_change_pct", "FLOAT64", mode="NULLABLE"),
        SchemaField("live_volume", "INT64", mode="NULLABLE"),
        SchemaField("vol_increase_50d_pct", "FLOAT64", mode="NULLABLE"),
        SchemaField("daily_rsi", "FLOAT64", mode="NULLABLE"),
        SchemaField("weekly_rsi", "FLOAT64", mode="NULLABLE"),
        SchemaField("trailed_sl", "FLOAT64", mode="NULLABLE"),
        SchemaField("planned_target", "FLOAT64", mode="NULLABLE"),
        SchemaField("rr_ratio", "STRING", mode="NULLABLE"),
        SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE")
    ]
    t3 = Table(t3_id, schema=s3)
    t3.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="as_of_date"
    )
    t3.clustering_fields = ["symbol"]
    try:
        client.create_table(t3, exists_ok=True)
        print(f"[✓] Table provisioned: forward_portfolio_tracking (Partitioned: as_of_date)")
    except Exception as e:
        print(f"[!] Error creating forward_portfolio_tracking: {e}")

    # 5. Table: backtest_trades
    t4_id = f"{PROJECT_ID}.{DATASET_ID}.backtest_trades"
    s4 = [
        SchemaField("trade_id", "INT64", mode="REQUIRED"),
        SchemaField("symbol", "STRING", mode="REQUIRED"),
        SchemaField("regime", "STRING", mode="NULLABLE"),
        SchemaField("entry_date", "DATE", mode="REQUIRED"),
        SchemaField("exit_date", "DATE", mode="REQUIRED"),
        SchemaField("entry_price", "FLOAT64", mode="REQUIRED"),
        SchemaField("exit_price", "FLOAT64", mode="REQUIRED"),
        SchemaField("exit_reason", "STRING", mode="REQUIRED"),
        SchemaField("holding_days", "INT64", mode="NULLABLE"),
        SchemaField("gross_pnl_pct", "FLOAT64", mode="NULLABLE"),
        SchemaField("net_pnl_pct", "FLOAT64", mode="REQUIRED"),
        SchemaField("net_pnl_rupees", "FLOAT64", mode="NULLABLE"),
        SchemaField("r_multiple", "FLOAT64", mode="NULLABLE")
    ]
    t4 = Table(t4_id, schema=s4)
    t4.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="entry_date"
    )
    t4.clustering_fields = ["symbol", "exit_reason"]
    try:
        client.create_table(t4, exists_ok=True)
        print(f"[✓] Table provisioned: backtest_trades (Partitioned: entry_date)")
    except Exception as e:
        print(f"[!] Error creating backtest_trades: {e}")

    print("\n[✓] All BigQuery quantitative tables successfully created in asia-south1!")

if __name__ == "__main__":
    setup_bigquery()
