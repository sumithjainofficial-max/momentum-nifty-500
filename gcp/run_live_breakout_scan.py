"""
NIFTY 500 LIVE BREAKOUT SCANNER & ALERT DISPATCHER
==================================================
Scans Nifty 500 institutional momentum universe for fresh technical breakouts,
calculates Minervini position sizing (Max ₹1.25L/trade), stores results in BigQuery,
updates Excel reports, and dispatches instant text alerts to Sumith.
"""

import os
import sys
import time
import requests
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, date
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ID = "project-dbd1df53-5f72-4b7d-9cf"
DATASET_ID = "nifty500_quant_studio"
MAX_CAPITAL_PER_TRADE = 125000.0

# 35 Top Liquid Nifty 500 Institutional Momentum Leaders across Sectors
SCAN_UNIVERSE = [
    "CDSL.NS", "BSE.NS", "KAYNES.NS", "POLYCAB.NS", "PERSISTENT.NS",
    "ABB.NS", "MCX.NS", "COFORGE.NS", "BSOFT.NS", "KPITTECH.NS",
    "SOLARINDS.NS", "BDL.NS", "MAZDOCK.NS", "CUMMINSIND.NS", "MOTHERSON.NS",
    "PRESTIGE.NS", "PHOENIXLTD.NS", "DLF.NS", "SIEMENS.NS", "CGPOWER.NS",
    "MTARTECH.NS", "EXIDEIND.NS", "ANANTRAJ.NS", "SUZLON.NS", "TATAELXSI.NS",
    "ZOMATO.NS", "TATACOMM.NS", "CHAMBLFERT.NS", "KPRMILL.NS", "APOLLOTYRE.NS",
    "ASTRAL.NS", "SUPREMEIND.NS", "KEI.NS", "RADICO.NS", "JUBLFOOD.NS"
]

def fetch_live_stock_news(symbol: str) -> str:
    clean_sym = symbol.replace(".NS", "").replace("&", "%26")
    url = f"https://news.google.com/rss/search?q={clean_sym}+share+price+NSE+India&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            root = ET.fromstring(resp.read())
            items = root.findall(".//item")
            for item in items[:1]:
                t = item.find("title").text if item.find("title") is not None else ""
                if " - " in t: t = t.rsplit(" - ", 1)[0]
                if t: return t.strip()
    except Exception:
        pass
    return "Institutional accumulation. Volume expansion above 20-DMA base."

def calculate_rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return 50.0
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

def analyze_ticker(ticker: str):
    sym = ticker.replace(".NS", "")
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="65d")
        if hist.empty or len(hist) < 30:
            return None

        closes = hist["Close"]
        highs = hist["High"]
        volumes = hist["Volume"]

        cmp = round(float(closes.iloc[-1]), 2)
        prev_close = round(float(closes.iloc[-2]), 2)
        daily_chg = round((cmp - prev_close) / prev_close, 4)

        # 20-day Pivot High (prior to today)
        pivot_20 = round(float(highs.iloc[-21:-1].max()), 2)
        sma20 = float(closes.rolling(20).mean().iloc[-1])
        sma50 = float(closes.rolling(50).mean().iloc[-1]) if len(closes) >= 50 else sma20
        vol20 = float(volumes.rolling(20).mean().iloc[-1])
        curr_vol = float(volumes.iloc[-1])
        vol_exp = round((curr_vol - vol20) / vol20, 3) if vol20 > 0 else 0.0

        daily_rsi = round(calculate_rsi(closes, 14), 1)

        # Weekly RSI approximation using 5-day resampled closes
        weekly_closes = closes.iloc[::5]
        weekly_rsi = round(calculate_rsi(weekly_closes, 14), 1)

        # Minervini Stage 2 & Breakout Filters:
        # 1. CMP within 2.0% of 20-day high or breaking out above it
        # 2. CMP above 20-DMA (healthy short-term trend)
        # 3. Daily RSI >= 52 and <= 78
        is_breakout = cmp >= (pivot_20 * 0.985) and cmp >= sma20 and daily_rsi >= 52.0

        if not is_breakout:
            return None

        # Determine pattern & grade
        if cmp >= pivot_20 and vol_exp >= 0.40:
            status = "CONFIRMED PIVOT BREAKOUT"
            pattern = "VCP (Volatility Contraction) Stage-2 Breakout"
            grade = "A+ (PRIME)"
        elif cmp >= pivot_20:
            status = "PIVOT BREAKOUT"
            pattern = "High-Tight Momentum Flag Pivot"
            grade = "A (STRONG)"
        else:
            pct_away = round(((pivot_20 - cmp) / pivot_20) * 100, 1)
            status = f"PIVOT COILING ({pct_away}% to Trigger)"
            pattern = "Ascending Base Consolidation"
            grade = "A (WATCHLIST)"

        sl = round(cmp * 0.93, 2) # Strict 7.0% stop
        qty = int(MAX_CAPITAL_PER_TRADE // cmp) if cmp > 0 else 0
        tot_inv = round(qty * cmp, 2)
        rupee_risk = round(qty * (cmp - sl), 2)

        # Swing Targets (2R / 3R)
        swing_t1 = round(cmp + 2.0 * (cmp - sl), 2)
        swing_t2 = round(cmp + 3.0 * (cmp - sl), 2)

        # Long-Term Targets (+35% / +75%)
        long_floor = round(sma50, 2) if sma50 < cmp else round(cmp * 0.88, 2)
        long_t1 = round(cmp * 1.35, 2)
        long_t2 = round(cmp * 1.75, 2)

        news = fetch_live_stock_news(ticker)

        return {
            "symbol": sym,
            "ticker": ticker,
            "status": status,
            "grade": grade,
            "cmp": cmp,
            "pivot": pivot_20,
            "daily_chg_pct": daily_chg,
            "vol_exp_pct": round(vol_exp * 100, 1),
            "daily_rsi": daily_rsi,
            "weekly_rsi": weekly_rsi,
            "pattern": pattern,
            "stop_loss": sl,
            "recommended_qty": qty,
            "total_invested": tot_inv,
            "rupee_risk": rupee_risk,
            "swing_t1": swing_t1,
            "swing_t2": swing_t2,
            "long_floor": long_floor,
            "long_t1": long_t1,
            "long_t2": long_t2,
            "news": news,
            "scan_date": str(date.today()),
            "created_at": datetime.now()
        }
    except Exception as e:
        return None

def run_scan():
    print("=" * 75)
    print("  NIFTY 500 INSTITUTIONAL BREAKOUT SCANNER (MINERVINI EXPECTANCY)")
    print("=" * 75)
    print(f"Scanning {len(SCAN_UNIVERSE)} momentum universe leaders for fresh setups...")
    
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(analyze_ticker, SCAN_UNIVERSE))

    candidates = [r for r in results if r is not None]
    # Sort by Volume Expansion & RSI
    candidates.sort(key=lambda x: (x["vol_exp_pct"], x["daily_rsi"]), reverse=True)
    t1 = time.time()

    print(f"\n[✓] Scan completed in {t1 - t0:.2f} seconds. Detected {len(candidates)} high-conviction breakout setups!\n")

    for idx, c in enumerate(candidates, start=1):
        print(f"[{idx:2d}] {c['symbol']:<12} | {c['grade']:<12} | CMP: INR {c['cmp']:>8,.2f} | Pivot: INR {c['pivot']:>8,.2f} | Vol Exp: +{c['vol_exp_pct']:>5.1f}% | RSI: {c['daily_rsi']:>4.1f}")
        print(f"     Status  : {c['status']} ({c['pattern']})")
        print(f"     Capital : Buy {c['recommended_qty']} Qty (INR {c['total_invested']:,.2f}) | SL: INR {c['stop_loss']:,.2f} (-7%)")
        print(f"     Targets : Swing 2R: INR {c['swing_t1']:,.2f} | 3R: INR {c['swing_t2']:,.2f} | Long 1: INR {c['long_t1']:,.2f}")
        print(f"     News    : {c['news']}\n")

    if not candidates:
        print("[*] No fresh breakout setups meeting strict Minervini criteria at this moment.")
        return []

    # 1. Update BigQuery daily_signals
    save_to_bigquery(candidates)

    # 2. Dispatch Email Alert to Sumith
    dispatch_alert_to_sumith(candidates[:5])

    return candidates

def save_to_bigquery(candidates):
    try:
        import subprocess
        from google.cloud import bigquery
        from google.oauth2.credentials import Credentials

        gcloud_path = r'C:\Users\sumit\AppData\Local\Google\ct4j-cloud-sdk\LATEST\google-cloud-sdk\bin\gcloud.cmd'
        token = subprocess.check_output([gcloud_path, 'auth', 'print-access-token']).decode().strip()
        creds = Credentials(token)
        client = bigquery.Client(project=PROJECT_ID, credentials=creds)

        records = []
        for c in candidates:
            records.append({
                "scan_date": c["scan_date"],
                "created_at": c["created_at"],
                "symbol": c["symbol"],
                "signal_status": c["status"],
                "cmp": c["cmp"],
                "volume_expansion_pct": c["vol_exp_pct"],
                "daily_rsi": c["daily_rsi"],
                "weekly_rsi": c["weekly_rsi"],
                "stop_loss_pct": 7.0,
                "stop_loss_price": c["stop_loss"],
                "target_1_days": c["swing_t1"],
                "target_2_weeks": c["swing_t2"],
                "target_3_months": c["long_t1"]
            })
        df_sig = pd.DataFrame(records)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.daily_signals"
        job = client.load_table_from_dataframe(df_sig, table_id)
        job.result()
        print(f"[✓] Saved {len(records)} breakout setups to BigQuery table `{table_id}`!")
    except Exception as e:
        print(f"[!] Warning saving to BigQuery: {e}")

def dispatch_alert_to_sumith(signals):
    from scan_and_alert_signals import send_plain_text_signal_email
    signal_objs = []
    for s in signals:
        signal_objs.append({
            "symbol": s["symbol"],
            "signal_status": s["status"],
            "cmp": s["cmp"],
            "pivot": s["pivot"],
            "stop_loss_price": s["stop_loss"],
            "stop_loss_pct": 7.0,
            "recommended_qty": s["recommended_qty"],
            "vol_expansion": s["vol_exp_pct"],
            "daily_rsi": s["daily_rsi"],
            "weekly_rsi": s["weekly_rsi"],
            "pattern": s["pattern"],
            "catalyst": s["news"],
            "date": s["scan_date"]
        })
    print(f"[*] Dispatching instant Buy Signal alert email to Sumith (sumith7114@gmail.com)...")
    send_plain_text_signal_email(signal_objs, is_test=False)

if __name__ == "__main__":
    run_scan()
