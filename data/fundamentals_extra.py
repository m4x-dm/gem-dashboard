"""Spolki spoza S&P 500 i GPW objete dziennym zrzutem danych fundamentalnych.

Popularne u inwestorow z Polski (XTB, IKE/IKZE), a nieobecne w universe S&P 500 / GPW.
Tickery Yahoo. Dopisz spolke, jesli na produkcji w Moim portfelu widzisz dla niej
"Yahoo nie zwrocil danych" — zrzut zlapie ja od nastepnego dnia.
"""

EXTRA_TICKERS: tuple[str, ...] = (
    # USA spoza S&P 500 / ADR
    "SPCX", "TSM", "ASML", "BABA", "PDD", "NVO", "ARM", "SHOP", "MELI", "SPOT", "SE", "NU",
    "SOFI", "RKLB", "ASTS", "IONQ", "RGTI", "HIMS", "NBIS", "OKLO", "CRWV", "NIO", "BIDU", "JD",
    # Europa
    "ASML.AS", "SAP.DE", "SIE.DE", "RHM.DE", "AIR.PA", "MC.PA",
)
