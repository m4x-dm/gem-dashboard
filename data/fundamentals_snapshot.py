"""Dzienny zrzut danych fundamentalnych z GitHub Actions (wyniki, data raportu, analitycy, insiderzy).

Spec: docs/superpowers/specs/2026-11-20-fundamentals-snapshot-design.md
Yahoo odrzuca zapytania quoteSummary z IP Streamlit Cloud (2026-11-20), a z GitHub Actions
je obsluguje. scripts/update_fundamentals.py codziennie zapisuje fundamentals.json.gz na galezi
`data-snapshots`; funkcje z data/financials.py najpierw pytaja ten zrzut, dopiero potem Yahoo.

Rodzaje (`kind`): "eh" historia wynikow, "rd" data ostatniego raportu, "nd" data nastepnego,
"ud" zmiany rekomendacji, "ins" transakcje insiderow, "espi" komunikaty ESPI (GPW, z Bankiera —
Bankier odpowiada 403 serwerom Streamlit Cloud, 2026-11-20).
"""
from __future__ import annotations

import gzip
import json
import math
import os
import threading
import time

import pandas as pd
import requests

URL = ("https://raw.githubusercontent.com/m4x-dm/gem-dashboard/"
       "data-snapshots/fundamentals.json.gz")
MAX_AGE = pd.Timedelta(days=3)
OK_TTL = 3600          # s — udane pobranie
FAIL_TTL = 300         # s — po porazce nie probujemy co wywolanie (timeouty)
VERSION = 1
FRAME_KINDS = ("eh", "ud", "ins", "espi")
DATE_KINDS = ("rd", "nd")

_lock = threading.Lock()
_state: dict = {"at": None, "snap": None, "ok": False, "test": False}


# --------------------------------------------------------------------------- zapis

def _frame_to_split(df: pd.DataFrame | None) -> dict | None:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    idx = pd.DatetimeIndex(pd.to_datetime(df.index, errors="coerce"))
    if idx.tz is not None:
        idx = idx.tz_localize(None)

    def clean(v):
        if v is None:
            return None
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        if hasattr(v, "item"):  # numpy skalary -> python
            v = v.item()
            if isinstance(v, float) and math.isnan(v):
                return None
        if isinstance(v, pd.Timestamp):
            return v.isoformat()
        return v

    return {"index": [d.strftime("%Y-%m-%d") if not pd.isna(d) else None for d in idx],
            "columns": [str(c) for c in df.columns],
            "data": [[clean(v) for v in row] for row in df.itertuples(index=False, name=None)]}


def _date_str(v) -> str | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        return pd.Timestamp(v).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def build_payload(per_ticker: dict[str, dict], generated_at: pd.Timestamp) -> dict:
    """{ticker: {"eh": df|None, "rd": ts|None, "nd": ts|None, "ud": df|None, "ins": df|None}} -> JSON."""
    out = {}
    for t, d in per_ticker.items():
        rec = {}
        for k in FRAME_KINDS:
            s = _frame_to_split(d.get(k))
            if s is not None:
                rec[k] = s
        for k in DATE_KINDS:
            s = _date_str(d.get(k))
            if s is not None:
                rec[k] = s
        out[t] = rec
    ts = pd.Timestamp(generated_at)
    if ts.tz is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return {"version": VERSION, "generated_at": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "tickers": out}


# --------------------------------------------------------------------------- odczyt

class Snapshot:
    def __init__(self, generated_at: pd.Timestamp, tickers: dict):
        self.generated_at = generated_at
        self._t = tickers
        self._frames: dict = {}

    @classmethod
    def from_payload(cls, payload: dict) -> "Snapshot":
        ts = pd.Timestamp(payload["generated_at"].rstrip("Z"))
        return cls(ts, payload.get("tickers") or {})

    def lookup(self, kind: str, ticker: str):
        """(trafienie, wartosc). Spolka w zrzucie = trafienie, takze gdy pole puste (wartosc None)."""
        rec = self._t.get(ticker)
        if rec is None:
            return False, None
        raw = rec.get(kind)
        if raw is None:
            return True, None
        if kind in DATE_KINDS:
            return True, pd.Timestamp(raw)
        key = (kind, ticker)
        if key not in self._frames:
            df = pd.DataFrame(raw["data"], columns=raw["columns"],
                              index=pd.DatetimeIndex(pd.to_datetime(raw["index"])))
            self._frames[key] = df
        return True, self._frames[key].copy()


def _enabled() -> bool:
    return os.environ.get("GEM_FUNDAMENTALS_SNAPSHOT", "1") != "0"


def _download() -> dict:
    url = os.environ.get("GEM_FUNDAMENTALS_URL", URL)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return json.loads(gzip.decompress(resp.content))


def snapshot(now: pd.Timestamp | None = None) -> Snapshot | None:
    """Aktualny zrzut (cache w pamieci: sukces 1 h, porazka 5 min) albo None (wylaczony / stary / brak)."""
    if not _enabled():
        return None
    now = pd.Timestamp.now(tz="UTC").tz_localize(None) if now is None else pd.Timestamp(now)
    with _lock:
        if not _state["test"]:
            at = _state["at"]
            ttl = OK_TTL if _state["ok"] else FAIL_TTL
            if at is None or (now - at).total_seconds() > ttl:
                try:
                    payload = _download()
                    _state.update(snap=Snapshot.from_payload(payload), ok=True)
                except Exception:
                    _state.update(snap=None, ok=False)
                _state["at"] = now
        snap = _state["snap"]
    if snap is None or now - snap.generated_at > MAX_AGE:
        return None
    return snap


def lookup(kind: str, ticker: str, now: pd.Timestamp | None = None):
    """(trafienie, wartosc) z aktualnego zrzutu; bez zrzutu (False, None) -> pytaj Yahoo."""
    snap = snapshot(now)
    if snap is None:
        return False, None
    return snap.lookup(kind, ticker)


def generated_at() -> pd.Timestamp | None:
    snap = snapshot()
    return None if snap is None else snap.generated_at


def set_for_tests(payload: dict | None) -> None:
    with _lock:
        _state.update(at=time.time(), snap=None if payload is None else Snapshot.from_payload(payload),
                      ok=payload is not None, test=True)


def reset() -> None:
    with _lock:
        _state.update(at=None, snap=None, ok=False, test=False)
