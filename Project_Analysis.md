# Project Analysis: IBKR Portfolio Reporting & Theme Attribution

## 1. Executive Summary

IBKR Reporting is an automated portfolio performance and macro/sector theme attribution pipeline built for Interactive Brokers (IBKR) accounts. It solves the fragmentation of native broker statements by:

- Programmatically fetching execution and position statements through the IBKR Flex Web Service API (`SendRequest` + `GetStatement`).
- Categorizing tickers and underlying assets into customizable macro and industry themes (e.g., `Big Tech`, `AI & Chips`, `Energy`, `Space & DF`, `Hedges`, `FX & FI`).
- Compiling a standalone client-side HTML dashboard (`public/index.html`) powered by Plotly.js (`2.27.0` CDN), Google Fonts (`Inter` / `JetBrains Mono`), responsive CSS, and vanilla JavaScript.
- Supporting multi-time-horizon evaluation (`1D`, `7D`, `30D`, `YTD`) and privacy-preserving portfolio sampling (`--sample-rate`, `--seed`) for development/staging previews.

---

## 2. Architecture & Data Flow

1. **Fetch & Cache (`flex_client.py`)**: Resolves requested time slices (`1d`, `7d`, `30d`, `ytd`). Outside CI (`CI` / `GITHUB_ACTIONS` env vars), reads/writes 24-hour local XML caches (`flex_cache_1d.xml`, `flex_cache_7d.xml`, `flex_cache_30d.xml`, `flex_report_cache.xml`). Failed slices are omitted rather than substituting stale caches from another period.
2. **Parse & Map (`parser.py`, `theme_map.py`)**: Extracts statement dates (`fromDate`, `toDate`, `period`, `whenGenerated`), reads `FIFOPerformanceSummaryUnderlying` (falling back to `Trade` + `OpenPosition`), strips IBKR `Total` summary rows, maps `UnderlyingSymbol` to one of 18 themes (or `"Other"`), and optionally runs deterministic/random sampling.
3. **Aggregate & Render (`report_generator.py`)**: Groups each slice by `["Theme", "UnderlyingSymbol"]`, rounds PnL figures, sets `IsActive = abs(UnrealizedPnl) > 0.001`, serializes `TIME_SLICES` JSON into an inline HTML/CSS/JS template, and writes `public/index.html`.
4. **Deploy (`.github/workflows/`, `wrangler.jsonc`)**:
   - `dev` branch pushes trigger `deploy-pages-dev.yml`, generating a sampled report (`0.3` default) for GitHub Pages.
   - Merged PRs to `main` trigger `draft-release.yml` to calculate semver bumps and draft a GitHub Release.
   - Published releases trigger `deploy.yml`, building the full report and deploying `./public` to Cloudflare via Wrangler.

---

## 3. Core Component Breakdown

| Module / Path | Purpose | Key Details |
| :--- | :--- | :--- |
| `main.py` | CLI orchestrator & entry point | Parses `--slices` (`1d,7d,30d,ytd`), `--sample-rate`, `--output`, and `--seed`; fetches slices, parses metadata/DataFrames, and triggers HTML generation. |
| `build_report_html.py` | Backward-compatible CLI wrapper | Thin wrapper invoking `main.main()`. |
| `flex_client.py` | IBKR Flex client & caching | Handles `SendRequest` retries, exponential-backoff polling on `GetStatement` (code `1019` in-progress, 5xx tolerance), business-day/period date resolution, and per-slice local XML caching. |
| `parser.py` | XML statement parser & sampler | Extracts `FlexStatement` metadata; parses `FIFOPerformanceSummaryUnderlying` (or falls back to `Trade` + `OpenPosition`), removes `Total` rows, applies `get_theme_for_symbol()`, and implements `sample_portfolio()`. |
| `theme_map.py` | Asset categorization engine | Static `THEME_MAP` of 18 macro/sector themes inverted into `SYMBOL_TO_THEME`; unmapped symbols default to `"Other"`. |
| `report_generator.py` | Dashboard generator | 2,405-line generator (CSS lines ~99–1320, HTML lines ~1322–1472, JS lines ~1474–2400) aggregating per-slice data and emitting the interactive dashboard with light/dark mode, drilldown breadcrumbs, table/graph views, sort controls, and win/loss ratio micro-bars. |
| `wrangler.jsonc` | Cloudflare deployment config | Serves static assets from `./public`. |
| `.github/workflows/` | CI/CD pipelines | `deploy.yml` (Cloudflare production), `deploy-pages-dev.yml` (GitHub Pages sampled preview), and `draft-release.yml` (automated semver draft release). |

---

## 4. Codebase Health & Quality Assessment

### Strengths
- **Resilient Network Client**: Handles IBKR `1019` statement generation delays with exponential backoff, 5xx retries, and timeouts, while avoiding misleading cross-slice cache fallbacks.
- **Offline / Local Dev Friendly**: 24-hour per-slice XML caches avoid hitting IBKR rate limits and speed up local dashboard iterations.
- **Zero Backend Server Dependency**: Produces a single self-contained HTML artifact (`public/index.html`) deployable to any static host (Cloudflare, GitHub Pages) or opened locally (with internet access for Plotly CDN and Google Fonts).
- **Privacy Protections**: Staging previews use `--sample-rate`, and `.gitignore` excludes credentials and local XML statement caches.

### Technical Debt, Risks & Areas for Improvement
1. **Monolithic Report Generator (`report_generator.py`)**:
   - At 2,405 lines (~1,220 lines of CSS and ~925 lines of JS inside a Python f-string with `{{ }}` escaping), UI code lacks native syntax highlighting, JS/CSS linting, and isolated unit testability.
   - *Recommendation*: Split HTML/CSS/JS into separate template/asset files (or Jinja2 templates) and inject `TIME_SLICES` cleanly.
2. **Missing Automated Test Suite & Dependency Alignment**:
   - No `tests/` directory exists, and `requirements.txt` only declares `pandas`, `requests`, and `python-dotenv` (while `pytest` and `playwright` are installed in `.venv` without being tracked in dev requirements).
   - *Critical test targets*: XML parsing & fallback (`Trade`/`OpenPosition`), `Total` row filtering, `--seed` sampling determinism, and Playwright UI tests (multi-token search, filters, drilldown KPIs, collapsed mobile sorting).
3. **External CDN Dependency**:
   - `public/index.html` relies on `cdn.plot.ly/plotly-2.27.0.min.js` and `fonts.googleapis.com`; offline environments without cached CDN assets will fail to render charts.
4. **Hardcoded Currency Badge & `IsActive` Heuristic**:
   - The header hardcodes `<span class="badge neutral">EUR</span>` rather than deriving base currency from Flex XML.
   - `IsActive` is defined as `abs(UnrealizedPnl) > 0.001`, which can misclassify an open position whose unrealized PnL is exactly `0.00`.
5. **Business-Day Calendar Limitation**:
   - `get_last_business_day()` in `flex_client.py` only skips weekends (`weekday() >= 5`) and does not account for exchange/market holidays.
6. **Static Theme Map**:
   - `THEME_MAP` in `theme_map.py` is hardcoded in Python; externalizing it to `themes.yaml` or `themes.json` would allow non-code portfolio updates.

---

## 5. Analysis of Active Tasks (`todo.md`)

All UI tasks below target `report_generator.py`. Implementing a single unified filtering/scoping pipeline (applying `activeTimeSlice`, `showActiveOnly`, multi-token search with `-` exclusions, `|Net PnL|` filter, and `drilldownTheme` scope consistently across KPIs, Performer Highlights, Table, and Graph) will prevent state drift.

### Group 1: Search Bar Enhancements
- **Allow several tickers + `-` to exclude tickers**
  - *Current behavior*: `renderDashboard()` (lines ~1811–1892) filters with a single lowercase substring `tickerSearchQuery` against `UnderlyingSymbol` and `Description`.
  - *Implementation*: Split `tickerSearchQuery` on commas and whitespace into tokens. Tokens prefixed with `-` (e.g., `-NVDA`, ignoring bare `"-"` while typing) act as exclusions (`!matches`); remaining tokens act as OR-matched inclusions across `UnderlyingSymbol`, `Description`, and `Theme`.
- **Decrease search bar length**
  - *Current behavior*: `.ticker-search-box` uses `flex: 1 1 280px; max-width: 420px;` (lines 635–641), with mobile full-width override at `max-width: 640px` (lines 448–452).
  - *Implementation*: Reduce desktop width to `flex: 0 1 220px; max-width: 240px;` (keeping `max-width: none; width: 100%;` on `<= 640px`) to free toolbar space for the new absolute-PnL filter.

### Group 2: Table View Enhancements
- **On table view hover, show ticker or theme name**
  - *Current behavior*: `.interactive-row` reveals `.drilldown-hint`, and `.subtable-desc` sets `title` on truncated descriptions (`renderTickersTable()`, line 2042). Theme rows and ticker pills have no explicit hover tooltip for full names.
  - *Implementation*: Add `title` attributes on theme name cells (`row.Theme` + asset/win-loss summary) and ticker cells (`UnderlyingSymbol — Description (Theme)`), ensuring truncated text is readable on hover.
- **Change column order to: `THEME, ASSETS, NET PNL, REALIZED, UNREALIZED`**
  - *Current behavior*: `renderThemesTable()` (lines 1934–1996) renders `Theme | Assets | Realized | Unrealized | Net PnL` across `thead`, `tbody`, and `tfoot` (`Total Portfolio` row). `renderTickersTable()` (lines 2006–2050) also places `Realized | Unrealized | Net PnL` last.
  - *Implementation*: Reorder `thead`, `tbody`, and `tfoot` in `renderThemesTable()` to `Theme | Assets | Net PnL | Realized | Unrealized` (and align `Net PnL | Realized | Unrealized` in `renderTickersTable()`), updating column width classes accordingly.
- **In collapsed view, allow sort button to affect shown measure**
  - *Current behavior*: On screens `<= 600px`, `.col-hide-mobile` (line 1229) hides `.col-realized` and `.col-unrealized`, leaving only Net PnL visible regardless of `sortColumn`.
  - *Implementation*: On collapsed/mobile viewports (or via CSS/JS toggling of the active metric column), display the column header and cell value corresponding to `sortColumn` (`TotalFifoPnl`, `RealizedPnl`, or `UnrealizedPnl`) so clicking a sort pill both re-sorts and shows that metric.

### Group 3: Navigation, KPI Synchronization & Sticky Header
- **Update top-level KPI summaries on drilldown (`Net FIFO PnL`, `Realized`, `Unrealized`, `Assets`)**
  - *Current behavior*: `updateKpis(availableTickers)` is only called in `refreshDataAndViews()` (line 2346) with the portfolio-wide `availableTickers`.
  - *Implementation*: Compute and call `updateKpis(scopedTickers)` inside `renderDashboard()` for the active scope (All Themes, specific `drilldownTheme`, `__TOTAL__`, or active search/`|Net PnL|` filter) so the top KPI strip always reflects the displayed slice/subset.
- **Freeze top-level summary when scrolling down**
  - *Current behavior*: `<header class="header">` and `.kpi-strip` scroll out of view; only `thead th` and `tfoot .total-row` are sticky inside `.table-container` (`max-height: clamp(380px, calc(100vh - 240px), 820px)`, line 889).
  - *Implementation*: Make `.header` (or `.kpi-strip`) `position: sticky; top: 0; z-index: 30;` with an opaque `--bg-page`/`--bg-card` backdrop and bottom border, and adjust `.table-container` `max-height` / `scroll-padding-top` so sticky page headers and sticky table headers do not collide when scrolling (especially in Graph view).
- **Remove current measures next to theme name (`Net`, ticker count)**
  - *Current behavior*: `renderDashboard()` populates `#view-pnl-pill` and `#view-count-pill` inside `.breadcrumb-nav` (lines 1393–1394, 1833–1916).
  - *Implementation*: Remove `#view-pnl-pill` and `#view-count-pill` from the breadcrumb bar since the frozen `.kpi-strip` now displays those exact metrics for the current view.

### Group 4: Absolute Net PnL Filter
- **Add filter for absolute value Net PnL (`|Net PnL|`) with `<` / `>` mode**
  - *Implementation*: Add a compact toolbar control with a mode toggle (`|Net| >` vs `|Net| <`) and a numeric EUR threshold input. Decide and document whether filtering applies at the **ticker level** before theme aggregation or at the **displayed row level** (themes in overview, tickers in drilldown), and feed the filtered results into KPIs, Table, and Graph consistently.

### Group 5: New Attribution Graph
- **New graph: Attribution per theme / in drilldown per ticker, with measure toggle (`Net PnL`, `Realized`, `Unrealized`)**
  - *Current behavior*: `renderThemesGraph()` (line 2055) and `renderTickersGraph()` (line 2188) render a single Plotly chart with Realized + Unrealized bars and Net PnL diamond markers.
  - *Implementation*:
    1. Add an attribution chart (either as a new chart panel or Graph sub-tab alongside the existing breakdown chart) displaying contribution by theme at the top level and by ticker on drilldown.
    2. Add a segmented metric toggle (`Net PnL | Realized | Unrealized`).
    3. Handle mixed-sign totals carefully: when positive and negative contributions offset (making net total near zero or negative), show signed EUR values alongside `% of gross |PnL|` (or clear signed % attribution) so percentages remain interpretable.
