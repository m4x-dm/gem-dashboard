"""Wspolne stale — kolory tematu i mapy okresow."""

# Kolory tematu
GOLD = "#C9A84C"
GREEN = "#22C55E"
RED = "#EF4444"
MUTED = "#9CA3AF"
BG = "#0B0E1A"
BG2 = "#111827"
BG_CARD = "#141929"
BORDER = "rgba(201,168,76,0.2)"
GRID = "rgba(255,255,255,0.06)"
AMBER = "#F59E0B"

# Paleta kolorow do wykresow (8 kolorow)
CHART_COLORS = [GOLD, "#3B82F6", GREEN, RED, "#A855F7", AMBER, "#EC4899", "#06B6D4"]

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
