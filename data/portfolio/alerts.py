"""Alerty fundamentalne dla spolek z portfela: wyniki beat/miss, rekomendacje analitykow, insiderzy.

Spec: docs/superpowers/specs/2026-11-20-moj-portfel-alerty-design.md
Czyste funkcje: DataFrame z Yahoo (data/financials.py) -> lista Alert. Tekst alertu to polski
szablon pod tr(text, **params); liczby (procenty, USD) formatuje strona przy renderze.
Pokrycie Yahoo: analitycy i insiderzy tylko dla spolek spoza GPW (dla .WA zwraca 404).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

WINDOW_DAYS = 30          # okno zdarzen wstecz
UPCOMING_DAYS = 14        # najblizsze raporty
BEAT_PCT = 2.0            # |niespodzianka EPS| w procentach, ponizej = zgodnie z oczekiwaniami
BIG_SELL_USD = 1_000_000  # sprzedaz insidera pokazywana osobno

DATED_KINDS = ("earnings", "rating", "insider_buy", "insider_sell",
               "tech_level", "tech_cross", "tech_sma200", "tech_52w", "tech_rsi")
SUMMARY_KINDS = ("targets", "insider_sells")

_ROLE_SHORT = {
    "chief executive officer": "CEO", "chief financial officer": "CFO", "chief operating officer": "COO",
    "chief technology officer": "CTO", "general counsel": "General Counsel",
}


@dataclass
class Alert:
    date: pd.Timestamp | None
    ticker: str
    kind: str
    tone: str                 # "pos" | "neg" | "neutral"
    text: str                 # polski szablon pod tr()
    params: dict = field(default_factory=dict)


def _naive(idx) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(pd.to_datetime(idx, errors="coerce"))
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def _recent(df: pd.DataFrame | None, today: pd.Timestamp) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out.index = _naive(out.index)
    lo = today.normalize() - pd.Timedelta(days=WINDOW_DAYS)
    return out[(out.index >= lo) & (out.index <= today.normalize())]


def earnings_alerts(ticker: str, df: pd.DataFrame | None, today: pd.Timestamp,
                    report_date: pd.Timestamp | None = None) -> list[Alert]:
    """Raport z ostatnich 30 dni (beat/miss/w linii) + przyszly raport w ciagu 14 dni.

    Historia wynikow z Yahoo jest indeksowana KONCEM KWARTALU (30.09), nie dniem publikacji
    (np. 21.10). report_date (Ticker.info['earningsTimestamp']) datuje najnowszy kwartal, jesli
    wypada po jego koncu i nie pozniej niz dzis. Bez niego zostaje data konca kwartalu.
    """
    if df is None or df.empty:
        return []
    d = df.copy()
    d.index = _naive(d.index)
    today = today.normalize()
    out = []
    past = d[~d["is_future"].astype(bool) & (d.index <= today)].sort_index()
    rd = None if report_date is None else _naive([report_date])[0]
    lo = today - pd.Timedelta(days=WINDOW_DAYS)
    for i, (date, r) in enumerate(past.iterrows()):
        s = r.get("eps_surprise_pct")
        if s is None or s != s:
            continue
        when = rd if (i == len(past) - 1 and rd is not None and date < rd <= today) else date
        if when < lo:
            continue
        tone = "pos" if s >= BEAT_PCT else "neg" if s <= -BEAT_PCT else "neutral"
        out.append(Alert(when, ticker, "earnings", tone, "wynik {q}: EPS {s} vs konsensus",
                         {"q": r.get("q_label") or "", "s": float(s)}))
    fut = d[(d.index >= today) & (d.index <= today + pd.Timedelta(days=UPCOMING_DAYS))]
    for date in fut.index.sort_values()[:1]:
        out.append(Alert(date, ticker, "upcoming", "neutral", "raport kwartalny {d} ({when})",
                         {"days": int((date - today).days)}))
    return out


def analyst_alerts(ticker: str, df: pd.DataFrame | None, today: pd.Timestamp) -> list[Alert]:
    """Zmiany rekomendacji (up/down/init) osobno + jedna linia z liczba zmian cen docelowych."""
    d = _recent(df, today)
    if d.empty:
        return []
    out = []
    for date, r in d.sort_index(ascending=False).iterrows():
        action = str(r.get("Action") or "").lower()
        firm, frm, to = str(r.get("Firm") or ""), str(r.get("FromGrade") or ""), str(r.get("ToGrade") or "")
        if action in ("up", "down"):
            out.append(Alert(date, ticker, "rating", "pos" if action == "up" else "neg",
                             "{firm}: {frm} → {to}", {"firm": firm, "frm": frm, "to": to}))
        elif action == "init":
            out.append(Alert(date, ticker, "rating", "neutral", "{firm} rozpoczyna: {to}",
                             {"firm": firm, "to": to}))
    pt = d["priceTargetAction"].astype(str).str.lower() if "priceTargetAction" in d.columns else pd.Series(dtype=str)
    up, down = int((pt == "raises").sum()), int((pt == "lowers").sum())
    if up or down:
        tone = "pos" if up > down else "neg" if down > up else "neutral"
        out.append(Alert(None, ticker, "targets", tone, "ceny docelowe: {up}↑ {down}↓ (30 dni)",
                         {"up": up, "down": down}))
    return out


def _who(r) -> str:
    pos = str(r.get("Position") or "").strip()
    if pos and pos.lower() not in ("nan", "none"):
        return _ROLE_SHORT.get(pos.lower(), pos)
    return str(r.get("Insider") or "").strip() or "insider"


def insider_alerts(ticker: str, df: pd.DataFrame | None, today: pd.Timestamp) -> list[Alert]:
    """Kazdy zakup + sprzedaz >= 1 mln USD osobno, mniejsze sprzedaze jedna linia; reszta pomijana."""
    d = _recent(df, today)
    if d.empty or "Type" not in d.columns:
        return []
    out = []
    small_n, small_usd = 0, 0.0
    for date, r in d.sort_index(ascending=False).iterrows():
        typ = str(r.get("Type") or "")
        val = r.get("Value")
        val = float(val) if val is not None and val == val else float("nan")
        if typ == "Buy":
            out.append(Alert(date, ticker, "insider_buy", "pos", "zakup akcji przez insidera: {who}",
                             {"who": _who(r), "usd": val}))
        elif typ == "Sell" and val == val and val >= BIG_SELL_USD:
            out.append(Alert(date, ticker, "insider_sell", "neg", "sprzedaż akcji przez insidera: {who}",
                             {"who": _who(r), "usd": val}))
        elif typ == "Sell":
            small_n += 1
            small_usd += val if val == val else 0.0
    if small_n:
        out.append(Alert(None, ticker, "insider_sells", "neg", "{n} mniejszych sprzedaży insiderów (30 dni)",
                         {"n": small_n, "usd": small_usd}))
    return out


def sort_alerts(items: list[Alert]) -> list[Alert]:
    """Zdarzenia z data (najnowsze) -> podsumowania -> najblizsze raporty (rosnaco) -> brak danych."""
    dated = sorted([a for a in items if a.kind in DATED_KINDS], key=lambda a: a.date, reverse=True)
    summaries = [a for a in items if a.kind in SUMMARY_KINDS]
    upcoming = sorted([a for a in items if a.kind == "upcoming"], key=lambda a: a.date)
    rest = sorted([a for a in items if a.kind not in DATED_KINDS + SUMMARY_KINDS + ("upcoming",)],
                  key=lambda a: a.kind != "fetch_failed")
    return dated + summaries + upcoming + rest


def _has(df) -> bool:
    return isinstance(df, pd.DataFrame) and not df.empty


def _is_gpw(ticker: str) -> bool:
    return ticker.upper().endswith(".WA")


def collect(tickers: tuple[str, ...], today: pd.Timestamp,
            fetch_earnings: Callable, fetch_ratings: Callable, fetch_insiders: Callable,
            fetch_report_date: Callable | None = None, max_workers: int = 6,
            status: dict | None = None) -> list[Alert]:
    """Alerty dla wszystkich tickerow (rownolegle).

    status (opcjonalny slownik do wypelnienia): {ticker: {"earnings"|"ratings"|"insiders":
    "ok" | "empty" | "error" | "skip"}} — diagnostyka zrodel na stronie.
    Spolka bez zadnych danych: GPW -> linia 'no_data' (Yahoo tego nie ma), pozostale ->
    'fetch_failed' (Yahoo nie odpowiedzial, np. blokada IP Streamlit Cloud — sprobuj pozniej).
    """
    def one(t: str) -> tuple[str, list[Alert], bool, dict]:
        items, has, st_ = [], False, {}

        def earn_build(tk, df, day):
            rd = None
            if fetch_report_date is not None:
                try:
                    rd = fetch_report_date(tk)
                except Exception:
                    rd = None
            return earnings_alerts(tk, df, day, rd)

        sources = [("earnings", fetch_earnings, earn_build),
                   ("ratings", fetch_ratings, analyst_alerts),
                   ("insiders", fetch_insiders, insider_alerts)]
        for name, fetch, build in sources:
            if name != "earnings" and _is_gpw(t):
                st_[name] = "skip"
                continue
            try:
                df = fetch(t)
            except Exception:
                st_[name] = "error"
                continue
            if _has(df):
                has = True
                st_[name] = "ok"
                items += build(t, df, today)
            else:
                st_[name] = "empty"
        return t, items, has, st_

    out, gpw_missing, failed = [], [], []
    if not tickers:
        return out
    with ThreadPoolExecutor(max_workers=min(max_workers, len(tickers))) as ex:
        for t, items, has, st_ in ex.map(one, tickers):
            out += items
            if status is not None:
                status[t] = st_
            if not has:
                (gpw_missing if _is_gpw(t) else failed).append(t)
    if failed:
        names = ", ".join(sorted(failed))
        out.append(Alert(None, names, "fetch_failed", "neutral",
                         "Yahoo nie zwrócił danych: {tickers} — spróbuj ponownie za kilka minut",
                         {"tickers": names}))
    if gpw_missing:
        names = ", ".join(sorted(gpw_missing))
        out.append(Alert(None, names, "no_data", "neutral", "brak danych Yahoo: {tickers}",
                         {"tickers": names}))
    return sort_alerts(out)
