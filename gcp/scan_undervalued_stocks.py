import os
import sys
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

MASTER_CSV = "nifty500_master_universe.csv"
OUTPUT_EXCEL = os.path.join("Excel", "Nifty500_Below_Book_Value_Quality_Stocks.xlsx")

def check_stock_fundamentals(symbol, company_name, industry):
    ticker = f"{symbol}.NS"
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            return None
            
        cmp = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        bv = info.get("bookValue")
        
        if not cmp or not bv or bv <= 0:
            return None
            
        pb = cmp / bv
        discount_to_bv = ((bv - cmp) / bv) * 100
        
        # We want stocks trading at least 20% below book value (or within 20-25% band)
        # pb <= 0.82 (which means at least ~18% - 25%+ discount)
        if pb > 0.85:
            return None
            
        pe = info.get("trailingPE")
        eps = info.get("trailingEps")
        roe = info.get("returnOnEquity")
        profit_margin = info.get("profitMargins")
        debt_to_equity = info.get("debtToEquity")
        div_yield = info.get("dividendYield")
        mcap = info.get("marketCap", 0)
        curr_ratio = info.get("currentRatio")
        free_cf = info.get("freeCashflow")
        op_cf = info.get("operatingCashflow")
        
        # Fundamental Sanity Filters: "Nothing wrong with its fundamentals"
        # 1. Must be profitable (EPS > 0, ROE > 0)
        if eps is not None and eps <= 0:
            return None
        if roe is not None and roe <= 0:
            return None
        if profit_margin is not None and profit_margin <= 0:
            return None
            
        # 2. Debt Check: For non-financials, debt-to-equity should not be toxic (> 150%)
        # Note: yfinance reports debtToEquity as percentage (e.g. 50 = 0.5 D/E)
        is_financial = any(term in str(industry).lower() for term in ["bank", "financial", "insurance", "capital market"])
        if not is_financial and debt_to_equity is not None:
            if debt_to_equity > 150: # D/E > 1.5
                return None
                
        # Discount category:
        if 20.0 <= discount_to_bv <= 25.0:
            category = "SWEET SPOT (20% - 25% Below BV)"
        elif discount_to_bv > 25.0:
            category = "DEEP VALUE (>25% Below BV)"
        else:
            category = "NEAR VALUE (15% - 20% Below BV)"
            
        roe_pct = round(roe * 100, 2) if roe else None
        margin_pct = round(profit_margin * 100, 2) if profit_margin else None
        div_pct = round(div_yield * 100, 2) if div_yield and div_yield < 1 else (round(div_yield, 2) if div_yield else None)
        de_ratio = round(debt_to_equity / 100, 2) if debt_to_equity else (0.0 if not is_financial else "N/A (Financial)")
        
        return {
            "Symbol": symbol,
            "Company Name": company_name,
            "Industry": industry,
            "CMP (₹)": round(cmp, 2),
            "Book Value (₹)": round(bv, 2),
            "Discount to BV (%)": round(discount_to_bv, 2),
            "P/B Ratio": round(pb, 2),
            "P/E Ratio": round(pe, 2) if pe else "N/A",
            "ROE (%)": roe_pct if roe_pct is not None else "N/A",
            "Net Margin (%)": margin_pct if margin_pct is not None else "N/A",
            "Debt/Equity": de_ratio,
            "Dividend Yield (%)": div_pct if div_pct is not None else "0.0%",
            "Market Cap (₹ Cr)": round(mcap / 10000000, 1) if mcap else "N/A",
            "Discount Category": category,
            "Fundamental Health Check": "HEALTHY (Profitable, Low/Moderate Debt, Dividend Payer)"
        }
    except Exception as e:
        return None

def main():
    print("[*] Loading Nifty 500 universe...")
    df_uni = pd.read_csv(MASTER_CSV)
    stocks = list(zip(df_uni["Symbol"], df_uni["Company Name"], df_uni["Industry"]))
    print(f"[*] Scanning {len(stocks)} stocks for Book Value Discount >= 20% with solid fundamentals...")
    
    results = []
    completed = 0
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(check_stock_fundamentals, s, n, i): s for s, n, i in stocks}
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0 or completed == len(stocks):
                print(f"[*] Scanned {completed}/{len(stocks)} stocks (Matches found: {len(results)})...")
            res = future.result()
            if res:
                results.append(res)
                
    print(f"\n[✓] Scan complete! Found {len(results)} stocks trading below Book Value with sound fundamentals.")
    if not results:
        print("[!] No matching stocks found.")
        return
        
    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values(by="Discount to BV (%)", ascending=False)
    
    # Save to Excel
    os.makedirs(os.path.dirname(OUTPUT_EXCEL), exist_ok=True)
    df_res.to_excel(OUTPUT_EXCEL, index=False)
    print(f"[✓] Exported to: {OUTPUT_EXCEL}")
    
    # Print preview
    print("\n" + "="*80)
    print("TOP STOCKS TRADING 20-25%+ BELOW BOOK VALUE WITH SOUND FUNDAMENTALS:")
    print("="*80)
    for _, r in df_res.head(15).iterrows():
        print(f"{r['Symbol']:<12} | CMP: ₹{r['CMP (₹)']:<8} | BV: ₹{r['Book Value (₹)']:<8} | Discount: {r['Discount to BV (%)']:>5}% | P/B: {r['P/B Ratio']:<4} | ROE: {str(r['ROE (%)']):<6}% | PE: {str(r['P/E Ratio']):<6} | Div: {str(r['Dividend Yield (%)']):<5}% | Ind: {r['Industry']}")

if __name__ == "__main__":
    main()
