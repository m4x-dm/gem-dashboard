"""Mapowanie tickerow XTB (np. META.US, SNT.PL) na tickery Yahoo Finance."""
from __future__ import annotations

# przyrostek XTB -> (przyrostek Yahoo, waluta notowan)
_SUFFIX: dict[str, tuple[str, str]] = {
    "US": ("", "USD"),
    "PL": (".WA", "PLN"),
    "DE": (".DE", "EUR"),
    "NL": (".AS", "EUR"),
    "FR": (".PA", "EUR"),
    "UK": (".L", "GBP"),
}


def _split(xtb_ticker: str) -> tuple[str, str] | None:
    base, sep, suffix = (xtb_ticker or "").rpartition(".")
    if not sep or not base or suffix.upper() not in _SUFFIX:
        return None
    return base, suffix.upper()


def xtb_to_yahoo(xtb_ticker: str) -> str | None:
    """META.US -> META, BRK.B.US -> BRK-B, SNT.PL -> SNT.WA; nieznana gielda -> None."""
    parts = _split(xtb_ticker)
    if parts is None:
        return None
    base, suffix = parts
    yahoo_suffix, _ = _SUFFIX[suffix]
    if suffix == "US":
        base = base.replace(".", "-")  # Yahoo: klasy akcji przez myslnik
    return f"{base}{yahoo_suffix}"


def currency_for(xtb_ticker: str) -> str | None:
    parts = _split(xtb_ticker)
    return _SUFFIX[parts[1]][1] if parts else None


def price_divisor(xtb_ticker: str) -> float:
    """Yahoo podaje kursy z LSE w pensach (GBp) — dzielimy przez 100."""
    parts = _split(xtb_ticker)
    return 100.0 if parts and parts[1] == "UK" else 1.0


def fx_ticker(currency: str | None) -> str | None:
    """Ticker Yahoo kursu waluty do PLN (PLN / brak waluty -> None)."""
    if not currency or currency == "PLN":
        return None
    return f"{currency}PLN=X"
