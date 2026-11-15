"""Deterministic tests for report data serialization and aggregation."""

import json
import re

import pandas as pd
import pytest

from report_generator import generate_html_report


@pytest.fixture
def portfolio_df():
    """Synthetic position rows covering aggregation, rounding, and active status."""
    return pd.DataFrame(
        [
            {
                "Theme": "Core Tech",
                "Symbol": "AAPL",
                "UnderlyingSymbol": "AAPL",
                "Description": "Apple Inc.",
                "TotalFifoPnl": 10.126,
                "TotalRealizedPnl": 4.125,
                "TotalUnrealizedPnl": 6.001,
            },
            {
                "Theme": "Core Tech",
                "Symbol": "AAPL 2025 Call",
                "UnderlyingSymbol": "AAPL",
                "Description": "Apple Inc. option",
                "TotalFifoPnl": -2.005,
                "TotalRealizedPnl": 1.005,
                "TotalUnrealizedPnl": -3.010,
            },
            {
                "Theme": "Semiconductors",
                "Symbol": "NVDA",
                "UnderlyingSymbol": "NVDA",
                "Description": "NVIDIA Corporation",
                "TotalFifoPnl": 20.0,
                "TotalRealizedPnl": 20.0,
                "TotalUnrealizedPnl": 0.001,
            },
            {
                "Theme": "Cash",
                "Symbol": "CASH",
                "UnderlyingSymbol": "CASH",
                "Description": "Cash balance",
                "TotalFifoPnl": 0.0,
                "TotalRealizedPnl": 0.0,
                "TotalUnrealizedPnl": 0.0,
            },
        ]
    )


def read_embedded_slices(html):
    """Read the JSON payload embedded in the generated dashboard script."""
    match = re.search(r"const TIME_SLICES = (.*);", html)
    assert match is not None, "generated HTML should include the time-slice payload"
    return json.loads(match.group(1))


def test_report_aggregates_rows_by_theme_and_underlying_ticker(
    tmp_path, portfolio_df
):
    output = tmp_path / "report.html"

    generate_html_report(portfolio_df, output_path=str(output), period_str="YTD")

    payload = read_embedded_slices(output.read_text(encoding="utf-8"))
    tickers = payload["ytd"]["tickers"]
    by_ticker = {ticker["UnderlyingSymbol"]: ticker for ticker in tickers}

    assert set(by_ticker) == {"AAPL", "NVDA", "CASH"}
    assert by_ticker["AAPL"]["Theme"] == "Core Tech"
    assert by_ticker["AAPL"]["Description"] == "Apple Inc."
    assert by_ticker["AAPL"]["TotalFifoPnl"] == 8.12
    assert by_ticker["AAPL"]["RealizedPnl"] == 5.13
    assert by_ticker["AAPL"]["UnrealizedPnl"] == 2.99
    assert by_ticker["AAPL"]["Count"] == 2


def test_report_derives_active_status_from_rounded_unrealized_pnl(
    tmp_path, portfolio_df
):
    output = tmp_path / "report.html"

    generate_html_report(portfolio_df, output_path=str(output))

    tickers = read_embedded_slices(output.read_text(encoding="utf-8"))["ytd"][
        "tickers"
    ]
    by_ticker = {ticker["UnderlyingSymbol"]: ticker for ticker in tickers}

    assert by_ticker["AAPL"]["IsActive"] is True
    # The source heuristic uses the aggregated, rounded unrealized value.
    assert by_ticker["NVDA"]["UnrealizedPnl"] == 0.0
    assert by_ticker["NVDA"]["IsActive"] is False
    assert by_ticker["CASH"]["IsActive"] is False


def test_report_serializes_all_slices_and_uses_requested_default(
    tmp_path, portfolio_df
):
    output = tmp_path / "report.html"
    slices = {
        "1d": {
            "label": "1D",
            "title": "Last business day",
            "period": "Day period",
            "df": portfolio_df.iloc[:1],
        },
        "ytd": {
            "label": "YTD",
            "title": "Year-to-date",
            "period": "Year period",
            "df": portfolio_df,
        },
    }

    generate_html_report(
        slices,
        output_path=str(output),
        default_slice="ytd",
    )

    html = output.read_text(encoding="utf-8")
    payload = read_embedded_slices(html)

    assert set(payload) == {"1d", "ytd"}
    assert payload["1d"]["period"] == "Day period"
    assert payload["ytd"]["period"] == "Year period"
    assert "let activeTimeSlice = 'ytd';" in html


def test_invalid_default_slice_falls_back_to_first_slice(tmp_path, portfolio_df):
    output = tmp_path / "report.html"

    generate_html_report(
        {
            "1d": {"df": portfolio_df.iloc[:1]},
            "ytd": {"df": portfolio_df},
        },
        output_path=str(output),
        default_slice="missing",
    )

    html = output.read_text(encoding="utf-8")
    assert "let activeTimeSlice = '1d';" in html


def test_empty_dataframe_produces_empty_ticker_payload(tmp_path):
    empty_df = pd.DataFrame(
        columns=[
            "Theme",
            "Symbol",
            "UnderlyingSymbol",
            "Description",
            "TotalFifoPnl",
            "TotalRealizedPnl",
            "TotalUnrealizedPnl",
        ]
    )
    output = tmp_path / "report.html"

    generate_html_report(empty_df, output_path=str(output))

    payload = read_embedded_slices(output.read_text(encoding="utf-8"))
    assert payload["ytd"]["tickers"] == []


def test_embedded_json_escapes_script_closing_sequences(tmp_path, portfolio_df):
    unsafe_df = portfolio_df.iloc[:1].copy()
    unsafe_df.loc[unsafe_df.index[0], "Description"] = "</script><script>alert(1)</script>"
    output = tmp_path / "report.html"

    generate_html_report(unsafe_df, output_path=str(output))

    html = output.read_text(encoding="utf-8")
    assert "<\\/script><script>alert(1)<\\/script>" in html
    payload = read_embedded_slices(html)
    assert payload["ytd"]["tickers"][0]["Description"] == (
        "</script><script>alert(1)</script>"
    )
