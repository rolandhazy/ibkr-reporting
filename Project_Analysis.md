# Project Analysis: IBKR Portfolio Reporting & Theme Attribution

## 1. Executive Summary

IBKR Reporting is a Python pipeline that fetches Interactive Brokers (IBKR) Flex statements, parses and groups portfolio performance by ticker and investment theme, and generates a static interactive HTML dashboard.

The pipeline supports multiple reporting periods (`1D`, `7D`, `30D`, and `YTD`), maps assets to configurable-in-code themes, and can produce deterministic or randomized portfolio samples for development previews. The generated dashboard is client-side HTML, CSS, and vanilla JavaScript, with Plotly for visualizations. It provides theme and ticker views, search and filtering controls, KPI summaries, table/graph modes, and light/dark display modes.

The dashboard’s core filtering and selection logic is centralized in a shared data-selection pipeline. Its current behavior and status are summarized below; `todo.md` is the authoritative source for dashboard task groupings and completion status.

## 2. Architecture & Data Flow

1. **Fetch and cache (`flex_client.py`)**: Resolves requested time slices (`1d`, `7d`, `30d`, `ytd`) and fetches Flex statements. Outside CI, it can read and write local XML caches. Failed slices are omitted rather than being silently replaced with stale data from another period.
2. **Parse and map (`parser.py`, `theme_map.py`)**: Parses Flex statement metadata and performance summaries, with a fallback to trade and open-position records. It removes broker `Total` rows, maps underlying symbols to themes, and can apply portfolio sampling.
3. **Aggregate and render (`report_generator.py`)**: Groups ticker summaries by time slice and theme, prepares PnL and active-status fields, embeds the data into an HTML/CSS/JavaScript template, and writes the static dashboard to `public/index.html`.
4. **Deploy (`.github/workflows/`, `wrangler.jsonc`)**:
   - Pushes to `dev` can generate a sampled GitHub Pages preview.
   - Merged PRs to `main` can trigger an automated draft release.
   - Published releases can build the full report and deploy the static output to Cloudflare using Wrangler.

The dashboard receives ticker-level summaries for each time slice. Its client-side selection pipeline applies active-only filtering, view scope, search, display grouping, and any active absolute Net PnL filter. KPIs, highlights, table rows, and graph data are derived from the resulting selection to keep displayed summaries aligned.

## 3. Core Component Breakdown

| Module / Path | Purpose | Key Details |
| :--- | :--- | :--- |
| `main.py` | CLI orchestrator and entry point | Accepts slice, sampling, output, and seed options; coordinates fetching, parsing, and report generation. |
| `build_report_html.py` | Backward-compatible CLI wrapper | Invokes `main.main()`. |
| `flex_client.py` | IBKR Flex client and caching | Handles request retries, statement-generation polling, date resolution, and local XML caches. |
| `parser.py` | XML statement parser and sampler | Parses performance summaries or fallback records, removes summary rows, assigns themes, and supports portfolio sampling. |
| `theme_map.py` | Asset categorization | Holds the static symbol-to-theme mapping; unmapped symbols are categorized as `Other`. |
| `report_generator.py` | Dashboard generator and client-side application | Produces the static report and contains the HTML/CSS/JavaScript for theme and ticker views, filtering, KPI summaries, table/graph modes, sorting, and display themes. |
| `tests/` | Automated tests | Includes Python report-generator tests and deterministic tests of dashboard selection logic. These tests are not browser-rendering or visual-layout tests. |
| `requirements.txt` | Production dependencies | Declares runtime Python dependencies. |
| `requirements-dev.txt` | Development/test dependencies | Declares pytest and Playwright. The current dashboard-selection tests use JavaScript execution; the presence of Playwright does not mean rendered browser interactions are covered. |
| `.github/workflows/` | CI/CD workflows | Contains sampled preview, release, and production deployment workflows. |
| `wrangler.jsonc` | Cloudflare deployment configuration | Configures static asset deployment from `public`. |
| `todo.md` | Dashboard task status | Authoritative checklist of completed and remaining dashboard work, organized by task group. |

## 4. Implemented Dashboard Behavior

The following summarizes the current implementation recorded in `todo.md`; consult that file for the detailed task checklist.

### Search and filtering

- Search supports multiple ticker, company-description, and theme terms separated by spaces or commas.
- Inclusion terms are OR-matched; `-term` excludes matching records; a bare `-` is ignored.
- The absolute Net PnL control uses `<` and `>` comparison buttons and an editable EUR threshold. It is inactive until a comparison is selected; clicking the selected comparison again deactivates it.
- The threshold applies after theme aggregation in overview and to ticker rows in ticker views.

### Shared selection and views

- KPIs, highlights, table rows, and graph data are derived from the shared filtered selection.
- The **All tickers** control switches from theme rows to ticker-level results across themes, in both table and graph modes. **Themes** provides navigation back to the theme overview.
- The former **Total Portfolio** table row has been removed.

### Layout and scrolling

- The toolbar has responsive wrapping adjustments, and the table uses page scrolling rather than a nested vertical scroller.
- The search field is reduced in width on desktop and mobile.
- Table/Graph and light/dark controls are included in the dashboard UI; responsive behavior across device sizes has not yet been comprehensively verified in a browser.

## 5. Task Status and Verification

`todo.md` is the single source of truth for dashboard task status. This document deliberately summarizes rather than maintaining a second, potentially conflicting task checklist.

### Completed groups in `todo.md`

- **Search and filtering:** multi-term inclusion/exclusion search, reduced search width, configurable absolute Net PnL filter, activation/deactivation behavior, and threshold application at the correct display aggregation level.
- **Shared dashboard data and views:** common selection for KPIs/highlights/table/graph, All tickers view, and removal of the Total Portfolio row.
- **Responsive layout and scrolling:** mobile toolbar rebalancing, graph resize work, and page-based table scrolling.

### Remaining groups in `todo.md`

- **Table usability:** full-name hover details, column ordering, and narrow-screen metric display based on the selected sort.
- **KPIs and summary layout:** verification of KPI behavior in theme drilldown and All tickers view, a safe sticky summary, and removal of redundant view-title badges (check the current UI before treating historical descriptions as current).
- **Attribution graph:** theme/ticker attribution and a Net/Realized/Unrealized measure control.
- **Cross-device verification:** browser checks at desktop, wide-monitor, tablet, and phone widths for toolbar, table, scrolling, sticky summary, and graph controls.

### Test and browser-verification status

- `requirements-dev.txt` separates development/test dependencies from `requirements.txt`.
- The test suite includes report-generation coverage and deterministic tests that execute the dashboard’s JavaScript selection logic against fixtures.
- The selector tests validate data behavior; they do not launch a browser or verify rendered controls, Plotly interactions, scrolling, or responsive layout.
- Playwright is listed as a development dependency, but a dependency declaration alone does not establish that a browser runtime is installed or that browser tests have been run.
- Treat visual and cross-device behavior as **not browser-verified** until the relevant checks are actually performed. The cross-device verification checklist is tracked in `todo.md`.

## 6. Codebase Health & Quality Assessment

### Strengths

- **Resilient network client:** Handles Flex statement generation delays with polling and retries, while avoiding misleading cross-slice cache fallbacks.
- **Offline-friendly development:** Local XML caches can reduce repeated IBKR requests and speed up report iteration.
- **Static deployment model:** Generates a report that can be hosted without a custom application server. Plotly and fonts may still require external network access, depending on the generated page and environment.
- **Privacy-aware previews:** Sampling options support reduced-data development previews, and local credentials/cache files are excluded through repository ignore rules.
- **Centralized dashboard selection:** A shared selection result reduces the risk that KPIs, highlights, tables, and graphs apply inconsistent filters.
- **Deterministic selection tests:** Fixture-driven JavaScript tests provide coverage of search, scope, aggregation, thresholds, and KPI semantics without requiring live IBKR data.

### Technical Debt, Risks & Areas for Improvement

1. **Monolithic report generator (`report_generator.py`)**
   - HTML, CSS, JavaScript, serialization, and rendering are maintained together in a Python template. This makes frontend syntax checking, independent testing, and targeted changes harder.
   - **Recommendation:** Consider extracting frontend assets or templates and adding appropriate JavaScript/CSS linting as a separate maintainability effort.

2. **Browser integration and visual coverage**
   - Selector tests do not verify that controls, graph updates, table scrolling, or responsive breakpoints work when rendered in a browser.
   - **Recommendation:** Add browser interaction tests where the browser runtime is available; prioritize the outstanding checks listed in `todo.md`. Avoid describing these behaviors as verified until tested.

3. **External CDN dependency**
   - Plotly and web fonts may be loaded from external CDNs, so charts or typography can be affected in offline or restricted-network environments.
   - **Recommendation:** Decide whether offline operation is a requirement; if it is, consider bundling required assets or providing graceful chart fallbacks.

4. **Active-status heuristic**
   - `IsActive` is inferred from non-zero unrealized PnL. An open position with zero unrealized PnL may therefore be classified as inactive.
   - **Recommendation:** Confirm whether this proxy matches the intended meaning of the Active control. If the source data provides position state, prefer that explicit signal.

5. **Business-day calendar limitation**
   - The current business-day calculation skips weekends but may not account for exchange or market holidays.
   - **Recommendation:** Confirm whether holiday-aware period boundaries are required and adopt a trading-calendar source if needed.

6. **Static theme mapping**
   - Theme assignments are maintained in Python code.
   - **Recommendation:** Consider externalizing the map only if non-code updates or user customization are needed; retain a clear validation path for unknown symbols and duplicate assignments.

7. **Rounding and derived totals**
   - Python-side ticker summaries and client-side aggregates must retain consistent precision and keep Net FIFO PnL, Realized PnL, and Unrealized PnL semantically distinct.
   - **Recommendation:** Preserve the existing independent-field behavior and add regression coverage if rounding or aggregation logic changes.
