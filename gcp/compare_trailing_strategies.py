"""
Head-to-Head Strategy Comparison Engine:
1. Baseline Strategy: Fixed Target 1:2 exit / standard 15-30 bar time trail.
2. Dynamic Ratchet Strategy:
   - Target 1 achieves -> Target 1 becomes the new Stop Loss, Target 2 becomes primary target.
   - Same-day Target 1 achievement:
     - 2% intraday buffer below Target 1.
     - If Close >= Target 1: Ratchet locked, pursue Target 2.
     - If Close < Target 1: Exit at Close (profit banked).
   - Momentum over condition: Close < 20 EMA and Daily RSI < 50.
Tested on ALL 499 Real NIFTY 500 stocks over 5 full years (2021-2026) with 15 bps friction.
"""

import os
import sys
import glob
import pandas as pd
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def load_universe():
    files = glob.glob('e:/SUMITH*PROJECT/STRATERGY*Antigravity/data/cache_ohlcv/*_5y.parquet')
    print(f"[+] Loading {len(files)} real stock histories from Parquet Lake...")
    universe = {}
    for f in files:
        sym = os.path.basename(f).replace('_5y.parquet', '')
        try:
            df = pd.read_parquet(f)
            df = df.rename(columns={'Close': 'close', 'High': 'high', 'Low': 'low', 'Open': 'open', 'Volume': 'volume'})
            df = df.sort_index()
            if len(df) < 60:
                continue
            df['vol_sma20'] = df['volume'].rolling(20).mean()
            df['vol_exp'] = (df['volume'] - df['vol_sma20']) / df['vol_sma20'].replace(0, np.nan)
            df['pivot_high20'] = df['high'].shift(1).rolling(20).max()
            df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
            universe[sym] = df
        except Exception:
            continue
    print(f"[✓] Successfully prepared {len(universe)} stock datasets.")
    return universe

def run_backtest_baseline(universe: dict, friction_bps: float = 15.0) -> pd.DataFrame:
    """Strategy A: Baseline Fixed Target (Exit at Target 1:2 or 30-day time trail)."""
    cost = friction_bps / 10000.0
    trades = []
    
    for sym, df in universe.items():
        in_trade = False
        entry_p = 0.0
        sl_p = 0.0
        tgt_p = 0.0
        entry_date = None
        
        for dt, row in df.iloc[30:].iterrows():
            c, h, l = row['close'], row['high'], row['low']
            rsi_d = row.get('RSI_Daily', 50)
            rsi_w = row.get('RSI_Weekly', 50)
            
            if not in_trade:
                if row['vol_exp'] >= 0.25 and (rsi_d >= 60) and (60 <= rsi_w <= 75) and (c >= row['pivot_high20']):
                    in_trade = True
                    entry_p = c
                    sl_p = round(entry_p * 0.93, 2)
                    risk = entry_p - sl_p
                    tgt_p = round(entry_p + 2.0 * risk, 2)
                    entry_date = dt
            else:
                bars_held = (dt - entry_date).days
                # Stop loss
                if l <= sl_p:
                    exit_p = sl_p
                    pnl = (exit_p - entry_p) / entry_p - cost
                    trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'LOSS', 'reason': 'STOP_LOSS', 'days': bars_held, 'r_multiple': -1.0})
                    in_trade = False
                # Fixed Target Hit
                elif h >= tgt_p:
                    exit_p = tgt_p
                    pnl = (exit_p - entry_p) / entry_p - cost
                    trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'TARGET_1_HIT', 'days': bars_held, 'r_multiple': 2.0})
                    in_trade = False
                # Time exit
                elif bars_held >= 30:
                    exit_p = c
                    pnl = (exit_p - entry_p) / entry_p - cost
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    rm = pnl / 0.07
                    trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': res, 'reason': 'TIME_EXIT', 'days': bars_held, 'r_multiple': rm})
                    in_trade = False
                    
    return pd.DataFrame(trades)

def run_backtest_ratchet(universe: dict, friction_bps: float = 15.0) -> pd.DataFrame:
    """Strategy B: User's Proposed Dynamic Target-as-Stop-Loss Ratchet."""
    cost = friction_bps / 10000.0
    trades = []
    
    for sym, df in universe.items():
        in_trade = False
        entry_p = 0.0
        active_sl = 0.0
        target_1 = 0.0
        target_2 = 0.0
        target_3 = 0.0
        active_target = 0.0
        stage = 0  # 0: Hunting T1, 1: T1 locked as SL (Hunting T2), 2: T2 locked as SL (Hunting T3+)
        entry_date = None
        
        for dt, row in df.iloc[30:].iterrows():
            c, h, l = row['close'], row['high'], row['low']
            rsi_d = row.get('RSI_Daily', 50)
            rsi_w = row.get('RSI_Weekly', 50)
            ema20 = row.get('ema20', c)
            
            if not in_trade:
                if row['vol_exp'] >= 0.25 and (rsi_d >= 60) and (60 <= rsi_w <= 75) and (c >= row['pivot_high20']):
                    in_trade = True
                    entry_p = c
                    active_sl = round(entry_p * 0.93, 2)
                    risk = entry_p - active_sl
                    target_1 = round(entry_p + 2.0 * risk, 2)
                    target_2 = round(entry_p + 3.5 * risk, 2)
                    target_3 = round(entry_p + 6.0 * risk, 2)
                    active_target = target_1
                    stage = 0
                    entry_date = dt
            else:
                bars_held = (dt - entry_date).days
                
                # STAGE 0: Hunting Target 1
                if stage == 0:
                    # Check if stop loss hit first
                    if l <= active_sl:
                        exit_p = active_sl
                        pnl = (exit_p - entry_p) / entry_p - cost
                        trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'LOSS', 'reason': 'INITIAL_SL', 'days': bars_held, 'r_multiple': -1.0, 'exit_stage': 'Initial SL'})
                        in_trade = False
                    # Check if Target 1 breached today!
                    elif h >= target_1:
                        # User Rule: Same-day Target 1 achievement
                        # "hold it till it fall 2% below target 1"
                        buffer_2pct_level = target_1 * 0.98
                        if l <= buffer_2pct_level:
                            # Retraced 2% below Target 1 intraday -> Exit
                            exit_p = buffer_2pct_level
                            pnl = (exit_p - entry_p) / entry_p - cost
                            trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'T1_INTRADAY_BUFFER_EXIT', 'days': bars_held, 'r_multiple': (exit_p - entry_p)/risk, 'exit_stage': 'T1 Buffer Exit'})
                            in_trade = False
                        else:
                            # Did not breach 2% buffer intraday. Now evaluate Close:
                            if c >= target_1:
                                # "if during closing its above target 1 then make target 1 as stoploss"
                                active_sl = target_1
                                active_target = target_2
                                stage = 1 # Ratchet locked! Now targeting T2
                            else:
                                # "and if its below target 1 then take exit"
                                exit_p = c
                                pnl = (exit_p - entry_p) / entry_p - cost
                                trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'T1_CLOSE_BELOW_EXIT', 'days': bars_held, 'r_multiple': (exit_p - entry_p)/risk, 'exit_stage': 'T1 Close Exit'})
                                in_trade = False
                                
                # STAGE 1: Target 1 is Stop Loss, Hunting Target 2
                elif stage == 1:
                    # Check if Trailed Stop Loss (Target 1) is breached
                    if l <= active_sl:
                        exit_p = active_sl
                        pnl = (exit_p - entry_p) / entry_p - cost
                        trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'TRAILED_T1_SL_HIT', 'days': bars_held, 'r_multiple': 2.0, 'exit_stage': 'T1 Trailed SL'})
                        in_trade = False
                    # Check if Target 2 is breached today!
                    elif h >= target_2:
                        # Same logic for Target 2
                        buffer_2pct_t2 = target_2 * 0.98
                        if l <= buffer_2pct_t2:
                            exit_p = buffer_2pct_t2
                            pnl = (exit_p - entry_p) / entry_p - cost
                            trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'T2_BUFFER_EXIT', 'days': bars_held, 'r_multiple': (exit_p - entry_p)/risk, 'exit_stage': 'T2 Buffer Exit'})
                            in_trade = False
                        else:
                            if c >= target_2:
                                active_sl = target_2
                                active_target = target_3
                                stage = 2 # Ratchet locked! Now targeting T3
                            else:
                                exit_p = c
                                pnl = (exit_p - entry_p) / entry_p - cost
                                trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'T2_CLOSE_EXIT', 'days': bars_held, 'r_multiple': (exit_p - entry_p)/risk, 'exit_stage': 'T2 Close Exit'})
                                in_trade = False
                    # Check Momentum Over: Close below 20 EMA and Daily RSI < 50
                    elif c < ema20 and rsi_d < 50:
                        exit_p = c
                        pnl = (exit_p - entry_p) / entry_p - cost
                        trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN' if pnl > 0 else 'LOSS', 'reason': 'MOMENTUM_OVER_20EMA', 'days': bars_held, 'r_multiple': (exit_p - entry_p)/risk, 'exit_stage': 'Momentum Over'})
                        in_trade = False

                # STAGE 2: Target 2 is Stop Loss, Hunting Target 3 (Multi-bagger runner)
                elif stage == 2:
                    if l <= active_sl:
                        exit_p = active_sl
                        pnl = (exit_p - entry_p) / entry_p - cost
                        trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'TRAILED_T2_SL_HIT', 'days': bars_held, 'r_multiple': 3.5, 'exit_stage': 'T2 Trailed SL'})
                        in_trade = False
                    elif h >= target_3:
                        exit_p = target_3
                        pnl = (exit_p - entry_p) / entry_p - cost
                        trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'TARGET_3_MAX_RUNNER', 'days': bars_held, 'r_multiple': 6.0, 'exit_stage': 'T3 Super Runner'})
                        in_trade = False
                    elif c < ema20 and rsi_d < 50:
                        exit_p = c
                        pnl = (exit_p - entry_p) / entry_p - cost
                        trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'MOMENTUM_OVER_RUNNER', 'days': bars_held, 'r_multiple': (exit_p - entry_p)/risk, 'exit_stage': 'Runner Momentum Over'})
                        in_trade = False

    return pd.DataFrame(trades)

def compute_metrics(df: pd.DataFrame, name: str) -> dict:
    if df.empty:
        return {}
    wins = df[df['result'] == 'WIN']
    losses = df[df['result'] == 'LOSS']
    total = len(df)
    win_rate = (len(wins) / total) * 100.0
    avg_win = wins['pnl_pct'].mean() * 100.0 if len(wins) > 0 else 0.0
    avg_loss = abs(losses['pnl_pct'].mean() * 100.0) if len(losses) > 0 else 0.0
    gl_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
    expectancy = ((win_rate / 100.0) * avg_win) - (((100.0 - win_rate) / 100.0) * avg_loss)
    gross_win_sum = wins['pnl_pct'].sum()
    gross_loss_sum = abs(losses['pnl_pct'].sum())
    profit_factor = gross_win_sum / gross_loss_sum if gross_loss_sum > 0 else 999.0
    avg_days = df['days'].mean()
    
    # Cumulative return approximation (assuming equal weight allocation per trade)
    total_cum_pnl_pct = df['pnl_pct'].sum() * 100.0
    
    # Large Winners (>= +20% gain or >= 3R)
    big_winners = len(df[df['pnl_pct'] >= 0.20])
    super_winners = len(df[df['pnl_pct'] >= 0.35])
    
    return {
        "Strategy Name": name,
        "Total Trades": total,
        "Win Rate %": round(win_rate, 2),
        "Average Win %": round(avg_win, 2),
        "Average Loss %": round(avg_loss, 2),
        "Gain/Loss Ratio": f"{round(gl_ratio, 2)} : 1",
        "Net Expectancy / Trade": f"+{round(expectancy, 2)}%" if expectancy > 0 else f"{round(expectancy, 2)}%",
        "Profit Factor": round(profit_factor, 2),
        "Avg Holding Period": f"{round(avg_days, 1)} Days",
        "Trades >= +20% (Runners)": big_winners,
        "Trades >= +35% (Super Runners)": super_winners,
        "Cumulative Net Return %": f"+{round(total_cum_pnl_pct, 1)}%"
    }

def main():
    universe = load_universe()
    
    print("\n" + "=" * 80)
    print("  SIMULATING STRATEGY 1: BASELINE (FIXED TARGET 1:2)")
    print("=" * 80)
    df_base = run_backtest_baseline(universe)
    m_base = compute_metrics(df_base, "Baseline (Fixed 1:2 Target)")
    
    print("\n" + "=" * 80)
    print("  SIMULATING STRATEGY 2: PROPOSED TARGET-AS-STOP-LOSS RATCHET")
    print("=" * 80)
    df_ratchet = run_backtest_ratchet(universe)
    m_ratchet = compute_metrics(df_ratchet, "Target-as-Stop-Loss Ratchet (With 2% Buffer)")
    
    comp_df = pd.DataFrame([m_base, m_ratchet]).T
    comp_df.columns = ["Baseline (Fixed Target)", "Proposed Ratchet Model"]
    
    print("\n" + "=" * 85)
    print("  HEAD-TO-HEAD SCIENTIFIC COMPARISON (5-YEAR REAL NSE DATA)")
    print("=" * 85)
    print(comp_df.to_string())
    
    # Exit Reason Breakdown for Ratchet Strategy
    print("\n" + "=" * 85)
    print("  RATCHET STRATEGY EXIT REASON BREAKDOWN")
    print("=" * 85)
    exit_counts = df_ratchet['exit_stage'].value_counts()
    for stage, count in exit_counts.items():
        pct = (count / len(df_ratchet)) * 100.0
        avg_p = df_ratchet[df_ratchet['exit_stage'] == stage]['pnl_pct'].mean() * 100.0
        print(f"  {stage:<25}: {count:>5} trades ({pct:>5.1f}%) | Avg PnL: {avg_p:>+6.2f}%")

if __name__ == "__main__":
    main()

