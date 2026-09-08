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

    # Theme aggregation
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

    total_assets = int(ticker_summary['UnderlyingSymbol'].nunique()) if not ticker_summary.empty else 0
    active_assets_count = int(ticker_summary['IsActive'].sum()) if not ticker_summary.empty else 0

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

        /* Unified Single-View Dashboard Container */
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
        }}

        .card-header {{
            background: var(--bg-card-header);
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .breadcrumb-nav {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .btn-drilldown-back {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--color-accent);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .btn-drilldown-back:hover {{
            background: var(--color-accent-bg);
            border-color: var(--color-accent);
        }}

        .breadcrumb-title {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        /* View Switcher Segmented Control */
        .view-switcher {{
            display: inline-flex;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 2px;
            gap: 2px;
        }}

        .view-btn {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 5px 12px;
            border-radius: 6px;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            font-family: var(--font-main);
        }}

        .view-btn:hover {{
            color: var(--text-primary);
        }}

        .view-btn.active {{
            background: var(--color-accent);
            color: #0b1120;
            font-weight: 700;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
        }}

        /* Secondary Toolbar: Ticker Search & Highlights */
        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 14px;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-subtle);
            flex-wrap: wrap;
            gap: 10px;
        }}

        .ticker-search-box {{
            display: flex;
            align-items: center;
            position: relative;
            flex: 1 1 280px;
            max-width: 420px;
        }}

        .ticker-search-box input {{
            width: 100%;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 6px 28px 6px 10px;
            color: var(--text-primary);
            font-size: 12px;
            font-family: var(--font-main);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        .ticker-search-box input:focus {{
            border-color: var(--color-accent);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
        }}

        .search-clear-btn {{
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 12px;
            display: none;
            line-height: 1;
        }}

        .search-clear-btn:hover {{
            color: var(--text-primary);
        }}

        .toolbar-right {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .performer-highlights {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
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

        /* Fully Responsive Table Design */
        .table-container {{
            /* Dynamic height responding to viewport height so headers & footers stay in view */
            max-height: clamp(380px, calc(100vh - 240px), 820px);
            overflow-y: auto;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            position: relative;
            width: 100%;
        }}

        table {{
            width: 100%;
            min-width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 12px;
        }}

        thead th {{
            position: sticky;
            top: 0;
            background: var(--bg-card-header);
            color: var(--text-secondary);
            font-weight: 600;
            text-align: left;
            padding: 9px 12px;
            border-bottom: 1px solid var(--border-color);
            z-index: 2;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
        }}

        tbody td {{
            padding: 9px 12px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            vertical-align: middle;
            background: var(--bg-card);
        }}

        .interactive-row {{
            cursor: pointer;
            transition: background 0.12s ease;
        }}

        .interactive-row:hover td {{
            background: var(--table-hover-bg);
        }}

        .interactive-row td:first-child {{
            border-left: 3px solid transparent;
        }}

        .interactive-row:hover td:first-child {{
            border-left-color: var(--color-accent);
        }}

        /* Responsive Column Width Rules */
        .col-theme {{
            width: auto;
            min-width: 130px;
        }}

        .col-assets {{
            width: 80px;
            min-width: 65px;
            text-align: center;
        }}

        .col-ticker {{
            width: 95px;
            min-width: 85px;
        }}

        .col-desc {{
            width: auto;
            min-width: 120px;
        }}

        .col-theme-tag {{
            width: 120px;
            min-width: 95px;
        }}

        .col-realized, .col-unrealized {{
            width: 110px;
            min-width: 85px;
        }}

        .col-pnl {{
            width: 155px;
            min-width: 125px;
        }}

        .theme-name-cell {{
            color: var(--text-primary);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }}

        .drilldown-hint {{
            font-size: 10px;
            color: var(--color-accent);
            opacity: 0;
            transition: opacity 0.15s ease;
            margin-left: 4px;
        }}

        .interactive-row:hover .drilldown-hint {{
            opacity: 1;
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
            z-index: 2;
            cursor: pointer;
        }}

        tfoot .total-row td {{
            padding: 10px 12px;
            color: var(--text-primary);
            font-weight: 700;
            background: var(--total-row-bg);
            border-top: 2px solid var(--border-color);
            border-bottom: none;
        }}

        tfoot .total-row:hover td {{
            background: var(--table-hover-bg);
        }}

        .ticker-pill {{
            background: var(--ticker-pill-bg);
            color: var(--ticker-pill-text);
            font-family: var(--font-mono);
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            border: 1px solid var(--ticker-pill-border);
            display: inline-block;
        }}

        .theme-pill-tag {{
            font-size: 10px;
            background: rgba(148, 163, 184, 0.12);
            color: var(--text-secondary);
            padding: 1px 6px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
            white-space: nowrap;
            display: inline-block;
        }}

        .theme-pill-tag:hover {{
            background: var(--color-accent-bg);
            color: var(--color-accent);
        }}

        .active-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--color-accent);
            display: inline-block;
            box-shadow: 0 0 5px var(--color-accent);
            flex-shrink: 0;
        }}

        .subtable-desc {{
            font-size: 11px;
            color: var(--text-muted);
            max-width: clamp(140px, 28vw, 360px);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        /* Graph View Container & Legend */
        .chart-view-panel {{
            padding: 8px 12px 14px 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .chart-legend {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: var(--text-secondary);
            padding: 4px 6px;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .chart-click-hint {{
            font-size: 11px;
            color: var(--text-muted);
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}

        .legend-items {{
            display: flex;
            align-items: center;
            gap: 12px;
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
            width: 100%;
            min-height: clamp(380px, calc(100vh - 300px), 720px);
        }}

        #main-chart {{
            width: 100%;
        }}

        /* Clickable Theme Labels in Graph View */
        #main-chart .ytick text {{
            cursor: pointer !important;
            pointer-events: all !important;
            transition: fill 0.15s ease, font-weight 0.15s ease;
        }}

        #main-chart .ytick text:hover {{
            fill: var(--color-accent) !important;
            font-weight: 700 !important;
            text-decoration: underline;
        }}

        /* Screen-Size Responsive Media Breakpoints for Tables */
        @media (min-width: 1280px) {{
            thead th {{
                padding: 11px 14px;
                font-size: 11.5px;
            }}
            tbody td {{
                padding: 10px 14px;
                font-size: 12.5px;
            }}
            .num {{
                font-size: 12.5px;
            }}
            .pnl-amount {{
                font-size: 12.5px;
            }}
            .ratio-bar-track {{
                width: 62px;
                height: 5px;
            }}
        }}

        @media (max-width: 768px) {{
            .table-container {{
                max-height: clamp(340px, calc(100vh - 250px), 620px);
            }}
            thead th {{
                padding: 8px 10px;
                font-size: 10.5px;
            }}
            tbody td {{
                padding: 8px 10px;
                font-size: 11.5px;
            }}
            .num {{
                font-size: 11.5px;
            }}
            .subtable-desc {{
                max-width: clamp(110px, 20vw, 200px);
            }}
            .ratio-bar-track {{
                width: 46px;
                height: 4px;
            }}
        }}

        @media (max-width: 600px) {{
            .col-hide-mobile {{
                display: none !important;
            }}
            .table-container {{
                max-height: calc(100vh - 280px);
                min-height: 300px;
            }}
            thead th {{
                padding: 7px 8px !important;
                font-size: 10px !important;
            }}
            tbody td {{
                padding: 7px 8px !important;
                font-size: 11px !important;
            }}
            tfoot .total-row td {{
                padding: 8px 8px !important;
                font-size: 11px !important;
            }}
            .num {{
                font-size: 11px !important;
            }}
            .pnl-amount {{
                font-size: 11px !important;
            }}
            .subtable-desc {{
                max-width: 120px;
            }}
            .ratio-bar-track {{
                width: 38px;
                height: 3.5px;
            }}
            .ratio-label {{
                font-size: 8.5px;
            }}
            .theme-name-cell {{
                gap: 6px;
            }}
        }}

        @media (max-width: 400px) {{
            thead th, tbody td, tfoot .total-row td {{
                padding: 6px 5px !important;
                font-size: 10px !important;
            }}
            .num, .pnl-amount {{
                font-size: 10.5px !important;
            }}
            .ticker-pill {{
                padding: 1px 4px;
                font-size: 10px;
            }}
            .subtable-desc {{
                max-width: 85px;
                font-size: 10px;
            }}
            .drilldown-hint {{
                display: none !important;
            }}
            .ratio-bar-track {{
                width: 30px;
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

        <!-- Unified Single-View Dashboard Container -->
        <main class="card" id="dashboard-card">
            <!-- Card Header: Breadcrumbs / Title + View Switcher -->
            <div class="card-header">
                <div class="breadcrumb-nav">
                    <button id="btn-back-to-themes" class="btn-drilldown-back" onclick="drillUpToThemes()" style="display: none;" title="Return to All Themes overview">
                        ← All Themes
                    </button>
                    <div class="breadcrumb-title" id="current-view-title">
                        <span>All Themes</span>
                    </div>
                    <span id="view-pnl-pill" class="badge" style="display: none;"></span>
                    <span id="view-count-pill" class="badge neutral"></span>
                </div>

                <!-- Segmented View Switcher: Table vs Graph -->
                <div class="view-switcher" role="tablist">
                    <button id="view-btn-table" class="view-btn active" onclick="switchView('table')" title="Switch to Table View">
                        <span>☷</span>
                        <span>Table</span>
                    </button>
                    <button id="view-btn-graph" class="view-btn" onclick="switchView('graph')" title="Switch to Graph View">
                        <span>📊</span>
                        <span>Graph</span>
                    </button>
                </div>
            </div>

            <!-- Toolbar: Ticker Search Bar & Performer Highlights -->
            <div class="toolbar">
                <div class="ticker-search-box">
                    <input id="ticker-search" type="text" placeholder="Search ticker or company (e.g. NVDA, Airbus, Boeing)..." oninput="handleTickerSearch(this.value)">
                    <button id="search-clear-btn" class="search-clear-btn" onclick="clearTickerSearch()" title="Clear search">✕</button>
                </div>

                <div class="toolbar-right">
                    <div class="performer-highlights" id="performer-highlights">
                        <!-- Populated dynamically: Best / Worst -->
                    </div>
                </div>
            </div>

            <!-- Viewport 1: Table View -->
            <div id="table-view-container" class="table-container">
                <table id="main-table">
                    <thead id="table-head">
                        <!-- Rendered dynamically depending on level (Themes vs Tickers) -->
                    </thead>
                    <tbody id="table-body">
                        <!-- Rendered dynamically -->
                    </tbody>
                    <tfoot id="table-foot">
                        <!-- Rendered dynamically (Total Portfolio row at Themes level) -->
                    </tfoot>
                </table>
            </div>

            <!-- Viewport 2: Graph View -->
            <div id="graph-view-container" class="chart-view-panel" style="display: none;">
                <div class="chart-legend">
                    <div class="chart-click-hint" id="chart-click-hint">
                        <span>💡 Tip: Tap any theme name or bar to drill down</span>
                    </div>
                    <div class="legend-items">
                        <span class="legend-item"><span class="legend-swatch realized-swatch"></span> Realized</span>
                        <span class="legend-item"><span class="legend-swatch unrealized-swatch"></span> Unrealized</span>
                        <span class="legend-item"><span class="legend-diamond">◆</span> Net PnL</span>
                    </div>
                </div>
                <div class="chart-wrapper">
                    <div id="main-chart"></div>
                </div>
            </div>
        </main>
    </div>

    <script>
        // Data passed from Python
        const TICKER_DATA = {ticker_json};

        // Application State
        let currentMode = 'table';         // 'table' | 'graph'
        let drilldownTheme = null;         // null (All Themes) | string (Theme Name) | '__TOTAL__' (Total Portfolio)
        let tickerSearchQuery = '';        // Active search filter for tickers
        let showActiveOnly = false;        // Toggle active/open positions only
        let currentThemeList = [];         // Aggregated themes list

        function escapeHtml(s) {{
            return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
                {{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]
            ));
        }}

        function formatCurrency(val) {{
            const sign = val >= 0 ? "+€" : "-€";
            return sign + Math.abs(val).toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
        }}

        /* Win/Loss & Realized/Unrealized Ratio Component */
        function renderRatioBar(realized, unrealized, total) {{
            const isPosTotal = total >= 0;
            const posPart = (realized > 0 ? realized : 0) + (unrealized > 0 ? unrealized : 0);
            const negPart = Math.abs((realized < 0 ? realized : 0) + (unrealized < 0 ? unrealized : 0));
            
            let trackHtml = '';
            let label = '';
            let tooltip = '';

            if (posPart > 0 && negPart > 0) {{
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
                const realPct = Math.round((Math.max(0, realized) / posPart) * 100);
                const unrealPct = 100 - realPct;
                tooltip = `100% Gains • Realized: +€${{realized.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (${{realPct}}%) | Unrealized: +€${{unrealized.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (${{unrealPct}}%)`;
                trackHtml = `
                    <div class="ratio-bar-seg" style="width: ${{realPct}}%; background: var(--color-realized-pos);"></div>
                    <div class="ratio-bar-seg" style="width: ${{unrealPct}}%; background: var(--color-unrealized-pos);"></div>
                `;
                label = `${{realPct}}% locked`;
            }} else if (negPart > 0) {{
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

        /* Data Helpers */
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
        }}

        /* View Switching (Table ⇄ Graph) */
        function switchView(mode) {{
            if (currentMode === mode) return;
            currentMode = mode;
            const btnTable = document.getElementById('view-btn-table');
            const btnGraph = document.getElementById('view-btn-graph');
            const tableContainer = document.getElementById('table-view-container');
            const graphContainer = document.getElementById('graph-view-container');

            if (mode === 'table') {{
                btnTable.classList.add('active');
                btnGraph.classList.remove('active');
                tableContainer.style.display = 'block';
                graphContainer.style.display = 'none';
            }} else {{
                btnGraph.classList.add('active');
                btnTable.classList.remove('active');
                tableContainer.style.display = 'none';
                graphContainer.style.display = 'flex';
            }}

            // Re-render current level (theme or ticker drilldown) synchronously in new view
            renderDashboard();

            // Ensure graph dimensions are calculated cleanly after unhiding
            if (mode === 'graph') {{
                setTimeout(() => {{
                    Plotly.Plots.resize('main-chart');
                }}, 30);
            }}
        }}

        /* Drill-down Navigation Functions */
        function drillDownToTheme(themeName) {{
            drilldownTheme = themeName;
            renderDashboard();
        }}

        function drillDownToTotalPortfolio() {{
            drilldownTheme = '__TOTAL__';
            renderDashboard();
        }}

        function drillUpToThemes() {{
            drilldownTheme = null;
            renderDashboard();
        }}

        /* Ticker Search Handling */
        function handleTickerSearch(val) {{
            tickerSearchQuery = val.trim();
            const clearBtn = document.getElementById('search-clear-btn');
            if (clearBtn) {{
                clearBtn.style.display = tickerSearchQuery.length > 0 ? 'inline-block' : 'none';
            }}
            renderDashboard();
        }}

        function clearTickerSearch() {{
            tickerSearchQuery = '';
            const input = document.getElementById('ticker-search');
            if (input) input.value = '';
            const clearBtn = document.getElementById('search-clear-btn');
            if (clearBtn) clearBtn.style.display = 'none';
            renderDashboard();
        }}

        function toggleActiveFilter(isActive) {{
            showActiveOnly = isActive;
            refreshDataAndViews();
        }}

        /* Performer Highlights */
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

        /* Master Render Controller */
        function renderDashboard() {{
            const availableTickers = getFilteredTickers();
            const searchQ = tickerSearchQuery.toLowerCase();
            const isSearching = searchQ.length > 0;

            const backBtn = document.getElementById('btn-back-to-themes');
            const titleEl = document.getElementById('current-view-title');
            const pnlPill = document.getElementById('view-pnl-pill');
            const countPill = document.getElementById('view-count-pill');
            const clickHint = document.getElementById('chart-click-hint');

            // CASE A: Search active across entire portfolio (when not inside a specific theme)
            if (isSearching && !drilldownTheme) {{
                backBtn.style.display = 'inline-flex';
                titleEl.innerHTML = `<span>Ticker Search: "${{escapeHtml(tickerSearchQuery)}}"</span>`;
                clickHint.style.display = 'none';

                const matchedTickers = availableTickers.filter(t => 
                    t.UnderlyingSymbol.toLowerCase().includes(searchQ) ||
                    (t.Description && t.Description.toLowerCase().includes(searchQ))
                );
                matchedTickers.sort((a, b) => b.TotalFifoPnl - a.TotalFifoPnl);

                const totalMatchedPnl = Math.round(matchedTickers.reduce((acc, t) => acc + t.TotalFifoPnl, 0) * 100) / 100;
                pnlPill.style.display = 'inline-flex';
                pnlPill.innerText = "Net " + formatCurrency(totalMatchedPnl);
                pnlPill.className = "badge " + (totalMatchedPnl >= 0 ? "positive" : "negative");
                countPill.innerText = `${{matchedTickers.length}} Matched Tickers`;

                renderPerformerHighlights(matchedTickers);

                if (currentMode === 'table') {{
                    renderTickersTable(matchedTickers, true);
                }} else {{
                    renderTickersGraph(matchedTickers);
                }}
                return;
            }}

            // CASE B: Drilled down into Total Portfolio View
            if (drilldownTheme === '__TOTAL__') {{
                backBtn.style.display = 'inline-flex';
                titleEl.innerHTML = `<span>Total Portfolio Drilldown</span>`;
                clickHint.style.display = 'none';

                let tickers = [...availableTickers];
                if (isSearching) {{
                    tickers = tickers.filter(t => 
                        t.UnderlyingSymbol.toLowerCase().includes(searchQ) ||
                        (t.Description && t.Description.toLowerCase().includes(searchQ))
                    );
                }}

                tickers.sort((a, b) => b.TotalFifoPnl - a.TotalFifoPnl);
                const totalPnl = Math.round(tickers.reduce((acc, t) => acc + t.TotalFifoPnl, 0) * 100) / 100;

                pnlPill.style.display = 'inline-flex';
                pnlPill.innerText = "Net " + formatCurrency(totalPnl);
                pnlPill.className = "badge " + (totalPnl >= 0 ? "positive" : "negative");
                countPill.innerText = `${{tickers.length}} Assets`;

                renderPerformerHighlights(tickers);

                if (currentMode === 'table') {{
                    renderTickersTable(tickers, true);
                }} else {{
                    renderTickersGraph(tickers);
                }}
                return;
            }}

            // CASE C: Drilled down into a Specific Theme
            if (drilldownTheme) {{
                backBtn.style.display = 'inline-flex';
                titleEl.innerHTML = `<span>${{escapeHtml(drilldownTheme)}}</span>`;
                clickHint.style.display = 'none';

                let tickers = availableTickers.filter(t => t.Theme === drilldownTheme);
                if (isSearching) {{
                    tickers = tickers.filter(t => 
                        t.UnderlyingSymbol.toLowerCase().includes(searchQ) ||
                        (t.Description && t.Description.toLowerCase().includes(searchQ))
                    );
                }}

                tickers.sort((a, b) => b.TotalFifoPnl - a.TotalFifoPnl);
                const themePnl = Math.round(tickers.reduce((acc, t) => acc + t.TotalFifoPnl, 0) * 100) / 100;

                pnlPill.style.display = 'inline-flex';
                pnlPill.innerText = "Net " + formatCurrency(themePnl);
                pnlPill.className = "badge " + (themePnl >= 0 ? "positive" : "negative");
                countPill.innerText = `${{tickers.length}} Tickers`;

                renderPerformerHighlights(tickers);

                if (currentMode === 'table') {{
                    renderTickersTable(tickers, false);
                }} else {{
                    renderTickersGraph(tickers);
                }}
                return;
            }}

            // CASE D: Level 1 - All Themes Overview
            backBtn.style.display = 'none';
            pnlPill.style.display = 'none';
            titleEl.innerHTML = `<span>All Themes</span>`;
            countPill.innerText = `${{currentThemeList.length}} Themes`;
            clickHint.style.display = 'inline-flex';

            renderPerformerHighlights(availableTickers);

            if (currentMode === 'table') {{
                renderThemesTable();
            }} else {{
                renderThemesGraph();
            }}
        }}

        /* Table Rendering: Themes Overview */
        function renderThemesTable() {{
            const thead = document.getElementById('table-head');
            const tbody = document.getElementById('table-body');
            const tfoot = document.getElementById('table-foot');

            thead.innerHTML = `
                <tr>
                    <th class="col-theme">Theme</th>
                    <th class="col-assets" style="text-align:center;">Assets</th>
                    <th class="num col-hide-mobile col-realized">Realized</th>
                    <th class="num col-hide-mobile col-unrealized">Unrealized</th>
                    <th class="num col-pnl">Net PnL</th>
                </tr>
            `;

            if (currentThemeList.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:28px 10px;">No themes found.</td></tr>`;
                tfoot.innerHTML = '';
                return;
            }}

            let rowsHtml = '';
            currentThemeList.forEach(row => {{
                const pnl = row.TotalFifoPnl;
                const indicatorColor = pnl >= 0 ? "var(--color-positive)" : "var(--color-negative)";
                const ratioHtml = renderRatioBar(row.RealizedPnl, row.UnrealizedPnl, pnl);

                rowsHtml += `
                    <tr class="interactive-row" onclick="drillDownToTheme('${{escapeHtml(row.Theme)}}')">
                        <td class="col-theme">
                            <div class="theme-name-cell">
                                <span class="theme-indicator" style="background: ${{indicatorColor}};"></span>
                                <span>${{escapeHtml(row.Theme)}}</span>
                                <span class="drilldown-hint">View Tickers →</span>
                            </div>
                        </td>
                        <td class="col-assets" style="text-align:center;"><span class="badge neutral" title="${{row.WinningAssets}} winning / ${{row.LosingAssets}} losing assets">${{row.AssetCount}}</span></td>
                        <td class="num col-hide-mobile col-realized">€${{row.RealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num col-hide-mobile col-unrealized">€${{row.UnrealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num col-pnl">${{ratioHtml}}</td>
                    </tr>
                `;
            }});
            tbody.innerHTML = rowsHtml;

            // Render Total Portfolio row in Footer
            const availableTickers = getFilteredTickers();
            const totalPnl = Math.round(availableTickers.reduce((acc, t) => acc + t.TotalFifoPnl, 0) * 100) / 100;
            const totalRealized = Math.round(availableTickers.reduce((acc, t) => acc + t.RealizedPnl, 0) * 100) / 100;
            const totalUnrealized = Math.round(availableTickers.reduce((acc, t) => acc + t.UnrealizedPnl, 0) * 100) / 100;
            const totalAssets = availableTickers.length;
            const ratioHtmlTotal = renderRatioBar(totalRealized, totalUnrealized, totalPnl);

            tfoot.innerHTML = `
                <tr class="total-row" onclick="drillDownToTotalPortfolio()" title="Click to view all individual tickers in the portfolio">
                    <td class="col-theme">
                        <div class="theme-name-cell" style="font-weight: 700;">
                            <span class="theme-indicator" style="background: var(--color-accent);"></span>
                            <span>Total Portfolio</span>
                            <span class="drilldown-hint">View All Tickers →</span>
                        </div>
                    </td>
                    <td class="col-assets" style="text-align:center;"><span class="badge neutral" style="font-weight: 700;">${{totalAssets}}</span></td>
                    <td class="num col-hide-mobile col-realized" style="font-weight: 700;">€${{totalRealized.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                    <td class="num col-hide-mobile col-unrealized" style="font-weight: 700;">€${{totalUnrealized.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                    <td class="num col-pnl" style="font-weight: 700;">${{ratioHtmlTotal}}</td>
                </tr>
            `;
        }}

        /* Table Rendering: Ticker Drilldown */
        function renderTickersTable(tickers, showThemeColumn = false) {{
            const thead = document.getElementById('table-head');
            const tbody = document.getElementById('table-body');
            const tfoot = document.getElementById('table-foot');
            tfoot.innerHTML = '';

            thead.innerHTML = `
                <tr>
                    <th class="col-ticker">Ticker</th>
                    <th class="col-desc">Description</th>
                    ${{showThemeColumn ? '<th class="col-theme-tag">Theme</th>' : ''}}
                    <th class="num col-hide-mobile col-realized">Realized</th>
                    <th class="num col-hide-mobile col-unrealized">Unrealized</th>
                    <th class="num col-pnl">Net PnL</th>
                </tr>
            `;

            if (!tickers || tickers.length === 0) {{
                const colSpan = showThemeColumn ? 6 : 5;
                tbody.innerHTML = `<tr><td colspan="${{colSpan}}" style="text-align:center; color:var(--text-muted); padding:28px 10px;">No tickers match the criteria.</td></tr>`;
                return;
            }}

            let rowsHtml = '';
            tickers.forEach(t => {{
                const pnl = t.TotalFifoPnl;
                const ticker = escapeHtml(t.UnderlyingSymbol);
                const desc = escapeHtml(t.Description);
                const activeDot = t.IsActive ? `<span class="active-dot" title="Active open position"></span>` : '';
                const ratioHtml = renderRatioBar(t.RealizedPnl, t.UnrealizedPnl, pnl);
                const themeTag = showThemeColumn && t.Theme 
                    ? `<td class="col-theme-tag"><span class="theme-pill-tag" onclick="event.stopPropagation(); drillDownToTheme('${{escapeHtml(t.Theme)}}')">${{escapeHtml(t.Theme)}}</span></td>`
                    : '';

                rowsHtml += `
                    <tr>
                        <td class="col-ticker">
                            <div style="display:flex; align-items:center; gap:6px;">
                                ${{activeDot}}
                                <span class="ticker-pill">${{ticker}}</span>
                            </div>
                        </td>
                        <td class="col-desc"><div class="subtable-desc" title="${{desc}}">${{desc}}</div></td>
                        ${{themeTag}}
                        <td class="num col-hide-mobile col-realized">€${{t.RealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num col-hide-mobile col-unrealized">€${{t.UnrealizedPnl.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                        <td class="num col-pnl">${{ratioHtml}}</td>
                    </tr>
                `;
            }});

            tbody.innerHTML = rowsHtml;
        }}

        /* Graph Rendering: Themes Overview */
        function renderThemesGraph() {{
            if (currentMode !== 'graph') return;
            const container = document.getElementById('main-chart');

            if (!currentThemeList || currentThemeList.length === 0) {{
                Plotly.purge(container);
                container.innerHTML = '<div style="color: var(--text-muted); padding: 40px; text-align: center; font-size: 13px;">No themes data to display.</div>';
                return;
            }}

            // Reverse for top-down descending visual hierarchy
            const dataToChart = [...currentThemeList].reverse();
            const yNames = dataToChart.map(t => t.Theme);
            const realized = dataToChart.map(t => t.RealizedPnl);
            const unrealized = dataToChart.map(t => t.UnrealizedPnl);
            const net = dataToChart.map(t => t.TotalFifoPnl);

            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            const textColor = isLight ? '#0f172a' : '#f8fafc';
            const gridColor = isLight ? '#e2e8f0' : '#1e293b';

            const traceRealized = {{
                x: realized,
                y: yNames,
                name: 'Realized PnL',
                type: 'bar',
                orientation: 'h',
                marker: {{
                    color: realized.map(v => v >= 0 ? '#16a34a' : '#dc2626'),
                    opacity: 0.85
                }},
                hovertemplate: '%{{y}}<br>Realized: €%{{x:,.2f}}<extra></extra>'
            }};

            const traceUnrealized = {{
                x: unrealized,
                y: yNames,
                name: 'Unrealized PnL',
                type: 'bar',
                orientation: 'h',
                marker: {{
                    color: unrealized.map(v => v >= 0 ? '#4ade80' : '#f87171'),
                    opacity: 0.75
                }},
                hovertemplate: '%{{y}}<br>Unrealized: €%{{x:,.2f}}<extra></extra>'
            }};

            const traceNet = {{
                x: net,
                y: yNames,
                name: 'Net PnL',
                type: 'scatter',
                mode: 'markers',
                marker: {{
                    symbol: 'diamond',
                    size: 8,
                    color: net.map(v => v >= 0 ? '#10b981' : '#f43f5e'),
                    line: {{ color: isLight ? '#ffffff' : '#0b1120', width: 1 }}
                }},
                hovertemplate: '%{{y}}<br><b>Net PnL: €%{{x:,.2f}}</b><extra></extra>'
            }};

            const layout = {{
                barmode: 'relative',
                autosize: true,
                height: Math.max(480, dataToChart.length * 30 + 100),
                margin: {{ l: 150, r: 35, t: 20, b: 35 }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ family: 'Inter', color: textColor, size: 11 }},
                showlegend: false,
                xaxis: {{
                    gridcolor: gridColor,
                    zerolinecolor: isLight ? '#94a3b8' : '#475569',
                    zerolinewidth: 1.5,
                    tickfont: {{ color: textColor, family: 'JetBrains Mono', size: 10 }},
                    tickprefix: '€',
                    tickformat: ',.0f'
                }},
                yaxis: {{
                    tickfont: {{ color: textColor, family: 'JetBrains Mono', size: 11, weight: 600 }},
                    automargin: true
                }},
                hoverlabel: {{
                    bgcolor: isLight ? '#ffffff' : '#1e293b',
                    bordercolor: isLight ? '#cbd5e1' : '#334155',
                    font: {{ color: textColor, family: 'JetBrains Mono', size: 11 }}
                }}
            }};

            const config = {{
                responsive: true,
                displayModeBar: false
            }};

            Plotly.react(container, [traceRealized, traceUnrealized, traceNet], layout, config).then(() => {{
                // Make theme labels (y-axis tick texts) direct click & touch drilldown triggers
                const yTicks = container.querySelectorAll('.ytick text');
                yTicks.forEach(tick => {{
                    tick.style.cursor = 'pointer';
                    tick.style.pointerEvents = 'all';
                    
                    const handleThemeClick = (e) => {{
                        e.stopPropagation();
                        e.preventDefault();
                        const themeName = tick.textContent.trim();
                        if (themeName) {{
                            drillDownToTheme(themeName);
                        }}
                    }};

                    tick.onclick = handleThemeClick;
                    tick.ontouchend = handleThemeClick;
                }});

                // Also support clicking the bars as secondary trigger
                if (container.removeAllListeners) {{
                    container.removeAllListeners('plotly_click');
                }}
                container.on('plotly_click', (data) => {{
                    if (!data || !data.points || data.points.length === 0) return;
                    const clickedTheme = data.points[0].y;
                    if (clickedTheme) {{
                        drillDownToTheme(clickedTheme);
                    }}
                }});
            }});
        }}

        /* Graph Rendering: Ticker Drilldown */
        function renderTickersGraph(tickers) {{
            if (currentMode !== 'graph') return;
            const container = document.getElementById('main-chart');

            if (!tickers || tickers.length === 0) {{
                Plotly.purge(container);
                container.innerHTML = '<div style="color: var(--text-muted); padding: 40px; text-align: center; font-size: 13px;">No tickers data to display.</div>';
                return;
            }}

            // Reverse for top-down descending visual hierarchy
            const dataToChart = [...tickers].reverse();
            const yNames = dataToChart.map(t => t.UnderlyingSymbol);
            const realized = dataToChart.map(t => t.RealizedPnl);
            const unrealized = dataToChart.map(t => t.UnrealizedPnl);
            const net = dataToChart.map(t => t.TotalFifoPnl);

            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            const textColor = isLight ? '#0f172a' : '#f8fafc';
            const gridColor = isLight ? '#e2e8f0' : '#1e293b';

            const traceRealized = {{
                x: realized,
                y: yNames,
                name: 'Realized PnL',
                type: 'bar',
                orientation: 'h',
                marker: {{
                    color: realized.map(v => v >= 0 ? '#16a34a' : '#dc2626'),
                    opacity: 0.85
                }},
                customdata: dataToChart.map(t => t.Description),
                hovertemplate: '<b>%{{y}}</b> (%{{customdata}})<br>Realized: €%{{x:,.2f}}<extra></extra>'
            }};

            const traceUnrealized = {{
                x: unrealized,
                y: yNames,
                name: 'Unrealized PnL',
                type: 'bar',
                orientation: 'h',
                marker: {{
                    color: unrealized.map(v => v >= 0 ? '#4ade80' : '#f87171'),
                    opacity: 0.75
                }},
                customdata: dataToChart.map(t => t.Description),
                hovertemplate: '<b>%{{y}}</b> (%{{customdata}})<br>Unrealized: €%{{x:,.2f}}<extra></extra>'
            }};

            const traceNet = {{
                x: net,
                y: yNames,
                name: 'Net PnL',
                type: 'scatter',
                mode: 'markers',
                marker: {{
                    symbol: 'diamond',
                    size: 8,
                    color: net.map(v => v >= 0 ? '#10b981' : '#f43f5e'),
                    line: {{ color: isLight ? '#ffffff' : '#0b1120', width: 1 }}
                }},
                customdata: dataToChart.map(t => t.Description),
                hovertemplate: '<b>%{{y}}</b> (%{{customdata}})<br><b>Net PnL: €%{{x:,.2f}}</b><extra></extra>'
            }};

            const layout = {{
                barmode: 'relative',
                autosize: true,
                height: Math.max(480, dataToChart.length * 28 + 100),
                margin: {{ l: 90, r: 35, t: 20, b: 35 }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ family: 'Inter', color: textColor, size: 11 }},
                showlegend: false,
                xaxis: {{
                    gridcolor: gridColor,
                    zerolinecolor: isLight ? '#94a3b8' : '#475569',
                    zerolinewidth: 1.5,
                    tickfont: {{ color: textColor, family: 'JetBrains Mono', size: 10 }},
                    tickprefix: '€',
                    tickformat: ',.0f'
                }},
                yaxis: {{
                    tickfont: {{ color: textColor, family: 'JetBrains Mono', size: 11, weight: 600 }},
                    automargin: true
                }},
                hoverlabel: {{
                    bgcolor: isLight ? '#ffffff' : '#1e293b',
                    bordercolor: isLight ? '#cbd5e1' : '#334155',
                    font: {{ color: textColor, family: 'JetBrains Mono', size: 11 }}
                }}
            }};

            const config = {{
                responsive: true,
                displayModeBar: false
            }};

            Plotly.react(container, [traceRealized, traceUnrealized, traceNet], layout, config).then(() => {{
                if (container.removeAllListeners) {{
                    container.removeAllListeners('plotly_click');
                }}
            }});
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

            if (currentMode === 'graph') {{
                renderDashboard();
            }}
        }}

        /* Master Refresh Function */
        function refreshDataAndViews() {{
            const availableTickers = getFilteredTickers();
            currentThemeList = aggregateThemes(availableTickers);
            updateKpis(availableTickers);

            // If selected theme no longer exists under current filter, reset to overview
            if (drilldownTheme && drilldownTheme !== '__TOTAL__') {{
                const exists = currentThemeList.some(t => t.Theme === drilldownTheme);
                if (!exists) drilldownTheme = null;
            }}

            renderDashboard();
        }}

        // Handle responsive window resize
        let resizeTimer;
        window.addEventListener('resize', () => {{
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {{
                if (currentMode === 'graph') {{
                    const chartDiv = document.getElementById('main-chart');
                    if (chartDiv && chartDiv.data) {{
                        Plotly.Plots.resize('main-chart');
                    }}
                }}
            }}, 120);
        }});

        // Initialization
        window.addEventListener('DOMContentLoaded', () => {{
            initThemeMode();
            refreshDataAndViews();
        }});
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
