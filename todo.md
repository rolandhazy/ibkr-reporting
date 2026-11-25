# Dashboard TODO

## Completed

### Search and filtering

- [x] Search supports multiple ticker/company/theme terms separated by spaces or commas.
- [x] Search supports `-term` exclusions; a bare `-` is ignored.
- [x] Reduce the search bar width on desktop and mobile. Current placeholder: `Ticker/company/theme; -term excludes`.
- [x] Add an absolute Net PnL filter with `<` and `>` comparison buttons and an editable EUR amount.
- [x] Keep the Net PnL filter inactive until a comparison button is selected; clicking the selected comparison again deactivates it.
- [x] Apply the threshold to displayed rows after overview aggregation, and to ticker rows in ticker views.

### Shared dashboard data and views

- [x] Derive KPIs, highlights, table rows, and graph data from the shared filtered selection.
- [x] Add a Show all control to switch from theme rows to all ticker rows in both table and graph modes.
- [x] Remove the Total Portfolio row from the table; use All Themes to return from the all-tickers view.

### Responsive layout and scrolling

- [x] Rebalance the filter toolbar for mobile layouts and improve graph resizing.
- [x] Use page scrolling for the table instead of a nested table scroller.

### KPIs and summary layout
- [X] Remove the redundant Net PnL and ticker-count badges beside the theme/view title.

## Remaining

### Table usability

- [ ] On table view, show the full ticker or theme name on hover (for truncated content).

### KPIs and summary layout

- [ ] Verify that the top KPI summaries update correctly during theme drilldown and all-tickers view.
- [ ] Make the top-level summary stay visible while scrolling, without reintroducing table/header overlap or preventing page scrolling.

### Attribution graph

- [ ] Add an attribution graph: themes in overview and tickers in drilldown/all-tickers view.
- [ ] Add a graph measure control for Net PnL, Realized, and Unrealized.

### Cross-device verification

- [ ] Verify the toolbar, table, scrolling, sticky summary, and graph controls in a browser at desktop, wide-monitor, tablet, and phone widths.
