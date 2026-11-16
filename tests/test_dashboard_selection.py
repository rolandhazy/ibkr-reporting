"""Focused tests for the JavaScript dashboard selector and KPI semantics."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "report_generator.py"


def _node_executable():
    """Find system Node or the private runtime bundled by Playwright, if installed."""
    node = shutil.which("node")
    if node:
        return node
    spec = importlib.util.find_spec("playwright")
    if spec and spec.origin:
        bundled = Path(spec.origin).parent / "driver" / "node"
        if bundled.is_file():
            return str(bundled)
    pytest.skip("JavaScript selector tests require Node.js (or Playwright's bundled Node)")


def run_selector(tickers, *, scope, active_only=False, search_query="", threshold=None):
    """Execute the pure selector from the report template with JSON fixture data."""
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("        function parseSearchQuery(query)")
    end = source.index("        function updateKpis(selection)", start)
    # report_generator.py is an f-string template: collapse doubled braces and
    # backslashes so the extracted functions match the JavaScript emitted in HTML.
    functions = (
        source[start:end]
        .replace("{{", "{")
        .replace("}}", "}")
        .replace("\\\\", "\\")
    )
    invocation = """
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const inputBefore = JSON.stringify(input.tickers);
const result = selectDashboardData({
  tickers: input.tickers,
  activeOnly: input.activeOnly,
  scope: input.scope,
  searchQuery: input.searchQuery,
  pnlThreshold: input.threshold
});
console.log(JSON.stringify({
  result,
  inputUnchanged: inputBefore === JSON.stringify(input.tickers)
}));
"""
    completed = subprocess.run(
        [_node_executable(), "-e", functions + invocation],
        input=json.dumps(
            {
                "tickers": tickers,
                "activeOnly": active_only,
                "scope": scope,
                "searchQuery": search_query,
                "threshold": threshold,
            }
        ),
        text=True,
        capture_output=True,
        check=True,
    )
    output = json.loads(completed.stdout)
    assert output["inputUnchanged"] is True
    return output["result"]


@pytest.fixture
def ticker_summaries():
    return [
        {
            "Theme": "Core Tech", "UnderlyingSymbol": "AAPL", "Description": "Apple",
            "TotalFifoPnl": 8.25, "RealizedPnl": 3.0, "UnrealizedPnl": 5.0, "IsActive": True,
        },
        {
            "Theme": "Core Tech", "UnderlyingSymbol": "MSFT", "Description": "Microsoft",
            "TotalFifoPnl": 3.75, "RealizedPnl": -2.0, "UnrealizedPnl": 5.75, "IsActive": False,
        },
        {
            "Theme": "Semiconductors", "UnderlyingSymbol": "NVDA", "Description": "NVIDIA",
            "TotalFifoPnl": -10.0, "RealizedPnl": -4.0, "UnrealizedPnl": -6.0, "IsActive": True,
        },
        {
            "Theme": "Healthcare", "UnderlyingSymbol": "LLY", "Description": "Eli Lilly",
            "TotalFifoPnl": 9.99, "RealizedPnl": 12.0, "UnrealizedPnl": -2.01, "IsActive": True,
        },
    ]


def test_overview_threshold_kpis_and_highlights_use_visible_theme_rows(ticker_summaries):
    result = run_selector(
        ticker_summaries,
        scope={"type": "overview"},
        threshold={"mode": "gt", "amountEUR": 10},
    )
    assert [row["Theme"] for row in result["visibleRows"]] == ["Core Tech"]
    assert {row["UnderlyingSymbol"] for row in result["representedTickers"]} == {"AAPL", "MSFT"}
    assert result["kpis"] == {
        "netFifoPnl": 12.0, "realizedPnl": 1.0,
        "unrealizedPnl": 10.75, "holdings": 2,
    }
    assert result["highlights"]["isTheme"] is True
    assert result["highlights"]["best"]["Theme"] == "Core Tech"
    assert result["graphData"][0]["Theme"] == "Core Tech"


def test_threshold_is_strict_and_applies_to_ticker_rows(ticker_summaries):
    records = [*ticker_summaries, {
        "Theme": "Other", "UnderlyingSymbol": "ABNB", "Description": "Airbnb",
        "TotalFifoPnl": 10.01, "RealizedPnl": 10.01, "UnrealizedPnl": 0.0, "IsActive": False,
    }]
    gt_result = run_selector(
        records, scope={"type": "portfolio"},
        threshold={"mode": "gt", "amountEUR": 10},
    )
    lt_result = run_selector(
        records, scope={"type": "portfolio"},
        threshold={"mode": "lt", "amountEUR": 10},
    )
    assert {row["UnderlyingSymbol"] for row in gt_result["visibleRows"]} == {"ABNB"}
    assert {row["UnderlyingSymbol"] for row in lt_result["visibleRows"]} == {"AAPL", "MSFT", "LLY"}
    # NVDA's absolute PnL is exactly €10, so strict comparisons exclude it in both modes.
    assert "NVDA" not in {row["UnderlyingSymbol"] for row in gt_result["visibleRows"]}
    assert "NVDA" not in {row["UnderlyingSymbol"] for row in lt_result["visibleRows"]}
    assert gt_result["kpis"]["holdings"] == 1
    assert lt_result["kpis"]["holdings"] == 3


def test_theme_scope_active_filter_search_and_independent_pnl_kpis(ticker_summaries):
    result = run_selector(
        ticker_summaries, scope={"type": "theme", "theme": "Core Tech"},
        active_only=True, search_query="Apple",
    )
    assert [row["UnderlyingSymbol"] for row in result["visibleRows"]] == ["AAPL"]
    assert result["kpis"] == {
        "netFifoPnl": 8.25, "realizedPnl": 3.0,
        "unrealizedPnl": 5.0, "holdings": 1,
    }
    assert result["highlights"]["isTheme"] is False
    assert result["highlights"]["best"]["UnderlyingSymbol"] == "AAPL"


def test_search_uses_comma_and_whitespace_tokens_as_or_matches_across_fields(ticker_summaries):
    result = run_selector(
        ticker_summaries,
        scope={"type": "portfolio"},
        search_query="MSFT, Apple Semiconductors",
    )
    assert {row["UnderlyingSymbol"] for row in result["visibleRows"]} == {
        "AAPL", "MSFT", "NVDA",
    }


def test_search_exclusions_take_precedence_and_bare_minus_is_ignored(ticker_summaries):
    excluded = run_selector(
        ticker_summaries,
        scope={"type": "portfolio"},
        search_query="Apple, NVIDIA -Core",
    )
    assert {row["UnderlyingSymbol"] for row in excluded["visibleRows"]} == {"NVDA"}

    bare_minus = run_selector(
        ticker_summaries,
        scope={"type": "portfolio"},
        search_query="-",
    )
    assert {row["UnderlyingSymbol"] for row in bare_minus["visibleRows"]} == {
        "AAPL", "MSFT", "NVDA", "LLY",
    }


def test_overview_threshold_is_applied_to_aggregated_theme_rows(ticker_summaries):
    result = run_selector(
        ticker_summaries,
        scope={"type": "overview"},
        threshold={"mode": "lt", "amountEUR": 10},
    )
    # Core Tech aggregates to €12 and Semiconductors is exactly -€10, so only Healthcare remains.
    assert {row["Theme"] for row in result["visibleRows"]} == {"Healthcare"}
    assert result["kpis"] == {
        "netFifoPnl": 9.99, "realizedPnl": 12.0,
        "unrealizedPnl": -2.01, "holdings": 1,
    }


def test_portfolio_scope_keeps_all_ticker_rows_and_kpis_deduplicate_holdings(ticker_summaries):
    duplicate_symbol = {
        "Theme": "Other", "UnderlyingSymbol": "AAPL", "Description": "Apple class B",
        "TotalFifoPnl": 1.0, "RealizedPnl": 2.0, "UnrealizedPnl": -1.0,
        "IsActive": True,
    }
    records = [*ticker_summaries, duplicate_symbol]
    result = run_selector(records, scope={"type": "portfolio"})

    assert len(result["displayRows"]) == len(records)
    assert len(result["visibleRows"]) == len(records)
    assert result["kpis"] == {
        "netFifoPnl": 12.99, "realizedPnl": 11.0,
        "unrealizedPnl": 1.74, "holdings": 4,
    }
    visible_symbols = {row["UnderlyingSymbol"] for row in result["visibleRows"]}
    assert {row["UnderlyingSymbol"] for row in result["graphData"]} == visible_symbols
    assert result["highlights"]["best"]["UnderlyingSymbol"] == "LLY"
    assert result["highlights"]["worst"]["UnderlyingSymbol"] == "NVDA"


def test_empty_selection_has_zero_kpis_and_no_highlights_or_graph_data(ticker_summaries):
    result = run_selector(
        ticker_summaries, scope={"type": "overview"}, search_query="not-a-ticker",
    )
    assert result["eligibleTickers"] == []
    assert result["displayRows"] == []
    assert result["visibleRows"] == []
    assert result["representedTickers"] == []
    assert result["kpis"] == {
        "netFifoPnl": 0, "realizedPnl": 0,
        "unrealizedPnl": 0, "holdings": 0,
    }
    assert result["highlights"]["best"] is None
    assert result["highlights"]["worst"] is None
    assert result["graphData"] == []


def test_empty_and_invalid_threshold_values_leave_rows_unfiltered(ticker_summaries):
    unfiltered = run_selector(ticker_summaries, scope={"type": "portfolio"})
    for threshold in (
        {"mode": "gt", "amountEUR": ""},
        {"mode": "lt", "amountEUR": -1},
        {"mode": "gt", "amountEUR": "not-a-number"},
        {"mode": "lt", "amountEUR": 10, "inputValid": False},
    ):
        result = run_selector(
            ticker_summaries, scope={"type": "portfolio"}, threshold=threshold,
        )
        assert result["visibleRows"] == unfiltered["visibleRows"]
        assert result["kpis"] == unfiltered["kpis"]


def test_zero_threshold_keeps_strict_comparison_semantics(ticker_summaries):
    gt_result = run_selector(
        ticker_summaries, scope={"type": "portfolio"},
        threshold={"mode": "gt", "amountEUR": 0},
    )
    lt_result = run_selector(
        ticker_summaries, scope={"type": "portfolio"},
        threshold={"mode": "lt", "amountEUR": 0},
    )
    assert len(gt_result["visibleRows"]) == len(ticker_summaries)
    assert lt_result["visibleRows"] == []
    assert lt_result["kpis"]["holdings"] == 0


def test_threshold_mode_control_starts_unselected_without_reset_button():
    source = SOURCE.read_text(encoding="utf-8")
    less_button = source.index('id="pnl-threshold-mode-lt"')
    greater_button = source.index('id="pnl-threshold-mode-gt"')
    assert less_button < greater_button
    assert 'id="pnl-threshold-mode-lt" class="threshold-mode-btn"' in source
    assert 'id="pnl-threshold-mode-gt" class="threshold-mode-btn"' in source
    assert source.count('aria-pressed="false"') >= 2
    assert 'value="1000"' in source
    assert 'let pnlThresholdMode = null;' in source
    assert 'let pnlThresholdActive = false;' in source
    assert 'pnlThresholdActive = true;' in source
    assert 'if (pnlThresholdActive && pnlThresholdMode === mode)' in source
    assert 'pnlThresholdMode = null;' in source
    assert 'pnlThresholdActive = false;' in source
    assert 'if (!pnlThresholdActive || !pnlThresholdMode || !amountInput) return null;' in source
    assert 'pnl-threshold-control:not(.enabled) .toolbar-number-input' in source
    assert 'id="pnl-threshold-clear"' not in source
    assert 'clearPnlThreshold' not in source
    assert '<select id="pnl-threshold-mode"' not in source

def test_show_all_toggle_uses_portfolio_scope_and_removes_total_row():
    source = SOURCE.read_text(encoding="utf-8")
    assert "let showAllTickers = false;" in source
    assert "function toggleShowAllTickers()" in source
    assert "showAllTickers = !showAllTickers;" in source
    assert "const scope = showAllTickers" in source
    assert "? {{ type: 'portfolio' }}" in source
    assert 'id="show-all-tickers-btn"' in source
    assert 'onclick="drillUpToThemes()"' in source
    assert "button.textContent = showAllTickers ?" not in source
    assert "function syncShowAllTickersButton()" not in source
    assert "showAllButton.style.display = scope.type === 'portfolio' ? 'none' : 'inline-flex';" in source
    assert "drillDownToTotalPortfolio" not in source
    assert "<span>Total Portfolio</span>" not in source
    assert "Total Portfolio Drilldown" not in source


def test_header_uses_compact_navigation_and_places_view_switcher_with_global_controls():
    source = SOURCE.read_text(encoding="utf-8")
    assert "← Themes" in source
    assert "<span>Themes</span>" in source
    assert 'onclick="toggleShowAllTickers()">All tickers</button>' in source
    assert 'id="view-pnl-pill"' not in source
    assert 'id="view-count-pill"' not in source
    theme_toggle = source.index('id="theme-toggle-btn"')
    view_switcher = source.index('class="view-switcher"')
    card_header = source.index('class="card-header"')
    assert theme_toggle < view_switcher < card_header
    assert 'class="view-btn-label">Table</span>' in source
    assert 'class="view-btn-label">Graph</span>' in source
    assert 'aria-label="Switch to Table View"' in source
    assert 'aria-label="Switch to Graph View"' in source
    assert '.view-btn-label {{\n                display: none;' in source


def test_mobile_toolbar_places_search_and_compact_controls_as_requested():
    source = SOURCE.read_text(encoding="utf-8")
    card_header_start = source.index('<!-- Card Header: Breadcrumbs / Title -->')
    card_header_end = source.index('<!-- Toolbar: PnL threshold, sorting & performer highlights -->')
    card_header = source[card_header_start:card_header_end]
    assert 'class="ticker-search-box card-search-box"' in card_header
    assert 'id="ticker-search"' in card_header
    assert 'id="pnl-threshold-label">|Net|</span>' in source
    assert 'id="pnl-threshold-label">Show |Net|' not in source
    assert '.display-controls {{' in source
    assert 'grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);' in source
    assert 'grid-column: 2;' in source
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr));' in source
    assert 'class="performer-label">Best:' in source
    assert 'class="performer-label">Worst:' in source


def test_mobile_sort_control_shows_metric_and_separate_direction_toggle():
    source = SOURCE.read_text(encoding="utf-8")
    assert 'id="sort-mobile-select"' in source
    assert 'aria-label="Sort metric"' in source
    assert 'id="sort-direction-btn"' in source
    assert 'onclick="toggleSortDirection()"' in source
    assert 'function setSortMetric(col)' in source
    assert 'function toggleSortDirection()' in source
    assert "mobileSelect.value = sortColumn;" in source
    assert "directionButton.textContent = ascending ? '▲' : '▼';" in source
    assert '.sort-btn-group {{\n                display: none;' in source
    assert '.sort-mobile-control {{\n                display: inline-flex;' in source


def test_mobile_header_fits_global_controls_and_search_shares_card_header_row():
    source = SOURCE.read_text(encoding="utf-8")
    assert ".header-controls {{\n                display: flex;\n                flex-wrap: nowrap;" in source
    assert ".slice-switcher {{\n                flex: 1 1 auto;" in source
    assert ".display-controls {{ margin-left: 0; gap: 3px; }}" in source
    assert "grid-template-columns: max-content minmax(0, 1fr);" in source
    assert ".card-search-box {{\n                grid-row: auto;" in source
    assert "font-size: clamp(11px, 3.8vw, 16px) !important;" in source
    assert ".filter-toggle-pill > span:nth-child(2) {{ display: none; }}" in source
    assert "padding: 16px 20px;" in source


def test_monetary_display_rounds_to_whole_euros_across_dashboard_views():
    source = SOURCE.read_text(encoding="utf-8")
    assert "Math.round(Math.abs(numericValue))" in source
    assert "function roundEuroValue(val)" in source
    assert "dataToChart.map(t => roundEuroValue(t.TotalFifoPnl))" in source
    assert "function formatCurrency(val)" in source
    assert "formatEuroAmount(row.RealizedPnl)" in source
    assert "formatEuroAmount(row.UnrealizedPnl)" in source
    assert "formatEuroAmount(t.RealizedPnl)" in source
    assert "formatEuroAmount(t.UnrealizedPnl)" in source
    assert "%{{x:,.0f}}" in source
    assert "%{{x:,.2f}}" not in source
