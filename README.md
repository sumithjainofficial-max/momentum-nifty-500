# NIFTY 500 Institutional Momentum Quantitative Trading Desk

Production-grade algorithmic momentum trading and forward-testing system designed for the National Stock Exchange of India (NSE) NIFTY 500 universe.

Built on **Google Cloud Platform (GCP)** leveraging **BigQuery**, **Cloud Run**, **Cloud Scheduler**, and **Looker Studio**.

---

## ⚡ Core Strategy Architecture (Strategy B: Target-as-SL Ratchet)

* **Universe**: NIFTY 500 (Broad institutional liquid universe).
* **Setup**:
  * 20-Day Resistance Breakout (`Close >= 20-Day Pivot High`).
  * Volume Expansion $\ge$ +25% above 20-DMA.
  * Momentum Gate: `Daily RSI(14) > 60` and `60 <= Weekly RSI(14) <= 75`.
* **Capital & Position Sizing**:
  * Max capital allocation: **₹1,25,000 per trade**.
  * No artificial trade count ceiling (amount-bound).
* **Dynamic Ratchet Trailing Stop (Strategy B)**:
  * Initial Hard Stop Loss: 7.0% (Swing low anchored).
  * Target 1: 1:2 Risk-to-Reward.
  * **Same-Day Target 1 Rule**:
    * 2% intraday buffer level (`Target 1 * 0.98`) to absorb intraday retest noise.
    * If `Close >= Target 1`: Target 1 is locked as the new Stop Loss, and primary target shifts to Target 2 (1:3.5 R:R).
    * If `Close < Target 1`: Exit at market close to bank profit.
  * **Runners**: Subsequent targets (Target 2 at +3.5R, Target 3 at +6.0R) continue ratcheting upwards until momentum exhaustion (`Close < 20 EMA` and `Daily RSI < 50`).

---

## 📊 Verified 5-Year Backtest Performance (2021–2026 Real NSE Data)

* **Total Trades**: 3,742
* **Batting Average (Win Rate)**: 43.96%
* **Average Win**: **+12.34%** (+34.1% higher than baseline)
* **Average Loss**: **-7.15%**
* **Gain / Loss Ratio**: **1.73 : 1**
* **Net Mathematical Expectancy**: **+1.42% per trade**
* **Profit Factor**: 1.35
* **Multi-Bagger Runners Captured**: 61 trades ($\ge$ +20% to +42% gains)

---

## ☁️ Google Cloud Platform Deployment

* **Project**: `momentum-based-nifty-500`
* **Region**: `asia-south1` (Mumbai, India)
* **BigQuery Dataset**: `nifty500_quant_studio`
  * `historical_ohlcv_daily`: Partitioned by date, clustered by symbol.
  * `daily_signals`: Partitioned by scan_date.
  * `forward_portfolio_tracking`: Partitioned by date.
  * `backtest_trades`: Partitioned by entry_date.
* **Cloud Run**: Microservice scheduled via **Cloud Scheduler** at **3:35 PM IST (Mon–Fri)** to run post-market momentum scans and update BigQuery.

---

## 🚀 Quickstart

### 1. Run Live Local Dashboard
```bash
streamlit run dashboard_app.py
```

### 2. Run Daily Momentum Scanner
```bash
python nifty500_gcp_pipeline.py --mode scan --data real
```

### 3. Deploy to Cloud Run
```powershell
.\cloud_run\deploy.ps1
```
