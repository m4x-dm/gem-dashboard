"""Dlugoterminowe stopy zwrotu ETF-ow (do 30 lat) — logika strony 6_stopy_zwrotu.

Wszystko na danych miesiecznych (cena z konca miesiaca). Czyste funkcje
na gorze pliku, warstwa pobierania z cache na dole.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

PERIOD_YEARS: tuple[int, ...] = (1, 3, 5, 10, 15, 20, 25, 30)


def period_label(years: int) -> str:
    """Polska etykieta okresu: 1 rok, 3 lata, 5 lat, 22 lata, 25 lat."""
    if years == 1:
        return "1 rok"
    if years % 10 in (2, 3, 4) and years % 100 not in (12, 13, 14):
        return f"{years} lata"
    return f"{years} lat"


def to_monthly(daily: pd.Series, today: pd.Timestamp | None = None) -> pd.Series:
    """Ceny z konca miesiaca (indeks = koniec miesiaca), bez biezacego niepelnego miesiaca."""
    s = daily.dropna()
    if s.empty:
        return s.astype(float)
    m = s.resample("ME").last().dropna()
    ref = pd.Timestamp(today) if today is not None else pd.Timestamp.today()
    current_month_end = ref.normalize() + pd.offsets.MonthEnd(0)
    if len(m) and m.index[-1] >= current_month_end:
        m = m.iloc[:-1]
    return m.astype(float)
