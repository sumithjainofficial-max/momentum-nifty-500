import os
import sys
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

NSE_CSV = "all_nse_equities.csv"
OUTPUT_EXCEL = os.path.join("Excel", "NSE_Undervalued_Quality_Stocks_Below_Book_Value.xlsx")

def evaluate_stock(symbol, company_name):
    ticker = f"{symbol}.NS"
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            return None
            
        cmp = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        bv = info.get("bookValue")
        
        if not cmp or not bv or bv <= 0 or cmp < 20.0:
            return None
            
        pb = cmp / bv
        discount_to_bv = ((bv - cmp) / bv) * 100
        
        # We want stocks trading 15% to 50% below book value
        if pb > 0.85 or pb < 0.35: # Exclude extreme micro-cap distress traps below 0.35 PB
            return None
            
        pe = info.get("trailingPE")
        eps = info.get("trailingEps")
        roe = info.get("returnOnEquity")
        profit_margin = info.get("profitMargins")
        debt_to_equity = info.get("debtToEquity")
        div_yield = info.get("dividendYield")
        mcap = info.get("marketCap", 0)
        
        # Fundamental Safety Checks ("Nothing wrong with fundamentals")
        # 1. Market Cap must be at least ₹500 Cr (eliminates penny shell companies)
        if not mcap or mcap < 500 * 10000000:
            return None
            
        # 2. Profitable: Positive EPS, Positive ROE, Positive Margin
        if eps is not None and eps <= 0:
            return None
        if roe is not None and roe <= 0:
            return None
        if profit_margin is not None and profit_margin <= 0:
            return None
            
        # 3. Debt to Equity: Non-financials must have D/E < 1.2
        industry = info.get("industry", "Unknown")
        sector = info.get("sector", "Unknown")
        is_fin = any(x in f"{sector} {industry}".lower() for x in ["bank", "financial", "insurance", "capital market", "credit"])
        
        if not is_fin and debt_to_equity is not None:
            if debt_to_equity > 120: # D/E > 1.2
                return None
                
        # Classify Discount
        if 20.0 <= discount_to_bv <= 26.0:
            tier = "🎯 EXACT SWEET SPOT (20% - 25% Below BV)"
        elif discount_to_bv > 26.0:
            tier = "💎 DEEP VALUE (>25% Below BV)"
        else:
            tier = "⚡ NEAR VALUE (15% - 20% Below BV)"
            
        roe_pct = round(roe * 100, 2) if roe else None
        margin_pct = round(profit_margin * 100, 2) if profit_margin else None
        div_pct = round(div_yield * 100, 2) if div_yield and div_yield < 1 else (round(div_yield, 2) if div_yield else 0.0)
        de_ratio = round(debt_to_equity / 100, 2) if debt_to_equity else (0.0 if not is_fin else "Financial (Regulated)")
        
        return {
            "Symbol": symbol,
            "Company Name": company_name,
            "Sector / Industry": f"{sector} / {industry}",
            "CMP (₹)": round(cmp, 2),
            "Book Value (₹)": round(bv, 2),
            "Discount to BV (%)": round(discount_to_bv, 2),
            "P/B Ratio": round(pb, 2),
            "Trailing P/E": round(pe, 2) if pe else "N/A",
            "ROE (%)": roe_pct if roe_pct is not None else "N/A",
            "Net Profit Margin (%)": margin_pct if margin_pct is not None else "N/A",
            "Debt-to-Equity": de_ratio,
            "Dividend Yield (%)": f"{div_pct:.2f}%",
            "Market Cap (₹ Cr)": round(mcap / 10000000, 1),
            "Discount Category": tier,
            "Fundamental Health Verdict": "CLEAN & PROFITABLE (Positive EPS/ROE, Low/Prudent Debt)"
        }
    except Exception:
        return None

def main():
    print("[*] Reading full NSE equities directory...")
    df_nse = pd.read_csv(NSE_CSV)
    if 'SERIES' in df_nse.columns:
        df_nse = df_nse[df_nse['SERIES'] == 'EQ']
        
    stocks = list(zip(df_nse['SYMBOL'], df_nse['NAME OF COMPANY']))
    print(f"[*] Total active regular equities: {len(stocks)}")
    print("[*] Running parallel fundamental audit for stocks trading 20-25%+ below Book Value...")
    
    results = []
    completed = 0
    with ThreadPoolExecutor(max_workers=35) as executor:
        futures = {executor.submit(evaluate_stock, s, n): s for s, n in stocks}
        for future in as_completed(futures):
            completed += 1
            if completed % 200 == 0 or completed == len(stocks):
                print(f"[*] Processed {completed}/{len(stocks)} stocks (Quality Undervalued found: {len(results)})...")
            res = future.result()
            if res:
                results.append(res)
                
    print(f"\n[✓] Scan Complete! Found {len(results)} high-quality fundamentally sound stocks trading below Book Value.")
    if not results:
        return
        
    df = pd.DataFrame(results)
    df = df.sort_values(by="Discount to BV (%)", ascending=False)
    
    os.makedirs(os.path.dirname(OUTPUT_EXCEL), exist_ok=True)
    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"[✓] Successfully exported full audit to Excel: {OUTPUT_EXCEL}")
    
    # Summary by Category
    print("\nBreakdown by Discount Category:")
    print(df["Discount Category"].value_counts())
    
    print("\nTop Candidates in the EXACT 20% - 25% Sweet Spot:")
    sweet_spot = df[df["Discount Category"].str.contains("SWEET SPOT")]
    print(sweet_spot[['Symbol', 'Company Name', 'CMP (₹)', 'Book Value (₹)', 'Discount to BV (%)', 'P/B Ratio', 'Trailing P/E', 'ROE (%)', 'Dividend Yield (%)']].to_string(index=False))

if __name__ == "__main__":
    main()
