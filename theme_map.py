"""Theme mappings and categorizations for portfolio assets."""

THEME_MAP = {
    'Big Tech': ['AAPL', 'AMZN', 'BABA', 'GOOG', 'GOOGL', 'META', 'MSFT', 'NVDA', 'TSLA'],
    'Software': ['ADBE', 'COUR', 'CRM', 'CRWD', 'CTSH', 'DOCU', 'DT', 'DUOL', 'GDDY', 'IBM', 'IGV', 'INFY', 'SAP', 'TDC', 'TEAM', 'TTWO', 'WDAY', 'ZS', 'HACK', 'CIBR', 'NEM', 'BSP'],
    'AI & Chips': ['AMD', 'ARM', 'AVGO', 'CRWV', 'DRAM', 'INTC', 'MU', 'QCOM', 'SNDK', 'SOXX', 'SFT', 'NBIS', 'ORCL', 'SNOW', 'CSCO', 'PLTR', 'LOGN', 'SOUN'],
    'Transport': ['AAL', 'AF', 'FDX', 'HTZ', 'LHA', 'PNL', 'QAN', 'RYAAY', 'WI2', 'WIZZ', 'UPS', 'XPO', 'NCLH', 'AMS', 'DHT'],
    'Space & DF': ['ASTS', 'GE', 'AIR', 'BA', 'RTX', 'LDOS', 'DFEU', 'ITA', '7011', 'SHLD', 'UMAC', 'DRNZ', 'RKLB', 'SPCX', 'SPCE', 'ETL', 'RDW', 'AADX'],
    'Health': ['AZN', 'BMY', 'NVO', 'PFE', 'ROG', 'SNY', 'ATAI', 'GHRS', 'MLTX', 'MRNA', 'XBI', 'DHR', 'HIMS', 'MDT', 'TMO', 'UNH', 'XLV', 'TEM', 'NOVN', 'ROP'],
    'Energy': ['CVX', 'EQNR', 'DNQ', 'USO', 'BNO', 'XLE', 'XOM', 'MPC', 'NEE', 'D2G', 'ENGI', 'PCG', 'XE', 'XLU', 'SXEP', 'SHELL', 'VLTSA', 'VG'],
    'Financials': ['EBS', 'SCHW', 'MA', 'IBKR', 'HOOD', 'BBVA', 'OTP', 'UCG', 'SAN', 'SPGI', 'EXX1', 'XLF', 'CRCL', 'RKT', 'KLAR', 'PYPL', 'V', 'BRK B', 'RELY'],
    'Cons Disc': ['ADS', 'AEO', 'BIRK', 'CVNA', 'GAP', 'GME', 'LULU', 'MAT', 'NKE', 'SONO', 'STUB', 'TSCO', 'XLY'],
    'Staples': ['BYND', 'BYND1', 'CALM', 'CASY', 'DLTR', 'GIS', 'HEIA', 'HEN', 'HEN3', 'NESN', 'WMT', 'XLP'],
    'Restos': ['CMG', 'JACK', 'MCD', 'PLAY', 'QSR', 'SBUX', 'SG', 'WEN', 'YUM'],
    'Comms': ['NFLX', 'SPOT', 'WBD', 'PSKY', 'T', 'VZ', 'ORA', 'VSNT', 'UBI', 'SONY', 'RDDT'],
    'Materials': ['BAS', 'LXS', 'ALB', 'LIN', 'SIKA', 'SOLB', 'MP', 'REB', 'USAR', 'LYI', 'ILZ', 'RNF', 'SJ60', 'N14', 'NCH2'],
    'Industrials': ['ACS', 'KGX', 'DHI', 'LEN', 'WY', 'ALO', 'LIGHT', 'LCID', 'CON', 'STLA', '7203', 'COLO', 'GM'],
    'Hedges': ['SPY', 'QQQ', 'QQQM', 'XSP', 'VIX', 'IWM', 'ESTX50', 'SPX', 'DJ600', 'MEME'],
    'Broad Market': ['RSP', 'FEZ', 'EWJ', 'EEM', 'ILF', 'XCS4', 'IBZL', 'XDJP', 'SXRZ', 'IKRA', 'MEUD', 'CS1', 'LYXIB', 'VGK', 'EXS1'],
    'Commodities': ['GLD', 'SLV', 'IBIT', 'DBA'],
    'FX & FI': ['USD.HUF', 'AUD', 'CHF', 'GBP', 'HUF', 'NOK', 'JPY', 'USD', 'TLT']
}

SYMBOL_TO_THEME = {sym: t for t, symbols in THEME_MAP.items() for sym in symbols}


def get_theme_for_symbol(symbol: str) -> str:
    """Return the theme mapped to the symbol, or 'Other' if not mapped."""
    return SYMBOL_TO_THEME.get(symbol, "Other")
