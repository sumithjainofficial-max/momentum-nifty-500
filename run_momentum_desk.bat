@echo off
title NIFTY 500 Institutional Momentum Desk - Live Launcher
color 0b
echo ======================================================================
echo    NIFTY 500 INSTITUTIONAL MOMENTUM DESK - AUTOMATED SCAN & LAUNCH
echo ======================================================================
echo.

cd /d "E:\SUMITH'S PROJECT\GOOGLE CLOUD\MOMENTUM NIFFTY 500"

echo [*] STEP 1/4: Syncing Live Market Prices & Strategy B Trailed SL...
python gcp\sync_live_market_prices.py

echo.
echo [*] STEP 2/4: Refreshing Multi-Sheet Portfolio Lifecycle Workbooks...
python gcp\generate_lifecycle_workbook.py

echo.
echo [*] STEP 3/4: Checking for New Buy Signals & Dispatching Text Alert to Sumith...
python gcp\scan_and_alert_signals.py

echo.
echo [*] STEP 4/4: Checking Streamlit Dashboard on port 8501...
netstat -ano | findstr :8501 >nul
if %errorlevel% neq 0 (
    echo [*] Starting Streamlit Dashboard background server...
    start /b streamlit run dashboard_app.py --server.headless true --server.port 8501
    timeout /t 3 >nul
) else (
    echo [✓] Streamlit server is already active on port 8501.
)

echo.
echo [✓] Launching browser: http://localhost:8501
start http://localhost:8501

echo.
echo ======================================================================
echo  DESK IS LIVE! Dashboard is open at http://localhost:8501
echo  This window can now be minimized or closed.
echo ======================================================================
timeout /t 5
exit
