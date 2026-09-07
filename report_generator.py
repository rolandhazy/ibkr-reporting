"""HTML report generation and UI serialization."""

import json
import os
import pandas as pd


def generate_html_report(
    df: pd.DataFrame,
    output_path: str = "public/index.html",
    period_str: str = ""
) -> None:
    """Aggregate portfolio data and output the standalone interactive dashboard HTML."""
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
    ticker_summary['IsActive'] = (ticker_summary['UnrealizedPnl'].abs() > 0.001).astype(bool)

    # Initial full-dataset theme aggregation
    theme_summary = ticker_summary.groupby('Theme').agg(
        TotalFifoPnl=('TotalFifoPnl', 'sum'),
        RealizedPnl=('RealizedPnl', 'sum'),
        UnrealizedPnl=('UnrealizedPnl', 'sum'),
        AssetCount=('UnderlyingSymbol', 'nunique'),
        WinningAssets=('TotalFifoPnl', lambda s: int((s > 0).sum())),
        LosingAssets=('TotalFifoPnl', lambda s: int((s < 0).sum()))
    ).reset_index().sort_values('TotalFifoPnl', ascending=False)

    theme_summary['TotalFifoPnl'] = theme_summary['TotalFifoPnl'].round(2)
    theme_summary['RealizedPnl'] = theme_summary['RealizedPnl'].round(2)
    theme_summary['UnrealizedPnl'] = theme_summary['UnrealizedPnl'].round(2)

    total_pnl = round(float(ticker_summary['TotalFifoPnl'].sum()), 2) if not ticker_summary.empty else 0.0
    total_realized = round(float(ticker_summary['RealizedPnl'].sum()), 2) if not ticker_summary.empty else 0.0
    total_unrealized = round(float(ticker_summary['UnrealizedPnl'].sum()), 2) if not ticker_summary.empty else 0.0
    total_assets = int(ticker_summary['UnderlyingSymbol'].nunique()) if not ticker_summary.empty else 0
    active_assets_count = int(ticker_summary['IsActive'].sum()) if not ticker_summary.empty else 0

    top_theme = str(theme_summary.iloc[0]['Theme']) if not theme_summary.empty else ""

    theme_json = json.dumps(theme_summary.to_dict(orient='records'))
    ticker_json = json.dumps(ticker_summary.to_dict(orient='records'))

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    period_badge_html = f'<div class="reporting-period">{period_str}</div>' if period_str else ""

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
            --color-realized-pos: #16a34a;
            --color-realized-neg: #dc2626;
            --color-unrealized-pos: #4ade80;
            --color-unrealized-neg: #f87171;
            --color-accent: #38bdf8;
            --color-accent-bg: rgba(56, 189, 248, 0.12);
            --input-bg: #0b1120;
            --ratio-track-bg: rgba(255, 255, 255, 0.08);
            --ratio-label-color: #64748b;
            --total-row-bg: #0d1527;
            --ticker-pill-bg: #1e293b;
            --ticker-pill-border: #334155;
            --ticker-pill-text: #38bdf8;
            --table-hover-bg: rgba(56, 189, 248, 0.06);
            --table-active-bg: rgba(56, 189, 248, 0.12);
            --font-main: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }}

        [data-theme="light"] {{
            --bg-page: #f1f5f9;
            --bg-card: #ffffff;
            --bg-card-header: #f8fafc;
            --border-color: #e2e8f0;
            --border-subtle: #edf2f7;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #64748b;
            --color-positive: #059669;
            --color-positive-bg: rgba(5, 150, 105, 0.12);
            --color-negative: #e11d48;
            --color-negative-bg: rgba(225, 29, 72, 0.12);
            --color-realized-pos: #16a34a;
            --color-realized-neg: #dc2626;
            --color-unrealized-pos: #16a34a;
            --color-unrealized-neg: #dc2626;
            --color-accent: #0284c7;
            --color-accent-bg: rgba(2, 132, 199, 0.12);
            --input-bg: #ffffff;
            --ratio-track-bg: rgba(0, 0, 0, 0.08);
            --ratio-label-color: #64748b;
            --total-row-bg: #f8fafc;
            --ticker-pill-bg: #f1f5f9;
            --ticker-pill-border: #cbd5e1;
            --ticker-pill-text: #0284c7;
            --table-hover-bg: rgba(2, 132, 199, 0.05);
            --table-active-bg: rgba(2, 132, 199, 0.10);
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
            transition: background 0.2s ease, color 0.2s ease;
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

        /* Header & Action Controls */
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .brand-container {{
            display: flex;
            flex-direction: column;
            gap: 3px;
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

        .reporting-period {{
            font-size: 11px;
            font-family: var(--font-mono);
            color: var(--text-secondary);
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}

        .header-right {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .header-controls {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        /* Global Filter Toggle Switch */
        .filter-toggle {{
            display: inline-flex;
            align-items: center;
            cursor: pointer;
            user-select: none;
        }}

        .filter-toggle input {{
            display: none;
        }}

        .filter-toggle-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 10px;
            border-radius: 20px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        .filter-toggle-pill:hover {{
            border-color: var(--color-accent);
            color: var(--text-primary);
        }}

        .filter-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--text-muted);
            transition: background 0.2s ease;
        }}

        .filter-toggle input:checked + .filter-toggle-pill {{
            background: var(--color-accent-bg);
            border-color: var(--color-accent);
            color: var(--color-accent);
            font-weight: 600;
        }}

        .filter-toggle input:checked + .filter-toggle-pill .filter-dot {{
            background: var(--color-accent);
            box-shadow: 0 0 6px var(--color-accent);
        }}

        .active-count-tag {{
            font-family: var(--font-mono);
            font-size: 10px;
            padding: 1px 5px;
            border-radius: 10px;
            background: rgba(125, 125, 125, 0.15);
        }}

        /* Light / Dark Mode Button */
        .header-btn {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 5px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .header-btn:hover {{
            color: var(--text-primary);
            border-color: var(--color-accent);
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

        @media (max-width: 960px) {{
            .header {{
                flex-direction: column;
                align-items: stretch;
                gap: 10px;
            }}
            .header-right {{
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
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
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

        .performer-badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 6px;
            font-family: var(--font-mono);
            white-space: nowrap;
        }}

        .performer-badge.best {{
            background: rgba(22, 163, 74, 0.15);
            color: var(--color-positive);
            border: 1px solid rgba(22, 163, 74, 0.35);
        }}

        .performer-badge.worst {{
            background: rgba(220, 38, 38, 0.15);
            color: var(--color-negative);
            border: 1px solid rgba(220, 38, 38, 0.35);
        }}

        .performer-badge strong {{
            font-weight: 700;
        }}

        /* Search box */
        .search-box {{
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-subtle);
            background: var(--bg-card);
        }}

        .search-box input {{
            width: 100%;
            background: var(--input-bg);
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
            background: var(--bg-card-header);
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
            padding: 8px 10px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            vertical-align: middle;
        }}

        .theme-row, .total-row {{
            cursor: pointer;
            transition: background 0.12s ease;
            border-left: 3px solid transparent;
        }}

        .theme-row:hover, .total-row:hover {{
            background: var(--table-hover-bg);
        }}

        .theme-row.active, .total-row.active {{
            background: var(--table-active-bg) !important;
            border-left: 3px solid var(--color-accent);
        }}

        .theme-row.active td, .total-row.active td {{
            color: var(--text-primary);
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

        /* Meaningful Win/Loss & Realized/Unrealized Ratio Micro-Bar */
        .pnl-cell-content {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 2px;
            cursor: help;
        }}

        .pnl-amount {{
            font-weight: 600;
            font-family: var(--font-mono);
            font-size: 12px;
            line-height: 1.2;
        }}

        .ratio-container {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}

        .ratio-bar-track {{
            width: 58px;
            height: 4px;
            background: var(--ratio-track-bg);
            border-radius: 2px;
            overflow: hidden;
            display: flex;
            flex-shrink: 0;
        }}

        .ratio-bar-seg {{
            height: 100%;
            transition: width 0.2s ease;
        }}

        .ratio-label {{
            font-family: var(--font-mono);
            font-size: 9.5px;
            color: var(--ratio-label-color);
            letter-spacing: -0.01em;
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
            background: var(--total-row-bg);
            border-top: 2px solid var(--border-color);
            z-index: 2;
        }}

        tfoot .total-row td {{
            padding: 9px 10px;
            color: var(--text-primary);
            font-weight: 700;
            background: var(--total-row-bg);
        }}

        /* Active position dot */
        .active-dot {{
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: var(--color-accent);
            display: inline-block;
            box-shadow: 0 0 4px var(--color-accent);
            flex-shrink: 0;
        }}

        /* Mobile Column Hiding */
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
                max-width: 140px;
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

        .btn-back-mobile {{
            display: none;
            background: var(--ticker-pill-bg);
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

        /* Details card toolbar */
        .controls-toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 14px;
            background: var(--bg-card-header);
            border-bottom: 1px solid var(--border-subtle);
            flex-wrap: wrap;
            gap: 8px;
        }}

        .performer-highlights {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }}

        /* Chart legend & wrapper */
        .chart-legend {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 12px;
            font-size: 11px;
            color: var(--text-secondary);
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}

        .legend-swatch {{
            width: 12px;
            height: 8px;
            border-radius: 2px;
            display: inline-block;
        }}

        .legend-swatch.realized-swatch {{
            background: linear-gradient(90deg, #16a34a 50%, #dc2626 50%);
        }}

        .legend-swatch.unrealized-swatch {{
            background: linear-gradient(90deg, #4ade80 50%, #f87171 50%);
        }}

        .legend-diamond {{
            color: var(--color-positive);
            font-size: 11px;
            line-height: 1;
        }}

        .chart-wrapper {{
            padding: 4px 6px 8px 6px;
            min-height: 220px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        @media (max-width: 640px) {{
            .chart-wrapper {{
                min-height: 150px;
                padding: 2px 4px 4px 4px;
            }}
        }}

        #ticker-chart {{
            width: 100%;
        }}

        /* Detail Ticker Sub-Table: sized to display 8 tickers comfortably */
        .subtable-container {{
            max-height: 380px;
            overflow-y: auto;
            border-top: 1px solid var(--border-color);
        }}

        @media (max-width: 640px) {{
            .subtable-container {{
                max-height: 350px;
            }}
        }}

        .ticker-pill {{
            background: var(--ticker-pill-bg);
            color: var(--ticker-pill-text);
            font-family: var(--font-mono);
            font-weight: 600;
            padding: 1px 5px;
            border-radius: 4px;
            font-size: 11px;
            border: 1px solid var(--ticker-pill-border);
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
            background: var(--border-color);
            border-radius: 3px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header & Action Controls -->
        <header class="header">
            <div class="brand-container">
                <div class="brand">
                    <h1>IBKR Intelligence</h1>
                    <span class="badge neutral">EUR</span>
                </div>
                {period_badge_html}
            </div>

            <div class="header-right">
                <div class="header-controls">
                    <!-- Global Filter Toggle Switch -->
                    <label class="filter-toggle" title="Filter dashboard to show only currently open / active positions">
                        <input type="checkbox" id="active-filter-checkbox" onchange="toggleActiveFilter(this.checked)">
                        <span class="filter-toggle-pill">
                            <span class="filter-dot"></span>
                            <span>Active Only</span>
                            <span class="active-count-tag" id="active-count-tag">{active_assets_count}</span>
                        </span>
                    </label>

                    <!-- Light / Dark Mode Toggle Button -->
                    <button id="theme-toggle-btn" class="header-btn" onclick="toggleThemeMode()" title="Toggle Light / Dark mode" aria-label="Toggle theme">
                        <span id="theme-toggle-icon">☀️</span>
                        <span id="theme-toggle-label" class="col-hide-mobile">Light</span>
                    </button>
                </div>

                <!-- KPI Strip -->
                <div class="kpi-strip">
                    <div class="kpi-item">
                        <span class="kpi-label">Net FIFO PnL</span>
                        <span class="kpi-val" id="kpi-net-pnl">€0.00</span>
                    </div>
                    <div class="kpi-item">
                        <span class="kpi-label">Realized</span>
                        <span class="kpi-val" id="kpi-realized-pnl">€0.00</span>
                    </div>
                    <div class="kpi-item">
                        <span class="kpi-label">Unrealized</span>
                        <span class="kpi-val" id="kpi-unrealized-pnl">€0.00</span>
                    </div>
                    <div class="kpi-item">
                        <span class="kpi-label">Holdings</span>
                        <span class="kpi-val" id="kpi-holdings-count" style="color: var(--color-accent);">{total_assets} Assets</span>
                    </div>
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
                        <span class="badge neutral" id="themes-count-badge">0</span>
                    </h2>
                    <span style="font-size: 11px; color: var(--text-muted);">Click theme or total row</span>
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
                            <!-- Populated dynamically via JavaScript -->
                        </tbody>
                        <tfoot>
                            <tr class="total-row" id="total-portfolio-row" onclick="selectTotalPortfolio(true)" title="Click to view Top 9 Winners & 9 Losers across all themes">
                                <td>
                                    <div class="theme-name-cell" style="font-weight: 700;">
                                        <span class="theme-indicator" style="background: var(--color-accent);"></span>
                                        <span>Total Portfolio</span>
                                    </div>
                                </td>
                                <td style="text-align:center;"><span class="badge neutral" id="total-assets-badge" style="font-weight: 700;">0</span></td>
                                <td class="num col-hide-mobile" id="total-realized-cell" style="font-weight: 700;">€0.00</td>
                                <td class="num col-hide-mobile" id="total-unrealized-cell" style="font-weight: 700;">€0.00</td>
                                <td class="num" id="total-net-cell" style="font-weight: 700;">
                                    <!-- Ratio bar for total -->
                                </td>
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
                    </div>

                    <!-- Performer Badges & Chart Legend (Sort buttons removed) -->
                    <div class="controls-toolbar">
                        <div class="performer-highlights" id="performer-highlights">
                            <!-- Populated dynamically: Best / Worst -->
                        </div>
                        <div class="chart-legend">
                            <span class="legend-item"><span class="legend-swatch realized-swatch"></span> Realized</span>
                            <span class="legend-item"><span class="legend-swatch unrealized-swatch"></span> Unrealized</span>
                            <span class="legend-item"><span class="legend-diamond">◆</span> Net PnL</span>
                        </div>
                    </div>
                    
                    <!-- Plotly Chart -->
                    <div class="chart-wrapper">
                        <div id="ticker-chart"></div>
                    </div>

                    <!-- Individual Ticker Sub-Table -->
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
        const TICKER_DATA = {ticker_json};

        let currentTheme = "{top_theme}";
        let isTotalPortfolioView = false;
        let showActiveOnly = false;
        let searchQuery = "";
        let currentThemeList = [];
        let windowChartTickers = [];

        function escapeHtml(s) {{
            return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
                {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]
            ));
        }}

        function formatCurrency(val) {{
            const sign = val >= 0 ? "+€" : "-€";
            return sign + Math.abs(val).toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
        }}

        /* Meaningful Win/Loss & Realized/Unrealized Ratio Component */
        function renderRatioBar(realized, unrealized, total) {{
            const isPosTotal = total >= 0;
            const posPart = (realized > 0 ? realized : 0) + (unrealized > 0 ? unrealized : 0);
            const negPart = Math.abs((realized < 0 ? realized : 0) + (unrealized < 0 ? unrealized : 0));
            
            let trackHtml = '';
            let label = '';
            let tooltip = '';

            if (posPart > 0 && negPart > 0) {{
                // Mixed: True Win vs Loss ratio
                const totalGross = posPart + negPart;
                const winPct = Math.round((posPart / totalGross) * 100);
                const lossPct = 100 - winPct;
                const ratio = (posPart / negPart).toFixed(1);
                tooltip = `Win/Loss Ratio: ${{ratio}}x • Gains: +€${{posPart.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (${{winPct}}%) | Drag: -€${{negPart.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (${{lossPct}}%)`;
                trackHtml = `
                    <div class="ratio-bar-seg" style="width: ${{winPct}}%; background: var(--color-positive);"></div>
                    <div class="ratio-bar-seg" style="width: ${{lossPct}}%; background: var(--color-negative);"></div>
                `;
                label = `${{ratio}}x W/L`;
            }} else if (posPart > 0) {{
                // Pure Gain: Realized (locked profit) vs Unrealized (open paper gain)
                const realPct = Math.round((Math.max(0, realized) / posPart) * 100);
                const unrealPct = 100 - realPct;
                tooltip = `100% Gains • Realized: +€${{realized.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (${{realPct}}%) | Unrealized: +€${{unrealized.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (${{unrealPct}}%)`;
                trackHtml = `
                    <div class="ratio-bar-seg" style="width: ${{realPct}}%; background: var(--color-realized-pos);"></div>
                    <div class="ratio-bar-seg" style="width: ${{unrealPct}}%; background: var(--color-unrealized-pos);"></div>
                `;
                label = `${{realPct}}% locked`;
            }} else if (negPart > 0) {{
                // Pure Loss: Realized (booked loss) vs Unrealized (open paper drawdown)
                const realPct = Math.round((Math.abs(Math.min(0, realized)) / negPart) * 100);
                const unrealPct = 100 - realPct;
                tooltip = `100% Loss • Realized: -€${{Math.abs(realized).toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (${{realPct}}%) | Unrealized: -€${{Math.abs(unrealized).toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (${{unrealPct}}%)`;
                trackHtml = `
                    <div class="ratio-bar-seg" style="width: ${{realPct}}%; background: var(--color-realized-neg);"></div>
                    <div class="ratio-bar-seg" style="width: ${{unrealPct}}%; background: var(--color-unrealized-neg);"></div>
                `;
                label = `${{realPct}}% booked`;
            }} else {{
                tooltip = "No PnL recorded";
                trackHtml = `<div class="ratio-bar-seg" style="width: 100%; background: var(--border-color);"></div>`;
                label = "—";
            }}

            return `
                <div class="pnl-cell-content" title="${{escapeHtml(tooltip)}}">
                    <span class="pnl-amount ${{isPosTotal ? 'positive' : 'negative'}}">€${{total.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</span>
                    <div class="ratio-container">
                        <div class="ratio-bar-track">
                            ${{trackHtml}}
                        </div>
                        <span class="ratio-label">${{label}}</span>
                    </div>
                </div>
            `;
        }}

        /* Theme & Portfolio Aggregation */
        function getFilteredTickers() {{
            if (showActiveOnly) {{
                return TICKER_DATA.filter(t => t.IsActive);
            }}
            return TICKER_DATA;
        }}

        function aggregateThemes(tickers) {{
            const map = new Map();
            tickers.forEach(t => {{
                if (!map.has(t.Theme)) {{
                    map.set(t.Theme, {{
                        Theme: t.Theme,
                        TotalFifoPnl: 0,
                        RealizedPnl: 0,
                        UnrealizedPnl: 0,
                        AssetCount: 0,
                        WinningAssets: 0,
                        LosingAssets: 0
                    }});
                }}
                const item = map.get(t.Theme);
                item.TotalFifoPnl += t.TotalFifoPnl;
                item.RealizedPnl += t.RealizedPnl;
                item.UnrealizedPnl += t.UnrealizedPnl;
                item.AssetCount += 1;
                if (t.TotalFifoPnl > 0) item.WinningAssets += 1;
                else if (t.TotalFifoPnl < 0) item.LosingAssets += 1;
            }});

            const result = Array.from(map.values()).map(item => ({{
                ...item,
                TotalFifoPnl: Math.round(item.TotalFifoPnl * 100) / 100,
                RealizedPnl: Math.round(item.RealizedPnl * 100) / 100,
                UnrealizedPnl: Math.round(item.UnrealizedPnl * 100) / 100
            }}));

            result.sort((a, b) => b.TotalFifoPnl - a.TotalFifoPnl);
            return result;
        }}

        function updateKpis(tickers) {{
            const totalPnl = Math.round(tickers.reduce((acc, t) => acc + t.TotalFifoPnl, 0) * 100) / 100;
            const totalRealized = Math.round(tickers.reduce((acc, t) => acc + t.RealizedPnl, 0) * 100) / 100;
            const totalUnrealized = Math.round(tickers.reduce((acc, t) => acc + t.UnrealizedPnl, 0) * 100) / 100;
            const totalHoldings = tickers.length;

            const pnlEl = document.getElementById('kpi-net-pnl');
            pnlEl.innerText = formatCurrency(totalPnl);
            pnlEl.className = "kpi-val " + (totalPnl >= 0 ? "positive" : "negative");

            const realEl = document.getElementById('kpi-realized-pnl');
            realEl.innerText = formatCurrency(totalRealized);
            realEl.className = "kpi-val " + (totalRealized >= 0 ? "positive" : "negative");

            const unrealEl = document.getElementById('kpi-unrealized-pnl');
            unrealEl.innerText = formatCurrency(totalUnrealized);
            unrealEl.className = "kpi-val " + (totalUnrealized >= 0 ? "positive" : "negative");

            const countEl = document.getElementById('kpi-holdings-count');
            countEl.innerText = `${{totalHoldings}} Assets`;

            // Update Total Portfolio Row in the themes table footer
            updateTotalPortfolioRow(totalPnl, totalRealized, totalUnrealized, totalHoldings);
        }}

        function updateTotalPortfolioRow(totalPnl, totalRealized, totalUnrealized, totalAssets) {{
            const totalNetCell = document.getElementById('total-net-cell');
            const totalRealizedCell = document.getElementById('total-realized-cell');
            const totalUnrealizedCell = document.getElementById('total-unrealized-cell');
            const totalAssetsBadge = document.getElementById('total-assets-badge');

            if (totalAssetsBadge) totalAssetsBadge.innerText = totalAssets;
            if (totalRealizedCell) totalRealizedCell.innerText = `€${{totalRealized.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}`;
            if (totalUnrealizedCell) totalUnrealizedCell.innerText = `€${{totalUnrealized.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}`;
            if (totalNetCell) {{
                totalNetCell.innerHTML = renderRatioBar(totalRealized, totalUnrealized, totalPnl);
            }}
        }}

        function renderThemesTable() {{
            const tbody = document.getElementById('themes-tbody');
            const q = searchQuery.toLowerCase().trim();
            const filteredThemes = currentThemeList.filter(t => t.Theme.toLowerCase().includes(q));

            if (filteredThemes.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:24px 10px;">No themes found matching "${{escapeHtml(searchQuery)}}"</td></tr>`;
                document.getElementById('themes-count-badge').innerText = '0';
                return;
            }}

            let rowsHtml = '';
            filteredThemes.forEach(row => {{
                const pnl = row.TotalFifoPnl;
                const indicatorColor = pnl >= 0 ? "var(--color-positive)" : "var(--color-negative)";
                const ratioHtml = renderRatioBar(row.RealizedPnl, row.UnrealizedPnl, pnl);
                const isActive = row.Theme === currentTheme && !isTotalPortfolioView;

                rowsHtml += `
                    <tr class="theme-row ${{isActive ? 'active' : ''}}" data-theme="${{escapeHtml(row.Theme)}}" onclick="selectTheme('${{escapeHtml(row.Theme)}}', true)">
                        <td>
                            <div class="theme-name-cell">
                                <span class="theme-indicator" style="background: ${{indicatorColor}};"></span>
                                <span>${{escapeHtml(row.Theme)}}</span>
                            </div>
                        </td>
                        <td style="text-align:center;"><span class="badge neutral" title="${{row.WinningAssets}} winning / ${{row.LosingAssets}} losing assets">${{row.AssetCount}}</span></td>
                        <td class="num col-hide-mobile">€${{row.RealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num col-hide-mobile">€${{row.UnrealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num">${{ratioHtml}}</td>
                    </tr>
                `;
            }});

            tbody.innerHTML = rowsHtml;
            document.getElementById('themes-count-badge').innerText = filteredThemes.length;
        }}

        function filterThemes(val) {{
            searchQuery = val;
            renderThemesTable();
        }}

        function toggleActiveFilter(isActive) {{
            showActiveOnly = isActive;
            refreshDataAndViews();
        }}

        function selectTheme(themeName, isUserClick = false) {{
            isTotalPortfolioView = false;
            currentTheme = themeName;

            document.querySelectorAll('.theme-row').forEach(r => {{
                if (r.getAttribute('data-theme') === themeName) {{
                    r.classList.add('active');
                }} else {{
                    r.classList.remove('active');
                }}
            }});
            const totalRow = document.getElementById('total-portfolio-row');
            if (totalRow) totalRow.classList.remove('active');

            renderActiveView();

            if (isUserClick && window.innerWidth <= 960) {{
                document.getElementById('details-card').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
        }}

        function selectTotalPortfolio(isUserClick = false) {{
            isTotalPortfolioView = true;

            document.querySelectorAll('.theme-row').forEach(r => r.classList.remove('active'));
            const totalRow = document.getElementById('total-portfolio-row');
            if (totalRow) totalRow.classList.add('active');

            renderActiveView();

            if (isUserClick && window.innerWidth <= 960) {{
                document.getElementById('details-card').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
        }}

        function scrollToThemes() {{
            document.getElementById('themes-card').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}

        function renderActiveView() {{
            const availableTickers = getFilteredTickers();
            let title = "";
            let pnlVal = 0;
            let assetCount = 0;
            let tickersToDisplay = [];

            if (isTotalPortfolioView) {{
                const filterTag = showActiveOnly ? "Active" : "Portfolio";
                title = `Total Portfolio (${{filterTag}} • Top 9 Winners & 9 Losers)`;
                pnlVal = Math.round(availableTickers.reduce((acc, t) => acc + t.TotalFifoPnl, 0) * 100) / 100;
                assetCount = availableTickers.length;

                // Pick Top 9 Winners & Top 9 Losers across the portfolio
                const sortedByPnl = [...availableTickers].sort((a, b) => b.TotalFifoPnl - a.TotalFifoPnl);
                const winners = sortedByPnl.filter(t => t.TotalFifoPnl > 0);
                const losers = sortedByPnl.filter(t => t.TotalFifoPnl < 0);

                const top9Winners = winners.slice(0, 9);
                const top9Losers = losers.slice(-9); // Worst 9 most negative performers

                const seen = new Set();
                tickersToDisplay = [];
                [...top9Winners, ...top9Losers].forEach(item => {{
                    if (!seen.has(item.UnderlyingSymbol)) {{
                        seen.add(item.UnderlyingSymbol);
                        tickersToDisplay.push(item);
                    }}
                }});
            }} else {{
                const themeObj = currentThemeList.find(t => t.Theme === currentTheme) || {{
                    Theme: currentTheme,
                    TotalFifoPnl: 0,
                    RealizedPnl: 0,
                    UnrealizedPnl: 0,
                    AssetCount: 0
                }};
                title = themeObj.Theme;
                pnlVal = themeObj.TotalFifoPnl;
                assetCount = themeObj.AssetCount;
                tickersToDisplay = availableTickers.filter(t => t.Theme === currentTheme);
                // Standard default sort: Net PnL descending
                tickersToDisplay.sort((a, b) => b.TotalFifoPnl - a.TotalFifoPnl);
            }}

            // Update Header & Badges
            document.getElementById('active-theme-title').innerText = title;
            const pnlPill = document.getElementById('theme-pnl-pill');
            pnlPill.innerText = "Net " + formatCurrency(pnlVal);
            pnlPill.className = "badge " + (pnlVal >= 0 ? "positive" : "negative");

            const assetPill = document.getElementById('theme-asset-pill');
            assetPill.innerText = isTotalPortfolioView 
                ? `${{tickersToDisplay.length}} of ${{assetCount}} Assets` 
                : `${{assetCount}} Tickers`;

            // Render Performer Highlights (Best & Worst)
            renderPerformerHighlights(tickersToDisplay);

            // Chart rendering order: reversed so highest performer is visually at the top
            windowChartTickers = [...tickersToDisplay];
            renderPlotlyChart(windowChartTickers);

            // Subtable rendering order: highest performer at top
            renderSubTable(tickersToDisplay);
        }}

        function renderPerformerHighlights(tickers) {{
            const container = document.getElementById('performer-highlights');
            if (!tickers || tickers.length === 0) {{
                container.innerHTML = '';
                return;
            }}

            const sortedByNet = [...tickers].sort((a, b) => b.TotalFifoPnl - a.TotalFifoPnl);
            const best = sortedByNet[0];
            const worst = sortedByNet[sortedByNet.length - 1];

            let html = '';
            if (best && best.TotalFifoPnl > 0) {{
                html += `
                    <div class="performer-badge best" title="${{escapeHtml(best.Description)}}">
                        <span>Best:</span>
                        <strong>${{escapeHtml(best.UnderlyingSymbol)}}</strong>
                        <span>(${{formatCurrency(best.TotalFifoPnl)}})</span>
                    </div>
                `;
            }}

            if (worst && worst.TotalFifoPnl < 0 && worst.UnderlyingSymbol !== (best && best.UnderlyingSymbol)) {{
                html += `
                    <div class="performer-badge worst" title="${{escapeHtml(worst.Description)}}">
                        <span>Worst:</span>
                        <strong>${{escapeHtml(worst.UnderlyingSymbol)}}</strong>
                        <span>(${{formatCurrency(worst.TotalFifoPnl)}})</span>
                    </div>
                `;
            }}

            container.innerHTML = html;
        }}

        function renderPlotlyChart(tickers) {{
            if (!tickers || tickers.length === 0) {{
                Plotly.purge('ticker-chart');
                document.getElementById('ticker-chart').innerHTML = '<div style="color: var(--text-muted); padding: 30px; text-align: center; font-size: 12px;">No individual ticker data found.</div>';
                return;
            }}

            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            const width = window.innerWidth;
            const isTiny = width <= 480;
            const isSmall = width <= 768;

            // Invert array so highest rank is displayed at top of vertical axis
            const chartData = [...tickers].reverse();
            const ySymbols = chartData.map(t => t.UnderlyingSymbol);
            const descriptions = chartData.map(t => t.Description);

            // Responsive sizing per screen tier
            let barHeight, dynamicHeight, markerSize, fontSize, yFontSize, xFontSize, margins;
            if (isTiny) {{
                barHeight = 16;
                dynamicHeight = Math.max(140, Math.min(260, chartData.length * barHeight + 40));
                markerSize = 6;
                fontSize = 10;
                yFontSize = 10;
                xFontSize = 9;
                margins = {{ l: 48, r: 10, t: 8, b: 22 }};
            }} else if (isSmall) {{
                barHeight = 19;
                dynamicHeight = Math.max(170, Math.min(320, chartData.length * barHeight + 48));
                markerSize = 7;
                fontSize = 11;
                yFontSize = 11;
                xFontSize = 10;
                margins = {{ l: 58, r: 14, t: 10, b: 24 }};
            }} else {{
                barHeight = 25;
                dynamicHeight = Math.max(220, Math.min(520, chartData.length * barHeight + 58));
                markerSize = 9;
                fontSize = 12;
                yFontSize = 12;
                xFontSize = 11;
                margins = {{ l: 78, r: 18, t: 14, b: 28 }};
            }}

            // Realized Trace
            const traceRealized = {{
                type: 'bar',
                orientation: 'h',
                name: 'Realized',
                y: ySymbols,
                x: chartData.map(t => t.RealizedPnl),
                marker: {{
                    color: chartData.map(t => t.RealizedPnl >= 0 ? '#16a34a' : '#dc2626'),
                    line: {{ width: 0 }}
                }},
                customdata: descriptions,
                hovertemplate: '<b>%{{y}}</b> (%{{customdata}})<br>Realized: <b>€%{{x:,.2f}}</b><extra></extra>'
            }};

            // Unrealized Trace
            const traceUnrealized = {{
                type: 'bar',
                orientation: 'h',
                name: 'Unrealized',
                y: ySymbols,
                x: chartData.map(t => t.UnrealizedPnl),
                marker: {{
                    color: chartData.map(t => t.UnrealizedPnl >= 0 ? '#4ade80' : '#f87171'),
                    line: {{ width: 0 }}
                }},
                customdata: descriptions,
                hovertemplate: '<b>%{{y}}</b> (%{{customdata}})<br>Unrealized: <b>€%{{x:,.2f}}</b><extra></extra>'
            }};

            // Net PnL Diamond Marker
            const traceNet = {{
                type: 'scatter',
                mode: 'markers',
                orientation: 'h',
                name: 'Net PnL',
                y: ySymbols,
                x: chartData.map(t => t.TotalFifoPnl),
                marker: {{
                    symbol: 'diamond',
                    size: markerSize,
                    color: chartData.map(t => t.TotalFifoPnl >= 0 ? '#10b981' : '#f43f5e'),
                    line: {{
                        color: isLight ? '#0f172a' : '#ffffff',
                        width: isTiny ? 1 : 1.5
                    }}
                }},
                customdata: descriptions,
                hovertemplate: '<b>%{{y}}</b> (%{{customdata}})<br>Net PnL: <b>€%{{x:,.2f}}</b><extra></extra>'
            }};

            const stackedPos = chartData.map(t => Math.max(0, t.RealizedPnl) + Math.max(0, t.UnrealizedPnl));
            const stackedNeg = chartData.map(t => Math.min(0, t.RealizedPnl) + Math.min(0, t.UnrealizedPnl));
            const netVals = chartData.map(t => t.TotalFifoPnl);

            const minVal = Math.min(0, ...stackedNeg, ...netVals);
            const maxVal = Math.max(0, ...stackedPos, ...netVals);
            const span = (maxVal - minVal) || 100;
            const xRange = [minVal - span * 0.08, maxVal + span * 0.08];

            const layout = {{
                barmode: 'relative',
                bargap: isSmall ? 0.28 : 0.32,
                height: dynamicHeight,
                margin: margins,
                showlegend: false,
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: {{
                    family: 'Inter, sans-serif',
                    color: isLight ? '#475569' : '#94a3b8',
                    size: fontSize
                }},
                xaxis: {{
                    range: xRange,
                    gridcolor: isLight ? '#e2e8f0' : '#1e293b',
                    zerolinecolor: isLight ? '#94a3b8' : '#475569',
                    zerolinewidth: 1.5,
                    tickprefix: '€',
                    automargin: true,
                    tickfont: {{ size: xFontSize }}
                }},
                yaxis: {{
                    automargin: true,
                    ticksuffix: '  ',
                    tickfont: {{
                        family: 'JetBrains Mono, monospace',
                        size: yFontSize,
                        color: isLight ? '#0f172a' : '#f8fafc',
                        weight: 600
                    }}
                }}
            }};

            const config = {{
                responsive: true,
                displayModeBar: false
            }};

            Plotly.react('ticker-chart', [traceRealized, traceUnrealized, traceNet], layout, config);
        }}

        function renderSubTable(tickers) {{
            const tbody = document.getElementById('ticker-tbody');
            if (!tickers || tickers.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:20px;">No assets match current criteria.</td></tr>';
                return;
            }}

            let rowsHtml = '';
            tickers.forEach(t => {{
                const pnl = t.TotalFifoPnl;
                const ticker = escapeHtml(t.UnderlyingSymbol);
                const desc = escapeHtml(t.Description);
                const themeTag = isTotalPortfolioView && t.Theme ? `<span style="font-size:10px; color:var(--text-muted); margin-left:4px;">[${{escapeHtml(t.Theme)}}]</span>` : '';
                const activeDot = t.IsActive ? `<span class="active-dot" title="Active open position"></span>` : '';
                const ratioHtml = renderRatioBar(t.RealizedPnl, t.UnrealizedPnl, pnl);

                rowsHtml += `
                    <tr>
                        <td>
                            <div style="display:flex; align-items:center; gap:5px;">
                                ${{activeDot}}
                                <span class="ticker-pill">${{ticker}}</span>
                                ${{themeTag}}
                            </div>
                        </td>
                        <td><div class="subtable-desc" title="${{desc}}">${{desc}}</div></td>
                        <td class="num col-hide-mobile">€${{t.RealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num col-hide-mobile">€${{t.UnrealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num">${{ratioHtml}}</td>
                    </tr>
                `;
            }});
            tbody.innerHTML = rowsHtml;
        }}

        /* Light / Dark Mode Handling */
        function initThemeMode() {{
            const saved = localStorage.getItem('ibkr_theme_mode');
            if (saved === 'light') {{
                applyThemeMode('light');
            }} else {{
                applyThemeMode('dark');
            }}
        }}

        function toggleThemeMode() {{
            const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
            const target = current === 'dark' ? 'light' : 'dark';
            applyThemeMode(target);
            localStorage.setItem('ibkr_theme_mode', target);
        }}

        function applyThemeMode(mode) {{
            const icon = document.getElementById('theme-toggle-icon');
            const label = document.getElementById('theme-toggle-label');

            if (mode === 'light') {{
                document.documentElement.setAttribute('data-theme', 'light');
                if (icon) icon.innerText = '🌙';
                if (label) label.innerText = 'Dark';
            }} else {{
                document.documentElement.removeAttribute('data-theme');
                if (icon) icon.innerText = '☀️';
                if (label) label.innerText = 'Light';
            }}

            if (windowChartTickers.length > 0) {{
                renderPlotlyChart(windowChartTickers);
            }}
        }}

        /* Master Refresh Function */
        function refreshDataAndViews() {{
            const availableTickers = getFilteredTickers();
            currentThemeList = aggregateThemes(availableTickers);

            updateKpis(availableTickers);
            renderThemesTable();

            // If selected theme no longer exists in current filtered theme list, select first available
            if (!isTotalPortfolioView) {{
                const themeExists = currentThemeList.some(t => t.Theme === currentTheme);
                if (!themeExists && currentThemeList.length > 0) {{
                    currentTheme = currentThemeList[0].Theme;
                }}
            }}

            renderActiveView();
        }}

        // Handle responsive window resize
        let resizeTimer;
        window.addEventListener('resize', () => {{
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {{
                if (windowChartTickers && windowChartTickers.length > 0) {{
                    renderPlotlyChart(windowChartTickers);
                }} else {{
                    const chartDiv = document.getElementById('ticker-chart');
                    if (chartDiv && chartDiv.data) {{
                        Plotly.Plots.resize('ticker-chart');
                    }}
                }}
            }}, 100);
        }});

        // Initialization
        window.addEventListener('DOMContentLoaded', () => {{
            initThemeMode();
            refreshDataAndViews();
            if (!isTotalPortfolioView && currentTheme) {{
                selectTheme(currentTheme);
            }}
        }});
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
