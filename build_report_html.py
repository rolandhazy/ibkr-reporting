import os
import time
import json
import xml.etree.ElementTree as ET
import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Secrets & Endpoints
IBKR_FLEX_TOKEN = os.getenv("IBKR_FLEX_TOKEN")
IBKR_QUERY_ID = os.getenv("IBKR_QUERY_ID")

FLEX_SEND_URL = f"https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest?t={IBKR_FLEX_TOKEN}&q={IBKR_QUERY_ID}&v=3"

THEME_MAP = {
    'Big Tech': ['AAPL', 'AMZN', 'GOOG', 'GOOGL', 'META', 'MSFT'],
    'Software & IT Services': ['ADBE', 'COUR', 'CRM', 'CRWD', 'CSCO', 'CTSH', 'DOCU', 'DT', 'DUOL', 'GDDY', 'IBM', 'IGV', 'INFY', 'LOGN', 'NBIS', 'ORCL', 'PLTR', 'RDDT', 'SAP', 'SNOW', 'SOUN', 'TDC', 'TEAM', 'WDAY', 'ZS', 'HACK', 'CIBR'],
    'Semiconductors & Hardware': ['AMD', 'ARM', 'AVGO', 'DRAM', 'INTC', 'MU', 'NVDA', 'QCOM', 'SNDK', 'SONY', 'SOXX', 'SFT'],
    'Airlines, Aviation & Logistics': ['AAL', 'AF', 'CON', 'CVNA', 'FDX', 'LCID', 'LHA', 'PNL', 'QAN', 'RYAAY', 'WI2', 'WIZZ', 'UPS', 'XPO', 'STLA', 'TSLA', '7203'],
    'Aerospace & Defense': ['AIR', 'BA', 'RTX', 'LDOS', 'DFEU', 'ITA', '7011', 'SHLD', 'UMAC', 'DRNZ'],
    'Space & Satellites': ['RKLB', 'SPCX', 'SPCE', 'ETL', 'RDW', 'AADX'],
    'Big Pharma': ['AZN', 'BMY', 'NVO', 'PFE', 'ROG', 'SNY'],
    'Biotech': ['ATAI', 'GHRS', 'MLTX', 'MRNA', 'XBI'],
    'Healthcare & Medical Devices': ['CALM', 'COLO', 'DHR', 'HIMS', 'MDT', 'TMO', 'UNH', 'XLV'],
    'Energy & Utilities': ['CVX', 'EQNR', 'DNQ', 'USO', 'BNO', 'XLE', 'XOM', 'MPC', 'NEE', 'D2G', 'ENGI', 'PCG', 'XE', 'XLU', 'SXEP', 'SHELL', 'VLTSA', 'VG'],
    'Financials & Fintech': ['MA', 'IBKR', 'HOOD', 'BBVA', 'OTP', 'UCG', 'SAN', 'SPGI', 'EXX1', 'XLF', 'CRCL', 'RKT', 'KLAR', 'PYPL', 'V', 'BRK B'],
    'Consumer Goods & Retail': ['ADS', 'BIRK', 'LULU', 'NKE', 'AEO', 'GAP', 'DLTR', 'MAT', 'WMT', 'XLY', 'XLP', 'TSCO', 'STUB', 'GME', 'SONO', 'HEN', 'HEN3', 'NCLH'],
    'Restaurants, Food & Beverages': ['MCD', 'CMG', 'QSR', 'WEN', 'SBUX', 'SG', 'HEIA', 'BYND', 'BYND1', 'NESN', 'JACK', 'PLAY', 'CASY', 'YUM', 'DBA', 'GIS'],
    'Media & Telecom': ['NFLX', 'SPOT', 'WBD', 'PSKY', 'T', 'VZ', 'ORA', 'VSNT', 'UBI', 'MEME', 'AMS'],
    'Materials & Mining': ['BAS', 'LXS', 'ALB', 'LIN', 'SIKA', 'SOLB', 'MP', 'REB', 'USAR', 'LYI', 'ILZ', 'RNF', 'SJ60', 'N14', 'NEM', 'NCH2'],
    'Industrials & Real Estate': ['ACS', 'KGX', 'DHI', 'LEN', 'ROP', 'WY', 'ALO', 'LIGHT'],
    'Portfolio Hedges & Volatility': ['SPY', 'QQQ', 'QQQM', 'XSP', 'VIX','IWM'],
    'Europe Broad Market ETFs': ['DJ600', 'MEUD', 'CS1', 'LYXIB', 'VGK', 'EXS1'],
    'Asia Broad Market ETFs': ['XDJP', 'SXRZ', 'IKRA'],
    'Emerging Markets ETFs': ['EEM', 'XCS4', 'IBZL'],
    'Box Spread Financing': ['ESTX50', 'SPX'],
    'Covered Call Broad Market': ['RSP', 'FEZ', 'EWJ'],
    'Precious Metals & Crypto': ['GLD', 'SLV', 'IBIT'],
    'FX': ['USD.HUF', 'AUD', 'CHF', 'GBP', 'HUF', 'NOK', 'JPY', 'USD'],
    'Fixed Income': ['TLT']
}

SYMBOL_TO_THEME = {sym: t for t, symbols in THEME_MAP.items() for sym in symbols}

def fetch_flex_report():
    if not IBKR_FLEX_TOKEN or not IBKR_QUERY_ID:
        raise ValueError("Missing IBKR_FLEX_TOKEN or IBKR_QUERY_ID environment variables.")

    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(FLEX_SEND_URL, headers=headers)
    res.raise_for_status()
    root = ET.fromstring(res.text)
    
    if root.findtext("Status") != "Success":
        code = root.findtext("ErrorCode") or ""
        msg = root.findtext("ErrorMessage") or res.text
        raise RuntimeError(f"Flex Request Failed ({code}): {msg}")
    
    ref_code = root.findtext("ReferenceCode")
    base_get_url = root.findtext("Url") or "https://gdcdyn.interactivebrokers.com/AccountManagement/FlexWebService/GetStatement"
    get_url = f"{base_get_url}?q={ref_code}&t={IBKR_FLEX_TOKEN}&v=3"
    print(f"Flex statement request accepted (Reference: {ref_code}). Polling for completion...")
    
    for attempt in range(1, 15):
        time.sleep(10)
        stmt_res = requests.get(get_url, headers=headers)
        if "<FlexQueryResponse" in stmt_res.text or "<FlexStatements" in stmt_res.text:
            print("Flex statement successfully retrieved.")
            return stmt_res.text
            
        if "<ErrorCode>" in stmt_res.text:
            err_root = ET.fromstring(stmt_res.text)
            err_code = err_root.findtext("ErrorCode")
            err_msg = err_root.findtext("ErrorMessage")
            if err_code != "1019":  # 1019 = in progress
                raise RuntimeError(f"IBKR Error ({err_code}): {err_msg}")
            print(f"Statement still generating... (attempt {attempt}/14)")
            
    raise TimeoutError("IBKR Flex Statement generation timed out.")

def parse_xml_to_df(xml_data):
    root = ET.fromstring(xml_data)
    records = []
    
    # FIFO Performance Summary Underlying (used in IBKR PnL summary reports)
    for item in root.iter("FIFOPerformanceSummaryUnderlying"):
        symbol = (item.get("symbol") or "").strip()
        underlying = (item.get("underlyingSymbol") or "").strip() or symbol
        desc = (item.get("description") or "").strip()

        # Filter out IBKR's portfolio summary row ('Total (All Assets)') so it does not double count totals or show up as a ticker
        if desc.lower().startswith("total") or (not symbol and not underlying):
            continue

        records.append({
            "Symbol": symbol,
            "UnderlyingSymbol": underlying,
            "Description": desc,
            "TotalFifoPnl": float(item.get("totalFifoPnl", 0.0) or 0.0),
            "TotalRealizedPnl": float(item.get("totalRealizedPnl", 0.0) or 0.0),
            "TotalUnrealizedPnl": float(item.get("totalUnrealizedPnl", 0.0) or 0.0)
        })
        
    for trade in root.iter("Trade"):
        symbol = (trade.get("symbol") or "").strip()
        underlying = (trade.get("underlyingSymbol") or "").strip() or symbol
        desc = (trade.get("description") or "").strip()
        if desc.lower().startswith("total") or (not symbol and not underlying):
            continue
        records.append({
            "Symbol": symbol,
            "UnderlyingSymbol": underlying,
            "Description": desc,
            "TotalFifoPnl": float(trade.get("fifoPnlRealized", 0.0) or 0.0),
            "TotalRealizedPnl": float(trade.get("fifoPnlRealized", 0.0) or 0.0),
            "TotalUnrealizedPnl": 0.0
        })
        
    for pos in root.iter("OpenPosition"):
        symbol = (pos.get("symbol") or "").strip()
        underlying = (pos.get("underlyingSymbol") or "").strip() or symbol
        desc = (pos.get("description") or "").strip()
        if desc.lower().startswith("total") or (not symbol and not underlying):
            continue
        records.append({
            "Symbol": symbol,
            "UnderlyingSymbol": underlying,
            "Description": desc,
            "TotalFifoPnl": float(pos.get("fifoPnlUnrealized", 0.0) or 0.0),
            "TotalRealizedPnl": 0.0,
            "TotalUnrealizedPnl": float(pos.get("fifoPnlUnrealized", 0.0) or 0.0)
        })
        
    df = pd.DataFrame(records)
    if df.empty:
        print("Warning: No records found in Flex report XML.")
        df = pd.DataFrame(columns=["Symbol", "UnderlyingSymbol", "Description", "TotalFifoPnl", "TotalRealizedPnl", "TotalUnrealizedPnl", "Theme"])
    else:
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
    
    # Calculate ticker-level contributions
    ticker_summary = df.groupby(['Theme', 'UnderlyingSymbol']).agg(
        Description=('Description', 'first'),
        TotalFifoPnl=('TotalFifoPnl', 'sum'),
        RealizedPnl=('TotalRealizedPnl', 'sum'),
        UnrealizedPnl=('TotalUnrealizedPnl', 'sum'),
        Count=('Symbol', 'count')
    ).reset_index()

    ticker_summary['Description'] = ticker_summary['Description'].fillna(ticker_summary['UnderlyingSymbol'])
    ticker_summary['TotalFifoPnl'] = ticker_summary['TotalFifoPnl'].round(2)
    ticker_summary['RealizedPnl'] = ticker_summary['RealizedPnl'].round(2)
    ticker_summary['UnrealizedPnl'] = ticker_summary['UnrealizedPnl'].round(2)

    theme_summary['TotalFifoPnl'] = theme_summary['TotalFifoPnl'].round(2)
    theme_summary['RealizedPnl'] = theme_summary['RealizedPnl'].round(2)
    theme_summary['UnrealizedPnl'] = theme_summary['UnrealizedPnl'].round(2)

    total_pnl = float(df['TotalFifoPnl'].sum())
    total_realized = float(df['TotalRealizedPnl'].sum())
    total_unrealized = float(df['TotalUnrealizedPnl'].sum())
    total_assets = int(df['UnderlyingSymbol'].nunique())
    total_themes = int(df['Theme'].nunique())

    top_theme = theme_summary.iloc[0]['Theme'] if not theme_summary.empty else ""

    theme_json = json.dumps(theme_summary.to_dict(orient='records'))
    ticker_json = json.dumps(ticker_summary.to_dict(orient='records'))

    os.makedirs("public", exist_ok=True)
    
    pnl_cls = "positive" if total_pnl >= 0 else "negative"
    realized_cls = "positive" if total_realized >= 0 else "negative"
    unrealized_cls = "positive" if total_unrealized >= 0 else "negative"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IBKR Portfolio Performance & Theme Attribution</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --bg-page: #090d16;
            --bg-card: #111827;
            --bg-card-header: #151d30;
            --border-color: #1e293b;
            --border-subtle: #182235;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --color-positive: #10b981;
            --color-positive-bg: rgba(16, 185, 129, 0.12);
            --color-negative: #f43f5e;
            --color-negative-bg: rgba(244, 63, 94, 0.12);
            --color-accent: #38bdf8;
            --color-accent-bg: rgba(56, 189, 248, 0.12);
            --font-main: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: var(--font-main);
            background: var(--bg-page);
            color: var(--text-primary);
            padding: 14px;
            line-height: 1.4;
            -webkit-font-smoothing: antialiased;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 8px 6px;
            }}
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        /* Concise Header & KPI Strip */
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .brand h1 {{
            font-size: 17px;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text-primary);
        }}

        .kpi-strip {{
            display: grid;
            grid-template-columns: repeat(4, auto);
            gap: 12px 18px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 7px 16px;
            align-items: center;
        }}

        @media (max-width: 840px) {{
            .header {{
                flex-direction: column;
                align-items: stretch;
                gap: 8px;
            }}
            .brand {{
                justify-content: space-between;
            }}
            .kpi-strip {{
                grid-template-columns: repeat(2, 1fr);
                gap: 8px 12px;
                padding: 8px 12px;
            }}
        }}

        .kpi-item {{
            display: flex;
            flex-direction: column;
            gap: 1px;
        }}

        .kpi-label {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .kpi-val {{
            font-family: var(--font-mono);
            font-size: 14px;
            font-weight: 700;
            white-space: nowrap;
        }}

        /* Main 2-Column Split Dashboard */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: 44% 56%;
            gap: 14px;
            align-items: start;
        }}

        @media (max-width: 960px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
                gap: 12px;
            }}
        }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
        }}

        .card-header {{
            background: var(--bg-card-header);
            padding: 9px 14px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .card-header h2 {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 2px 7px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            font-family: var(--font-mono);
            line-height: 1.2;
        }}

        .badge.positive {{
            background: var(--color-positive-bg);
            color: var(--color-positive);
            border: 1px solid rgba(16, 185, 129, 0.25);
        }}

        .badge.negative {{
            background: var(--color-negative-bg);
            color: var(--color-negative);
            border: 1px solid rgba(244, 63, 94, 0.25);
        }}

        .badge.neutral {{
            background: var(--color-accent-bg);
            color: var(--color-accent);
            border: 1px solid rgba(56, 189, 248, 0.25);
        }}

        /* Search input */
        .search-box {{
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-subtle);
            background: rgba(17, 24, 39, 0.6);
        }}

        .search-box input {{
            width: 100%;
            background: #0b1120;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 6px 10px;
            color: var(--text-primary);
            font-size: 12px;
            font-family: var(--font-main);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        .search-box input:focus {{
            border-color: var(--color-accent);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
        }}

        /* Table Design */
        .table-container {{
            max-height: 640px;
            overflow-y: auto;
            position: relative;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}

        thead th {{
            position: sticky;
            top: 0;
            background: #0f172a;
            color: var(--text-secondary);
            font-weight: 600;
            text-align: left;
            padding: 8px 10px;
            border-bottom: 1px solid var(--border-color);
            z-index: 2;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}

        tbody td {{
            padding: 9px 10px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            vertical-align: middle;
        }}

        .theme-row {{
            cursor: pointer;
            transition: background 0.12s ease;
            border-left: 3px solid transparent;
        }}

        .theme-row:hover {{
            background: rgba(56, 189, 248, 0.05);
        }}

        .theme-row.active {{
            background: rgba(56, 189, 248, 0.12) !important;
            border-left: 3px solid var(--color-accent);
        }}

        .theme-row.active td {{
            color: var(--text-primary);
            font-weight: 500;
        }}

        .theme-name-cell {{
            color: var(--text-primary);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .theme-indicator {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .num {{
            text-align: right;
            font-family: var(--font-mono);
            font-size: 12px;
            white-space: nowrap;
        }}

        .positive {{
            color: var(--color-positive) !important;
        }}

        .negative {{
            color: var(--color-negative) !important;
        }}

        tfoot .total-row {{
            position: sticky;
            bottom: 0;
            background: #0d1527;
            border-top: 2px solid #334155;
            z-index: 2;
        }}

        tfoot .total-row td {{
            padding: 10px 10px;
            color: var(--text-primary);
            font-weight: 700;
            background: #0d1527;
        }}

        /* Mobile Column Hiding to Prevent Cramping */
        @media (max-width: 640px) {{
            .col-hide-mobile {{
                display: none !important;
            }}
            .table-container {{
                max-height: 480px;
            }}
            tbody td, thead th, tfoot .total-row td {{
                padding: 7px 7px !important;
                font-size: 11px !important;
            }}
            .num {{
                font-size: 11px !important;
            }}
            .theme-name-cell span {{
                max-width: 150px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }}
        }}

        /* Right Sticky Panel */
        .sticky-panel {{
            position: sticky;
            top: 14px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}

        @media (max-width: 960px) {{
            .sticky-panel {{
                position: static;
            }}
        }}

        /* Controls / Metric Toggle */
        .view-controls {{
            display: flex;
            gap: 4px;
            background: #0b1120;
            padding: 2px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }}

        .btn-toggle {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 600;
            padding: 4px 9px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s;
        }}

        .btn-toggle:hover {{
            color: var(--text-primary);
        }}

        .btn-toggle.active {{
            background: var(--color-accent);
            color: #0b1120;
        }}

        .btn-back-mobile {{
            display: none;
            background: #1e293b;
            color: var(--color-accent);
            border: 1px solid var(--border-color);
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
        }}

        @media (max-width: 960px) {{
            .btn-back-mobile {{
                display: inline-block;
            }}
        }}

        /* Chart container */
        .chart-wrapper {{
            padding: 8px 6px;
            min-height: 280px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        #ticker-chart {{
            width: 100%;
        }}

        /* Detail Ticker Sub-Table */
        .subtable-container {{
            max-height: 240px;
            overflow-y: auto;
            border-top: 1px solid var(--border-color);
        }}

        .ticker-pill {{
            background: #1e293b;
            color: #38bdf8;
            font-family: var(--font-mono);
            font-weight: 600;
            padding: 1px 5px;
            border-radius: 4px;
            font-size: 11px;
            border: 1px solid #334155;
        }}

        .subtable-desc {{
            font-size: 11px;
            color: var(--text-muted);
            max-width: 190px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        @media (max-width: 480px) {{
            .subtable-desc {{
                max-width: 110px;
            }}
        }}

        /* Custom Scrollbar */
        ::-webkit-scrollbar {{
            width: 5px;
            height: 5px;
        }}
        ::-webkit-scrollbar-track {{
            background: var(--bg-card);
        }}
        ::-webkit-scrollbar-thumb {{
            background: #27354a;
            border-radius: 3px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #3b4d66;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Concise Header & KPI Strip -->
        <header class="header">
            <div class="brand">
                <h1>IBKR Intelligence</h1>
                <span class="badge neutral">EUR</span>
            </div>
            <div class="kpi-strip">
                <div class="kpi-item">
                    <span class="kpi-label">Net FIFO PnL</span>
                    <span class="kpi-val {pnl_cls}">€{total_pnl:,.2f}</span>
                </div>
                <div class="kpi-item">
                    <span class="kpi-label">Realized</span>
                    <span class="kpi-val {realized_cls}">€{total_realized:,.2f}</span>
                </div>
                <div class="kpi-item">
                    <span class="kpi-label">Unrealized</span>
                    <span class="kpi-val {unrealized_cls}">€{total_unrealized:,.2f}</span>
                </div>
                <div class="kpi-item">
                    <span class="kpi-label">Holdings</span>
                    <span class="kpi-val" style="color: var(--color-accent);">{total_assets} Assets</span>
                </div>
            </div>
        </header>

        <!-- 2-Column Split Dashboard -->
        <main class="dashboard-grid">
            <!-- Left Side: Themes List -->
            <div class="card" id="themes-card">
                <div class="card-header">
                    <h2>
                        <span>Themes</span>
                        <span class="badge neutral" id="themes-count-badge">{len(theme_summary)}</span>
                    </h2>
                    <span style="font-size: 11px; color: var(--text-muted);">Tap to inspect</span>
                </div>
                <div class="search-box">
                    <input id="theme-search" type="text" placeholder="Search themes..." oninput="filterThemes(this.value)">
                </div>
                <div class="table-container">
                    <table id="themes-table">
                        <thead>
                            <tr>
                                <th>Theme</th>
                                <th style="text-align:center;">Assets</th>
                                <th class="num col-hide-mobile">Realized</th>
                                <th class="num col-hide-mobile">Unrealized</th>
                                <th class="num">Net PnL</th>
                            </tr>
                        </thead>
                        <tbody id="themes-tbody">
"""
    for idx, row in theme_summary.iterrows():
        pnl = row['TotalFifoPnl']
        cls = "positive" if pnl >= 0 else "negative"
        indicator_color = "#10b981" if pnl >= 0 else "#f43f5e"
        html += f"""                            <tr class="theme-row" data-theme="{row['Theme']}" onclick="selectTheme('{row['Theme']}', true)">
                                <td>
                                    <div class="theme-name-cell">
                                        <span class="theme-indicator" style="background: {indicator_color};"></span>
                                        <span>{row['Theme']}</span>
                                    </div>
                                </td>
                                <td style="text-align:center;"><span class="badge neutral">{row['AssetCount']}</span></td>
                                <td class="num col-hide-mobile">€{row['RealizedPnl']:,.2f}</td>
                                <td class="num col-hide-mobile">€{row['UnrealizedPnl']:,.2f}</td>
                                <td class="num {cls}" style="font-weight: 600;">€{pnl:,.2f}</td>
                            </tr>
"""

    html += f"""                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td>
                                    <div class="theme-name-cell" style="font-weight: 700; color: #fff;">
                                        <span class="theme-indicator" style="background: var(--color-accent);"></span>
                                        <span>Total Portfolio</span>
                                    </div>
                                </td>
                                <td style="text-align:center;"><span class="badge neutral" style="font-weight: 700;">{total_assets}</span></td>
                                <td class="num col-hide-mobile" style="font-weight: 700;">€{total_realized:,.2f}</td>
                                <td class="num col-hide-mobile" style="font-weight: 700;">€{total_unrealized:,.2f}</td>
                                <td class="num {pnl_cls}" style="font-weight: 700; font-size: 13px;">€{total_pnl:,.2f}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            <!-- Right Side: Interactive Ticker Contribution Chart & Details -->
            <div class="sticky-panel" id="details-card">
                <div class="card">
                    <div class="card-header">
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <button class="btn-back-mobile" onclick="scrollToThemes()">↑ Themes</button>
                            <h2 id="active-theme-title">{top_theme}</h2>
                            <span id="theme-pnl-pill" class="badge"></span>
                            <span id="theme-asset-pill" class="badge neutral"></span>
                        </div>
                        <div class="view-controls">
                            <button class="btn-toggle active" id="btn-metric-TotalFifoPnl" onclick="changeMetric('TotalFifoPnl')">Net</button>
                            <button class="btn-toggle" id="btn-metric-RealizedPnl" onclick="changeMetric('RealizedPnl')">Realized</button>
                            <button class="btn-toggle" id="btn-metric-UnrealizedPnl" onclick="changeMetric('UnrealizedPnl')">Unrealized</button>
                        </div>
                    </div>
                    
                    <!-- Plotly Chart -->
                    <div class="chart-wrapper">
                        <div id="ticker-chart"></div>
                    </div>

                    <!-- Individual Ticker Table -->
                    <div class="subtable-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Description</th>
                                    <th class="num col-hide-mobile">Realized</th>
                                    <th class="num col-hide-mobile">Unrealized</th>
                                    <th class="num">Net PnL</th>
                                </tr>
                            </thead>
                            <tbody id="ticker-tbody">
                                <!-- Populated dynamically by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        // Data passed from Python
        const THEME_DATA = {theme_json};
        const TICKER_DATA = {ticker_json};

        let currentTheme = "{top_theme}";
        let currentMetric = "TotalFifoPnl";

        const METRIC_LABELS = {{
            "TotalFifoPnl": "Net FIFO PnL (€)",
            "RealizedPnl": "Realized PnL (€)",
            "UnrealizedPnl": "Unrealized PnL (€)"
        }};

        function formatCurrency(val) {{
            const sign = val >= 0 ? "+€" : "-€";
            return sign + Math.abs(val).toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
        }}

        function selectTheme(themeName, isUserClick = false) {{
            currentTheme = themeName;

            // Update row active state in table
            const rows = document.querySelectorAll('.theme-row');
            rows.forEach(r => {{
                if (r.getAttribute('data-theme') === themeName) {{
                    r.classList.add('active');
                }} else {{
                    r.classList.remove('active');
                }}
            }});

            renderActiveTheme();

            // Smooth scroll to chart on mobile phones when tapped
            if (isUserClick && window.innerWidth <= 960) {{
                document.getElementById('details-card').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
        }}

        function scrollToThemes() {{
            document.getElementById('themes-card').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}

        function changeMetric(metricKey) {{
            currentMetric = metricKey;
            document.querySelectorAll('.btn-toggle').forEach(b => b.classList.remove('active'));
            const activeBtn = document.getElementById('btn-metric-' + metricKey);
            if (activeBtn) activeBtn.classList.add('active');

            renderActiveTheme();
        }}

        function renderActiveTheme() {{
            const themeObj = THEME_DATA.find(t => t.Theme === currentTheme) || {{
                Theme: currentTheme,
                TotalFifoPnl: 0,
                RealizedPnl: 0,
                UnrealizedPnl: 0,
                AssetCount: 0
            }};

            // Update Header & Badges
            document.getElementById('active-theme-title').innerText = themeObj.Theme;
            const pnlPill = document.getElementById('theme-pnl-pill');
            const pnlVal = themeObj.TotalFifoPnl;
            pnlPill.innerText = "Net " + formatCurrency(pnlVal);
            pnlPill.className = "badge " + (pnlVal >= 0 ? "positive" : "negative");

            const assetPill = document.getElementById('theme-asset-pill');
            assetPill.innerText = themeObj.AssetCount + " Tickers";

            // Filter tickers for active theme
            const tickers = TICKER_DATA.filter(t => t.Theme === currentTheme);

            // Sort ascending for horizontal bar chart (so largest is at top)
            const sortedTickers = [...tickers].sort((a, b) => a[currentMetric] - b[currentMetric]);

            // Render Plotly Chart
            renderPlotlyChart(sortedTickers);

            // Render Subtable (sorted descending by Net PnL)
            renderSubTable([...tickers].sort((a, b) => b.TotalFifoPnl - a.TotalFifoPnl));
        }}

        function renderPlotlyChart(tickers) {{
            if (!tickers || tickers.length === 0) {{
                Plotly.purge('ticker-chart');
                document.getElementById('ticker-chart').innerHTML = '<div style="color: #64748b; padding: 30px; text-align: center; font-size: 12px;">No individual ticker data found.</div>';
                return;
            }}

            const isMobile = window.innerWidth <= 640;

            const yValues = tickers.map(t => t.UnderlyingSymbol);
            const xValues = tickers.map(t => t[currentMetric]);
            const colors = xValues.map(v => v >= 0 ? '#10b981' : '#f43f5e');
            const textLabels = xValues.map(v => formatCurrency(v));

            const customData = tickers.map(t => [
                t.Description,
                t.TotalFifoPnl,
                t.RealizedPnl,
                t.UnrealizedPnl
            ]);

            const trace = {{
                type: 'bar',
                orientation: 'h',
                y: yValues,
                x: xValues,
                text: textLabels,
                textposition: 'outside',
                cliponaxis: false,
                marker: {{
                    color: colors,
                    line: {{ width: 0 }}
                }},
                customdata: customData,
                hovertemplate: 
                    '<b>%{{y}}</b> — %{{customdata[0]}}<br>' +
                    'Selected: <b>%{{x:€,.2f}}</b><br>' +
                    '<span style="color:#94a3b8">Net:</span> €%{{customdata[1]:,.2f}}<br>' +
                    '<span style="color:#94a3b8">Realized:</span> €%{{customdata[2]:,.2f}}<br>' +
                    '<span style="color:#94a3b8">Unrealized:</span> €%{{customdata[3]:,.2f}}<extra></extra>'
            }};

            // Calculate padded x-axis range so outside bar labels never overlap the y-axis or border
            const minVal = Math.min(0, ...xValues);
            const maxVal = Math.max(0, ...xValues);
            const span = (maxVal - minVal) || 100;
            const padLeft = minVal < 0 ? Math.abs(minVal) * 0.28 + span * 0.05 : span * 0.05;
            const padRight = maxVal > 0 ? maxVal * 0.28 + span * 0.05 : span * 0.15;
            const xRange = [minVal - padLeft, maxVal + padRight];

            const barSpacing = isMobile ? 26 : 32;
            const dynamicHeight = Math.max(isMobile ? 260 : 320, Math.min(isMobile ? 550 : 700, tickers.length * barSpacing + 50));

            const layout = {{
                height: dynamicHeight,
                margin: {{ 
                    l: isMobile ? 65 : 85, 
                    r: isMobile ? 65 : 85, 
                    t: 10, 
                    b: 30 
                }},
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: {{
                    family: 'Inter, sans-serif',
                    color: '#94a3b8',
                    size: isMobile ? 11 : 12
                }},
                xaxis: {{
                    range: xRange,
                    title: {{
                        text: METRIC_LABELS[currentMetric],
                        font: {{ size: 11, color: '#64748b' }}
                    }},
                    gridcolor: '#1e293b',
                    zerolinecolor: '#475569',
                    zerolinewidth: 1.5,
                    tickprefix: '€',
                    automargin: true,
                    tickfont: {{ size: isMobile ? 10 : 11 }}
                }},
                yaxis: {{
                    automargin: true,
                    ticksuffix: '  ',
                    tickfont: {{
                        family: 'JetBrains Mono, monospace',
                        size: isMobile ? 11 : 12,
                        color: '#f8fafc',
                        weight: 600
                    }}
                }}
            }};

            const config = {{
                responsive: true,
                displayModeBar: false
            }};

            Plotly.react('ticker-chart', [trace], layout, config);
        }}

        function renderSubTable(tickers) {{
            const tbody = document.getElementById('ticker-tbody');
            if (!tickers || tickers.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#64748b; padding:15px;">No assets</td></tr>';
                return;
            }}

            let rowsHtml = '';
            tickers.forEach(t => {{
                const pnl = t.TotalFifoPnl;
                const pnlCls = pnl >= 0 ? "positive" : "negative";
                rowsHtml += `
                    <tr>
                        <td><span class="ticker-pill">${{t.UnderlyingSymbol}}</span></td>
                        <td><div class="subtable-desc" title="${{t.Description}}">${{t.Description}}</div></td>
                        <td class="num col-hide-mobile">€${{t.RealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num col-hide-mobile">€${{t.UnrealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num ${{pnlCls}}" style="font-weight: 600;">€${{pnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                    </tr>
                `;
            }});
            tbody.innerHTML = rowsHtml;
        }}

        function filterThemes(query) {{
            const q = query.toLowerCase().trim();
            const rows = document.querySelectorAll('.theme-row');
            let visibleCount = 0;
            rows.forEach(r => {{
                const themeName = r.getAttribute('data-theme').toLowerCase();
                if (themeName.includes(q)) {{
                    r.style.display = '';
                    visibleCount++;
                }} else {{
                    r.style.display = 'none';
                }}
            }});
            document.getElementById('themes-count-badge').innerText = visibleCount;
        }}

        // Handle window resize for Plotly responsiveness
        window.addEventListener('resize', () => {{
            const chartDiv = document.getElementById('ticker-chart');
            if (chartDiv && chartDiv.data) {{
                Plotly.Plots.resize('ticker-chart');
            }}
        }});

        // Initialize with default theme
        window.addEventListener('DOMContentLoaded', () => {{
            selectTheme(currentTheme);
        }});
    </script>
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