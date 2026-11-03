"""
Cloud Run Serverless Trading Engine for NIFTY 500 Institutional Momentum Desk.
Triggered automatically by Cloud Scheduler at 3:35 PM IST every market day.
"""

import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask, jsonify, request
import pandas as pd
import numpy as np
from google.cloud import bigquery

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "momentum-based-nifty-500")
DATASET_ID = "nifty500_quant_studio"
MAX_CAPITAL_PER_TRADE = 125000.0

def get_bq_client():
    return bigquery.Client(project=PROJECT_ID)

@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ONLINE",
        "service": "nifty500-quant-cloud-engine",
        "project": PROJECT_ID,
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/run-daily-pipeline", methods=["POST", "GET"])
def run_daily_pipeline():
    """
    Executes post-market daily momentum scan:
    1. Evaluates universe momentum setups.
    2. Identifies volume breakouts, near breakouts, and pullbacks.
    3. Calculates structural stop losses & Minervini multi-horizon targets.
    4. Writes daily signals to BigQuery table: nifty500_quant_studio.daily_signals.
    """
    logging.info("[*] Triggering NIFTY 500 Daily Momentum Pipeline...")
    today_date = datetime.now().date()
    
    try:
        client = get_bq_client()
    except Exception as e:
        logging.error(f"Failed to connect to BigQuery: {e}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500

    # Query latest daily bars from BigQuery historical table
    query = f"""
    SELECT 
        date, symbol, open, high, low, close, volume, vol_sma20, vol_expansion, 
        daily_rsi, weekly_rsi, pivot_high20, ema20, ema50, sma200
    FROM `{PROJECT_ID}.{DATASET_ID}.historical_ohlcv_daily`
    WHERE date = (SELECT MAX(date) FROM `{PROJECT_ID}.{DATASET_ID}.historical_ohlcv_daily`)
    """
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        logging.warning(f"BigQuery live query fallback: {e}")
        df = pd.DataFrame()

    signals = []
    if not df.empty:
        for _, row in df.iterrows():
            sym = row["symbol"]
            cmp = float(row["close"])
            high = float(row["high"])
            pivot = float(row["pivot_high20"]) if row["pivot_high20"] else cmp * 0.98
            vol_exp = float(row["vol_expansion"]) if row["vol_expansion"] else 0.0
            rsi_d = float(row["daily_rsi"]) if row["daily_rsi"] else 50.0
            rsi_w = float(row["weekly_rsi"]) if row["weekly_rsi"] else 50.0

            status = "NO_SIGNAL"
            if vol_exp >= 0.25 and rsi_d >= 60.0 and (60.0 <= rsi_w <= 75.0):
                if cmp >= pivot:
                    status = "BULLISH_BREAKOUT"
                elif cmp >= (0.985 * pivot):
                    status = "NEAR_BREAKOUT"
                elif cmp > row["open"]:
                    status = "PULLBACK_CONFIRMED"
            elif (high >= pivot) and (cmp < pivot):
                status = "FALSE_BREAKOUT"

            if status != "NO_SIGNAL":
                sl_pct = 0.07 # Standard 7% SL
                sl_price = round(cmp * (1 - sl_pct), 2)
                risk_per_share = cmp - sl_price
                qty = int(MAX_CAPITAL_PER_TRADE // cmp) if cmp > 0 else 0
                tot_inv = round(qty * cmp, 2)
                
                signals.append({
                    "scan_date": today_date,
                    "symbol": sym,
                    "signal_status": status,
                    "cmp": cmp,
                    "volume_expansion_pct": round(vol_exp * 100, 1),
                    "daily_rsi": round(rsi_d, 1),
                    "weekly_rsi": round(rsi_w, 1),
                    "market_regime": "BULLISH (FULL SL)",
                    "stop_loss_pct": round(sl_pct * 100, 2),
                    "stop_loss_price": sl_price,
                    "recommended_qty": qty,
                    "total_investment": tot_inv,
                    "target_1_days": round(cmp + 2.0 * risk_per_share, 2),
                    "target_2_weeks": round(cmp + 3.0 * risk_per_share, 2),
                    "target_3_months": round(cmp + 5.0 * risk_per_share, 2),
                    "rr_ratio": "1:2",
                    "created_at": datetime.now()
                })

    if signals:
        signals_df = pd.DataFrame(signals)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.daily_signals"
        try:
            job = client.load_table_from_dataframe(signals_df, table_id)
            job.result()
            logging.info(f"[✓] Uploaded {len(signals)} signals to {table_id}")
        except Exception as e:
            logging.error(f"Failed to stream signals into BQ: {e}")

    return jsonify({
        "status": "SUCCESS",
        "date": str(today_date),
        "total_evaluated": len(df),
        "signals_generated": len(signals),
        "actionable_setups": signals
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

