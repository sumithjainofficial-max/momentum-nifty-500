import yfinance as yf
import pandas as pd
import numpy as np

# Download 5 years daily data for DIXON.NS
df = yf.download('DIXON.NS', period='5y', interval='1d', progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df['SMA50'] = df['Close'].rolling(50).mean()
df['VolAvg20'] = df['Volume'].rolling(20).mean()
df['High20'] = df['High'].shift(1).rolling(20).max() # 20-day high excluding current bar

# RSI 14
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# Entry Condition:
df['Cross'] = (df['Close'] > df['High20']) & (df['Close'].shift(1) <= df['High20'].shift(1))
df['Entry'] = df['Cross'] & (df['Volume'] > 1.5 * df['VolAvg20']) & (df['RSI'] > 55) & (df['Close'] > df['SMA50'])

trades = []
in_pos = False
entry_price = 0.0
entry_date = None
sl_price = 0.0
tp_price = 0.0

capital = 100000.0
curr_capital = capital

for i in range(50, len(df)):
    row = df.iloc[i]
    dt = df.index[i].strftime('%Y-%m-%d')
    c = float(row['Close'])
    h = float(row['High'])
    l = float(row['Low'])
    
    if not in_pos:
        if row['Entry']:
            in_pos = True
            entry_price = c
            entry_date = dt
            sl_price = entry_price * 0.93  # 7% SL
            tp_price = entry_price * 1.14  # 14% TP
            shares = max(1, int(curr_capital // entry_price))
    else:
        # Check exit
        exit_price = None
        exit_reason = None
        
        # Check SL/TP
        if l <= sl_price:
            exit_price = sl_price
            exit_reason = 'STOP_LOSS (-7%)'
        elif h >= tp_price:
            exit_price = tp_price
            exit_reason = 'TARGET (+14%)'
            
        if exit_price:
            pnl_pct = (exit_price - entry_price) / entry_price - 0.0005 # 0.05% slippage
            pnl_rs = shares * entry_price * pnl_pct
            curr_capital += pnl_rs
            trades.append({
                'Entry Date': entry_date,
                'Exit Date': dt,
                'Entry Price': round(entry_price, 2),
                'Exit Price': round(exit_price, 2),
                'Shares': shares,
                'Reason': exit_reason,
                'PnL %': round(pnl_pct * 100, 2),
                'PnL (Rs)': round(pnl_rs, 2),
                'Ending Capital': round(curr_capital, 2)
            })
            in_pos = False

trades_df = pd.DataFrame(trades)
print(f"Total Trades: {len(trades_df)}")
if len(trades_df) > 0:
    wins = trades_df[trades_df['PnL %'] > 0]
    losses = trades_df[trades_df['PnL %'] <= 0]
    win_rate = len(wins) / len(trades_df) * 100
    tot_pnl = curr_capital - capital
    ret_pct = (tot_pnl / capital) * 100
    avg_gain = wins['PnL %'].mean() if len(wins) > 0 else 0
    avg_loss = losses['PnL %'].mean() if len(losses) > 0 else 0
    gross_win = wins['PnL (Rs)'].sum()
    gross_loss = abs(losses['PnL (Rs)'].sum()) if len(losses) > 0 else 1
    pf = gross_win / gross_loss
    
    print(f"Win Rate: {win_rate:.1f}% ({len(wins)} Wins / {len(losses)} Losses)")
    print(f"Starting Capital: Rs {capital:,.2f}")
    print(f"Ending Capital: Rs {curr_capital:,.2f} ({ret_pct:+.2f}%)")
    print(f"Average Gain: +{avg_gain:.2f}%")
    print(f"Average Loss: {avg_loss:.2f}%")
    print(f"Profit Factor: {pf:.2f}")
    print("\nComplete Trade Log:")
    print(trades_df.to_string(index=False))

