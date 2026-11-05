"""
ALL-NSE COMPREHENSIVE BULLISH CHART PATTERN SCANNER (2,393 EQUITIES)
=====================================================================
Scans the entire National Stock Exchange of India (NSE) regular equity universe (2,393 stocks)
for high-probability bullish continuation and reversal chart patterns:
1. High-Tight Bull Flag
2. Cup and Handle (VCP Contraction)
3. Double Bottom (W-Base Breakout)
4. Triple Bottom (Multi-Month Demand Wall)
5. Ascending Triangle Base

Sizing: Strictly capped at ₹1,25,000 per trade (Minervini Expectancy Model).
"""

import os
import sys
import time
import requests
from datetime import datetime, date
import pandas as pd
import numpy as np
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

MAX_CAPITAL_PER_TRADE = 125000.0
OUTPUT_EXCEL = "Excel/ALL_NSE_Bullish_Patterns_Report.xlsx"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def load_all_nse_symbols():
    csv_path = "all_nse_equities.csv"
    if not os.path.exists(csv_path):
        url = 'https://archives.nseindia.com/content/equities/EQUITY_L.csv'
        r = requests.get(url, headers=HEADERS, timeout=10)
        with open(csv_path, 'wb') as f:
            f.write(r.content)

    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    eq_df = df[df['SERIES'] == 'EQ'].copy()
    
    meta_map = {}
    for _, row in eq_df.iterrows():
        sym = str(row['SYMBOL']).strip()
        comp_name = str(row.get('NAME OF COMPANY', sym)).strip()
        meta_map[sym] = comp_name

    symbols = list(meta_map.keys())
    return symbols, meta_map

def calculate_rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1: return 50.0
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

def fetch_and_evaluate(symbol: str, company_name: str, session: requests.Session):
    ticker = f"{symbol}.NS"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=6mo&interval=1d"
    try:
        r = session.get(url, headers=HEADERS, timeout=4)
        if r.status_code != 200:
            return None
        data = r.json()
        result = data.get('chart', {}).get('result')
        if not result:
            return None
        
        quote = result[0]['indicators']['quote'][0]
        closes = [c for c in quote['close'] if c is not None]
        highs = [h for h in quote['high'] if h is not None]
        lows = [l for l in quote['low'] if l is not None]
        volumes = [v for v in quote['volume'] if v is not None]

        if len(closes) < 45:
            return None

        closes = pd.Series(closes)
        highs = pd.Series(highs)
        lows = pd.Series(lows)
        volumes = pd.Series(volumes)

        cmp = round(float(closes.iloc[-1]), 2)
        prev_close = round(float(closes.iloc[-2]), 2)
        daily_chg = round((cmp - prev_close) / prev_close, 4)

        # Basic liquidity and penny stock filter
        if cmp < 20.0:  # Exclude penny stocks
            return None

        sma20 = float(closes.rolling(20).mean().iloc[-1])
        sma50 = float(closes.rolling(50).mean().iloc[-1]) if len(closes) >= 50 else sma20
        vol20 = float(volumes.rolling(20).mean().iloc[-1])
        curr_vol = float(volumes.iloc[-1])

        if vol20 < 20000:  # Exclude dead/illiquid stocks
            return None

        vol_exp = round((curr_vol - vol20) / vol20, 3) if vol20 > 0 else 0.0
        daily_rsi = round(calculate_rsi(closes, 14), 1)

        # General Stage 2 health filter: Not in deep bear market
        if cmp < sma50 * 0.94 or daily_rsi < 50.0:
            return None

        pattern_name = None
        pattern_desc = ""
        pattern_anatomy = ""
        pivot_trigger = cmp
        structural_sl = round(cmp * 0.93, 2)
        grade = "A (STRONG)"

        # 1. BULL FLAG / HIGH-TIGHT FLAG
        if len(closes) >= 45:
            window_pole = closes.iloc[-45:-8]
            if len(window_pole) >= 15:
                pole_low = float(window_pole.min())
                pole_high = float(highs.iloc[-30:-5].max())
                pole_gain = (pole_high - pole_low) / pole_low if pole_low > 0 else 0.0

                if pole_gain >= 0.18:
                    flag_low = float(lows.iloc[-12:].min())
                    flag_pullback = (pole_high - flag_low) / pole_high
                    if flag_pullback <= 0.12 and cmp >= sma20 * 0.98 and cmp >= pole_high * 0.975:
                        pattern_name = "Bull Flag (High-Tight)"
                        pattern_desc = "Sharp flagpole advance followed by compact consolidation above 20-DMA."
                        pattern_anatomy = f"+{pole_gain*100:.1f}% Pole advance | Compact -{flag_pullback*100:.1f}% consolidation."
                        pivot_trigger = pole_high
                        structural_sl = round(flag_low * 0.99, 2)
                        grade = "A+ (PRIME)" if vol_exp >= 0.25 else "A (STRONG)"

        # 2. CUP AND HANDLE (VCP)
        if not pattern_name and len(closes) >= 65:
            left_window = highs.iloc[-75:-30]
            if len(left_window) > 0:
                cup_left_rim = float(left_window.max())
                left_rim_idx = left_window.idxmax()
                cup_bottom_window = lows.loc[left_rim_idx:].iloc[:-8]
                if len(cup_bottom_window) > 0:
                    cup_bottom = float(cup_bottom_window.min())
                    cup_depth = (cup_left_rim - cup_bottom) / cup_left_rim
                    if 0.10 <= cup_depth <= 0.35:
                        right_rim = float(highs.iloc[-15:].max())
                        if right_rim >= cup_left_rim * 0.95:
                            handle_low = float(lows.iloc[-8:].min())
                            handle_depth = (right_rim - handle_low) / right_rim
                            if handle_depth <= 0.11 and cmp >= right_rim * 0.975:
                                pattern_name = "Cup and Handle (VCP)"
                                pattern_desc = "Rounded institutional accumulation cup with tight right-side handle dry-up."
                                pattern_anatomy = f"Cup depth: -{cup_depth*100:.1f}% | Handle contraction: -{handle_depth*100:.1f}% at pivot."
                                pivot_trigger = right_rim
                                structural_sl = round(handle_low * 0.99, 2)
                                grade = "A+ (PRIME)" if daily_rsi >= 60 else "A (STRONG)"

        # 3. DOUBLE BOTTOM (W-Base Breakout)
        if not pattern_name and len(closes) >= 55:
            w_window = lows.iloc[-60:-5]
            mid_idx = len(w_window) // 2
            t1_val = float(w_window.iloc[:mid_idx].min())
            t2_val = float(w_window.iloc[mid_idx:].min())
            neckline = float(highs.iloc[-45:-12].max())

            if t1_val > 0 and abs(t2_val - t1_val) / t1_val <= 0.045:
                neckline_rise = (neckline - t1_val) / t1_val
                if 0.08 <= neckline_rise <= 0.28:
                    if cmp >= neckline * 0.975 and cmp >= sma20:
                        pattern_name = "Double Bottom (W-Base)"
                        pattern_desc = "Dual test of institutional demand floor followed by strong neckline challenge."
                        pattern_anatomy = f"T1: ₹{t1_val:,.1f} | T2: ₹{t2_val:,.1f} (within {abs(t2_val-t1_val)/t1_val*100:.1f}%) | Neckline: ₹{neckline:,.1f}."
                        pivot_trigger = neckline
                        structural_sl = round(t2_val * 0.99, 2)
                        grade = "A (STRONG)"

        # 4. TRIPLE BOTTOM
        if not pattern_name and len(closes) >= 80:
            segment_len = len(lows.iloc[-80:-5]) // 3
            w_all = lows.iloc[-80:-5]
            t1 = float(w_all.iloc[:segment_len].min())
            t2 = float(w_all.iloc[segment_len:2*segment_len].min())
            t3 = float(w_all.iloc[2*segment_len:].min())
            t_avg = (t1 + t2 + t3) / 3.0

            if t_avg > 0 and max(abs(t1-t_avg), abs(t2-t_avg), abs(t3-t_avg)) / t_avg <= 0.035:
                neckline = float(highs.iloc[-60:-15].max())
                if cmp >= neckline * 0.97:
                    pattern_name = "Triple Bottom Demand Wall"
                    pattern_desc = "Multi-month concrete floor with three failed selling attempts and expanding volume."
                    pattern_anatomy = f"3-Touch demand baseline ~₹{t_avg:,.1f} (T1: {t1:.1f}, T2: {t2:.1f}, T3: {t3:.1f}) | Neckline: ₹{neckline:,.1f}."
                    pivot_trigger = neckline
                    structural_sl = round(t3 * 0.99, 2)
                    grade = "A (STRONG)"

        # 5. ASCENDING TRIANGLE
        if not pattern_name and len(closes) >= 45:
            recent_highs = highs.iloc[-40:]
            p1 = float(recent_highs.iloc[:20].max())
            p2 = float(recent_highs.iloc[20:].max())
            l1 = float(lows.iloc[-40:-20].min())
            l2 = float(lows.iloc[-20:].min())

            if abs(p2 - p1) / p1 <= 0.02 and (l2 - l1) / l1 >= 0.025:
                if cmp >= p2 * 0.98:
                    pattern_name = "Ascending Triangle Base"
                    pattern_desc = "Horizontal resistance ceiling compressed by higher swing lows."
                    pattern_anatomy = f"Horizontal resistance @ ₹{p2:,.1f} with +{(l2-l1)/l1*100:.1f}% higher low support floor."
                    pivot_trigger = p2
                    structural_sl = round(l2 * 0.99, 2)
                    grade = "A (STRONG)"

        if not pattern_name:
            return None

        # Minervini Risk Management Protocol
        hard_sl_7pct = round(cmp * 0.93, 2)
        effective_sl = max(structural_sl, hard_sl_7pct) # tighter stop
        sl_pct = round(((cmp - effective_sl) / cmp) * 100, 2)

        qty = int(MAX_CAPITAL_PER_TRADE // cmp) if cmp > 0 else 0
        tot_inv = round(qty * cmp, 2)
        rupee_risk = round(qty * (cmp - effective_sl), 2)

        # Targets
        base_risk = cmp - effective_sl
        swing_t1 = round(cmp + 2.0 * base_risk, 2)
        swing_t2 = round(cmp + 3.0 * base_risk, 2)

        long_floor = round(sma50, 2) if sma50 < cmp else round(cmp * 0.90, 2)
        long_t1 = round(cmp * 1.35, 2)
        long_t2 = round(cmp * 1.75, 2)

        status = "CONFIRMED BREAKOUT" if cmp >= pivot_trigger else f"NEAR PIVOT ({round(((pivot_trigger-cmp)/pivot_trigger)*100, 1)}% Away)"

        return {
            "symbol": symbol,
            "company_name": company_name,
            "pattern_name": pattern_name,
            "status": status,
            "grade": grade,
            "cmp": cmp,
            "pivot_trigger": round(pivot_trigger, 2),
            "pattern_desc": pattern_desc,
            "pattern_anatomy": pattern_anatomy,
            "vol_exp_pct": round(vol_exp * 100, 1),
            "daily_rsi": daily_rsi,
            "effective_sl": effective_sl,
            "sl_pct": sl_pct,
            "recommended_qty": qty,
            "total_invested": tot_inv,
            "rupee_risk": rupee_risk,
            "swing_t1": swing_t1,
            "swing_t2": swing_t2,
            "long_floor": long_floor,
            "long_t1": long_t1,
            "long_t2": long_t2,
            "scan_date": str(date.today())
        }
    except Exception:
        return None

def scan_all_nse():
    symbols, meta_map = load_all_nse_symbols()
    total_count = len(symbols)
    print("=" * 80)
    print(f"  SCANNING ALL {total_count} NSE LISTED EQUITIES FOR BULLISH PATTERNS")
    print("=" * 80)
    print(f"Filters: Price >= ₹20 | 20-DMA Volume >= 20,000 | Minervini Cap: ₹1,25,000/trade")
    print("Running parallel multi-worker engine across all NSE equities...\n")

    t0 = time.time()
    matches = []
    processed = 0

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=40, pool_maxsize=40)
    session.mount("https://", adapter)

    with ThreadPoolExecutor(max_workers=35) as executor:
        future_to_sym = {
            executor.submit(fetch_and_evaluate, sym, meta_map.get(sym, sym), session): sym
            for sym in symbols
        }

        for future in as_completed(future_to_sym):
            processed += 1
            if processed % 150 == 0 or processed == total_count:
                print(f"[*] Processed {processed}/{total_count} stocks (Found: {len(matches)} patterns)...", flush=True)
            res = future.result()
            if res:
                matches.append(res)

    t1 = time.time()
    matches.sort(key=lambda x: (1 if "A+" in x["grade"] else 0, x["vol_exp_pct"], x["daily_rsi"]), reverse=True)

    print(f"\n[✓] FULL NSE SCAN COMPLETED in {t1 - t0:.1f} seconds!")
    print(f"[✓] Detected {len(matches)} High-Probability Bullish Chart Setups across ALL NSE Stocks!\n")

    # Save to Excel
    export_to_excel(matches)

    return matches

def export_to_excel(matches):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    DARK_BLUE = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    TEAL_FILL = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    AMBER_FILL = PatternFill(start_color="B45309", end_color="B45309", fill_type="solid")
    ZEBRA_FILL = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    HEADER_FONT = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    BOLD_FONT = Font(name="Segoe UI", size=10, bold=True)
    REGULAR_FONT = Font(name="Segoe UI", size=10)
    GREEN_FONT = Font(name="Segoe UI", size=10, bold=True, color="047857")

    THIN_BORDER = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    # Sheet 1: ALL PATTERNS MASTER
    ws = wb.create_sheet(title="ALL_NSE_BULLISH_PATTERNS")
    ws.views.sheetView[0].showGridLines = True

    headers = [
        "Symbol", "Company Name", "Pattern Detected", "Grade", "Status", "CMP (₹)",
        "Pivot Trigger (₹)", "Pattern Contraction Anatomy", "Recommended Qty",
        "Invested Capital (₹)", "Base SL (₹)", "Risk %", "Max Rupee Risk (₹)",
        "Swing T1 (+14% / 2R)", "Swing T2 (+21% / 3R)", "Long 50-DMA Floor (₹)",
        "Long T1 (+35%)", "Long T2 (+75%)", "Daily RSI"
    ]

    ws.append(headers)
    ws.row_dimensions[1].height = 28
    for c_idx in range(1, len(headers) + 1):
        cell = ws.cell(1, c_idx)
        cell.font = HEADER_FONT
        cell.fill = DARK_BLUE
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for m in matches:
        row_vals = [
            m["symbol"], m["company_name"], m["pattern_name"], m["grade"], m["status"],
            m["cmp"], m["pivot_trigger"], m["pattern_anatomy"], m["recommended_qty"],
            m["total_invested"], m["effective_sl"], f"-{m['sl_pct']}%", m["rupee_risk"],
            m["swing_t1"], m["swing_t2"], m["long_floor"], m["long_t1"], m["long_t2"],
            m["daily_rsi"]
        ]
        ws.append(row_vals)
        curr_r = ws.max_row
        ws.row_dimensions[curr_r].height = 24
        fill = ZEBRA_FILL if curr_r % 2 == 0 else PatternFill(fill_type=None)
        for c in range(1, len(row_vals) + 1):
            cell = ws.cell(curr_r, c)
            cell.font = REGULAR_FONT
            cell.border = THIN_BORDER
            if fill.fill_type: cell.fill = fill
        ws[f"A{curr_r}"].font = BOLD_FONT
        ws[f"C{curr_r}"].font = BOLD_FONT
        ws[f"D{curr_r}"].font = GREEN_FONT if "A+" in m["grade"] else BOLD_FONT
        ws[f"F{curr_r}"].number_format = '₹#,##0.00'
        ws[f"G{curr_r}"].number_format = '₹#,##0.00'
        ws[f"I{curr_r}"].number_format = '#,##0'
        ws[f"J{curr_r}"].number_format = '₹#,##0.00'
        ws[f"K{curr_r}"].number_format = '₹#,##0.00'
        ws[f"M{curr_r}"].number_format = '₹#,##0.00'
        ws[f"N{curr_r}"].number_format = '₹#,##0.00'
        ws[f"O{curr_r}"].number_format = '₹#,##0.00'
        ws[f"P{curr_r}"].number_format = '₹#,##0.00'
        ws[f"Q{curr_r}"].number_format = '₹#,##0.00'
        ws[f"R{curr_r}"].number_format = '₹#,##0.00'

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 65)

    os.makedirs(os.path.dirname(OUTPUT_EXCEL), exist_ok=True)
    wb.save(OUTPUT_EXCEL)
    print(f"[✓] Successfully exported all {len(matches)} NSE patterns to Master Excel: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    scan_all_nse()
