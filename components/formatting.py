"""Polskie formatowanie: procenty, liczby, kolory."""

import numpy as np
import pandas as pd

from components.constants import GOLD, GREEN, RED, MUTED, BG, BG2, BG_CARD, BORDER  # noqa: F401


def fmt_pct(value: float | None, decimals: int = 2) -> str:
    """Formatuje procent: +12,34% / -5,67%."""
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return "—"
    v = value * 100
    sign = "+" if v > 0 else ""
    return f"{sign}{v:,.{decimals}f}%".replace(",", " ").replace(".", ",")


def fmt_number(value: float | None, decimals: int = 0) -> str:
    """Formatuje liczbę po polsku: 10 000, 1 234,56."""
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return "—"
    if decimals == 0:
        return f"{value:,.0f}".replace(",", " ")
    formatted = f"{value:,.{decimals}f}"
    parts = formatted.split(".")
    integer_part = parts[0].replace(",", " ")
    return f"{integer_part},{parts[1]}"


def color_for_value(value: float | None) -> str:
    """Zwraca kolor: zielony dla dodatnich, czerwony dla ujemnych."""
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return MUTED
    return GREEN if value > 0 else RED if value < 0 else MUTED


def styled_pct(value: float | None, decimals: int = 2) -> str:
    """HTML span z kolorowym procentem."""
    color = color_for_value(value)
    text = fmt_pct(value, decimals)
    return f'<span style="color:{color};font-weight:600">{text}</span>'


def signal_badge(signal: str) -> str:
    """HTML badge dla sygnału GEM."""
    colors = {
        "QQQ": (GREEN, "Akcje USA"),
        "VEA": ("#3B82F6", "Akcje miedzynar."),
        "AGG": ("#F59E0B", "Obligacje"),
        "TAK": (GREEN, "TAK"),
        "NIE": (RED, "NIE"),
    }
    color, label = colors.get(signal, (MUTED, signal))
    return (
        f'<span style="background:{color}20;color:{color};padding:4px 12px;'
        f'border-radius:20px;font-weight:700;font-size:0.85rem">{label}</span>'
    )
