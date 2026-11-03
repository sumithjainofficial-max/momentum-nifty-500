"""
AUTOMATED DAILY PORTFOLIO LIFECYCLE EMAIL DISPATCHER
Sends the complete Nifty500_Lifecycle_Portfolio_Report.xlsx attachment to:
- sumith7114@gmail.com
- mannathkatariya67@gmail.com
from:
- sumithjainofficial@gmail.com
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
RECIPIENTS = ["sumith7114@gmail.com", "mannathkatariya67@gmail.com"]
SUBJECT = f"⚡ NIFTY 500 Institutional Momentum Desk | Daily Lifecycle Report [{datetime.now().strftime('%d-%b-%Y')}]"

ATTACHMENT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Excel", "Nifty500_Lifecycle_Portfolio_Report.xlsx"))

def send_lifecycle_report(app_password: str = None):
    # Check environment or argument
    password = app_password or os.getenv("GMAIL_APP_PASSWORD")
    if not password:
        print("\n[!] GMAIL_APP_PASSWORD not detected.")
        print("To send automated emails from sumithjainofficial@gmail.com, generate a 16-character Google App Password:")
        print("1. Go to: https://myaccount.google.com/apppasswords")
        print("2. Type 'Momentum Desk' and click 'Create'.")
        print("3. Set in your environment: $env:GMAIL_APP_PASSWORD = 'your-16-char-password'")
        return False

    if not os.path.exists(ATTACHMENT_PATH):
        print(f"[!] Attachment not found at {ATTACHMENT_PATH}. Run generate_lifecycle_workbook.py first.")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"NIFTY 500 Momentum Desk <{SENDER_EMAIL}>"
    msg["To"] = ", ".join(RECIPIENTS)
    msg["Subject"] = SUBJECT

    # High-impact Executive HTML Body
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.5; }}
            .container {{ max-width: 650px; margin: 0 auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px; }}
            .header {{ background-color: #0d1117; color: #ffffff; padding: 18px; border-radius: 6px; text-align: center; }}
            .card {{ background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 14px; margin-top: 15px; }}
            .kpi-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
            .kpi-label {{ font-size: 13px; color: #6b7280; font-weight: 600; text-transform: uppercase; }}
            .kpi-val {{ font-size: 15px; font-weight: bold; color: #111827; }}
            .green {{ color: #059669 !important; font-weight: bold; }}
            .badge {{ display: inline-block; padding: 3px 8px; font-size: 11px; font-weight: bold; border-radius: 4px; background: #e0e7ff; color: #3730a3; }}
            .footer {{ font-size: 11px; color: #9ca3af; text-align: center; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin: 0; font-size: 18px; letter-spacing: 0.5px;">⚡ NIFTY 500 MOMENTUM LIFECYCLE AUDIT</h2>
                <p style="margin: 4px 0 0 0; font-size: 12px; color: #9ca3af;">Automated Daily Institutional Briefing | Asia/Kolkata</p>
            </div>

            <p style="margin-top: 18px; font-size: 14px;">Hello Team,</p>
            <p style="font-size: 14px;">The daily portfolio audit, Strategy B ratchet stops, and new breakout setups have been compiled. Find the full multi-sheet audit attached:</p>

            <div class="card">
                <div style="font-weight: bold; font-size: 14px; margin-bottom: 10px; color: #1e3a8a;">📊 Key Portfolio Snapshot:</div>
                <div style="font-size: 13px; line-height: 1.8;">
                    • <b>Active Holdings:</b> 5 Positions (Trent, Dixon, BEL, HAL, VBL)<br>
                    • <b>Total Capital Invested:</b> ₹6,12,165.66<br>
                    • <b>Current Portfolio Value:</b> ₹6,29,926.15<br>
                    • <b>Unrealized P&L:</b> <span class="green">+₹17,760.49 (+2.90%)</span><br>
                    • <b>Top Performer:</b> TRENT (LTP: ₹3,036.50 | <b>+6.38%</b> | Trailing T2 Stop Active)<br>
                    • <b>Strategy B Engine:</b> Target-as-Stop-Loss + 2% Buffer Active
                </div>
            </div>

            <div class="card">
                <div style="font-weight: bold; font-size: 14px; margin-bottom: 8px; color: #4c1d95;">📑 Attached Workbook Structure:</div>
                <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #374151;">
                    <li><b>MAIN_IN_PROCESS:</b> Live active positions with trailing stops, gap to target, and latest news/plans.</li>
                    <li><b>WINS:</b> All trades successfully closed in profit with rationale and days held.</li>
                    <li><b>FAILED:</b> Stopped-out trades with systematic loss containment post-mortem.</li>
                    <li><b>DAILY_BREAKOUT_ANALYSIS:</b> New momentum candidates with targets, SL, and news catalysts.</li>
                </ul>
            </div>

            <div class="footer">
                Automated by Google Cloud Platform (Cloud Run & BigQuery) | Project: momentum-based-nifty-500<br>
                Recipient list: sumith7114@gmail.com, mannathkatariya67@gmail.com
            </div>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_content, "html"))

    # Attach Excel file
    with open(ATTACHMENT_PATH, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=Nifty500_Lifecycle_Portfolio_Report.xlsx")
        msg.attach(part)

    try:
        print(f"[*] Connecting to SMTP server (smtp.gmail.com:587) via {SENDER_EMAIL}...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, password.strip())
        server.send_message(msg)
        server.quit()
        print(f"[✓] Email successfully dispatched to: {', '.join(RECIPIENTS)}")
        return True
    except Exception as e:
        print(f"[!] Failed to send email: {e}")
        return False

if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else None
    send_lifecycle_report(pwd)
