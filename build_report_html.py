import os
import time
import json
import xml.etree.ElementTree as ET
import pandas as pd
import requests

# Secrets & Endpoints
IBKR_FLEX_TOKEN = os.getenv("IBKR_FLEX_TOKEN")
IBKR_QUERY_ID = os.getenv("IBKR_QUERY_ID")

FLEX_SEND_URL = f"https://www.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest?t={IBKR_FLEX_TOKEN}&q={IBKR_QUERY_ID}&v=3"
FLEX_GET_URL = "https://www.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement?q={ref_code}&t={token}&v=3"

THEME_MAP = {
    'Big Tech': ['AAPL', 'AMZN', 'GOOG', 'GOOGL', 'META', 'MSFT'],
    'Software & IT Services': ['ADBE', 'COUR', 'CRM', 'CRWD', 'CSCO', 'CTSH', 'DOCU', 'DT', 'DUOL', 'GDDY', 'IBM', 'IGV', 'INFY', 'LOGN', 'NBIS', 'ORCL', 'PLTR', 'RDDT', 'SAP', 'SNOW', 'SOUN', 'TDC', 'TEAM', 'WDAY', 'ZS', 'HACK', 'CIBR'],
    'Semiconductors & Hardware': ['AMD', 'ARM', 'AVGO', 'DRAM', 'INTC', 'MU', 'NVDA', 'QCOM', 'SNDK', 'SONY', 'SOXX'],
    'Airlines, Aviation & Logistics': ['AAL', 'AF', 'CON', 'CVNA', 'FDX', 'LCID', 'LHA', 'PNL', 'QAN', 'RYAAY', 'WI2', 'WIZZ', 'UPS', 'XPO', 'STLA', 'TSLA', '7203'],
    'Aerospace & Defense': ['AIR', 'BA', 'RTX', 'LDOS', 'DFEU', 'RKLB', 'SPCX', 'SPCE', 'RDW', 'ITA', '7011'],
    'Healthcare & Biotech': ['AZN', 'NVO', 'BMY', 'MRNA', 'DHR', 'MDT', 'UNH', 'PFE', 'XLV', 'SNY', 'MLTX', 'ATAI', 'XBI', 'GHRS', 'CALM', 'ROG', 'COLO', 'TMO', 'HIMS'],
    'Energy & Utilities': ['CVX', 'EQNR', 'DNQ', 'USO', 'BNO', 'XLE', 'XOM', 'MPC', 'NEE', 'D2G', 'ENGI', 'PCG', 'XE', 'XLU', 'SXEP', 'SHELL', 'VLTSA', 'DRNZ', 'VG'],
    'Financials & Fintech': ['MA', 'IBKR', 'HOOD', 'BBVA', 'OTP', 'UCG', 'SAN', 'SPGI', 'EXX1', 'XLF', 'CRCL', 'RKT', 'KLAR', 'PYPL', 'V', 'BRK B'],
    'Consumer Goods & Retail': ['ADS', 'BIRK', 'LULU', 'NKE', 'AEO', 'GAP', 'DLTR', 'MAT', 'WMT', 'XLY', 'XLP', 'TSCO', 'STUB', 'GME', 'SONO', 'HEN', 'HEN3', 'NCLH'],
    'Restaurants, Food & Beverages': ['MCD', 'CMG', 'QSR', 'WEN', 'SBUX', 'SG', 'HEIA', 'BYND', 'BYND1', 'NESN', 'JACK', 'PLAY', 'CASY', 'YUM', 'DBA', 'GIS'],
    'Media & Telecom': ['NFLX', 'SPOT', 'WBD', 'PSKY', 'T', 'VZ', 'ORA', 'ETL', 'VSNT', 'UBI', 'MEME', 'AMS'],
    'Materials & Mining': ['BAS', 'LXS', 'ALB', 'LIN', 'SIKA', 'SOLB', 'MP', 'REB', 'USAR', 'LYI', 'ILZ', 'RNF', 'SJ60', 'N14', 'NEM', 'NCH2'],
    'Industrials & Real Estate': ['ACS', 'KGX', 'DHI', 'LEN', 'ROP', 'WY', 'SHLD', 'UMAC', 'AADX', 'ALO', 'LIGHT', 'SFT'],
    'Portfolio Hedges & Volatility': ['SPY', 'QQQ', 'QQQM', 'XSP', 'VIX'],
    'US Broad Market & Sector ETFs': ['IWM'],
    'Europe Broad Market ETFs': ['DJ600', 'MEUD', 'CS1', 'LYXIB', 'VGK', 'EXS1'],
    'Asia Broad Market ETFs': ['XDJP', 'SXRZ', 'IKRA', 'EWJ'],
    'Emerging Markets ETFs': ['EEM', 'XCS4', 'IBZL'],
    'Box Spread Financing': ['ESTX50', 'SPX'],
    'Covered Call Broad Market': ['RSP', 'FEZ'],
    'Precious Metals & Crypto': ['GLD', 'SLV', 'IBIT'],
    'Fixed Income': ['TLT']
}

SYMBOL_TO_THEME = {sym: t for t, symbols in THEME_MAP.items() for sym in symbols}

def fetch_flex_report():
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(FLEX_SEND_URL, headers=headers)
    res.raise_for_status()
    root = ET.fromstring(res.text)
    
    if root.findtext("Status") != "Success":
        raise RuntimeError(f"Flex Request Failed: {root.findtext('ErrorMessage')}")
    
    ref_code = root.findtext("ReferenceCode")
    get_url = FLEX_GET_URL.format(ref_code=ref_code, token=IBKR_FLEX_TOKEN)
    
    for _ in range(12):
        time.sleep(10)
        stmt_res = requests.get(get_url, headers=headers)
        if "<FlexQueryResponse" in stmt_res.text:
            return stmt_res.text
    raise TimeoutError("IBKR Flex Statement generation timed out.")

def parse_xml_to_df(xml_data):
    root = ET.fromstring(xml_data)
    records = []
    
    for trade in root.iter("Trade"):
        symbol = trade.get("symbol")
        underlying = trade.get("underlyingSymbol") or symbol
        records.append({
            "Symbol": symbol,
            "UnderlyingSymbol": underlying,
            "Description": trade.get("description"),
            "TotalFifoPnl": float(trade.get("fifoPnlRealized", 0.0)),
            "TotalRealizedPnl": float(trade.get("fifoPnlRealized", 0.0)),
            "TotalUnrealizedPnl": 0.0
        })
        
    for pos in root.iter("OpenPosition"):
        symbol = pos.get("symbol")
        underlying = pos.get("underlyingSymbol") or symbol
        records.append({
            "Symbol": symbol,
            "UnderlyingSymbol": underlying,
            "Description": pos.get("description"),
            "TotalFifoPnl": float(pos.get("fifoPnlUnrealized", 0.0)),
            "TotalRealizedPnl": 0.0,
            "TotalUnrealizedPnl": float(pos.get("fifoPnlUnrealized", 0.0))
        })
        
    df = pd.DataFrame(records)
    df["Theme"] = df["UnderlyingSymbol"].map(lambda x: SYMBOL_TO_THEME.get(x, "Other"))
    return df

def generate_html_report(df):
    theme_summary = df.groupby('Theme').agg(
        TotalFifoPnl=('TotalFifoPnl', 'sum'),
        RealizedPnl=('TotalRealizedPnl', 'sum'),
        UnrealizedPnl=('TotalUnrealizedPnl', 'sum'),
        AssetCount=('UnderlyingSymbol', 'nunique'),
        TradeCount=('Symbol', 'count')
    ).reset_index().sort_values('TotalFifoPnl', ascending=False)
    
    os.makedirs("public", exist_ok=True)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>IBKR Portfolio Performance Report (EUR)</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 24px; border: 1px solid #334155; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; }}
        .positive {{ color: #10b981; font-weight: bold; }}
        .negative {{ color: #ef4444; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Portfolio PnL Performance Report (EUR)</h1>
    <div class="card">
        <h2>Theme Performance Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Theme</th>
                    <th>Assets</th>
                    <th style="text-align:right;">Realized PnL (€)</th>
                    <th style="text-align:right;">Unrealized PnL (€)</th>
                    <th style="text-align:right;">Net FIFO PnL (€)</th>
                </tr>
            </thead>
            <tbody>
"""
    for _, row in theme_summary.iterrows():
        pnl = row['TotalFifoPnl']
        cls = "positive" if pnl >= 0 else "negative"
        html += f"""
            <tr>
                <td>{row['Theme']}</td>
                <td>{row['AssetCount']}</td>
                <td style="text-align:right;">€{row['RealizedPnl']:,.2f}</td>
                <td style="text-align:right;">€{row['UnrealizedPnl']:,.2f}</td>
                <td style="text-align:right;" class="{cls}">€{pnl:,.2f}</td>
            </tr>"""
            
    html += """
            </tbody>
        </table>
    </div>
</body>
</html>"""
    
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html)

def main():
    xml_data = fetch_flex_report()
    df = parse_xml_to_df(xml_data)
    generate_html_report(df)
    print("Successfully built public/index.html")

if __name__ == "__main__":
    main()