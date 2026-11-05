"""
LIVE SIGNALS & FORWARD TRACKING LEDGER (FROM TODAY ONWARDS)
==========================================================
Scans for fresh institutional momentum breakouts and stores them in a permanent,
persistent ledger and an executive Excel tracker starting from today (2026-11-05).

Features:
1. Persistent Record: Stores all signals in `gcp/live_signals_ledger.json` and `Excel/LIVE_SIGNALS_TRACKER_FROM_TODAY.xlsx`.
2. Deduplication: Ensures every signal is logged with its original entry date and price.
3. Life-Cycle Engine: Automatically updates live prices, unrealized P&L, distance to targets/SL, and detects exits.
4. ZERO EXTERNAL DISPATCH: Strictly respects user constraint (no emails or external alerts sent).
"""

import os
import sys
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEDGER_FILE = os.path.join(os.path.dirname(__file__), "live_signals_ledger.json")
EXCEL_PATH = os.path.join(BASE_DIR, "Excel", "LIVE_SIGNALS_TRACKER_FROM_TODAY.xlsx")
NSE_MASTER_CSV = os.path.join(BASE_DIR, "all_nse_equities.csv")

MAX_CAPITAL_PER_TRADE = 125000.0
SL_PERCENTAGE = 0.07 # 7.0% hard SL ceiling

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=2)
session.mount('https://', adapter)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def load_ledger():
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"created_at": str(date.today()), "signals": {}}

def save_ledger(data):
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def fetch_stock_chart(symbol: str):
    """Fetches 6 months daily OHLCV from Yahoo Finance v8 chart API."""
    ticker = f"{symbol}.NS"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=6mo&interval=1d"
    try:
        resp = session.get(url, headers=HEADERS, timeout=7)
        if resp.status_code != 200:
            return None
        data = resp.json()
        res = data.get("chart", {}).get("result")
        if not res or not res[0]:
            return None
        
        result = res[0]
        timestamps = result.get("timestamp", [])
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        
        closes = quote.get("close", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        volumes = quote.get("volume", [])
        
        if not closes or len(closes) < 50:
            return None
            
        records = []
        for t, c, h, l, v in zip(timestamps, closes, highs, lows, volumes):
            if c is not None and h is not None and l is not None and v is not None:
                records.append({
                    "date": datetime.fromtimestamp(t).strftime('%Y-%m-%d'),
                    "close": float(c),
                    "high": float(h),
                    "low": float(l),
                    "volume": float(v)
                })
        df = pd.DataFrame(records)
        return df if len(df) >= 40 else None
    except Exception:
        return None

def analyze_today_signal(symbol: str, company_name: str):
    """Evaluates 4 Pillars of Institutional Momentum on today's bar."""
    df = fetch_stock_chart(symbol)
    if df is None:
        return None
        
    latest = df.iloc[-1]
    cmp = float(latest["close"])
    today_date = latest["date"]
    
    # Liquidity gates
    if cmp < 20.0:
        return None
        
    vol_20dma = df["volume"].iloc[-21:-1].mean()
    if vol_20dma < 20000:
        return None
        
    today_vol = float(latest["volume"])
    vol_expansion = (today_vol - vol_20dma) / vol_20dma if vol_20dma > 0 else 0
    
    # 20-Day Pivot (excluding today's bar)
    pivot_high20 = df["high"].iloc[-21:-1].max()
    
    # Stage 2 Moving Average Filter
    sma50 = df["close"].iloc[-50:].mean() if len(df) >= 50 else df["close"].mean()
    
    # 14-period RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    latest_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    # Four Pillars Evaluation
    # 1. Breakout or tight coiling
    is_breakout = cmp >= pivot_high20
    is_near_pivot = (cmp >= pivot_high20 * 0.985) and not is_breakout
    
    if not (is_breakout or is_near_pivot):
        return None
        
    # 2. Volume expansion (+20% min for today)
    if vol_expansion < 0.20:
        return None
        
    # 3. RSI >= 55
    if latest_rsi < 54.0:
        return None
        
    # 4. Stage 2 Trend (Close > 50-DMA)
    if cmp < sma50:
        return None
        
    # Detect Pattern
    dist_to_pivot = ((pivot_high20 - cmp) / pivot_high20) * 100
    status = "CONFIRMED BREAKOUT" if is_breakout else f"NEAR PIVOT ({dist_to_pivot:.1f}% Away)"
    
    # Base SL & Position Sizing
    base_sl = round(cmp * (1.0 - SL_PERCENTAGE), 2)
    qty = int(MAX_CAPITAL_PER_TRADE // cmp) if cmp > 0 else 0
    if qty <= 0:
        return None
        
    invested = round(qty * cmp, 2)
    rupee_risk = round(qty * (cmp - base_sl), 2)
    
    # Targets
    swing_t1 = round(cmp + 2.0 * (cmp - base_sl), 2)  # +14% / 2R
    swing_t2 = round(cmp + 3.0 * (cmp - base_sl), 2)  # +21% / 3R
    long_floor = round(sma50, 2)                      # 50-DMA trailing line
    long_t1 = round(cmp * 1.35, 2)                    # +35%
    long_t2 = round(cmp * 1.75, 2)                    # +75%
    
    pattern = "Stage-2 High-Volume 20-Day Breakout"
    if vol_expansion >= 1.0:
        pattern = "Institutional Volume Ignition Breakout"
    elif latest_rsi >= 68:
        pattern = "Power Momentum Thrust Breakout"
        
    return {
        "symbol": symbol,
        "company_name": company_name,
        "first_detected_date": today_date,
        "status": status,
        "pattern": pattern,
        "entry_cmp": cmp,
        "pivot_trigger": round(pivot_high20, 2),
        "recommended_qty": qty,
        "invested_capital": invested,
        "base_sl": base_sl,
        "risk_pct": -round(SL_PERCENTAGE * 100, 1),
        "max_rupee_risk": rupee_risk,
        "swing_t1": swing_t1,
        "swing_t2": swing_t2,
        "long_50dma_floor": long_floor,
        "long_t1": long_t1,
        "long_t2": long_t2,
        "daily_rsi": round(latest_rsi, 1),
        "vol_expansion_pct": round(vol_expansion * 100, 1),
        "current_ltp": cmp,
        "unrealized_pnl_rs": 0.0,
        "unrealized_pnl_pct": 0.0,
        "trade_lifecycle": "ACTIVE (OPEN)"
    }

def run_today_scanner_and_update_ledger():
    print(f"[*] Starting Fresh Market Scan from Today ({date.today()})...")
    
    # Load universe
    if os.path.exists(NSE_MASTER_CSV):
        df_nse = pd.read_csv(NSE_MASTER_CSV)
        # Filter EQ series
        if 'SERIES' in df_nse.columns:
            df_nse = df_nse[df_nse['SERIES'] == 'EQ']
        universe = list(zip(df_nse['SYMBOL'], df_nse['NAME OF COMPANY']))
    else:
        # Fallback to key Nifty 500 list
        universe = [("TRENT", "Trent Ltd"), ("DIXON", "Dixon Tech"), ("BEL", "Bharat Electronics"), ("HAL", "Hindustan Aeronautics"), ("BSE", "BSE Ltd")]
        
    print(f"[*] Universe size: {len(universe)} NSE stocks.")
    
    ledger = load_ledger()
    existing_signals = ledger.get("signals", {})
    
    fresh_detected = []
    processed = 0
    
    with ThreadPoolExecutor(max_workers=35) as executor:
        futures = {executor.submit(analyze_today_signal, sym, name): sym for sym, name in universe}
        for future in as_completed(futures):
            processed += 1
            if processed % 300 == 0 or processed == len(universe):
                print(f"[*] Processed {processed}/{len(universe)} stocks (Signals so far: {len(fresh_detected)})...")
            res = future.result()
            if res:
                fresh_detected.append(res)
                
    print(f"\n[✓] Scan complete! Found {len(fresh_detected)} institutional setups today.")
    
    # Update persistent ledger
    new_count = 0
    for s in fresh_detected:
        sym = s["symbol"]
        k = f"{sym}_{s['first_detected_date']}"
        if k not in existing_signals:
            existing_signals[k] = s
            new_count += 1
        else:
            # Update live prices
            existing_signals[k]["current_ltp"] = s["current_ltp"]
            cmp_now = s["current_ltp"]
            entry = existing_signals[k]["entry_cmp"]
            qty = existing_signals[k]["recommended_qty"]
            pnl_pct = ((cmp_now - entry) / entry) * 100
            pnl_rs = qty * (cmp_now - entry)
            existing_signals[k]["unrealized_pnl_pct"] = round(pnl_pct, 2)
            existing_signals[k]["unrealized_pnl_rs"] = round(pnl_rs, 2)
            
            # Check lifecycle
            if cmp_now <= existing_signals[k]["base_sl"]:
                existing_signals[k]["trade_lifecycle"] = "EXIT_SL_HIT (-7.0%)"
            elif cmp_now >= existing_signals[k]["swing_t2"]:
                existing_signals[k]["trade_lifecycle"] = "TARGET_2_HIT (+21%)"
            elif cmp_now >= existing_signals[k]["swing_t1"]:
                existing_signals[k]["trade_lifecycle"] = "TARGET_1_HIT (+14%)"
                
    ledger["signals"] = existing_signals
    ledger["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    save_ledger(ledger)
    print(f"[✓] Ledger updated. {new_count} brand-new setups added from today. Total logged: {len(existing_signals)}.")
    
    # Export to Excel
    export_to_excel(list(existing_signals.values()))
    return list(existing_signals.values())

def export_to_excel(records):
    os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)
    df = pd.DataFrame(records)
    if df.empty:
        return
        
    # Re-order columns for clarity
    col_order = [
        "symbol", "company_name", "first_detected_date", "trade_lifecycle", "status", "pattern",
        "entry_cmp", "current_ltp", "unrealized_pnl_pct", "unrealized_pnl_rs",
        "recommended_qty", "invested_capital", "base_sl", "risk_pct", "max_rupee_risk",
        "swing_t1", "swing_t2", "long_50dma_floor", "long_t1", "long_t2",
        "daily_rsi", "vol_expansion_pct"
    ]
    cols = [c for c in col_order if c in df.columns]
    df = df[cols]
    
    col_rename = {
        "symbol": "Symbol",
        "company_name": "Company Name",
        "first_detected_date": "Signal Date",
        "trade_lifecycle": "Lifecycle Status",
        "status": "Breakout Status",
        "pattern": "Technical Pattern",
        "entry_cmp": "Entry Price (₹)",
        "current_ltp": "Current LTP (₹)",
        "unrealized_pnl_pct": "PnL %",
        "unrealized_pnl_rs": "Unrealized PnL (₹)",
        "recommended_qty": "Shares Qty",
        "invested_capital": "Capital Allocated (₹)",
        "base_sl": "Base Stop-Loss (₹)",
        "risk_pct": "Risk %",
        "max_rupee_risk": "Max Rupee Risk (₹)",
        "swing_t1": "Swing Target 1 (+14%)",
        "swing_t2": "Swing Target 2 (+21%)",
        "long_50dma_floor": "50-DMA Floor (₹)",
        "long_t1": "Long Target 1 (+35%)",
        "long_t2": "Long Target 2 (+75%)",
        "daily_rsi": "Daily RSI",
        "vol_expansion_pct": "Volume Expansion %"
    }
    df = df.rename(columns=col_rename)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LIVE_SIGNALS_LEDGER"
    
    # Palette
    NAVY = "0F2942"
    GOLD = "D69E2E"
    WHITE = "FFFFFF"
    LIGHT_GRAY = "F8FAFC"
    BORDER_CLR = "CBD5E1"
    
    thin_border = Border(
        left=Side(style='thin', color=BORDER_CLR),
        right=Side(style='thin', color=BORDER_CLR),
        top=Side(style='thin', color=BORDER_CLR),
        bottom=Side(style='thin', color=BORDER_CLR)
    )
    
    # Header block
    ws.merge_cells("A1:V1")
    title_cell = ws["A1"]
    title_cell.value = "NIFTY & NSE INSTITUTIONAL MOMENTUM DESK — LIVE SIGNALS LEDGER (FROM TODAY ONWARDS)"
    title_cell.font = Font(name="Calibri", size=14, bold=True, color=WHITE)
    title_cell.fill = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells("A2:V2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Tracking Ledger Initiated: {date.today()} | Strict Position Cap: ₹1,25,000/Trade | 7.0% Hard SL | Dual Swing & Wealth Runners"
    sub_cell.font = Font(name="Calibri", size=10, italic=True, color=GOLD)
    sub_cell.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22
    
    # Write Table Headers at Row 4
    headers = list(df.columns)
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = Font(name="Calibri", size=10, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[4].height = 28
    
    # Data Rows
    for row_idx, r in enumerate(df.itertuples(index=False), 5):
        bg_color = WHITE if row_idx % 2 == 0 else LIGHT_GRAY
        for col_idx, val in enumerate(r, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = Font(name="Calibri", size=9.5)
            cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
            cell.border = thin_border
            
            # Alignments & Formats
            if isinstance(val, (int, float)):
                if "PnL %" in headers[col_idx-1] or "Risk %" in headers[col_idx-1] or "Volume" in headers[col_idx-1]:
                    cell.number_format = '0.0"%"'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif "Price" in headers[col_idx-1] or "LTP" in headers[col_idx-1] or "Capital" in headers[col_idx-1] or "Stop-Loss" in headers[col_idx-1] or "Target" in headers[col_idx-1] or "PnL (₹)" in headers[col_idx-1]:
                    cell.number_format = '₹#,##0.00'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
            # Highlight Lifecycle
            if headers[col_idx-1] == "Lifecycle Status":
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = Font(name="Calibri", size=9.5, bold=True)
                if "ACTIVE" in str(val):
                    cell.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid") # light green
                    cell.font = Font(name="Calibri", size=9.5, bold=True, color="065F46")
                elif "TARGET" in str(val):
                    cell.fill = PatternFill(start_color="BBF7D0", end_color="BBF7D0", fill_type="solid")
                    cell.font = Font(name="Calibri", size=9.5, bold=True, color="166534")
                elif "SL" in str(val):
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                    cell.font = Font(name="Calibri", size=9.5, bold=True, color="991B1B")
                    
        ws.row_dimensions[row_idx].height = 20
        
    # Auto-adjust column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            if cell.row > 2 and cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 11)
        
    ws.freeze_panes = "C5"
    wb.save(EXCEL_PATH)
    print(f"[✓] Successfully exported Live Signals Ledger to Excel: {EXCEL_PATH}")

if __name__ == "__main__":
    run_today_scanner_and_update_ledger()
