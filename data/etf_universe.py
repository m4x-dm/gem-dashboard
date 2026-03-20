"""Universum 30 ETF-ów z polskimi nazwami i kategoriami."""

ETF_CATEGORIES = {
    "Akcje USA": {
        "SPY": "S&P 500 (SPDR)",
        "QQQ": "Nasdaq 100 (Invesco)",
        "VTI": "Caly rynek USA (Vanguard)",
        "VOO": "S&P 500 (Vanguard)",
        "IWM": "Russell 2000 male spolki USA",
    },
    "Rynki rozwinięte": {
        "VEA": "Rynki rozw. bez USA (Vanguard)",
        "EFA": "EAFE — Europa, Azja, Daleki Wsch.",
        "ACWI": "MSCI All Country World (iShares)",
        "VGK": "Europa (Vanguard)",
        "EWJ": "Japonia (iShares)",
        "EWU": "Wielka Brytania (iShares)",
    },
    "Rynki wschodzące": {
        "EEM": "Rynki wschodzace (iShares)",
        "VWO": "Rynki wschodzace (Vanguard)",
        "FXI": "Chiny large-cap (iShares)",
    },
    "Obligacje USA": {
        "AGG": "Obligacje zagregowane USA",
        "BND": "Obligacje calkowity rynek USA",
        "TLT": "Obligacje dlugot. 20+ lat",
        "IEF": "Obligacje sredniot. 7-10 lat",
        "SHY": "Obligacje krotkot. 1-3 lata",
        "TIP": "Obligacje indeks. inflacja",
    },
    "Zloto i surowce": {
        "GLD": "Zloto (SPDR)",
        "IAU": "Zloto (iShares)",
        "GSG": "Surowce (iShares)",
        "DBC": "Surowce (Invesco)",
    },
    "Nieruchomosci (REIT)": {
        "VNQ": "REIT USA (Vanguard)",
        "VNQI": "REIT miedzynarodowy (Vanguard)",
    },
    "Sektory USA": {
        "XLK": "Sektor technologiczny",
        "XLF": "Sektor finansowy",
        "XLE": "Sektor energetyczny",
        "XLV": "Sektor ochrony zdrowia",
        "XLI": "Sektor przemyslowy",
        "XLY": "Sektor konsumpcji cyklicznej",
        "XLP": "Sektor konsumpcji podstawowej",
        "XLC": "Sektor komunikacji",
        "XLRE": "Sektor nieruchomosci",
        "XLU": "Sektor uzytecznosci publ.",
        "XLB": "Sektor materialowy",
    },
}

# Flat dict: ticker -> nazwa PL
ETF_NAMES: dict[str, str] = {}
# Flat dict: ticker -> kategoria
ETF_CATEGORY_MAP: dict[str, str] = {}

for category, etfs in ETF_CATEGORIES.items():
    for ticker, name in etfs.items():
        ETF_NAMES[ticker] = name
        ETF_CATEGORY_MAP[ticker] = category

ALL_TICKERS = list(ETF_NAMES.keys())

# Klasyczny GEM: 3 aktywa
GEM_US = "SPY"
GEM_INTL = "VEA"
GEM_BONDS = "AGG"
RISK_FREE_TICKER = "^IRX"  # 13-week T-bill yield
