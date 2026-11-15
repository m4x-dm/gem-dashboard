"""Wspolne stale — kolory tematu i mapy okresow."""

# Kolory tematu (szata B — nowoczesny fintech)
BG = "#0E1117"
BG2 = "#0B0E14"
BG_CARD = "#151922"
BG_HOVER = "#1A1F29"
BORDER = "#232937"
TEXT = "#E6E8EC"
MUTED = "#7C8595"
GOLD = "#D4B062"
GOLD_SOFT = "rgba(212,176,98,0.12)"
GREEN = "#34D399"
RED = "#F87171"
AMBER = "#FBBF24"
GRID = "rgba(255,255,255,0.05)"
SHADOW = "0 1px 0 rgba(255,255,255,.03) inset, 0 8px 24px rgba(0,0,0,.25)"

# Paleta kolorow do wykresow (8 kolorow)
CHART_COLORS = [GOLD, "#60A5FA", "#34D399", "#F87171", "#A78BFA", "#FBBF24", "#F472B6", "#22D3EE"]

# Mapa okresow — pelna (do Porownanie, Wykresy)
PERIOD_MAP_FULL = {
    "Strategia 12-1": "2y",
    "1 miesiac": "1mo",
    "3 miesiace": "3mo",
    "6 miesiecy": "6mo",
    "1 rok": "1y",
    "2 lata": "2y",
    "5 lat": "5y",
    "10 lat": "10y",
    "Maksymalny": "max",
}

# Mapa okresow — backtest (bez krotkich)
PERIOD_MAP_BACKTEST = {
    "2 lata": "2y",
    "5 lat": "5y",
    "10 lat": "10y",
    "Maksymalny": "max",
}
