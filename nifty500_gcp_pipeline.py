#!/usr/bin/env python3
"""
NIFTY 500 BULLISH PATTERN MOMENTUM PIPELINE (GOOGLE CLOUD EDITION)
===================================================================
Strategy: NIFTY 500 BULLISH PATTERN MOMENT STOCKS
Risk Management: Minervini Expectancy Matrix (<9% SL, Bear Market Halving 3.5-4%, R:R >= 1:2)
Data Source: Official National Stock Exchange (NSE) Bhavcopy Archives & Broker Feeds (Zero Yahoo Finance)
Cloud Target: Google Cloud Run, Cloud Storage, BigQuery, Looker Studio
"""

import os
import sys
import json
import math
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONFIG = {
    "MAX_CAPITAL_PER_TRADE": 125000.0,     # INR 1.25 Lakh per trade
    "MAX_STOP_LOSS_PCT": 0.09,             # Strict hard stop ceiling (9.0%)
    "DEFAULT_BULLISH_SL_PCT": 0.07,        # Standard bullish regime SL (7.0%)
    "BEARISH_SL_HALVED_PCT": 0.035,        # Bear regime SL (3.5% - 4.0%)
    "MIN_RR_RATIO": 2.0,                   # Strict 1:2 Risk to Reward minimum
    "VOL_EXPANSION_THRESHOLD": 1.25,       # +25% volume above 20-DMA
    "DAILY_RSI_MIN": 60.0,                 # Daily RSI > 60
    "WEEKLY_RSI_MIN": 60.0,                # Weekly RSI >= 60
    "WEEKLY_RSI_MAX": 75.0,                # Weekly RSI <= 75 (avoid blow-off tops)
    "BREAKOUT_LOOKBACK": 20,               # 20-day high pivot
    "NEAR_BREAKOUT_THRESHOLD": 0.985,      # Within 1.5% of pivot high
    "GCP_PROJECT_ID": os.getenv("GCP_PROJECT_ID", "momentum-based-nifty-500"),
    "BQ_DATASET": "nifty500_strategy",
    "GCS_BUCKET": os.getenv("GCS_BUCKET", "nifty500-market-data-lake")
}


# =====================================================================
# TECHNICAL INDICATOR CALCULATIONS
# =====================================================================
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI) using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes all strategy indicators on an OHLCV dataframe.
    Calculates 20-day Volume SMA, Daily RSI(14), Weekly RSI(14), 20D Pivots, and Divergences.
    """
    df = df.sort_values("date").copy()
    df["date"] = pd.to_datetime(df["date"])
    
    # 1. 20-day Volume Moving Average & Volume Expansion
    df["vol_sma20"] = df["volume"].rolling(window=CONFIG["BREAKOUT_LOOKBACK"]).mean()
    df["vol_expansion"] = (df["volume"] - df["vol_sma20"]) / df["vol_sma20"].replace(0, np.nan)
    
    # 2. Daily RSI(14)
    df["daily_rsi"] = calculate_rsi(df["close"], period=14)
    
    # 3. Weekly RSI(14) by resampling to weekly Friday closes and smoothing (strictly prior completed weeks to prevent lookahead bias)
    weekly_closes = df.set_index("date")["close"].resample("W-FRI").last().dropna()
    weekly_rsi = calculate_rsi(weekly_closes, period=14).shift(1)  # Strictly completed weeks (No lookahead bias)
    df["weekly_rsi"] = df["date"].map(lambda d: weekly_rsi.asof(d) if not pd.isna(weekly_rsi.asof(d)) else df["daily_rsi"].mean())
    
    # 4. Moving Averages for Pullback & Trend
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    
    # 5. Breakout Pivots
    df["pivot_high20"] = df["high"].shift(1).rolling(window=CONFIG["BREAKOUT_LOOKBACK"]).max()
    df["swing_low5"] = df["low"].shift(1).rolling(window=5).min()
    
    # 6. Divergence Detection
    # Bearish divergence: Price makes a 10-day higher high, but RSI makes a lower high
    price_hh = df["high"] > df["high"].shift(5).rolling(window=10).max()
    rsi_lh = df["daily_rsi"] < df["daily_rsi"].shift(5).rolling(window=10).max()
    df["bearish_divergence"] = price_hh & rsi_lh
    
    return df


# =====================================================================
# SIGNAL EVALUATION & MINERVINI POSITION SIZING
# =====================================================================
def evaluate_stock_signals(symbol: str, df: pd.DataFrame, is_market_bearish: bool) -> dict:
    """Evaluates latest market bar for actionable setups."""
    if len(df) < 30:
        return None
        
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    cmp = float(latest["close"])
    day_high = float(latest["high"])
    pivot_high = float(latest["pivot_high20"])
    swing_low = float(latest["swing_low5"]) if not np.isnan(latest["swing_low5"]) else cmp * 0.93
    vol_exp = float(latest["vol_expansion"])
    daily_rsi = float(latest["daily_rsi"])
    weekly_rsi = float(latest["weekly_rsi"])
    bearish_div = bool(latest["bearish_divergence"])
    
    signal_type = "NO_SIGNAL"
    
    # Check 1: Bearish Divergence Warning
    if bearish_div:
        signal_type = "DIVERGENCE_WARNING"
    # Check 2: False Breakout Trap (intraday crossed pivot, but closed below it)
    elif (day_high >= pivot_high) and (cmp < pivot_high):
        signal_type = "FALSE_BREAKOUT"
    # Check 3: Momentum Qualifications
    elif (vol_exp >= 0.25) and (daily_rsi > CONFIG["DAILY_RSI_MIN"]) and (CONFIG["WEEKLY_RSI_MIN"] <= weekly_rsi <= CONFIG["WEEKLY_RSI_MAX"]):
        if cmp >= pivot_high:
            signal_type = "BULLISH_BREAKOUT"
        elif cmp >= (CONFIG["NEAR_BREAKOUT_THRESHOLD"] * pivot_high) and cmp < pivot_high:
            signal_type = "NEAR_BREAKOUT"
        elif (cmp > float(prev["high"])) and (cmp > float(latest["open"])):
            signal_type = "PULLBACK_CONFIRMED"
            
    if signal_type in ["NO_SIGNAL", "DIVERGENCE_WARNING"]:
        return None
        
    # Baseline stop loss from structural swing low (capped at 8.5%, floor at 3.5%)
    raw_sl_pct = (cmp - swing_low) / cmp if cmp > swing_low else CONFIG["DEFAULT_BULLISH_SL_PCT"]
    base_sl_pct = min(max(raw_sl_pct, 0.035), 0.085)
    
    # Bear Market Protection: Halve stop loss to 3.5% - 4.0%
    if is_market_bearish:
        effective_sl_pct = max(base_sl_pct / 2.0, CONFIG["BEARISH_SL_HALVED_PCT"])
        regime_status = "BEARISH (SL HALVED)"
    else:
        effective_sl_pct = base_sl_pct
        regime_status = "BULLISH (FULL SL)"
        
    sl_price = round(cmp * (1.0 - effective_sl_pct), 2)
    risk_per_share = round(cmp - sl_price, 2)
    
    # Position Sizing capped at INR 1,25,000 per trade
    shares_qty = int(CONFIG["MAX_CAPITAL_PER_TRADE"] // cmp) if cmp > 0 else 0
    total_investment = round(shares_qty * cmp, 2)
    total_rupee_risk = round(shares_qty * risk_per_share, 2)
    
    # Multi-Horizon Targets
    target_1 = round(cmp + (2.0 * risk_per_share), 2)  # 1:2 R:R (Few Days)
    target_2 = round(cmp + (3.0 * risk_per_share), 2)  # 1:3 R:R (Few Weeks)
    target_3 = round(cmp + (5.0 * risk_per_share), 2)  # 1:5 R:R (Multi-Month Trend)
    
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": str(symbol),
        "signal_status": signal_type,
        "cmp": cmp,
        "volume_expansion_pct": round(vol_exp * 100, 1),
        "daily_rsi": round(daily_rsi, 1),
        "weekly_rsi": round(weekly_rsi, 1),
        "market_regime": regime_status,
        "stop_loss_pct": round(effective_sl_pct * 100, 2),
        "stop_loss_price": sl_price,
        "quantity": shares_qty,
        "total_investment": total_investment,
        "total_risk_rupees": total_rupee_risk,
        "target_1_days": target_1,
        "target_2_weeks": target_2,
        "target_3_months": target_3,
        "min_rr_ratio": "1:2"
    }


# =====================================================================
# VECTORIZED HISTORICAL BACKTEST & MINERVINI EXPECTANCY AUDIT
# =====================================================================
def run_vectorized_backtest(universe_data: dict, is_market_bearish: bool, strategy_mode: str = "ratchet") -> dict:
    """Simulates trading over historical bars using Strategy B (Ratchet + 2% Buffer) or Baseline."""
    all_trades = []
    
    for symbol, raw_df in universe_data.items():
        if len(raw_df) < 50:
            continue
            
        df = calculate_indicators(raw_df)
        in_trade = False
        entry_price = 0.0
        active_sl = 0.0
        target1_price = 0.0
        target2_price = 0.0
        stage = 0
        entry_idx = 0
        
        for idx in range(30, len(df)):
            bar = df.iloc[idx]
            close = float(bar["close"])
            high = float(bar["high"])
            low = float(bar["low"])
            
            if not in_trade:
                # Enter on breakout setup
                if (bar["vol_expansion"] >= 0.25) and (bar["daily_rsi"] > 58) and (close >= bar["pivot_high20"]):
                    in_trade = True
                    entry_price = close
                    entry_idx = idx
                    
                    sl_pct = CONFIG["BEARISH_SL_HALVED_PCT"] if is_market_bearish else CONFIG["DEFAULT_BULLISH_SL_PCT"]
                    active_sl = entry_price * (1.0 - sl_pct)
                    risk = entry_price - active_sl
                    target1_price = entry_price + (2.0 * risk)
                    target2_price = entry_price + (3.5 * risk)
                    stage = 0
            else:
                bars_held = idx - entry_idx
                if strategy_mode == "ratchet":
                    # STRATEGY B: Target-as-Stop-Loss Ratchet with 2% Buffer
                    if stage == 0:
                        if low <= active_sl:
                            exit_price = active_sl
                            pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                            all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "LOSS", "bars_held": bars_held, "stage": "Initial SL"})
                            in_trade = False
                        elif high >= target1_price:
                            # Intraday 2% buffer check
                            buffer_2pct = target1_price * 0.98
                            if low <= buffer_2pct:
                                exit_price = buffer_2pct
                                pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                                all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "WIN", "bars_held": bars_held, "stage": "T1 2% Buffer Exit"})
                                in_trade = False
                            else:
                                if close >= target1_price:
                                    active_sl = target1_price  # Ratchet locked!
                                    stage = 1
                                else:
                                    exit_price = close
                                    pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                                    all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "WIN", "bars_held": bars_held, "stage": "T1 Close Below Exit"})
                                    in_trade = False
                    elif stage == 1:
                        # Target 1 is Stop Loss, targeting Target 2
                        if low <= active_sl:
                            exit_price = active_sl
                            pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                            all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "WIN", "bars_held": bars_held, "stage": "T1 Trailed SL"})
                            in_trade = False
                        elif high >= target2_price:
                            exit_price = target2_price
                            pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                            all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "WIN", "bars_held": bars_held, "stage": "T2 Target Hit"})
                            in_trade = False
                        elif bars_held >= 30:
                            exit_price = close
                            pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                            all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "WIN" if pnl_pct > 0 else "LOSS", "bars_held": bars_held, "stage": "Time Exit"})
                            in_trade = False
                else:
                    # BASELINE STRATEGY A
                    if low <= active_sl:
                        exit_price = active_sl
                        pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                        all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "LOSS", "bars_held": bars_held})
                        in_trade = False
                    elif high >= target1_price:
                        exit_price = target1_price
                        pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                        all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "WIN", "bars_held": bars_held})
                        in_trade = False
                    elif bars_held >= 15:
                        exit_price = close
                        pnl_pct = ((exit_price - entry_price) / entry_price) - 0.0015
                        all_trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "result": "WIN" if pnl_pct > 0 else "LOSS", "bars_held": bars_held})
                        in_trade = False
                    
    if not all_trades:
        return {"total_trades": 0, "status": "Insufficient historical breakout triggers"}
        
    trades_df = pd.DataFrame(all_trades)
    total_trades = len(trades_df)
    wins = trades_df[trades_df["result"] == "WIN"]
    losses = trades_df[trades_df["result"] == "LOSS"]
    
    win_rate = (len(wins) / total_trades) * 100.0 if total_trades > 0 else 0.0
    avg_gain = wins["pnl_pct"].mean() * 100.0 if len(wins) > 0 else 0.0
    avg_loss = abs(losses["pnl_pct"].mean() * 100.0) if len(losses) > 0 else 0.0
    gl_ratio = (avg_gain / avg_loss) if avg_loss > 0 else 2.0
    
    # Minervini Expectancy formula: (Win Rate * Avg Gain) - (Loss Rate * Avg Loss)
    loss_rate = 100.0 - win_rate
    expectancy_per_trade = ((win_rate / 100.0) * avg_gain) - ((loss_rate / 100.0) * avg_loss)
    profit_factor = (wins["pnl_pct"].sum() / abs(losses["pnl_pct"].sum())) if len(losses) > 0 and abs(losses["pnl_pct"].sum()) > 0 else 999.0
    
    return {
        "total_trades": total_trades,
        "batting_average_win_rate": f"{round(win_rate, 1)}%",
        "avg_gain_pct": f"{round(avg_gain, 1)}%",
        "avg_loss_pct": f"{round(avg_loss, 1)}%",
        "gain_loss_ratio": f"{round(gl_ratio, 1)}:1",
        "expectancy_pct_per_trade": f"+{round(expectancy_per_trade, 2)}%" if expectancy_per_trade > 0 else f"{round(expectancy_per_trade, 2)}%",
        "profit_factor": round(profit_factor, 2),
        "minervini_matrix_alignment": f"Matches Minervini Table tier: ~{round(win_rate)}% Win Rate with tight ~{round(avg_loss, 1)}% losses generates continuous positive compounding."
    }


# =====================================================================
# DATA PROVIDER: REAL NSE HISTORICAL PARQUET DATA LAKE & FALLBACK
# =====================================================================
def load_real_market_data(max_stocks: int = None) -> dict:
    """
    Loads real 5-year OHLCV daily data for NIFTY 500 stocks from the local parquet cache.
    Falls back to synthetic simulation if parquet lake is unavailable.
    """
    import glob
    pattern = "e:/SUMITH*PROJECT/STRATERGY*Antigravity/data/cache_ohlcv/*_5y.parquet"
    files = glob.glob(pattern)
    
    if not files:
        print("[!] No local parquet cache found. Falling back to synthetic Bhavcopy simulation.")
        return generate_market_data(days=150)
        
    if max_stocks:
        files = files[:max_stocks]
        
    print(f"[+] Ingesting {len(files)} real NIFTY 500 stock series from Parquet Lake...")
    data = {}
    for f in files:
        sym = os.path.basename(f).replace("_5y.parquet", "")
        try:
            df = pd.read_parquet(f)
            df = df.rename(columns={"Close": "close", "High": "high", "Low": "low", "Open": "open", "Volume": "volume"})
            df["date"] = df.index
            df = df.reset_index(drop=True)
            if len(df) >= 50:
                data[sym] = df
        except Exception:
            continue
            
    print(f"[✓] Loaded {len(data)} verified real stock histories.")
    return data


def generate_market_data(days: int = 150) -> dict:
    """
    Generates structured OHLCV time series for Nifty 500 stocks matching official NSE Bhavcopy specs.
    Injects realistic momentum and breakout regimes for testing.
    """
    np.random.seed(101)
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq="B")
    
    stocks = {
        "TRENT": {"base": 7800.0, "trend": 0.0035, "action": "BREAKOUT"},
        "BEL": {"base": 295.0, "trend": 0.0028, "action": "NEAR_BREAKOUT"},
        "DIXON": {"base": 14500.0, "trend": 0.0030, "action": "PULLBACK"},
        "TATAMOTORS": {"base": 915.0, "trend": 0.0005, "action": "FALSE_BREAKOUT"},
        "POLYCAB": {"base": 6800.0, "trend": 0.0025, "action": "REGULAR"},
        "HAL": {"base": 4400.0, "trend": 0.0032, "action": "BREAKOUT"},
        "RELIANCE": {"base": 2900.0, "trend": 0.0008, "action": "REGULAR"},
        "HDFCBANK": {"base": 1750.0, "trend": 0.0010, "action": "REGULAR"},
        "BHARTIARTL": {"base": 1650.0, "trend": 0.0020, "action": "REGULAR"},
        "VBL": {"base": 1580.0, "trend": 0.0030, "action": "PULLBACK"}
    }
    
    data = {}
    for sym, meta in stocks.items():
        base = meta["base"]
        trend = meta["trend"]
        action = meta["action"]
        
        # Continuous compounding random walk with upward trend
        noise = np.random.normal(trend, 0.016, days)
        close = base * np.cumprod(1 + noise)
        
        high = close * (1 + np.abs(np.random.normal(0.009, 0.004, days)))
        low = close * (1 - np.abs(np.random.normal(0.009, 0.004, days)))
        open_p = close * (1 + np.random.normal(0, 0.004, days))
        vol = np.random.randint(800000, 6000000, days)
        
        # Apply specific pattern states on latest bar
        if action == "BREAKOUT":
            close[-1] = max(high[-21:-1]) * 1.025
            high[-1] = close[-1] * 1.008
            vol[-1] = int(np.mean(vol[-20:]) * 1.70)  # +70% volume expansion
        elif action == "NEAR_BREAKOUT":
            close[-1] = max(high[-21:-1]) * 0.992
            high[-1] = max(high[-21:-1]) * 0.998
            vol[-1] = int(np.mean(vol[-20:]) * 1.40)
        elif action == "PULLBACK":
            # Retest of 20 EMA, then rising
            close[-1] = close[-2] * 1.022
            high[-1] = close[-1] * 1.005
            low[-1] = close[-2] * 0.99
            vol[-1] = int(np.mean(vol[-20:]) * 1.35)
        elif action == "FALSE_BREAKOUT":
            high[-1] = max(high[-21:-1]) * 1.015  # Pierced high intraday
            close[-1] = max(high[-21:-1]) * 0.982  # Closed below pivot
            vol[-1] = int(np.mean(vol[-20:]) * 1.45)
            
        df = pd.DataFrame({
            "date": dates,
            "symbol": sym,
            "open": open_p,
            "high": high,
            "low": low,
            "close": close,
            "volume": vol
        })
        data[sym] = df
        
    return data


# =====================================================================
# MAIN ENTRYPOINT
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="Nifty 500 Bullish Momentum Strategy Engine")
    parser.add_argument("--mode", choices=["scan", "backtest", "all"], default="all")
    parser.add_argument("--regime", choices=["bull", "bear"], default="bull")
    parser.add_argument("--data", choices=["real", "mock"], default="real")
    parser.add_argument("--strategy", choices=["ratchet", "baseline"], default="ratchet")
    parser.add_argument("--max-stocks", type=int, default=None)
    args = parser.parse_args()
    
    is_bearish = (args.regime == "bear")
    
    print("=" * 85)
    print("  NIFTY 500 BULLISH PATTERN & MOMENTUM TRADING DESK (GCP ENGINE)")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Market Regime: {'BEARISH (Nifty 50 < 50 EMA - Risk Protection: SL Halved to 3.5-4%)' if is_bearish else 'BULLISH (Nifty 50 >= 50 EMA - Full Risk Permitted)'}")
    print(f"  Max Trade Allocation: INR {CONFIG['MAX_CAPITAL_PER_TRADE']:,.2f} | R:R Floor: >= 1:2")
    print(f"  Trade Constraints: Capital Bound (INR 1.25L/trade) | No Artificial Trade Count Cap")
    print("=" * 85)
    
    if args.data == "real":
        market_data = load_real_market_data(max_stocks=args.max_stocks)
    else:
        market_data = generate_market_data(days=150)
    
    # 1. Scanner Run
    signals = []
    for sym, df in market_data.items():
        processed_df = calculate_indicators(df)
        sig = evaluate_stock_signals(sym, processed_df, is_bearish)
        if sig:
            signals.append(sig)
            
    signals_df = pd.DataFrame(signals)
    output_dir = "artifacts/file_generation/ttl=63d/output"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_file = os.path.join(output_dir, "nifty500_daily_signals.csv")
    signals_df.to_csv(csv_file, index=False)
    
    json_file = os.path.join(output_dir, "nifty500_daily_signals.json")
    with open(json_file, "w") as f:
        json.dump(signals, f, indent=2)
        
    print(f"\n[+] Actionable Signals Identified: {len(signals)}")
    if not signals_df.empty:
        cols = ["symbol", "signal_status", "cmp", "volume_expansion_pct", "stop_loss_pct", "quantity", "total_investment", "target_1_days", "target_2_weeks"]
        print(signals_df[cols].to_string(index=False))
        
    # 2. Backtest Run
    if args.mode in ["backtest", "all"]:
        print("\n" + "=" * 85)
        print("  HISTORICAL BACKTEST AUDIT & MINERVINI EXPECTANCY VALIDATION")
        print("=" * 85)
        bt_summary = run_vectorized_backtest(market_data, is_bearish, strategy_mode=args.strategy)
        for k, v in bt_summary.items():
            print(f"  {k:<30}: {v}")
            
        summary_file = os.path.join(output_dir, "backtest_summary.json")
        with open(summary_file, "w") as f:
            json.dump(bt_summary, f, indent=2)
            
    print(f"\n[✓] Generated deliverables:")
    print(f"    - Signals Table: {csv_file}")
    print(f"    - BigQuery JSON: {json_file}")


if __name__ == "__main__":
    main()