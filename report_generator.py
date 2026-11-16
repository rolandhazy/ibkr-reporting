"""HTML report generation and UI serialization."""

import json
import os

import pandas as pd


def generate_html_report(
    data: pd.DataFrame | dict[str, dict],
    output_path: str = "public/index.html",
    period_str: str = "",
    default_slice: str = "ytd",
) -> None:
    """Aggregate portfolio data and output the standalone interactive dashboard HTML with multi-slice support."""
    if isinstance(data, pd.DataFrame):
        slices_input = {
            "ytd": {
                "label": "YTD",
                "title": "Year-to-Date",
                "period": period_str,
                "df": data,
            }
        }
    else:
        slices_input = data

    if default_slice not in slices_input:
        default_slice = next(iter(slices_input.keys())) if slices_input else "ytd"

    slices_payload = {}
    for key, sinfo in slices_input.items():
        df_slice = sinfo["df"]
        ticker_summary = (
            df_slice.groupby(["Theme", "UnderlyingSymbol"])
            .agg(
                Description=("Description", "first"),
                TotalFifoPnl=("TotalFifoPnl", "sum"),
                RealizedPnl=("TotalRealizedPnl", "sum"),
                UnrealizedPnl=("TotalUnrealizedPnl", "sum"),
                Count=("Symbol", "count"),
            )
            .reset_index()
        )

        ticker_summary["Description"] = ticker_summary["Description"].fillna(
            ticker_summary["UnderlyingSymbol"]
        )
        ticker_summary["TotalFifoPnl"] = ticker_summary["TotalFifoPnl"].round(2)
        ticker_summary["RealizedPnl"] = ticker_summary["RealizedPnl"].round(2)
        ticker_summary["UnrealizedPnl"] = ticker_summary["UnrealizedPnl"].round(2)
        ticker_summary["IsActive"] = (
            ticker_summary["UnrealizedPnl"].abs() > 0.001
        ).astype(bool)

        slices_payload[key] = {
            "label": sinfo.get("label", key.upper()),
            "title": sinfo.get("title", key.upper()),
            "period": sinfo.get("period", ""),
            "tickers": ticker_summary.to_dict(orient="records"),
        }

    # Initial metrics from default slice
    default_tickers = slices_payload.get(default_slice, {}).get("tickers", [])
    active_assets_count = sum(1 for t in default_tickers if t.get("IsActive"))
    initial_period = (
        slices_payload.get(default_slice, {}).get("period", "") or period_str
    )

    # Escape '</' so no embedded description can terminate the script block early;
    # the inserted backslash is a valid escape sequence in both JSON and JS strings.
    slices_json = json.dumps(slices_payload).replace("</", "<\\/")

    # Slice switcher buttons HTML
    slice_buttons_html = ""
    for k, s in slices_payload.items():
        active_cls = " active" if k == default_slice else ""
        s_title = s.get("title", "")
        s_label = s.get("label", "")
        slice_buttons_html += f'<button class="slice-btn{active_cls}" data-slice="{k}" onclick="switchTimeSlice(\'{k}\')" title="{s_title}">{s_label}</button>\n'

    slice_switcher_html = (
        f'<div class="slice-switcher" role="tablist" id="time-slice-switcher">\n{slice_buttons_html}</div>'
        if len(slices_payload) > 1
        else ""
    )

    period_badge_html = f'<div class="reporting-period" id="reporting-period-badge" style="{"display: inline-block;" if initial_period else "display: none;"}">{initial_period}</div>'

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

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
            color-scheme: dark;
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
            color-scheme: light;
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
            --color-realized-pos: #15803d;
            --color-realized-neg: #b91c1c;
            --color-unrealized-pos: #0f766e;
            --color-unrealized-neg: #c2410c;
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
            scrollbar-gutter: stable;
            -webkit-font-smoothing: antialiased;
            transition: background 0.2s ease, color 0.2s ease;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 8px 6px;
            }}
        }}

        .container {{
            max-width: 1560px;
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

        .display-controls {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            flex: 0 0 auto;
        }}

        /* Time Slice Segmented Switcher */
        .slice-switcher {{
            display: inline-flex;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 2px;
            gap: 2px;
        }}

        .slice-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            background: transparent;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
            font-family: var(--font-main);
        }}

        .slice-btn:hover {{
            color: var(--text-primary);
            background: var(--ratio-track-bg);
        }}

        .slice-btn.active {{
            background: var(--border-color);
            color: var(--color-accent);
            font-weight: 700;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
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
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                grid-template-areas:
                    "brand controls"
                    "kpi kpi";
                gap: 8px 10px;
                align-items: center;
                min-width: 0;
            }}
            .brand-container {{
                grid-area: brand;
                min-width: 0;
            }}
            .header-right {{
                display: contents;
            }}
            .header-controls {{
                grid-area: controls;
                justify-self: end;
                min-width: 0;
            }}
            .kpi-strip {{
                grid-area: kpi;
                width: 100%;
                min-width: 0;
                grid-template-columns: repeat(4, 1fr);
                gap: 8px 12px;
                padding: 8px 14px;
            }}
        }}

        /* Phone layout: keep global controls paired and compact dashboard rows. */
        @media (max-width: 640px) {{
            html, body {{
                max-width: 100%;
                overflow-x: clip;
            }}
            .container, .card {{
                width: 100%;
                min-width: 0;
            }}
            .header {{
                grid-template-columns: minmax(0, 1fr);
                grid-template-areas:
                    "brand"
                    "controls"
                    "kpi";
                align-items: stretch;
            }}
            .header-controls {{
                width: 100%;
                justify-self: stretch;
                flex-wrap: wrap;
                row-gap: 6px;
            }}
            .display-controls {{
                flex-wrap: nowrap;
                margin-left: auto;
            }}
            .slice-switcher {{
                flex: 0 0 auto;
                width: max-content;
            }}
            .slice-btn {{
                flex: 0 0 auto;
            }}
            .filter-toggle, .header-btn {{
                flex: 0 0 auto;
            }}
            .reporting-period {{
                max-width: 100%;
                overflow-wrap: anywhere;
            }}
            .card-header {{
                grid-template-columns: minmax(0, 1fr);
                gap: 8px;
                padding: 8px;
            }}
            .breadcrumb-nav {{
                min-width: 0;
            }}
            .card-search-box {{
                grid-row: 2;
                max-width: none;
                justify-self: stretch;
            }}
            .toolbar {{
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
                align-items: center;
                padding: 8px;
                gap: 7px;
            }}
            .toolbar-right {{
                display: contents;
            }}
            .pnl-threshold-control {{
                grid-column: 1;
                justify-self: start;
                flex-wrap: nowrap;
                gap: 3px;
                min-width: 0;
            }}
            .pnl-threshold-label {{
                font-size: 9px;
                letter-spacing: 0;
            }}
            .threshold-mode-group {{
                gap: 0;
                padding: 1px;
            }}
            .threshold-mode-btn {{
                min-width: 22px;
                min-height: 25px;
                padding: 2px 5px;
            }}
            .toolbar-number-input {{
                width: clamp(48px, 17vw, 72px);
                min-width: 0;
                padding: 4px 4px;
                font-size: 10px;
            }}
            .sort-control {{
                grid-column: 2;
                justify-self: stretch;
                min-width: 0;
                gap: 3px;
            }}
            .sort-label {{
                display: none;
            }}
            .sort-control {{
                justify-self: end;
                width: max-content;
                max-width: 100%;
            }}
            .sort-btn-group {{
                display: none;
            }}
            .sort-mobile-control {{
                display: inline-flex;
                align-items: center;
                min-width: 0;
                background: var(--input-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 2px;
                gap: 2px;
            }}
            .sort-mobile-select {{
                appearance: none;
                min-width: 0;
                max-width: 112px;
                border: 0;
                border-radius: 6px;
                padding: 5px 18px 5px 7px;
                color: var(--color-accent);
                background: var(--border-color);
                font: 700 10px var(--font-main);
                cursor: pointer;
                background-image: linear-gradient(45deg, transparent 50%, currentColor 50%), linear-gradient(135deg, currentColor 50%, transparent 50%);
                background-position: calc(100% - 8px) 50%, calc(100% - 5px) 50%;
                background-size: 3px 3px, 3px 3px;
                background-repeat: no-repeat;
            }}
            .sort-direction-btn {{
                min-width: 28px;
                min-height: 28px;
                border: 0;
                border-radius: 6px;
                background: transparent;
                color: var(--text-secondary);
                font: 700 12px var(--font-main);
                cursor: pointer;
            }}
            .sort-direction-btn:hover {{
                color: var(--color-accent);
                background: var(--ratio-track-bg);
            }}
            .sort-direction-btn:focus-visible,
            .sort-mobile-select:focus-visible {{
                outline: 2px solid var(--color-accent);
                outline-offset: 1px;
            }}
            .performer-highlights {{
                grid-column: 1 / -1;
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 6px;
                min-width: 0;
            }}
            .performer-badge {{
                min-width: 0;
                max-width: 100%;
                overflow: hidden;
                gap: 3px;
                padding: 3px 5px;
                font-size: 9px;
            }}
            .performer-badge strong,
            .performer-badge .performer-label,
            .performer-badge .performer-value {{
                min-width: 0;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .performer-badge strong {{
                flex: 0 1 auto;
            }}
            .performer-badge .performer-value {{
                flex: 0 1 auto;
                white-space: nowrap;
            }}
        }}

        @media (max-width: 380px) {{
            .header-controls {{
                gap: 5px;
            }}
            .slice-btn {{
                padding-left: 6px;
                padding-right: 6px;
            }}
            .filter-toggle-pill {{
                gap: 4px;
                padding: 5px 7px;
            }}
            .header-btn {{
                padding: 5px 7px;
            }}
            .pnl-threshold-label {{
                font-size: 8px;
            }}
            .toolbar-number-input {{
                width: 48px;
            }}
            .performer-highlights {{
                gap: 4px;
            }}
        }}

        @media (max-width: 640px) {{
            .kpi-strip {{
                grid-template-columns: repeat(4, 1fr);
                gap: 4px 6px;
                padding: 6px 8px;
                border-radius: 8px;
            }}
            .kpi-item {{
                min-width: 0;
            }}
            .kpi-label {{
                font-size: 8.5px !important;
                letter-spacing: 0.01em !important;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .kpi-val {{
                font-size: 11.5px !important;
                letter-spacing: -0.02em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
        }}

        @media (max-width: 400px) {{
            .kpi-strip {{
                gap: 2px 4px;
                padding: 5px 6px;
            }}
            .kpi-label {{
                font-size: 8px !important;
            }}
            .kpi-val {{
                font-size: 10.5px !important;
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
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }}

        .kpi-error {{
            grid-column: 1 / -1;
            padding: 7px 10px;
            border: 1px solid var(--color-negative);
            border-radius: 6px;
            background: var(--color-negative-bg);
            color: var(--color-negative);
            font-size: 12px;
        }}

        .kpi-error[hidden] {{
            display: none !important;
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
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(180px, 320px);
            align-items: center;
            gap: 10px;
        }}

        .card-search-box {{
            width: 100%;
            max-width: 320px;
            justify-self: end;
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

        .show-all-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--color-accent);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            white-space: nowrap;
        }}

        .show-all-btn:hover, .show-all-btn[aria-pressed="true"] {{
            background: var(--color-accent-bg);
            border-color: var(--color-accent);
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

        @media (max-width: 600px) {{
            .view-btn-label {{
                display: none;
            }}
            .view-btn {{
                justify-content: center;
                min-width: 34px;
                padding: 6px 9px;
            }}
        }}

        /* Secondary Toolbar: Ticker Search & Highlights */
        .toolbar {{
            display: flex;
            justify-content: flex-start;
            align-items: center;
            padding: 8px 14px;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-subtle);
            flex-wrap: wrap;
            gap: 10px;
            min-width: 0;
        }}

        .ticker-search-box {{
            display: flex;
            align-items: center;
            position: relative;
            flex: 0 1 320px;
            max-width: 320px;
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
            justify-content: flex-end;
            gap: 10px 12px;
            flex: 1 1 440px;
            flex-wrap: wrap;
            min-width: 0;
            max-width: 100%;
        }}

        .pnl-threshold-control {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            flex-wrap: wrap;
            min-width: 0;
        }}

        .pnl-threshold-label {{
            color: var(--text-muted);
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            white-space: nowrap;
        }}

        .toolbar-number-input {{
            min-height: 29px;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            font: 11px var(--font-main);
            padding: 4px 7px;
        }}

        .toolbar-number-input:focus {{
            outline: none;
            border-color: var(--color-accent);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
        }}

        .threshold-mode-group {{
            display: inline-flex;
            align-items: center;
            gap: 2px;
            padding: 2px;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 7px;
        }}

        .threshold-mode-btn {{
            min-height: 25px;
            border: 0;
            border-radius: 5px;
            padding: 3px 8px;
            background: transparent;
            color: var(--text-secondary);
            font: 600 11px var(--font-main);
            cursor: pointer;
        }}

        .threshold-mode-btn:hover {{
            color: var(--text-primary);
            background: var(--ratio-track-bg);
        }}

        .threshold-mode-btn.active {{
            background: var(--border-color);
            color: var(--color-accent);
        }}

        .pnl-threshold-control:not(.enabled) .toolbar-number-input {{
            color: var(--text-muted);
            background: var(--bg-card-header);
            border-color: var(--border-color);
        }}

        .threshold-mode-btn:focus-visible {{
            outline: 2px solid var(--color-accent);
            outline-offset: 1px;
        }}

        .toolbar-number-input {{
            width: 92px;
            font-family: var(--font-mono);
            font-variant-numeric: tabular-nums;
        }}

        .toolbar-eur-suffix {{
            color: var(--text-muted);
            font-size: 10px;
        }}

        /* Sort Controls */
        .sort-control {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        .sort-label {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .sort-btn-group {{
            display: inline-flex;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 2px;
            gap: 2px;
        }}

        .sort-pill-btn {{
            display: inline-flex;
            align-items: center;
            gap: 3px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            background: transparent;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
            font-family: var(--font-main);
        }}

        .sort-pill-btn:hover {{
            color: var(--text-primary);
            background: var(--ratio-track-bg);
        }}

        .sort-pill-btn.active {{
            background: var(--border-color);
            color: var(--color-accent);
            font-weight: 700;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
        }}

        .sort-short-label {{
            display: none;
        }}

        .sort-mobile-control {{
            display: none;
        }}

        .sort-arrow {{
            font-size: 9px;
            line-height: 1;
        }}

        .sortable-th {{
            cursor: pointer;
            user-select: none;
            transition: color 0.15s ease;
        }}

        .sortable-th:hover {{
            color: var(--color-accent);
        }}

        .sort-indicator {{
            display: inline-block;
            margin-left: 4px;
            font-size: 9px;
            color: var(--text-muted);
            opacity: 0.4;
        }}

        .sort-indicator.active {{
            color: var(--color-accent);
            opacity: 1;
            font-weight: 700;
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

        /* Final responsive overrides follow base component rules intentionally. */
        @media (max-width: 640px) {{
            .card-header {{
                grid-template-columns: minmax(0, 1fr) minmax(110px, 1fr);
                gap: 6px;
                padding: 8px;
            }}
            .breadcrumb-nav {{
                min-width: 0;
                flex-wrap: nowrap;
                gap: 5px;
            }}
            .breadcrumb-title {{
                min-width: 0;
                font-size: 12px;
                white-space: nowrap;
            }}
            .btn-drilldown-back,
            .show-all-btn {{
                flex: 0 0 auto;
                padding: 3px 6px;
                font-size: 9px;
            }}
            .card-search-box {{
                grid-row: auto;
                width: 100%;
                max-width: none;
                min-width: 0;
                justify-self: stretch;
            }}
            .card-search-box input {{
                min-width: 0;
                padding: 6px 24px 6px 7px;
                font-size: 10px;
            }}
            .toolbar {{
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
                align-items: center;
                padding: 8px;
                gap: 7px;
            }}
            .toolbar-right {{
                display: contents;
            }}
            .pnl-threshold-control {{
                grid-column: 1;
                justify-self: start;
                flex-wrap: nowrap;
                gap: 3px;
                min-width: 0;
            }}
            .sort-control {{
                grid-column: 2;
                justify-self: stretch;
                min-width: 0;
                gap: 3px;
            }}
            .performer-highlights {{
                grid-column: 1 / -1;
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 6px;
                min-width: 0;
            }}
        }}

        @media (max-width: 430px) {{
            .card-header {{
                grid-template-columns: minmax(0, 1fr);
                gap: 6px;
                padding: 7px;
            }}
            .card-search-box {{
                grid-row: 2;
            }}
            .breadcrumb-nav {{
                gap: 3px;
            }}
            .breadcrumb-title {{
                font-size: 11px;
            }}
            .btn-drilldown-back,
            .show-all-btn {{
                padding: 3px 4px;
                font-size: 8px;
            }}
            .card-search-box input {{
                font-size: 9px;
                padding-left: 5px;
            }}
        }}

        /* Fully Responsive Table Design */
        .table-container {{
            /* Use page scrolling instead of nested scrolling to prevent row/header paint overlap. */
            max-height: none;
            overflow: visible;
            position: static;
            width: 100%;
        }}

        table {{
            width: 100%;
            min-width: 100%;
            table-layout: fixed;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 12px;
        }}

        thead th {{
            position: static;
            background: var(--bg-card-header);
            color: var(--text-secondary);
            font-weight: 600;
            text-align: left;
            padding: 9px 12px;
            border-bottom: 1px solid var(--border-color);
            z-index: 20;
            background-color: var(--bg-card-header);
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
            width: 32%;
            min-width: 140px;
        }}

        .col-assets {{
            width: 12%;
            min-width: 65px;
            text-align: center;
        }}

        .col-ticker {{
            width: 14%;
            min-width: 85px;
        }}

        .col-desc {{
            width: 32%;
            min-width: 120px;
        }}

        .col-theme-tag {{
            width: 14%;
            min-width: 95px;
        }}

        .col-realized, .col-unrealized {{
            width: 18%;
            min-width: 95px;
        }}

        .col-pnl {{
            width: 20%;
            min-width: 130px;
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
            font-variant-numeric: tabular-nums;
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
            width: 72px;
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
            position: static;
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

        @media (max-width: 640px) {{
            .chart-view-panel {{
                padding: 6px 4px 10px 4px;
            }}
            .chart-legend {{
                font-size: 10px !important;
                padding: 2px 4px !important;
                gap: 4px 8px !important;
            }}
            .chart-click-hint {{
                font-size: 10px !important;
            }}
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
            background: linear-gradient(90deg, var(--color-realized-pos) 50%, var(--color-realized-neg) 50%);
        }}

        .legend-swatch.unrealized-swatch {{
            background: linear-gradient(90deg, var(--color-unrealized-pos) 50%, var(--color-unrealized-neg) 50%);
        }}

        .legend-diamond {{
            color: var(--color-positive);
            font-size: 11px;
            line-height: 1;
        }}

        .chart-wrapper {{
            width: 100%;
            min-height: 0;
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

        /* Modern Standard Scrollbars & WebKit Fallback */
        * {{
            scrollbar-color: var(--border-color) var(--bg-card);
            scrollbar-width: thin;
        }}
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

        @media (prefers-reduced-motion: reduce) {{
            *, ::before, ::after {{
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
                scroll-behavior: auto !important;
            }}
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
                    <!-- Time Slice Segmented Switcher -->
                    {slice_switcher_html}

                    <!-- Global Filter Toggle Switch -->
                    <label class="filter-toggle" title="Filter dashboard to show only currently open / active positions">
                        <input type="checkbox" id="active-filter-checkbox" onchange="toggleActiveFilter(this.checked)">
                        <span class="filter-toggle-pill">
                            <span class="filter-dot"></span>
                            <span>Active</span>
                            <span class="active-count-tag" id="active-count-tag">{active_assets_count}</span>
                        </span>
                    </label>

                    <div class="display-controls">
                        <!-- Light / Dark Mode Toggle Button -->
                        <button id="theme-toggle-btn" class="header-btn" onclick="toggleThemeMode()" title="Toggle Light / Dark mode" aria-label="Toggle theme">
                            <span id="theme-toggle-icon">☀️</span>
                            <span id="theme-toggle-label" class="col-hide-mobile">Light</span>
                        </button>

                        <!-- Segmented View Switcher: Table vs Graph -->
                        <div class="view-switcher" role="tablist" aria-label="Dashboard display">
                        <button id="view-btn-table" class="view-btn active" onclick="switchView('table')" title="Switch to Table View" aria-label="Switch to Table View">
                            <span class="view-btn-icon" aria-hidden="true">☷</span>
                            <span class="view-btn-label">Table</span>
                        </button>
                        <button id="view-btn-graph" class="view-btn" onclick="switchView('graph')" title="Switch to Graph View" aria-label="Switch to Graph View">
                            <span class="view-btn-icon" aria-hidden="true">📊</span>
                            <span class="view-btn-label">Graph</span>
                        </button>
                        </div>
                    </div>
                </div>

                <!-- KPI Strip -->
                <div class="kpi-strip">
                    <div class="kpi-item">
                        <span class="kpi-label">Net FIFO PnL</span>
                        <span class="kpi-val" id="kpi-net-pnl">—</span>
                    </div>
                    <div class="kpi-item">
                        <span class="kpi-label">Realized</span>
                        <span class="kpi-val" id="kpi-realized-pnl">—</span>
                    </div>
                    <div class="kpi-item">
                        <span class="kpi-label">Unrealized</span>
                        <span class="kpi-val" id="kpi-unrealized-pnl">—</span>
                    </div>
                    <div class="kpi-item">
                        <span class="kpi-label">Holdings</span>
                        <span class="kpi-val" id="kpi-holdings-count" style="color: var(--color-accent);">—</span>
                    </div>
                    <div id="kpi-error" class="kpi-error" role="alert" aria-live="assertive" hidden>
                        Report data could not be initialized. Please reload the report.
                    </div>
                </div>
            </div>
        </header>

        <!-- Unified Single-View Dashboard Container -->
        <main class="card" id="dashboard-card">
            <!-- Card Header: Breadcrumbs / Title -->
            <div class="card-header">
                <div class="breadcrumb-nav">
                    <button id="btn-back-to-themes" class="btn-drilldown-back" onclick="drillUpToThemes()" style="display: none;" title="Return to Themes overview">
                        ← Themes
                    </button>
                    <div class="breadcrumb-title" id="current-view-title">
                        <span>Themes</span>
                    </div>
                    <button id="show-all-tickers-btn" class="show-all-btn" type="button"
                        aria-label="Show all tickers across themes"
                        onclick="toggleShowAllTickers()">All tickers</button>
                </div>
                <div class="ticker-search-box card-search-box">
                    <input id="ticker-search" type="search" placeholder="Ticker/company/theme; -term excludes" title="Search ticker, description, or theme. Separate terms with spaces or commas; prefix a term with minus to exclude it." enterkeyhint="search" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" role="searchbox" aria-label="Search ticker, description, or theme. Separate terms with spaces or commas; prefix a term with minus to exclude it." oninput="handleTickerSearch(this.value)">
                    <button id="search-clear-btn" class="search-clear-btn" onclick="clearTickerSearch()" title="Clear search" aria-label="Clear search">✕</button>
                </div>
            </div>

            <!-- Toolbar: PnL threshold, sorting & performer highlights -->
            <div class="toolbar">
                <div class="toolbar-right">
                    <div class="pnl-threshold-control" title="Show rows where the absolute value of Net FIFO PnL matches the selected comparison">
                        <span class="pnl-threshold-label" id="pnl-threshold-label">|Net|</span>
                        <div class="threshold-mode-group" role="group" aria-labelledby="pnl-threshold-label">
                            <button id="pnl-threshold-mode-lt" class="threshold-mode-btn" type="button" aria-label="Show rows where absolute Net PnL is less than the amount" aria-pressed="false" onclick="setPnlThresholdMode('lt')">&lt;</button>
                            <button id="pnl-threshold-mode-gt" class="threshold-mode-btn" type="button" aria-label="Show rows where absolute Net PnL is greater than the amount" aria-pressed="false" onclick="setPnlThresholdMode('gt')">&gt;</button>
                        </div>
                        <input id="pnl-threshold-amount" class="toolbar-number-input" type="number" min="0" step="0.01" inputmode="decimal" value="1000" aria-label="Absolute Net PnL threshold amount in euros (EUR); choose a comparison to enable filtering" oninput="handlePnlThresholdChange()">
                    </div>

                    <!-- Global Sort Control (operates across Table and Graph views) -->
                    <div class="sort-control" title="Sort themes and tickers by metric">
                        <span class="sort-label">Sort:</span>
                        <div class="sort-btn-group" role="tablist">
                            <button id="sort-btn-pnl" class="sort-pill-btn active" onclick="setSort('pnl')" title="Sort by Net FIFO PnL">
                                <span class="sort-full-label">Net PnL</span><span class="sort-short-label">Net</span> <span id="sort-icon-pnl" class="sort-arrow">▼</span>
                            </button>
                            <button id="sort-btn-realized" class="sort-pill-btn" onclick="setSort('realized')" title="Sort by Realized PnL">
                                <span class="sort-full-label">Realized</span><span class="sort-short-label">Real</span> <span id="sort-icon-realized" class="sort-arrow"></span>
                            </button>
                            <button id="sort-btn-unrealized" class="sort-pill-btn" onclick="setSort('unrealized')" title="Sort by Unrealized PnL">
                                <span class="sort-full-label">Unrealized</span><span class="sort-short-label">Unreal</span> <span id="sort-icon-unrealized" class="sort-arrow"></span>
                            </button>
                        </div>
                        <div class="sort-mobile-control" aria-label="Sort options">
                            <select id="sort-mobile-select" class="sort-mobile-select" aria-label="Sort metric" onchange="setSortMetric(this.value)">
                                <option value="pnl">Net PnL</option>
                                <option value="realized">Realized</option>
                                <option value="unrealized">Unrealized</option>
                            </select>
                            <button id="sort-direction-btn" class="sort-direction-btn" type="button" aria-label="Change sort direction; currently descending" title="Reverse sort direction" onclick="toggleSortDirection()">▼</button>
                        </div>
                    </div>

                    <div class="performer-highlights" id="performer-highlights">
                        <!-- Populated dynamically: Best / Worst -->
                    </div>
                </div>
            </div>

            <!-- Viewport 1: Table View -->
            <div id="table-view-container" class="table-container" role="region" aria-label="Portfolio performance table">
                <table id="main-table">
                    <thead id="table-head">
                        <!-- Rendered dynamically depending on level (Themes vs Tickers) -->
                    </thead>
                    <tbody id="table-body">
                        <!-- Rendered dynamically -->
                    </tbody>
                    <tfoot id="table-foot"></tfoot>
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
        // Multi-slice data passed from Python
        const TIME_SLICES = {slices_json};
        let activeTimeSlice = '{default_slice}';

        // Dynamic ticker dataset pointer for current time slice
        let TICKER_DATA = TIME_SLICES[activeTimeSlice] ? TIME_SLICES[activeTimeSlice].tickers : [];

        function switchTimeSlice(sliceKey) {{
            if (!TIME_SLICES[sliceKey]) return;
            activeTimeSlice = sliceKey;

            // Update segmented button UI
            document.querySelectorAll('.slice-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.getAttribute('data-slice') === sliceKey);
            }});

            // Switch active dataset
            TICKER_DATA = TIME_SLICES[sliceKey].tickers;

            // Update reporting period badge
            const badge = document.getElementById('reporting-period-badge');
            if (badge) {{
                const p = TIME_SLICES[sliceKey].period;
                badge.innerText = p ? p : '';
                badge.style.display = p ? 'inline-block' : 'none';
            }}

            refreshDataAndViews();
        }}

        // Application State
        let currentMode = 'table';         // 'table' | 'graph'
        let drilldownTheme = null;         // null (All Themes) | string (Theme Name)
        let showAllTickers = false;        // Toggle between grouped themes and all ticker rows
        let tickerSearchQuery = '';        // Active search filter for tickers
        let pnlThresholdMode = null;          // No comparison until the user selects 'gt' or 'lt'
        let pnlThresholdActive = false;       // Activated by choosing either comparison mode
        let showActiveOnly = false;        // Toggle active/open positions only
        let currentThemeList = [];         // Aggregated themes list
        let currentSelection = null;         // Canonical filtered dashboard result
        let sortColumn = 'pnl';            // 'pnl' | 'realized' | 'unrealized'
        let sortDirection = 'desc';        // 'desc' | 'asc'

        function setSort(col) {{
            if (sortColumn === col) {{
                toggleSortDirection();
                return;
            }}
            setSortMetric(col);
        }}

        function setSortMetric(col) {{
            if (!['pnl', 'realized', 'unrealized'].includes(col)) return;
            if (sortColumn !== col) {{
                sortColumn = col;
                sortDirection = 'desc';
            }}
            updateSortControls();
            refreshDataAndViews();
        }}

        function toggleSortDirection() {{
            sortDirection = sortDirection === 'desc' ? 'asc' : 'desc';
            updateSortControls();
            refreshDataAndViews();
        }}

        function updateSortControls() {{
            ['pnl', 'realized', 'unrealized'].forEach(col => {{
                const btn = document.getElementById(`sort-btn-${{col}}`);
                const icon = document.getElementById(`sort-icon-${{col}}`);
                const isActive = sortColumn === col;
                if (btn) btn.classList.toggle('active', isActive);
                if (icon) icon.textContent = isActive ? (sortDirection === 'asc' ? '▲' : '▼') : '';
            }});
            const mobileSelect = document.getElementById('sort-mobile-select');
            if (mobileSelect) mobileSelect.value = sortColumn;
            const directionButton = document.getElementById('sort-direction-btn');
            if (directionButton) {{
                const ascending = sortDirection === 'asc';
                directionButton.textContent = ascending ? '▲' : '▼';
                directionButton.setAttribute('aria-label', `Change sort direction; currently ${{ascending ? 'ascending' : 'descending'}}`);
                directionButton.title = `Reverse sort direction (currently ${{ascending ? 'ascending' : 'descending'}})`;
            }}
        }}

        function getSortIndicator(col) {{
            if (sortColumn === col) {{
                return `<span class="sort-indicator active">${{sortDirection === 'asc' ? '▲' : '▼'}}</span>`;
            }}
            return `<span class="sort-indicator">↕</span>`;
        }}

        function getAriaSort(col) {{
            if (sortColumn === col) {{
                return sortDirection === 'asc' ? 'ascending' : 'descending';
            }}
            return 'none';
        }}

        function sortItems(items) {{
            const mult = sortDirection === 'asc' ? 1 : -1;
            return [...items].sort((a, b) => {{
                let valA = 0;
                let valB = 0;
                if (sortColumn === 'realized') {{
                    valA = a.RealizedPnl || 0;
                    valB = b.RealizedPnl || 0;
                }} else if (sortColumn === 'unrealized') {{
                    valA = a.UnrealizedPnl || 0;
                    valB = b.UnrealizedPnl || 0;
                }} else {{
                    valA = a.TotalFifoPnl || 0;
                    valB = b.TotalFifoPnl || 0;
                }}
                return (valA - valB) * mult;
            }});
        }}

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
            if (showActiveOnly) return TICKER_DATA.filter(t => t.IsActive);
            return TICKER_DATA;
        }}

        function parseSearchQuery(query) {{
            const tokens = String(query || '').split(/[\\s,]+/).filter(Boolean);
            const include = [];
            const exclude = [];

            tokens.forEach(token => {{
                if (token === '-') return;
                if (token.startsWith('-')) {{
                    const term = token.slice(1).toLocaleLowerCase();
                    if (term) exclude.push(term);
                }} else {{
                    include.push(token.toLocaleLowerCase());
                }}
            }});
            return {{ include, exclude }};
        }}

        function matchesSearch(record, terms) {{
            const fields = [record.UnderlyingSymbol, record.Description, record.Theme]
                .map(value => String(value || '').toLocaleLowerCase());
            const matchesTerm = term => fields.some(field => field.includes(term));
            if (terms.exclude.some(matchesTerm)) return false;
            return terms.include.length === 0 || terms.include.some(matchesTerm);
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
                        LosingAssets: 0,
                        Tickers: []
                    }});
                }}
                const item = map.get(t.Theme);
                item.TotalFifoPnl += Number(t.TotalFifoPnl) || 0;
                item.RealizedPnl += Number(t.RealizedPnl) || 0;
                item.UnrealizedPnl += Number(t.UnrealizedPnl) || 0;
                item.AssetCount += 1;
                item.Tickers.push(t);
                if (t.TotalFifoPnl > 0) item.WinningAssets += 1;
                else if (t.TotalFifoPnl < 0) item.LosingAssets += 1;
            }});

            return Array.from(map.values()).map(item => ({{
                ...item,
                TotalFifoPnl: Math.round(item.TotalFifoPnl * 100) / 100,
                RealizedPnl: Math.round(item.RealizedPnl * 100) / 100,
                UnrealizedPnl: Math.round(item.UnrealizedPnl * 100) / 100
            }}));
        }}

        // Invalid, incomplete, or negative amounts disable the threshold instead of
        // leaving stale filter state active. Zero is a valid threshold.
        function normalizePnlThreshold(mode, amountValue, inputValid = true) {{
            if (!inputValid || amountValue === null || amountValue === undefined
                || String(amountValue).trim() === '') return null;
            const amountEUR = Number(amountValue);
            if (!Number.isFinite(amountEUR) || amountEUR < 0) return null;
            return {{ mode: mode === 'lt' ? 'lt' : 'gt', amountEUR }};
        }}

        // Pure selection/aggregation step: no DOM access and no input mutation.
        function selectDashboardData({{ tickers, activeOnly, scope, searchQuery, pnlThreshold = null }}) {{
            if (pnlThreshold) {{
                pnlThreshold = normalizePnlThreshold(
                    pnlThreshold.mode, pnlThreshold.amountEUR, pnlThreshold.inputValid !== false
                );
            }}
            const terms = parseSearchQuery(searchQuery);
            let eligibleTickers = [...(tickers || [])];

            // 1. Active-only filter.
            if (activeOnly) eligibleTickers = eligibleTickers.filter(t => Boolean(t.IsActive));

            // 2. View scope.
            if (scope.type === 'theme') {{
                eligibleTickers = eligibleTickers.filter(t => t.Theme === scope.theme);
            }}

            // 3. Search ticker, description, and theme.
            eligibleTickers = eligibleTickers.filter(t => matchesSearch(t, terms));

            // 4. Aggregate only in overview; detail views keep ticker rows.
            const displayRows = scope.type === 'overview'
                ? aggregateThemes(eligibleTickers)
                : [...eligibleTickers];

            // 5. Optional strict absolute-Net-PnL threshold on displayed rows.
            const visibleRows = pnlThreshold
                ? displayRows.filter(row => {{
                    const amount = Math.abs(Number(row.TotalFifoPnl) || 0);
                    return pnlThreshold.mode === 'gt'
                        ? amount > Number(pnlThreshold.amountEUR)
                        : amount < Number(pnlThreshold.amountEUR);
                }})
                : displayRows;

            // Overview rows represent all eligible ticker summaries in each retained theme.
            const representedTickers = scope.type === 'overview'
                ? visibleRows.flatMap(row => row.Tickers)
                : visibleRows;
            const sum = field => Math.round(representedTickers.reduce(
                (total, ticker) => total + (Number(ticker[field]) || 0), 0
            ) * 100) / 100;

            // Highlights describe visible display rows: themes in overview, tickers in detail.
            const sortedHighlightRows = [...visibleRows].sort(
                (a, b) => (Number(b.TotalFifoPnl) || 0) - (Number(a.TotalFifoPnl) || 0)
            );
            const bestCandidate = sortedHighlightRows[0] || null;
            const worstCandidate = sortedHighlightRows[sortedHighlightRows.length - 1] || null;
            const highlights = {{
                isTheme: scope.type === 'overview',
                best: bestCandidate && Number(bestCandidate.TotalFifoPnl) > 0 ? bestCandidate : null,
                worst: worstCandidate && Number(worstCandidate.TotalFifoPnl) < 0
                    && worstCandidate !== bestCandidate
                    ? worstCandidate
                    : null
            }};
            const graphData = visibleRows.map(row => ({{
                Theme: row.Theme || null,
                UnderlyingSymbol: row.UnderlyingSymbol || null,
                Description: row.Description || '',
                TotalFifoPnl: Number(row.TotalFifoPnl) || 0,
                RealizedPnl: Number(row.RealizedPnl) || 0,
                UnrealizedPnl: Number(row.UnrealizedPnl) || 0
            }}));

            return {{
                eligibleTickers,
                displayRows,
                visibleRows,
                representedTickers,
                kpis: {{
                    netFifoPnl: sum('TotalFifoPnl'),
                    realizedPnl: sum('RealizedPnl'),
                    unrealizedPnl: sum('UnrealizedPnl'),
                    holdings: new Set(representedTickers.map(t => t.UnderlyingSymbol)).size
                }},
                highlights,
                graphData
            }};
        }}

        function updateKpis(selection) {{
            const kpis = selection.kpis;
            const totalPnl = kpis.netFifoPnl;
            const totalRealized = kpis.realizedPnl;
            const totalUnrealized = kpis.unrealizedPnl;
            const totalHoldings = kpis.holdings;

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
            countEl.innerText = `${{totalHoldings}}`;
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

            // Graph sizing is handled after each Plotly render completes.
        }}

        /* Drill-down Navigation Functions */
        function drillDownToTheme(themeName) {{
            drilldownTheme = themeName;
            renderDashboard();
        }}

        function toggleShowAllTickers() {{
            showAllTickers = !showAllTickers;
            drilldownTheme = null;
            renderDashboard();
        }}

        function drillUpToThemes() {{
            showAllTickers = false;
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

        function syncPnlThresholdModeButtons() {{
            ['gt', 'lt'].forEach(mode => {{
                const button = document.getElementById(`pnl-threshold-mode-${{mode}}`);
                if (!button) return;
                const selected = pnlThresholdActive && pnlThresholdMode === mode;
                button.classList.toggle('active', selected);
                button.setAttribute('aria-pressed', String(selected));
            }});
            const control = document.querySelector('.pnl-threshold-control');
            if (control) control.classList.toggle('enabled', pnlThresholdActive);
        }}

        function setPnlThresholdMode(mode) {{
            if (mode !== 'lt' && mode !== 'gt') return;
            if (pnlThresholdActive && pnlThresholdMode === mode) {{
                pnlThresholdMode = null;
                pnlThresholdActive = false;
            }} else {{
                pnlThresholdMode = mode;
                pnlThresholdActive = true;
            }}
            syncPnlThresholdModeButtons();
            renderDashboard();
        }}

        function handlePnlThresholdChange() {{
            const amountInput = document.getElementById('pnl-threshold-amount');
            if (amountInput) {{
                const valueIsEmpty = amountInput.value.trim() === '';
                amountInput.setAttribute('aria-invalid', String(
                    !valueIsEmpty && (!amountInput.validity.valid
                        || normalizePnlThreshold(pnlThresholdMode, amountInput.value) === null)
                ));
            }}
            renderDashboard();
        }}

        function getPnlThreshold() {{
            const amountInput = document.getElementById('pnl-threshold-amount');
            if (!pnlThresholdActive || !pnlThresholdMode || !amountInput) return null;
            return normalizePnlThreshold(
                pnlThresholdMode,
                amountInput.value,
                amountInput.value.trim() === '' || amountInput.validity.valid
            );
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
        function renderPerformerHighlights(selection) {{
            const highlights = selection.highlights;
            const container = document.getElementById('performer-highlights');
            if (!highlights || (!highlights.best && !highlights.worst)) {{
                container.innerHTML = '';
                return;
            }}

            let html = '';
            const labelFor = row => highlights.isTheme ? row.Theme : row.UnderlyingSymbol;
            if (highlights.best) {{
                const best = highlights.best;
                html += `
                    <div class="performer-badge best" title="${{escapeHtml(best.Description || best.Theme || '')}}">
                        <span class="performer-label">Best:</span>
                        <strong>${{escapeHtml(labelFor(best))}}</strong>
                        <span class="performer-value">(${{formatCurrency(best.TotalFifoPnl)}})</span>
                    </div>
                `;
            }}

            if (highlights.worst) {{
                const worst = highlights.worst;
                html += `
                    <div class="performer-badge worst" title="${{escapeHtml(worst.Description || worst.Theme || '')}}">
                        <span class="performer-label">Worst:</span>
                        <strong>${{escapeHtml(labelFor(worst))}}</strong>
                        <span class="performer-value">(${{formatCurrency(worst.TotalFifoPnl)}})</span>
                    </div>
                `;
            }}

            container.innerHTML = html;
        }}

        /* Master Render Controller */
        function renderDashboard() {{
            const tableContainer = document.getElementById('table-view-container');
            if (tableContainer) tableContainer.scrollTop = 0;
            const scope = showAllTickers
                ? {{ type: 'portfolio' }}
                : drilldownTheme
                    ? {{ type: 'theme', theme: drilldownTheme }}
                    : {{ type: 'overview' }};
            currentSelection = selectDashboardData({{
                tickers: TICKER_DATA,
                activeOnly: showActiveOnly,
                scope,
                searchQuery: tickerSearchQuery,
                pnlThreshold: getPnlThreshold()
            }});
            const selection = currentSelection;
            updateKpis(selection);
            renderPerformerHighlights(selection);

            const backBtn = document.getElementById('btn-back-to-themes');
            const titleEl = document.getElementById('current-view-title');
            const clickHint = document.getElementById('chart-click-hint');

            const showAllButton = document.getElementById('show-all-tickers-btn');
            if (scope.type === 'overview') {{
                backBtn.style.display = 'none';
                if (showAllButton) showAllButton.style.display = 'inline-flex';
                titleEl.innerHTML = `<span>Themes</span>`;
                clickHint.style.display = 'inline-flex';

                if (currentMode === 'table') renderThemesTable(selection);
                else renderThemesGraph(selection);
                return;
            }}

            backBtn.style.display = 'inline-flex';
            if (showAllButton) showAllButton.style.display = scope.type === 'portfolio' ? 'none' : 'inline-flex';
            clickHint.style.display = 'none';
            if (scope.type === 'portfolio') {{
                titleEl.innerHTML = `<span>All tickers</span>`;
                if (currentMode === 'table') renderTickersTable(selection, true);
                else renderTickersGraph(selection);
            }} else {{
                titleEl.innerHTML = `<span>${{escapeHtml(drilldownTheme)}}</span>`;
                if (currentMode === 'table') renderTickersTable(selection, false);
                else renderTickersGraph(selection);
            }}
        }}

        /* Table Rendering: Themes Overview */
        function renderThemesTable(selection) {{
            const themeRows = sortItems(selection.visibleRows);
            const thead = document.getElementById('table-head');
            const tbody = document.getElementById('table-body');
            const tfoot = document.getElementById('table-foot');

            thead.innerHTML = `
                <tr>
                    <th class="col-theme">Theme</th>
                    <th class="col-assets" style="text-align:center;">Assets</th>
                    <th class="num col-hide-mobile col-realized sortable-th" onclick="setSort('realized')" aria-sort="${{getAriaSort('realized')}}" title="Sort by Realized PnL">Realized ${{getSortIndicator('realized')}}</th>
                    <th class="num col-hide-mobile col-unrealized sortable-th" onclick="setSort('unrealized')" aria-sort="${{getAriaSort('unrealized')}}" title="Sort by Unrealized PnL">Unrealized ${{getSortIndicator('unrealized')}}</th>
                    <th class="num col-pnl sortable-th" onclick="setSort('pnl')" aria-sort="${{getAriaSort('pnl')}}" title="Sort by Net FIFO PnL">Net PnL ${{getSortIndicator('pnl')}}</th>
                </tr>
            `;

            if (!themeRows || themeRows.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:28px 10px;">No themes found.</td></tr>`;
                tfoot.innerHTML = '';
                return;
            }}

            let rowsHtml = '';
            themeRows.forEach(row => {{
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

            tfoot.innerHTML = '';
        }}

        /* Table Rendering: Ticker Drilldown */
        function renderTickersTable(selection, showThemeColumn = false) {{
            const tickers = sortItems(selection.visibleRows);
            const thead = document.getElementById('table-head');
            const tbody = document.getElementById('table-body');
            const tfoot = document.getElementById('table-foot');
            tfoot.innerHTML = '';

            thead.innerHTML = `
                <tr>
                    <th class="col-ticker">Ticker</th>
                    <th class="col-desc">Description</th>
                    ${{showThemeColumn ? '<th class="col-theme-tag">Theme</th>' : ''}}
                    <th class="num col-hide-mobile col-realized sortable-th" onclick="setSort('realized')" aria-sort="${{getAriaSort('realized')}}" title="Sort by Realized PnL">Realized ${{getSortIndicator('realized')}}</th>
                    <th class="num col-hide-mobile col-unrealized sortable-th" onclick="setSort('unrealized')" aria-sort="${{getAriaSort('unrealized')}}" title="Sort by Unrealized PnL">Unrealized ${{getSortIndicator('unrealized')}}</th>
                    <th class="num col-pnl sortable-th" onclick="setSort('pnl')" aria-sort="${{getAriaSort('pnl')}}" title="Sort by Net FIFO PnL">Net PnL ${{getSortIndicator('pnl')}}</th>
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

        function renderPlotlyChart(container, traces, layout, config) {{
            const renderPromise = container.classList.contains('js-plotly-plot')
                ? Plotly.react(container, traces, layout, config)
                : Plotly.newPlot(container, traces, layout, config);
            return renderPromise.then(() => {{
                if (container.isConnected && container.classList.contains('js-plotly-plot')) {{
                    Plotly.Plots.resize(container);
                }}
            }});
        }}

        /* Graph Rendering: Themes Overview */
        function renderThemesGraph(selection) {{
            if (currentMode !== 'graph') return;
            const graphData = sortItems(selection.graphData);
            const container = document.getElementById('main-chart');

            if (!graphData || graphData.length === 0) {{
                if (window.Plotly) Plotly.purge(container);
                container.innerHTML = '<div style="color: var(--text-muted); padding: 40px; text-align: center; font-size: 13px;">No themes data to display.</div>';
                return;
            }}

            // Preserve Plotly's existing DOM so updated filter data can be rendered.

            // Reverse for top-down descending visual hierarchy
            const dataToChart = [...graphData].reverse();
            const yNames = dataToChart.map(t => t.Theme);
            const realized = dataToChart.map(t => t.RealizedPnl);
            const unrealized = dataToChart.map(t => t.UnrealizedPnl);
            const net = dataToChart.map(t => t.TotalFifoPnl);

            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            const textColor = isLight ? '#0f172a' : '#f8fafc';
            const gridColor = isLight ? '#e2e8f0' : '#1e293b';
            const isMobile = window.innerWidth <= 640;
            const leftMargin = isMobile ? 70 : 85;
            const rightMargin = isMobile ? 12 : 25;

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
                height: Math.max(isMobile ? 440 : 480, dataToChart.length * (isMobile ? 26 : 30) + 70),
                margin: {{ l: leftMargin, r: rightMargin, t: 15, b: 30 }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ family: 'Inter', color: textColor, size: 11 }},
                showlegend: false,
                xaxis: {{
                    gridcolor: gridColor,
                    zerolinecolor: isLight ? '#94a3b8' : '#475569',
                    zerolinewidth: 1.5,
                    tickfont: {{ color: textColor, family: 'JetBrains Mono', size: isMobile ? 9 : 10 }},
                    tickprefix: '€',
                    tickformat: ',.0f'
                }},
                yaxis: {{
                    tickfont: {{ color: textColor, family: 'JetBrains Mono', size: isMobile ? 10 : 11, weight: 600 }},
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

            renderPlotlyChart(container, [traceRealized, traceUnrealized, traceNet], layout, config).then(() => {{
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
        function renderTickersGraph(selection) {{
            if (currentMode !== 'graph') return;
            const tickers = sortItems(selection.graphData);
            const container = document.getElementById('main-chart');

            if (!tickers || tickers.length === 0) {{
                if (window.Plotly) Plotly.purge(container);
                container.innerHTML = '<div style="color: var(--text-muted); padding: 40px; text-align: center; font-size: 13px;">No tickers data to display.</div>';
                return;
            }}

            // Preserve Plotly's existing DOM so updated filter data can be rendered.

            // Reverse for top-down descending visual hierarchy
            const dataToChart = [...tickers].reverse();
            const yNames = dataToChart.map(t => t.UnderlyingSymbol);
            const realized = dataToChart.map(t => t.RealizedPnl);
            const unrealized = dataToChart.map(t => t.UnrealizedPnl);
            const net = dataToChart.map(t => t.TotalFifoPnl);

            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            const textColor = isLight ? '#0f172a' : '#f8fafc';
            const gridColor = isLight ? '#e2e8f0' : '#1e293b';
            const isMobile = window.innerWidth <= 640;
            const leftMargin = isMobile ? 50 : 68;
            const rightMargin = isMobile ? 12 : 25;

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
                height: Math.max(isMobile ? 440 : 480, dataToChart.length * (isMobile ? 26 : 30) + 70),
                margin: {{ l: leftMargin, r: rightMargin, t: 15, b: 30 }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ family: 'Inter', color: textColor, size: 11 }},
                showlegend: false,
                xaxis: {{
                    gridcolor: gridColor,
                    zerolinecolor: isLight ? '#94a3b8' : '#475569',
                    zerolinewidth: 1.5,
                    tickfont: {{ color: textColor, family: 'JetBrains Mono', size: isMobile ? 9 : 10 }},
                    tickprefix: '€',
                    tickformat: ',.0f'
                }},
                yaxis: {{
                    tickfont: {{ color: textColor, family: 'JetBrains Mono', size: isMobile ? 10 : 11, weight: 600 }},
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

            renderPlotlyChart(container, [traceRealized, traceUnrealized, traceNet], layout, config).then(() => {{
                if (container.removeAllListeners) {{
                    container.removeAllListeners('plotly_click');
                }}
            }});
        }}

        /* Light / Dark Mode Handling */
        function initThemeMode() {{
            const saved = localStorage.getItem('ibkr_theme_mode');
            if (saved) {{
                applyThemeMode(saved);
            }} else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {{
                applyThemeMode('light');
            }} else {{
                applyThemeMode('dark');
            }}

            if (window.matchMedia) {{
                window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', e => {{
                    if (!localStorage.getItem('ibkr_theme_mode')) {{
                        applyThemeMode(e.matches ? 'light' : 'dark');
                    }}
                }});
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
            const activeCountTag = document.getElementById('active-count-tag');
            if (activeCountTag) {{
                activeCountTag.innerText = TICKER_DATA.filter(t => t.IsActive).length;
            }}
            renderDashboard();
        }}

        // Handle responsive chart resize via ResizeObserver with debounced window resize fallback
        let resizeTimer;
        window.addEventListener('resize', () => {{
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {{
                if (currentMode === 'graph' && window.Plotly) {{
                    requestAnimationFrame(() => {{
                        Plotly.Plots.resize('main-chart');
                    }});
                }}
            }}, 120);
        }});

        if (window.ResizeObserver) {{
            const chartWrapper = document.querySelector('.chart-wrapper');
            if (chartWrapper) {{
                const observer = new ResizeObserver(() => {{
                    if (currentMode === 'graph' && window.Plotly) {{
                        requestAnimationFrame(() => {{
                            Plotly.Plots.resize('main-chart');
                        }});
                    }}
                }});
                observer.observe(chartWrapper);
            }}
        }}

        // Initialization
        window.addEventListener('DOMContentLoaded', () => {{
            try {{
                initThemeMode();
                refreshDataAndViews();
            }} catch (error) {{
                console.error('Report initialization failed:', error);
                const errorEl = document.getElementById('kpi-error');
                if (errorEl) errorEl.hidden = false;
            }}
        }});
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
