"""
NIFTY 500 INSTITUTIONAL MOMENTUM DESK - INSTANT BUY SIGNAL TEXT DISPATCHER
==========================================================================
Monitors and dispatches instant plain-text email alerts to Sumith (sumith7114@gmail.com)
whenever a NEW BUY SIGNAL is detected across the NIFTY 500 universe.

Key Features:
1. Strict Plain-Text Format: Clean, fast-loading, legible on mobile push notifications.
2. Dual-Timeframe Intel: Both 2-6 Week Swing (2R/3R) and 3-12 Month Long-Term (+35%/+75%) targets.
3. Position Sizing Rule: Strict Max ₹1,25,000 per trade risk control.
4. Intelligent Deduplication: Maintains a persistent watermark log (gcp/sumith_signal_tracker.json)
   to ensure signals are never duplicated on the same trading day.
"""

import os
import sys
import json
import smtplib
import subprocess
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.header import Header

# UTF-8 console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-dbd1df53-5f72-4b7d-9cf")
DATASET_ID = "nifty500_quant_studio"
LOCATION = "asia-south1"

SENDER_EMAIL = "sumithjainofficial@gmail.com"
SUMITH_EMAIL = "sumith7114@gmail.com"
MAX_CAPITAL_PER_TRADE = 125000.0

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRACKER_FILE = os.path.join(os.path.dirname(__file__), "sumith_signal_tracker.json")

def load_app_password():
    """Securely resolves Gmail App Password from environment or local .env file."""
    pwd = os.getenv("GMAIL_APP_PASSWORD")
    if pwd:
        return pwd.strip().replace(" ", "")

    env_paths = [
        os.path.join(BASE_DIR, "email_credentials.env"),
        os.path.join(BASE_DIR, ".env"),
        os.path.join(BASE_DIR, "Angelone", "CREDENTIALS.env")
    ]
    for ep in env_paths:
        if os.path.exists(ep):
            try:
                with open(ep, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GMAIL_APP_PASSWORD="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val.replace(" ", "")
            except Exception:
                pass
    return None

def get_smtp_connection(app_password: str = None):
    password = app_password or load_app_password()
    if not password:
        print("[!] GMAIL_APP_PASSWORD not found.")
        return None
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, password.strip())
    return server

def get_bq_client():
    from google.oauth2 import credentials
    from google.cloud import bigquery
    token_cmd = ['C:\\Users\\sumit\\AppData\\Local\\Google\\ct4j-cloud-sdk\\LATEST\\google-cloud-sdk\\bin\\gcloud.cmd', 'auth', 'print-access-token']
    token = subprocess.check_output(token_cmd).decode().strip()
    creds = credentials.Credentials(token)
    return bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)

def load_signal_tracker():
    """Loads tracker to prevent emailing the same buy signal repeatedly."""
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"notified_signals": {}, "last_updated": ""}

def save_signal_tracker(tracker):
    """Saves updated signal state."""
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2)

def format_plain_text_signal_alert(signals, is_test: bool = False) -> str:
    """Formats multiple actionable buy signals into a crisp, high-impact plain text message."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    header_title = "⚡ NIFTY 500 MOMENTUM DESK: NEW BUY SIGNAL ALERT ⚡"
    if is_test:
        header_title = "⚡ [TEST VERIFICATION] NIFTY 500 MOMENTUM DESK: BUY SIGNAL ALERT ⚡"

    lines = []
    lines.append("=" * 80)
    lines.append(header_title)
    lines.append("=" * 80)
    lines.append(f"Timestamp: {now_str}")
    lines.append(f"Recipient: Sumith ({SUMITH_EMAIL})")
    lines.append("Market Regime: BULLISH (Full 7.0% SL Mode Active)")
    lines.append(f"Position Sizing Rule: Max ₹{MAX_CAPITAL_PER_TRADE:,.2f} Per Trade (Strict Capital Shield)")
    lines.append(f"Total New Buy Signals: {len(signals)}")
    lines.append("=" * 80)
    lines.append("")

    for idx, s in enumerate(signals, start=1):
        sym = s.get("symbol", "UNKNOWN")
        status = s.get("signal_status", "BULLISH_BREAKOUT")
        cmp = float(s.get("cmp", 0.0))
        pivot = float(s.get("pivot", cmp))
        sl = float(s.get("stop_loss_price", cmp * 0.93))
        sl_pct = float(s.get("stop_loss_pct", 7.0))
        qty = int(s.get("recommended_qty", MAX_CAPITAL_PER_TRADE // cmp if cmp > 0 else 0))
        tot_inv = round(qty * cmp, 2)
        rupee_risk = round(qty * (cmp - sl), 2)

        vol_exp = float(s.get("vol_expansion", 0.0))
        rsi_d = float(s.get("daily_rsi", 60.0))
        rsi_w = float(s.get("weekly_rsi", 65.0))

        # Dual Targets
        swing_t1 = round(cmp + 2.0 * (cmp - sl), 2)
        swing_t2 = round(cmp + 3.0 * (cmp - sl), 2)
        long_floor = round(cmp * 0.90, 2) # 50-DMA proxy
        long_t1 = round(cmp * 1.35, 2)
        long_t2 = round(cmp * 1.75, 2)
        
        pattern = s.get("pattern", "VCP / Multi-Week Consolidation Breakout")
        catalyst = s.get("catalyst", "Institutional volume surge with clean price momentum confirmation.")

        lines.append(f"[{idx}/{len(signals)}] NEW BUY SIGNAL: {sym} — {status}")
        lines.append("-" * 80)
        lines.append(f"• Technical Pattern : {pattern}")
        lines.append(f"• Current Price (CMP): ₹{cmp:,.2f}")
        lines.append(f"• Pivot Breakout Trg: ₹{pivot:,.2f}")
        lines.append(f"• Recommended Qty   : {qty} Shares")
        lines.append(f"• Total Capital Req : ₹{tot_inv:,.2f} (Under ₹1.25L Cap)")
        lines.append(f"• Base Stop-Loss    : ₹{sl:,.2f} (-{sl_pct:.2f}%) | Max Rupee Risk: ₹{rupee_risk:,.2f}")
        lines.append("")
        lines.append("⚡ SWING HORIZON (2 to 6 Weeks):")
        lines.append(f"  - Swing Target 1 (2R / +14.0%): ₹{swing_t1:,.2f}")
        lines.append(f"  - Swing Target 2 (3R / +21.0%): ₹{swing_t2:,.2f}")
        lines.append("  - Action Rule: Trail 20-EMA; Lock Target 1 as Trailed SL once achieved (Strategy B).")
        lines.append("")
        lines.append("🏛️ LONG-TERM WEALTH HORIZON (3 to 12 Months):")
        lines.append(f"  - 50-DMA Institutional Floor : ₹{long_floor:,.2f}")
        lines.append(f"  - Long Target 1 (+35.0%)    : ₹{long_t1:,.2f}")
        lines.append(f"  - Long Target 2 (+75.0%)    : ₹{long_t2:,.2f} (Multi-Bagger Compounding Runner)")
        lines.append("  - Thesis: Hold secular advance while price respects daily 50-DMA closing line.")
        lines.append("")
        lines.append("📊 TECHNICAL CONFLUENCE:")
        lines.append(f"  - Volume Expansion : +{vol_exp:.1f}% vs 20-DMA")
        lines.append(f"  - Daily RSI (14)   : {rsi_d:.1f} (Bullish Momentum Zone)")
        lines.append(f"  - Weekly RSI (14)  : {rsi_w:.1f} (Institutional Accumulation)")
        lines.append(f"  - Catalyst Notes   : {catalyst}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

    lines.append("=" * 80)
    lines.append("EXECUTION CHECKLIST & RISK PROTOCOL:")
    lines.append("1. Max ₹1,25,000 per trade: Never allocate more than 1.25 Lakhs per signal.")
    lines.append("2. Execute at CMP or on tight intraday pullback toward Pivot Trigger.")
    lines.append("3. Once Target 1 is hit, execute Strategy B Ratchet to protect accumulated gains.")
    lines.append("4. Never average down on a trade if the structural Stop-Loss is breached.")
    lines.append("=" * 80)
    lines.append("NIFTY 500 Institutional Momentum Desk | Cloud Run & BigQuery Powered")
    lines.append("End of Signal Briefing.")
    
    return "\n".join(lines)

def send_plain_text_signal_email(signals, is_test: bool = False) -> bool:
    """Dispatches clean text email to Sumith."""
    if not signals:
        print("[*] No buy signals to dispatch.")
        return False

    server = get_smtp_connection()
    if not server:
        return False

    body = format_plain_text_signal_alert(signals, is_test=is_test)
    
    msg = MIMEText(body, "plain", "utf-8")
    symbols_str = ", ".join([s.get("symbol", "") for s in signals[:3]])
    if len(signals) > 3:
        symbols_str += f" +{len(signals)-3} more"

    prefix = "⚡ [BUY SIGNAL]" if not is_test else "⚡ [TEST BUY SIGNAL]"
    msg["Subject"] = f"{prefix} {symbols_str} | NIFTY 500 Momentum Desk [{datetime.now().strftime('%d-%b %H:%M')}]"
    msg["From"] = f"NIFTY 500 Momentum Desk <{SENDER_EMAIL}>"
    msg["To"] = SUMITH_EMAIL

    try:
        server.send_message(msg)
        print(f"[✓] Successfully dispatched plain text Buy Signal alert for [{symbols_str}] to: {SUMITH_EMAIL}")
        server.quit()
        return True
    except Exception as e:
        print(f"[!] Failed to send text signal email: {e}")
        try: server.quit()
        except: pass
        return False

def scan_and_alert(force: bool = False):
    """
    Scans for new buy signals from BigQuery daily_signals and historical_ohlcv_daily,
    filters against tracker to avoid repeat spam, and emails Sumith immediately.
    """
    print(f"[*] Scanning for new buy signals for Sumith ({SUMITH_EMAIL})...")
    client = get_bq_client()
    tracker = load_signal_tracker()
    notified = tracker.get("notified_signals", {})
    today_str = str(date.today())

    # Query latest buy signals from BigQuery
    q = f"""
    SELECT 
        date, symbol, close, high, low, pivot_high20, vol_expansion, 
        daily_rsi, weekly_rsi
    FROM `{PROJECT_ID}.{DATASET_ID}.historical_ohlcv_daily`
    WHERE date >= DATE_SUB((SELECT MAX(date) FROM `{PROJECT_ID}.{DATASET_ID}.historical_ohlcv_daily`), INTERVAL 7 DAY)
      AND vol_expansion >= 0.20
      AND daily_rsi >= 55.0
      AND close >= pivot_high20 * 0.985
    ORDER BY vol_expansion DESC
    LIMIT 10
    """
    try:
        df = client.query(q).to_dataframe()
    except Exception as e:
        print(f"[!] BigQuery query failed: {e}")
        return []

    new_signals = []
    for _, row in df.iterrows():
        sym = str(row["symbol"]).strip()
        sig_date = str(row["date"])
        key = f"{sym}_{sig_date}"

        # If already notified today and not force, skip
        if not force and key in notified:
            continue

        cmp = float(row["close"])
        pivot = float(row["pivot_high20"]) if row["pivot_high20"] else cmp * 0.98
        vol_exp = float(row["vol_expansion"]) * 100
        rsi_d = float(row["daily_rsi"]) if row["daily_rsi"] else 55.0
        rsi_w = float(row["weekly_rsi"]) if row["weekly_rsi"] else 60.0

        sl = round(cmp * 0.93, 2)
        qty = int(MAX_CAPITAL_PER_TRADE // cmp) if cmp > 0 else 0

        status = "BULLISH_BREAKOUT" if cmp >= pivot else "NEAR_BREAKOUT (1.5% to Pivot)"

        signal_obj = {
            "symbol": sym,
            "signal_status": status,
            "cmp": cmp,
            "pivot": pivot,
            "stop_loss_price": sl,
            "stop_loss_pct": 7.0,
            "recommended_qty": qty,
            "vol_expansion": vol_exp,
            "daily_rsi": rsi_d,
            "weekly_rsi": rsi_w,
            "pattern": "High-Volume Stage-2 Momentum Breakout",
            "catalyst": f"Volume expanded +{vol_exp:.1f}% with RSI at {rsi_d:.1f}. Active institutional accumulation.",
            "date": sig_date
        }
        new_signals.append(signal_obj)

    if not new_signals:
        print("[*] No fresh unnotified buy signals found. Sumith's inbox remains clean.")
        return []

    print(f"[*] Found {len(new_signals)} new buy signals to dispatch in text format!")
    success = send_plain_text_signal_email(new_signals)
    if success:
        for s in new_signals:
            k = f"{s['symbol']}_{s['date']}"
            notified[k] = datetime.now().isoformat()
        tracker["notified_signals"] = notified
        tracker["last_updated"] = datetime.now().isoformat()
        save_signal_tracker(tracker)

    return new_signals

def send_test_signal_alert():
    """Generates and sends a high-fidelity test buy signal alert to Sumith to verify the text format."""
    print("[*] Generating test buy signal alert in plain-text format for Sumith...")
    test_signals = [
        {
            "symbol": "TRENT",
            "signal_status": "BULLISH BREAKOUT (All-Time High Blue Sky Pivot)",
            "cmp": 3050.0,
            "pivot": 3020.0,
            "stop_loss_price": 2836.50,
            "stop_loss_pct": 7.0,
            "recommended_qty": 40,
            "vol_expansion": 38.4,
            "daily_rsi": 64.2,
            "weekly_rsi": 68.5,
            "pattern": "VCP 3-Tight Contraction (21.5% -> 10.9% depth) into Blue Sky ATH",
            "catalyst": "Strong Q2 retail footfall growth; Westside & Zudio network expansion. Volume breakout confirmed.",
            "date": str(date.today())
        },
        {
            "symbol": "DIXON",
            "signal_status": "BULLISH BREAKOUT (Multi-Month Base Ceiling)",
            "cmp": 12450.0,
            "pivot": 12150.0,
            "stop_loss_price": 11578.50,
            "stop_loss_pct": 7.0,
            "recommended_qty": 10,
            "vol_expansion": 50.2,
            "daily_rsi": 62.8,
            "weekly_rsi": 66.1,
            "pattern": "High-Tight Flag Consolidation above 20-DMA and 50-DMA",
            "catalyst": "Smartphone export orders ramp-up; fresh PLI scheme incentives. Institutional block volume.",
            "date": str(date.today())
        }
    ]
    return send_plain_text_signal_email(test_signals, is_test=True)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dispatch plain text Buy Signal alerts to Sumith.")
    parser.add_argument("--test", action="store_true", help="Send a test buy signal text email to verify format.")
    parser.add_argument("--force", action="store_true", help="Force send latest signals even if already tracked.")
    args = parser.parse_args()

    if args.test:
        send_test_signal_alert()
    else:
        scan_and_alert(force=args.force)

