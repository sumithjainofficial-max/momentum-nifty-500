import glob
import os
import pandas as pd
import numpy as np

def test_real_data():
    files = glob.glob('e:/SUMITH*PROJECT/STRATERGY*Antigravity/data/cache_ohlcv/*_5y.parquet')
    print(f"Found {len(files)} real stock parquets.")
    
    all_trades = []
    
    for f in files:
        sym = os.path.basename(f).replace('_5y.parquet', '')
        df = pd.read_parquet(f)
        df = df.rename(columns={'Close': 'close', 'High': 'high', 'Low': 'low', 'Open': 'open', 'Volume': 'volume'})
        df = df.sort_index()
        if len(df) < 60:
            continue
            
        # Indicators
        df['vol_sma20'] = df['volume'].rolling(20).mean()
        df['vol_exp'] = (df['volume'] - df['vol_sma20']) / df['vol_sma20'].replace(0, np.nan)
        df['pivot_high20'] = df['high'].shift(1).rolling(20).max()
        
        in_trade = False
        entry_p = 0.0
        sl_p = 0.0
        tgt_p = 0.0
        entry_date = None
        
        for dt, row in df.iloc[30:].iterrows():
            c, h, l = row['close'], row['high'], row['low']
            if not in_trade:
                # Breakout signal: vol expansion >= 25%, Daily RSI >= 60, Weekly RSI in 60-75, close >= 20-day pivot
                rsi_d = row.get('RSI_Daily', 50)
                rsi_w = row.get('RSI_Weekly', 50)
                if row['vol_exp'] >= 0.25 and (rsi_d >= 60) and (60 <= rsi_w <= 75) and (c >= row['pivot_high20']):
                    in_trade = True
                    entry_p = c
                    sl_p = round(entry_p * 0.93, 2)  # 7% standard SL
                    risk = entry_p - sl_p
                    tgt_p = round(entry_p + 2.0 * risk, 2) # 1:2 RR (14%)
                    entry_date = dt
            else:
                bars_held = (dt - entry_date).days
                # Stop hit
                if l <= sl_p:
                    exit_p = sl_p
                    pnl = (exit_p - entry_p) / entry_p - 0.0015 # 15 bps friction
                    all_trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'LOSS', 'reason': 'STOP_LOSS', 'days': bars_held})
                    in_trade = False
                # Target hit
                elif h >= tgt_p:
                    exit_p = tgt_p
                    pnl = (exit_p - entry_p) / entry_p - 0.0015
                    all_trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': 'WIN', 'reason': 'TARGET_HIT', 'days': bars_held})
                    in_trade = False
                # Time exit after 30 days
                elif bars_held >= 30:
                    exit_p = c
                    pnl = (exit_p - entry_p) / entry_p - 0.0015
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    all_trades.append({'symbol': sym, 'entry_date': entry_date, 'exit_date': dt, 'entry_price': entry_p, 'exit_price': exit_p, 'pnl_pct': pnl, 'result': res, 'reason': 'TIME_EXIT', 'days': bars_held})
                    in_trade = False

    tdf = pd.DataFrame(all_trades)
    print(f"Total Trades Executed: {len(tdf)}")
    if not tdf.empty:
        wins = tdf[tdf['result'] == 'WIN']
        losses = tdf[tdf['result'] == 'LOSS']
        win_rate = len(wins) / len(tdf) * 100
        avg_gain = wins['pnl_pct'].mean() * 100
        avg_loss = abs(losses['pnl_pct'].mean()) * 100
        gl_ratio = avg_gain / avg_loss if avg_loss > 0 else 0
        loss_rate = 100 - win_rate
        expectancy = ((win_rate / 100) * avg_gain) - ((loss_rate / 100) * avg_loss)
        pf = wins['pnl_pct'].sum() / abs(losses['pnl_pct'].sum()) if abs(losses['pnl_pct'].sum()) > 0 else 0
        
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Average Win: +{avg_gain:.2f}%")
        print(f"Average Loss: -{avg_loss:.2f}%")
        print(f"Gain/Loss Ratio: {gl_ratio:.2f}:1")
        print(f"Net Expectancy per trade: {expectancy:+.2f}%")
        print(f"Profit Factor: {pf:.2f}")

if __name__ == '__main__':
    test_real_data()

