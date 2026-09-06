"""Theme mappings and categorizations for portfolio assets."""

THEME_MAP = {
    'Big Tech': ['AAPL', 'AMZN', 'GOOG', 'GOOGL', 'META', 'MSFT'],
    'Software & IT Services': ['ADBE', 'COUR', 'CRM', 'CRWD', 'CSCO', 'CTSH', 'DOCU', 'DT', 'DUOL', 'GDDY', 'IBM', 'IGV', 'INFY', 'LOGN', 'NBIS', 'ORCL', 'PLTR', 'RDDT', 'SAP', 'SNOW', 'SOUN', 'TDC', 'TEAM', 'WDAY', 'ZS', 'HACK', 'CIBR'],
    'Semiconductors & Hardware': ['AMD', 'ARM', 'AVGO', 'DRAM', 'INTC', 'MU', 'NVDA', 'QCOM', 'SNDK', 'SONY', 'SOXX', 'SFT'],
    'Airlines, Aviation & Logistics': ['AAL', 'AF', 'CON', 'CVNA', 'FDX', 'LCID', 'LHA', 'PNL', 'QAN', 'RYAAY', 'WI2', 'WIZZ', 'UPS', 'XPO', 'STLA', 'TSLA', '7203'],
    'Aerospace & Defense': ['AIR', 'BA', 'RTX', 'LDOS', 'DFEU', 'ITA', '7011', 'SHLD', 'UMAC', 'DRNZ'],
    'Space & Satellites': ['RKLB', 'SPCX', 'SPCE', 'ETL', 'RDW', 'AADX'],
    'Big Pharma': ['AZN', 'BMY', 'NVO', 'PFE', 'ROG', 'SNY'],
    'Biotech': ['ATAI', 'GHRS', 'MLTX', 'MRNA', 'XBI'],
    'Healthcare & Medical Devices': ['CALM', 'COLO', 'DHR', 'HIMS', 'MDT', 'TMO', 'UNH', 'XLV'],
    'Energy & Utilities': ['CVX', 'EQNR', 'DNQ', 'USO', 'BNO', 'XLE', 'XOM', 'MPC', 'NEE', 'D2G', 'ENGI', 'PCG', 'XE', 'XLU', 'SXEP', 'SHELL', 'VLTSA', 'VG'],
    'Financials & Fintech': ['MA', 'IBKR', 'HOOD', 'BBVA', 'OTP', 'UCG', 'SAN', 'SPGI', 'EXX1', 'XLF', 'CRCL', 'RKT', 'KLAR', 'PYPL', 'V', 'BRK B'],
    'Consumer Goods & Retail': ['ADS', 'BIRK', 'LULU', 'NKE', 'AEO', 'GAP', 'DLTR', 'MAT', 'WMT', 'XLY', 'XLP', 'TSCO', 'STUB', 'GME', 'SONO', 'HEN', 'HEN3', 'NCLH'],
    'Restaurants, Food & Beverages': ['MCD', 'CMG', 'QSR', 'WEN', 'SBUX', 'SG', 'HEIA', 'BYND', 'BYND1', 'NESN', 'JACK', 'PLAY', 'CASY', 'YUM', 'DBA', 'GIS'],
    'Media & Telecom': ['NFLX', 'SPOT', 'WBD', 'PSKY', 'T', 'VZ', 'ORA', 'VSNT', 'UBI', 'MEME', 'AMS'],
    'Materials & Mining': ['BAS', 'LXS', 'ALB', 'LIN', 'SIKA', 'SOLB', 'MP', 'REB', 'USAR', 'LYI', 'ILZ', 'RNF', 'SJ60', 'N14', 'NEM', 'NCH2'],
    'Industrials & Real Estate': ['ACS', 'KGX', 'DHI', 'LEN', 'ROP', 'WY', 'ALO', 'LIGHT'],
    'Portfolio Hedges & Volatility': ['SPY', 'QQQ', 'QQQM', 'XSP', 'VIX', 'IWM'],
    'Europe Broad Market ETFs': ['DJ600', 'MEUD', 'CS1', 'LYXIB', 'VGK', 'EXS1'],
    'Asia Broad Market ETFs': ['XDJP', 'SXRZ', 'IKRA'],
    'Emerging Markets ETFs': ['EEM', 'XCS4', 'IBZL'],
    'Box Spread Financing': ['ESTX50', 'SPX'],
    'Covered Call Broad Market': ['RSP', 'FEZ', 'EWJ'],
    'Precious Metals & Crypto': ['GLD', 'SLV', 'IBIT'],
    'FX': ['USD.HUF', 'AUD', 'CHF', 'GBP', 'HUF', 'NOK', 'JPY', 'USD'],
    'Fixed Income': ['TLT']
}

SYMBOL_TO_THEME = {sym: t for t, symbols in THEME_MAP.items() for sym in symbols}


def get_theme_for_symbol(symbol: str) -> str:
    """Return the theme mapped to the symbol, or 'Other' if not mapped."""
    return SYMBOL_TO_THEME.get(symbol, "Other")
