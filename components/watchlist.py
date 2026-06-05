"""Watchlist user-defined (localStorage przez streamlit-local-storage).

Cross-feature module — uzywany przez:
- pages/22_earnings_calendar.py (filter "tylko watchlist")
- (v2) pages/7_sp500.py + 8_gpw.py screener F13 (filter)

Format storage: JSON array tickerow (sorted, deduplicated).
Klucz wersjonowany ("_v1") na wypadek przyszlej migracji.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from streamlit_local_storage import LocalStorage

WATCHLIST_KEY = "gem_dashboard_watchlist_v1"


def get_watchlist(ls: "LocalStorage") -> set[str]:
    """Zwraca set tickerow w watchlistui. Pusty set gdy brak / corrupt."""
    raw = ls.getItem(WATCHLIST_KEY)
    if not raw:
        return set()
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return set()
        return set(str(t) for t in data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return set()


def save_watchlist(ls: "LocalStorage", tickers: set[str]) -> None:
    """Zapisuje watchlist (sorted JSON array)."""
    ls.setItem(WATCHLIST_KEY, json.dumps(sorted(tickers)))


def toggle_ticker(ls: "LocalStorage", ticker: str) -> bool:
    """Toggle ticker w watchlistui.

    Returns: True jesli w watchlistui PO toggle, False wpp.
    """
    wl = get_watchlist(ls)
    if ticker in wl:
        wl.discard(ticker)
        save_watchlist(ls, wl)
        return False
    wl.add(ticker)
    save_watchlist(ls, wl)
    return True
