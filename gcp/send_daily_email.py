"""
NIFTY 500 INSTITUTIONAL MOMENTUM DESK - DUAL REPORT EMAIL DISPATCHER
Enforces strict recipient privacy and authorization controls:
1. sumith7114@gmail.com:
   - Receives MASTER PORTFOLIO LIFECYCLE (Active Holdings, Wins, Failed, P&L, Strategy B Trailing Stops, Daily Breakouts).
2. mannathkatariya67@gmail.com:
   - Receives STOCKS BREAKOUT ANALYSIS ONLY (Targets, Stop-Loss, Technical Setup, Corporate News & Catalysts).
   - ZERO HOLDINGS, ZERO BALANCES, ZERO PERSONAL DATA.
   - GATEKEEPER: Dispatches ONLY upon explicit user instruction (requires --confirm-mannath flag).
"""

import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# UTF-8 console output
sys.stdout.reconfigure(encoding="utf-8")

SENDER_EMAIL = "sumithjainofficial@gmail.com"
SUMITH_EMAIL = "sumith7114@gmail.com"
MANNATH_EMAIL = "mannathkatariya67@gmail.com"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MASTER_REPORT = os.path.join(BASE_DIR, "Excel", "Nifty500_Lifecycle_Portfolio_Report.xlsx")
STOCKS_ONLY_REPORT = os.path.join(BASE_DIR, "Excel", "Nifty500_Stock_Breakout_Analysis.xlsx")

def load_app_password():
    """Securely resolves Gmail App Password from environment or local .env file."""
    # 1. System/User Environment variable
    pwd = os.getenv("GMAIL_APP_PASSWORD")
    if pwd:
        return pwd.strip().replace(" ", "")

    # 2. Local secure env files (excluded by .gitignore)
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
        print("\n[!] GMAIL_APP_PASSWORD not found.")
        print("To save your password permanently so you never have to type it again:")
        print("Create 'email_credentials.env' in project root with: GMAIL_APP_PASSWORD=your_16_char_password")
        print("Or share the 16-character code here and I will save it to email_credentials.env for you.\n")
        return None, None
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, password.strip())
    return server, password

def send_to_sumith(server = None, app_password: str = None):
    """Dispatches complete master portfolio lifecycle report to Sumith."""
    owns_server = False
    if server is None:
        server, _ = get_smtp_connection(app_password)
        if not server: return False
        owns_server = True

    if not os.path.exists(MASTER_REPORT):
        print(f"[!] Master report missing: {MASTER_REPORT}")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"NIFTY 500 Momentum Desk <{SENDER_EMAIL}>"
    msg["To"] = SUMITH_EMAIL
    msg["Subject"] = f"⚡ NIFTY 500 Master Portfolio Lifecycle Audit [{datetime.now().strftime('%d-%b-%Y')}]"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #0d1117; color: #fff; padding: 15px; border-radius: 6px; text-align: center;">
            <h2 style="margin: 0;">⚡ MASTER PORTFOLIO LIFECYCLE REPORT</h2>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #9ca3af;">Institutional Momentum Desk | Active & Historical Audit</p>
        </div>
        <p>Hi Sumith,</p>
        <p>The updated portfolio lifecycle workbook is attached with live market prices, Strategy B ratchets, and closed trade audits:</p>
        <ul>
            <li><b>MAIN_IN_PROCESS:</b> 5 Active holdings (Trent, Dixon, HAL, BEL, VBL) with trailed stop-losses & catalysts.</li>
            <li><b>WINS:</b> Successfully closed winning trades with net profit in INR and holding days.</li>
            <li><b>FAILED:</b> Stopped-out trades with strict ₹1.25L loss containment post-mortem.</li>
            <li><b>DAILY_BREAKOUT_ANALYSIS:</b> New momentum breakout setups with targets and news.</li>
        </ul>
        <p style="font-size: 11px; color: #9ca3af;">Generated automatically via BigQuery & Cloud Run.</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))

    with open(MASTER_REPORT, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=Nifty500_Master_Portfolio_Report.xlsx")
        msg.attach(part)

    server.send_message(msg)
    print(f"[✓] Master Portfolio Report dispatched to: {SUMITH_EMAIL}")
    if owns_server: server.quit()
    return True

def send_to_mannath(server = None, app_password: str = None, user_confirmed: bool = False):
    """
    Dispatches Stocks Breakout Analysis ONLY to Mannath.
    STRICT POLICY: Executes ONLY when user_confirmed == True.
    Contains ZERO holdings, ZERO portfolio values, and ZERO personal balances.
    """
    if not user_confirmed:
        print("\n" + "="*70)
        print("[GATEKEEPER ENGAGED] Email to mannathkatariya67@gmail.com is PROTECTED.")
        print("Rule Enforced: 'SEND ONLY IF I SAY'.")
        print("To confirm and dispatch this specific email, pass --confirm-mannath.")
        print("="*70 + "\n")
        return False

    owns_server = False
    if server is None:
        server, _ = get_smtp_connection(app_password)
        if not server: return False
        owns_server = True

    if not os.path.exists(STOCKS_ONLY_REPORT):
        print(f"[!] Stocks-only report missing: {STOCKS_ONLY_REPORT}")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"NIFTY 500 Research Desk <{SENDER_EMAIL}>"
    msg["To"] = MANNATH_EMAIL
    msg["Subject"] = f"📈 NIFTY 500 Daily Momentum Breakout Analysis [{datetime.now().strftime('%d-%b-%Y')}]"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #1e1b4b; color: #fff; padding: 15px; border-radius: 6px; text-align: center;">
            <h2 style="margin: 0;">📈 NIFTY 500 DAILY STOCK BREAKOUT ANALYSIS</h2>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #c7d2fe;">Technical Breakouts, Targets, Stop-Loss & Catalysts</p>
        </div>
        <p>Hi Mannath,</p>
        <p>Attached is today's institutional momentum scan report for NIFTY 500 stocks displaying fresh breakout setups.</p>
        <div style="background-color: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 6px; padding: 12px; margin: 12px 0;">
            <b>Report Details:</b>
            <ul style="margin: 6px 0 0 0; padding-left: 20px;">
                <li>Breakout candidate symbols with Setup Grade (A+ / A)</li>
                <li>Pivot Breakout Price Triggers & Structural Stop-Loss (7%)</li>
                <li>Multi-Horizon Targets (Target 1: 2R, Target 2: 3R, Target 3: 5R)</li>
                <li>20-Day Volume Expansion %, Daily & Weekly RSI</li>
                <li>Corporate News, Growth Catalysts & Business Developments</li>
            </ul>
        </div>
        <p style="font-size: 11px; color: #9ca3af;">Research Desk Briefing | Asia/Kolkata</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))

    with open(STOCKS_ONLY_REPORT, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=Nifty500_Stock_Breakout_Analysis.xlsx")
        msg.attach(part)

    server.send_message(msg)
    print(f"[✓] Stock Breakout Analysis Report dispatched to: {MANNATH_EMAIL}")
    if owns_server: server.quit()
    return True

def send_buy_signal_text_alert(signals=None, is_test: bool = False):
    """Dispatches instant plain text Buy Signal alerts to Sumith (sumith7114@gmail.com)."""
    try:
        try:
            from gcp.scan_and_alert_signals import send_plain_text_signal_email, scan_and_alert, send_test_signal_alert
        except ImportError:
            sys.path.insert(0, os.path.dirname(__file__))
            from scan_and_alert_signals import send_plain_text_signal_email, scan_and_alert, send_test_signal_alert
            
        if is_test:
            return send_test_signal_alert()
        elif signals:
            return send_plain_text_signal_email(signals)
        else:
            return scan_and_alert(force=False)
    except Exception as e:
        print(f"[!] Error invoking scan_and_alert_signals: {e}")
        return False

if __name__ == "__main__":
    confirm_mannath = "--confirm-mannath" in sys.argv
    target = sys.argv[1].lower() if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "all"

    if target in ["signal", "sumith-signal", "buy-signal"]:
        send_buy_signal_text_alert(is_test=("--test" in sys.argv))
    else:
        server, pwd = get_smtp_connection()
        if server:
            if target in ["all", "sumith"]:
                send_to_sumith(server)
            if target in ["all", "mannath"]:
                send_to_mannath(server, user_confirmed=confirm_mannath)
            server.quit()
