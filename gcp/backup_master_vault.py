r"""
NIFTY 500 INSTITUTIONAL MOMENTUM DESK - MASTER SYSTEM VAULT BACKUP ENGINE
Backs up ALL Passwords, Secrets, Strategy Codes, Cloud Infrastructure, and Excel Workbooks to:
1. Local Vault: E:\SUMITH'S PROJECT\GOOGLE CLOUD\MOMENTUM NIFFTY 500\master_vault_backup\
2. Google Drive H: H:\My Drive\Nifty 500 Momentum Trading System\Master_System_Vault\
3. Google Drive G: G:\My Drive\Nifty 500 Momentum Trading System\Master_System_Vault\
"""

import os
import sys
import shutil
import zipfile
from datetime import datetime

# UTF-8 console output
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOCAL_VAULT_DIR = os.path.join(PROJECT_DIR, "master_vault_backup", f"vault_{TIMESTAMP}")

DRIVE_H_VAULT = os.path.join(r"H:\My Drive\Nifty 500 Momentum Trading System\Master_System_Vault")
DRIVE_G_VAULT = os.path.join(r"G:\My Drive\Nifty 500 Momentum Trading System\Master_System_Vault")

def create_system_passport(out_path: str):
    """Generates the Master System Passport containing all credentials, architecture & links."""
    print("[*] Generating System & Credentials Passport...")

    # Read local envs if present
    gmail_pwd = "noxt wsak jzhe mlrj"
    angel_content = ""
    angel_path = os.path.join(PROJECT_DIR, "Angelone", "CREDENTIALS.env")
    if os.path.exists(angel_path):
        with open(angel_path, "r", encoding="utf-8") as f:
            angel_content = f.read().strip()

    passport_text = f"""# 🔐 NIFTY 500 INSTITUTIONAL MOMENTUM DESK | SYSTEM & CREDENTIALS PASSPORT
**Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}  
**Security Level:** CONFIDENTIAL MASTER VAULT

---

## 🔑 1. AUTHENTICATION & PASSWORDS VAULT

### A. Gmail Automated Dispatch Credentials
- **Sender Account:** `sumithjainofficial@gmail.com`
- **16-Character Google App Password:** `{gmail_pwd}`
- **Primary Recipient (Master Lifecycle):** `sumith7114@gmail.com`
- **Secondary Recipient (Stock Analysis Only):** `mannathkatariya67@gmail.com`
- **Gatekeeper Status:** Strictly protected. Dispatches to Mannath ONLY upon explicit user command.
- **Local Env File:** `email_credentials.env` (Saved & locked in `.gitignore`)
- **Windows User Environment Variable:** `GMAIL_APP_PASSWORD=noxtwsakjzhemlrj`

### B. Angel One SmartAPI Credentials
```env
{angel_content if angel_content else "# Add Angel One credentials in Angelone/CREDENTIALS.env"}
```

### C. Google Cloud Platform (GCP)
- **Active Owner Account:** `sumithjainofficial@gmail.com`
- **GCP Project ID:** `momentum-based-nifty-500`
- **Compute Region:** `asia-south1` (Mumbai)
- **Dedicated Service Account:** `streamlit-dashboard@momentum-based-nifty-500.iam.gserviceaccount.com`
  - Roles: `roles/bigquery.dataViewer`, `roles/bigquery.jobUser`
- **Promotional Credits Pool:** ~₹28,000 (Expiring 1st Feb)

### D. GitHub Remote Repository
- **Repository URL:** `https://github.com/sumithjainofficial-max/momentum-nifty-500.git`
- **Account:** `sumithjainofficial-max`
- **Branch:** `main`
- **Status:** Public (Streamlit Community Cloud ready)

---

## ☁️ 2. CLOUD INFRASTRUCTURE & LIVE DEPLOYMENTS

### A. Cloud Run Serverless Trading Engine (Live in Mumbai)
- **Service Name:** `nifty500-quant-engine`
- **Live Endpoint:** `https://nifty500-quant-engine-1039043025627.asia-south1.run.app`
- **Health Check:** `https://nifty500-quant-engine-1039043025627.asia-south1.run.app/health`
- **Status:** ONLINE (Serving 100% traffic)

### B. Cloud Scheduler Automated Cron Job
- **Job ID:** `projects/momentum-based-nifty-500/locations/asia-south1/jobs/nifty500-daily-scanner`
- **Schedule:** `35 15 * * 1-5` (Every market day at 3:35 PM IST)
- **Target URL:** `https://nifty500-quant-engine-1039043025627.asia-south1.run.app/run-daily-pipeline`
- **Action:** Post-market automated breakout scan, Strategy B stop-loss calculation, BigQuery table updates.

### C. BigQuery Data Lake Architecture
- **Dataset:** `momentum-based-nifty-500.nifty500_quant_studio`
  - `historical_ohlcv_daily`: 11,073+ bars, partitioned by date, clustered by symbol.
  - `daily_signals`: Partitioned by scan_date.
  - `forward_portfolio_tracking`: Live portfolio holdings, real LTPs & Strategy B stops.
  - `backtest_trades`: 5-year trade logs with R-multiples and rationale.
  - Views: `v_portfolio_summary`, `v_active_positions_monitor`, `v_daily_breakout_candidates`.

### D. Live Streamlit Web Dashboard
- **Local URL:** `http://localhost:8501`
- **Features:** KPI Header, Active Holdings, Strategy B Ratchet Monitor, Monte Carlo Tail-Risk, Backtest History.

---

## 📈 3. STRATEGY B SPECIFICATIONS (ACTIVE ENGINE)

1. **Capital Allocation:** Strictly ₹1,25,000 max capital per trade (No cap on number of simultaneous trades).
2. **Breakout Setup:** 20-DMA volume expansion >= 20%, Daily RSI >= 60, Weekly RSI 60-75.
3. **Base Stop Loss:** 7.0% below breakout pivot (Halved to 3.5% in bear market regimes).
4. **Target 1:** 2R (+14.0%).
5. **Target 2:** 3R (+21.0%).
6. **Strategy B Ratchet (Target-as-Stop-Loss):**
   - Once Target 1 is hit, Target 1 becomes the new trailing Stop-Loss.
   - If stock hits T1 today and pulls back, hold with a **2% intraday buffer below T1**.
   - If closing price is >= T1, T1 is locked as the stop-loss for subsequent days.
   - If closing price is < T1 (below buffer), exit trade systematically.
7. **5-Year Simulation Results (499 NIFTY 500 Stocks, 1,236 Trading Days):**
   - Avg Win %: **+12.34%** (vs +9.20% Baseline) -> +34.1% improvement.
   - Gain/Loss Ratio: **1.73:1** (vs 1.51:1 Baseline).
   - Net Expectancy: **+1.42% per trade** (vs +1.27% Baseline).

---

## 📊 4. WORKBOOK & REPORTING SUITE

1. `Excel/Nifty500_Lifecycle_Portfolio_Report.xlsx`:
   - Sheets: `EXECUTIVE_DASHBOARD`, `MAIN_IN_PROCESS`, `WINS`, `FAILED`, `DAILY_BREAKOUT_ANALYSIS`.
   - Sent to: `sumith7114@gmail.com`.
2. `Excel/Nifty500_Stock_Breakout_Analysis.xlsx`:
   - Sheets: `DAILY_BREAKOUT_ANALYSIS`, `STRATEGY_FRAMEWORK`.
   - Sent to: `mannathkatariya67@gmail.com` (ONLY when confirmed).
   - ZERO holdings, ZERO capital, ZERO P&L data.
3. `Excel/Nifty500_Backtest_Studio.xlsx`: Clean 13KB optimized Excel backtest studio with dynamic Excel formulas.
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(passport_text)
    print(f"[✓] System Passport generated at: {out_path}")

def backup_master_vault():
    print(f"[*] Starting Master Vault Backup [{TIMESTAMP}]...")
    os.makedirs(LOCAL_VAULT_DIR, exist_ok=True)

    # 1. System Passport
    passport_file = os.path.join(LOCAL_VAULT_DIR, "SYSTEM_AND_CREDENTIALS_PASSPORT.md")
    create_system_passport(passport_file)

    # 2. Backup Credentials Files
    creds_dir = os.path.join(LOCAL_VAULT_DIR, "credentials_and_secrets")
    os.makedirs(creds_dir, exist_ok=True)
    for cf in ["email_credentials.env", os.path.join("Angelone", "CREDENTIALS.env")]:
        src = os.path.join(PROJECT_DIR, cf)
        if os.path.exists(src):
            dst = os.path.join(creds_dir, os.path.basename(cf) if "Angelone" not in cf else "Angelone_CREDENTIALS.env")
            shutil.copy2(src, dst)
            print(f"[✓] Backed up secret: {cf}")

    # 3. Backup Strategy & Python Code Files
    code_dir = os.path.join(LOCAL_VAULT_DIR, "strategy_code_and_scripts")
    os.makedirs(code_dir, exist_ok=True)
    
    root_scripts = [
        "nifty500_gcp_pipeline.py",
        "dashboard_app.py",
        "verify_strategy.py",
        "create_improved_studio.py",
        "requirements.txt",
        "README.md",
        ".gitignore"
    ]
    for s in root_scripts:
        src = os.path.join(PROJECT_DIR, s)
        if os.path.exists(src):
            shutil.copy2(src, code_dir)

    # GCP subfolder
    gcp_dest = os.path.join(code_dir, "gcp")
    os.makedirs(gcp_dest, exist_ok=True)
    gcp_src = os.path.join(PROJECT_DIR, "gcp")
    if os.path.exists(gcp_src):
        for f in os.listdir(gcp_src):
            if f.endswith(".py") or f.endswith(".json") or f.endswith(".sql"):
                shutil.copy2(os.path.join(gcp_src, f), gcp_dest)

    # Cloud Run subfolder
    cr_dest = os.path.join(code_dir, "cloud_run")
    os.makedirs(cr_dest, exist_ok=True)
    cr_src = os.path.join(PROJECT_DIR, "cloud_run")
    if os.path.exists(cr_src):
        for f in os.listdir(cr_src):
            shutil.copy2(os.path.join(cr_src, f), cr_dest)

    print("[✓] Backed up all Strategy Code, Cloud Run & Pipeline Scripts.")

    # 4. Backup Excel Workbooks & Models
    excel_dir = os.path.join(LOCAL_VAULT_DIR, "excel_models_and_reports")
    os.makedirs(excel_dir, exist_ok=True)
    excel_src = os.path.join(PROJECT_DIR, "Excel")
    if os.path.exists(excel_src):
        for f in os.listdir(excel_src):
            if f.endswith(".xlsx") or f.endswith(".xlsm"):
                shutil.copy2(os.path.join(excel_src, f), excel_dir)
    print("[✓] Backed up all Excel Studios and Reports.")

    # 5. Compress into a Master ZIP Archive
    zip_path = os.path.join(PROJECT_DIR, "master_vault_backup", f"NIFTY500_MASTER_SYSTEM_VAULT_{TIMESTAMP}.zip")
    print(f"[*] Compressing Master Vault into: {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(LOCAL_VAULT_DIR):
            for file in files:
                full = os.path.join(root, file)
                rel = os.path.relpath(full, LOCAL_VAULT_DIR)
                zipf.write(full, rel)
    print(f"[✓] Consolidated Master ZIP created ({os.path.getsize(zip_path) / 1024:.1f} KB)")

    # 6. Copy to Google Drive (H: & G:)
    for drive_vault in [DRIVE_H_VAULT, DRIVE_G_VAULT]:
        drive_letter = os.path.splitdrive(drive_vault)[0]
        if os.path.exists(drive_letter):
            try:
                os.makedirs(drive_vault, exist_ok=True)
                dest_zip = os.path.join(drive_vault, os.path.basename(zip_path))
                dest_passport = os.path.join(drive_vault, f"SYSTEM_AND_CREDENTIALS_PASSPORT_{TIMESTAMP}.md")
                shutil.copy2(zip_path, dest_zip)
                shutil.copy2(passport_file, dest_passport)
                print(f"[✓] Google Drive Master Vault SUCCESS -> {drive_vault}")
            except Exception as e:
                print(f"[!] Warning copying to Google Drive {drive_vault}: {e}")

if __name__ == "__main__":
    backup_master_vault()

