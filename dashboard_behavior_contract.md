# Dashboard Behavior Contract

This document defines the dashboard filtering and summary behavior for implementation and testing. It is the source of truth for how the time-slice selection, Active-only toggle, drilldown, search, absolute-Net-PnL filter, and KPI summaries interact.

## Filtering and display order

For the selected time slice, the dashboard applies these steps in order:

1. **Time slice:** Start with records from the currently selected time slice.
2. **Active-only:** If enabled, retain only records marked active by the report data.
3. **View scope:** In the overview, keep all themes. In drilldown, keep only the selected theme. A total-portfolio view uses all themes.
4. **Search:** Match ticker records using the search rules below.
5. **Aggregate for display:** In the overview, aggregate eligible ticker records into theme rows. In drilldown, display ticker rows.
6. **Absolute-Net-PnL threshold:** Apply the threshold to the displayed row after aggregation: a theme's aggregate in overview, or a ticker's PnL in drilldown.
7. **Render all dashboard summaries:** Derive the KPI strip, performer highlights, table, and graph from the same final filtered result. No region should independently apply a different interpretation of the filters.

If no records remain, render a clear empty state and zero/empty summaries; do not retain values from the previous filter state.

## Search behavior

- Search is case-insensitive and matches ticker symbol, description, and theme.
- Separate terms with whitespace or commas.
- Positive terms are OR-matched: a record is included when it matches at least one positive term. If there are no positive terms, inclusion is unrestricted before exclusions.
- A term prefixed with `-` excludes records matching that term. Exclusions take precedence over positive matches.
- A bare `-` is ignored, so typing the exclusion prefix alone does not unexpectedly remove results.
- A record is excluded if any valid exclusion term matches any searchable field.

## Absolute-Net-PnL threshold

- The threshold compares the absolute value of the displayed row's Net PnL (`TotalFifoPnl`) with the selected EUR amount.
- The `>` mode retains rows where `abs(Net PnL) > threshold`.
- The `<` mode retains rows where `abs(Net PnL) < threshold`.
- Both comparisons are strict: a row exactly equal to the threshold is excluded in either mode.
- The threshold is applied after search and aggregation. Thus, in overview it filters aggregated theme rows; in drilldown it filters ticker rows.
- When the threshold control is unset or disabled, it does not remove rows.

## KPI semantics

All four KPIs describe the **final displayed results** for the selected time slice and current view. They update together when time slice, Active-only, scope/drilldown, search, or the absolute-Net-PnL threshold changes. Calculate the PnL KPIs from the underlying ticker records represented by the rows that remain after the threshold; do not sum display aggregates in a way that double-counts records.

- **Net FIFO PnL:** Sum `TotalFifoPnl` across the represented ticker records. This is the portfolio/report's Net PnL measure and is distinct from Realized and Unrealized PnL.
- **Realized:** Sum `RealizedPnl` across the same represented ticker records.
- **Unrealized:** Sum `UnrealizedPnl` across the same represented ticker records.
- **Holdings:** Count distinct ticker symbols (`UnderlyingSymbol`) across the same represented ticker records. This is a ticker count, not a count of theme rows or positions/contracts.

In overview, if a theme row passes the threshold, all eligible ticker records contributing to that displayed theme row are represented in all four KPI calculations. A theme row that fails the threshold contributes nothing. In drilldown, only displayed ticker rows in the selected theme contribute. Deduplicate ticker symbols for Holdings; sum each represented ticker record's PnL fields for the three PnL KPIs.

If no records remain, show zero for all three PnL KPIs and zero for Holdings. Preserve the source measures as distinct fields; do not substitute one for another or assume that Net FIFO PnL equals Realized plus Unrealized.

## Active status

The current report generator marks a record active when `abs(UnrealizedPnl) > 0.001`. This contract does not redefine that source-data heuristic. Changing how open positions are identified is a separate data/product decision.

## Test approach

Use a two-layer test strategy:

1. **Deterministic unit/data tests with pytest.** Test pure filtering, search parsing/matching, aggregation, threshold comparisons, and KPI calculations against synthetic local fixtures. Test report generation/serialization with temporary output files where appropriate. These tests must not make live IBKR requests.
2. **Browser-level dashboard tests with Playwright.** Load a generated report using fixture data and exercise the user-facing controls and rendered results, including filter combinations, drilldown, empty results, KPI synchronization, and responsive/mobile behavior. Stub or intercept external network requests (including CDN assets) so tests remain offline and deterministic.

Keep test-only dependencies separate from production `requirements.txt` (for example, in a development requirements file). Pytest is present in the workspace virtual environment, but Playwright and a compatible browser runtime must be verified before browser tests are implemented. Do not download dependencies or browser binaries as part of the test suite; document any one-time local/CI setup needed.

## Test expectations

Tests should verify search parsing and matching, exclusion precedence, active-only behavior, overview aggregation and drilldown scope, strict threshold boundaries, each KPI's calculation and synchronization, distinct Holdings counting, and empty-result handling. Use deterministic local fixtures; dashboard tests must not require live IBKR requests.
