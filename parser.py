"""Parsers to convert IBKR Flex XML into normalized DataFrames."""

import xml.etree.ElementTree as ET
import pandas as pd
from theme_map import get_theme_for_symbol


def parse_xml_to_df(xml_data: str) -> pd.DataFrame:
    """Parse IBKR Flex statement XML into a pandas DataFrame.

    Prioritizes FIFOPerformanceSummaryUnderlying to prevent double counting.
    Falls back to individual Trade and OpenPosition tags if summary is missing.
    """
    root = ET.fromstring(xml_data)
    records = []

    # Primary source: FIFO Performance Summary Underlying
    for item in root.iter("FIFOPerformanceSummaryUnderlying"):
        symbol = (item.get("symbol") or "").strip()
        underlying = (item.get("underlyingSymbol") or "").strip() or symbol
        desc = (item.get("description") or "").strip()

        # Filter out IBKR's portfolio summary row ('Total (All Assets)')
        if desc.lower().startswith("total") or (not symbol and not underlying):
            continue

        records.append({
            "Symbol": symbol,
            "UnderlyingSymbol": underlying,
            "Description": desc,
            "TotalFifoPnl": float(item.get("totalFifoPnl", 0.0) or 0.0),
            "TotalRealizedPnl": float(item.get("totalRealizedPnl", 0.0) or 0.0),
            "TotalUnrealizedPnl": float(item.get("totalUnrealizedPnl", 0.0) or 0.0)
        })

    # Fallback only: parse Trade and OpenPosition if no FIFOPerformanceSummaryUnderlying records exist
    if not records:
        for trade in root.iter("Trade"):
            symbol = (trade.get("symbol") or "").strip()
            underlying = (trade.get("underlyingSymbol") or "").strip() or symbol
            desc = (trade.get("description") or "").strip()
            if desc.lower().startswith("total") or (not symbol and not underlying):
                continue
            records.append({
                "Symbol": symbol,
                "UnderlyingSymbol": underlying,
                "Description": desc,
                "TotalFifoPnl": float(trade.get("fifoPnlRealized", 0.0) or 0.0),
                "TotalRealizedPnl": float(trade.get("fifoPnlRealized", 0.0) or 0.0),
                "TotalUnrealizedPnl": 0.0
            })

        for pos in root.iter("OpenPosition"):
            symbol = (pos.get("symbol") or "").strip()
            underlying = (pos.get("underlyingSymbol") or "").strip() or symbol
            desc = (pos.get("description") or "").strip()
            if desc.lower().startswith("total") or (not symbol and not underlying):
                continue
            records.append({
                "Symbol": symbol,
                "UnderlyingSymbol": underlying,
                "Description": desc,
                "TotalFifoPnl": float(pos.get("fifoPnlUnrealized", 0.0) or 0.0),
                "TotalRealizedPnl": 0.0,
                "TotalUnrealizedPnl": float(pos.get("fifoPnlUnrealized", 0.0) or 0.0)
            })

    df = pd.DataFrame(records)
    if df.empty:
        print("Warning: No records found in Flex report XML.")
        df = pd.DataFrame(columns=[
            "Symbol", "UnderlyingSymbol", "Description",
            "TotalFifoPnl", "TotalRealizedPnl", "TotalUnrealizedPnl", "Theme"
        ])
    else:
        df["Theme"] = df["UnderlyingSymbol"].map(get_theme_for_symbol)

    return df
