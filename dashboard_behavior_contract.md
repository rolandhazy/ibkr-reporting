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

### Threshold control input behavior

- The control consists of a comparison mode (`|Net| >` or `|Net| <`) and a EUR amount.
- An empty amount disables the threshold, regardless of the selected mode.
- A valid amount is a finite, non-negative EUR number. Decimal amounts are allowed; zero is valid. The UI should use a numeric input with a minimum of zero and cent-level steps (`0.01`).
- While the amount is incomplete or invalid, including a negative value, treat the threshold as unset (`null`). Do not keep applying an earlier valid amount or accidentally filter rows based on malformed input. Once the user enters a valid amount, apply the currently selected mode and amount.
- With a valid amount of zero, retain the same strict rules: `>` retains rows with non-zero absolute Net PnL; `<` retains no rows because absolute PnL cannot be less than zero.
- Changing either the mode or a valid amount, or clearing the amount, refreshes all dashboard regions from the shared selection result.

## KPI semantics

All four KPIs describe the **final displayed results** for the selected time slice and current view. They update together when time slice, Active-only, scope/drilldown, search, or the absolute-Net-PnL threshold changes. Calculate the PnL KPIs from the underlying ticker records represented by the rows that remain after the threshold; do not sum display aggregates in a way that double-counts records.

- **Net FIFO PnL:** Sum `TotalFifoPnl` across the represented ticker records. This is the portfolio/report's Net PnL measure and is distinct from Realized and Unrealized PnL.
- **Realized:** Sum `RealizedPnl` across the same represented ticker records.
- **Unrealized:** Sum `UnrealizedPnl` across the same represented ticker records.
- **Holdings:** Count distinct ticker symbols (`UnderlyingSymbol`) across the same represented ticker records. This is a ticker count, not a count of theme rows or positions/contracts.

In overview, if a theme row passes the threshold, all eligible ticker records contributing to that displayed theme row are represented in all four KPI calculations. A theme row that fails the threshold contributes nothing. In drilldown, only displayed ticker rows in the selected theme contribute. Deduplicate ticker symbols for Holdings; sum each represented ticker record's PnL fields for the three PnL KPIs.

If no records remain, show zero for all three PnL KPIs and zero for Holdings. Preserve the source measures as distinct fields; do not substitute one for another or assume that Net FIFO PnL equals Realized plus Unrealized.

## Dashboard data-selection pipeline interface

The dashboard's selection and aggregation logic is a pure function: it receives the already-serialized ticker summaries for one selected time slice and the current filter/view state, and returns data for the renderers. It does not fetch IBKR data, access the DOM, or mutate the input records. The existing `TIME_SLICES[sliceKey].tickers` payload is the source of records; each record represents a ticker summary for one theme in that slice.

### Inputs

Conceptual JavaScript interface (names are descriptive, not implementation requirements):

```js
selectDashboardData({
  tickers,       // Array of selected-slice ticker-summary records
  activeOnly,    // Boolean
  scope,         // { type: 'overview' | 'theme' | 'portfolio', theme?: string }
  searchQuery,   // Raw search string; empty string means no search constraint
  pnlThreshold,  // null, or { mode: 'gt' | 'lt', amountEUR: number }
});
```

Each ticker-summary record must provide:

- `Theme`: theme name used for scoping, search, and overview aggregation.
- `UnderlyingSymbol`: ticker identity, used for search, drilldown rows, and distinct Holdings count.
- `Description`: ticker/company description used for search and display.
- `TotalFifoPnl`, `RealizedPnl`, `UnrealizedPnl`: numeric PnL values in EUR, used for aggregation, thresholds, KPIs, and graph/table data.
- `IsActive`: boolean active status supplied by the report generator.

`scope` has these meanings:

- `{ type: 'overview' }`: all themes; group eligible tickers into theme display rows.
- `{ type: 'theme', theme: '...' }`: selected theme only; display eligible tickers as ticker rows.
- `{ type: 'portfolio' }`: all themes; display eligible tickers as ticker rows (the total-portfolio detail view).

`pnlThreshold: null` means no threshold. A non-null threshold uses the strict comparisons defined above and is applied to display rows after the scope-specific display aggregation. Sorting state is intentionally not an input: sorting changes presentation order only, never eligibility or KPI membership.

### Output

Return one result object, conceptually:

```js
{
  eligibleTickers,   // Ticker records after active-only, scope, and search filters
  displayRows,       // Rows before threshold: themes in overview; tickers in detail views
  visibleRows,       // Display rows remaining after the optional absolute-Net-PnL threshold
  representedTickers,// Underlying ticker records represented by visibleRows; source for KPIs
  kpis: {
    netFifoPnl,      // Sum of representedTickers.TotalFifoPnl
    realizedPnl,     // Sum of representedTickers.RealizedPnl
    unrealizedPnl,   // Sum of representedTickers.UnrealizedPnl
    holdings         // Distinct UnderlyingSymbol count in representedTickers
  },
  highlights,        // Best/worst performer data derived only from visibleRows
  graphData          // Chart-ready row data derived only from visibleRows
}
```

`displayRows` and `visibleRows` contain renderable rows with their PnL fields and the underlying eligible ticker records (or an equivalent stable association to those records). In overview, a visible theme row represents all eligible ticker records aggregated into that theme; in theme and portfolio detail views, a visible ticker row represents its ticker record. Thus `representedTickers` is formed from the visible rows, not by summing both rows and their underlying records. `highlights` and `graphData` must be projections of the same `visibleRows`; rendering and formatting remain the responsibility of the UI layer. For empty results, all row/ticker arrays and highlights are empty, graph data is empty, and every KPI is zero.

## Active status

The current report generator marks a record active when `abs(UnrealizedPnl) > 0.001`. This contract does not redefine that source-data heuristic. Changing how open positions are identified is a separate data/product decision.

## Test approach

The current automated tests have two layers, both deterministic and offline:

1. **Pytest report-generation and serialization tests.** These exercise Python-side report data preparation and serialization using local inputs. They do not make live IBKR requests.
2. **Deterministic dashboard selector tests.** Pytest tests run the pure JavaScript selection logic against synthetic ticker-summary fixtures using a local JavaScript runtime. These cover data-selection behavior such as filtering, search, aggregation, thresholds, KPI derivation, and empty results. They do not load the generated page, launch a browser, or interact with rendered controls.

**Playwright browser interaction tests are future work.** When added, they should load a generated report with fixture data and verify rendered control interactions and synchronized results. They should intercept external requests so the tests remain offline and deterministic. The current suite does not verify mobile layout, graph interaction, or button behavior in a browser; those remain unverified until browser-level tests are implemented and run.

Keep test-only dependencies separate from production `requirements.txt`. The current deterministic selector tests use a local JavaScript runtime and do not require launching a browser. Before implementing Playwright browser tests, verify that Playwright and a compatible browser runtime are available, document any one-time local/CI setup, and avoid downloading browser binaries as part of the test suite.

## Test expectations

The current pytest suite should remain deterministic and independent of live IBKR access. Report-generation tests verify Python-side data preparation/serialization; selector tests verify pure selection logic against local fixtures, including the filtering rules specified above. These tests do not establish that browser controls, graph interactions, or responsive/mobile layouts work as rendered.

Future Playwright browser tests should verify user interactions for search and threshold controls, view switching and drilldown, empty-result rendering, synchronized KPIs/table/highlights/graph, and responsive layouts. Report browser-level coverage separately from selector/unit coverage so documentation and test results do not imply that an untested UI behavior has been verified.
