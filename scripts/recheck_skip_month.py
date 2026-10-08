"""Re-test konwencji momentum dla koszykow ETF: 12M-1 (273/21) vs czyste 12M (252/0).

Powod istnienia: default zmieniono 2026-05-23 na czyste 12M, ale liczby z pierwotnego
uzasadnienia nie odtworzyly sie w audycie 2026-10-08. Ten skrypt pozwala powtorzyc
pomiar w dowolnym momencie zamiast polegac na zapisanych liczbach.

Uruchomienie:
    python scripts/recheck_skip_month.py

Jesli yfinance zwraca "TypeError: 'NoneType' object is not subscriptable" na maszynie
z Nortonem, ustaw najpierw polaczony bundle certyfikatow:
    SSL_CERT_FILE / REQUESTS_CA_BUNDLE / CURL_CA_BUNDLE
    = certifi.where() + C:\\ProgramData\\Norton\\Antivirus\\wscert.pem
"""
from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf

from data.momentum import backtest_gem

TICKERS = ["QQQ", "VEA", "EEM", "ACWI", "AGG"]
START = "2012-01-01"
# UWAGA: backtest_gem przyjmuje risk_free_annual w PROCENTACH (rf_decimal = arg/100).
# RF = 0.02 oznaczaloby 0,02%, a nie 2% — latwa pomylka, ktora raz juz zafalszowala
# test wrazliwosci. 4.0 = 4%.
RF = 4.0

VARIANTS = [
    ("12M-1 klasyczne (273/21)", {"lookback": 273, "skip": 21}),
    ("czyste 12M      (252/0)", {"lookback": 252, "skip": 0}),
]


def load_prices() -> pd.DataFrame:
    raw = yf.download(TICKERS, start=START, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        raise SystemExit(
            "Brak danych z yfinance. Na maszynie z Nortonem ustaw SSL_CERT_FILE "
            "(certifi + wscert.pem) — patrz docstring."
        )
    return raw["Close"][TICKERS].dropna()


def stats_for(px: pd.DataFrame, **kw) -> dict | None:
    res = backtest_gem(px, RF, **kw)
    return None if res is None else res["stats"]["GEM"]


def main() -> None:
    px = load_prices()
    print("Dane: %s -> %s (%d sesji)\n" % (px.index[0].date(), px.index[-1].date(), len(px)))

    print("PELNY OKRES")
    print("  %-26s %8s %8s %8s" % ("", "CAGR", "Sharpe", "trades"))
    for label, kw in VARIANTS:
        s = stats_for(px, **kw)
        res = backtest_gem(px, RF, **kw)
        print("  %-26s %7.2f%% %8.2f %8d"
              % (label, s["CAGR"] * 100, s["Sharpe"], len(res["signals"])))

    print("\nOKNA KROCZACE 5-LETNIE (CAGR 12M-1 minus czyste 12M, p.p.)")
    print("  Dodatnie = 12M-1 lepsze, ujemne = czyste 12M lepsze.")
    years = sorted({d.year for d in px.index})
    for y0 in years:
        sub = px[(px.index.year >= y0) & (px.index.year < y0 + 5)]
        if len(sub) < 1100:
            continue
        a, b = stats_for(sub, **VARIANTS[0][1]), stats_for(sub, **VARIANTS[1][1])
        if a is None or b is None:
            continue
        diff = (a["CAGR"] - b["CAGR"]) * 100
        print("  %d-%d  %+6.2f p.p.  %s"
              % (y0, y0 + 4, diff, ("+" if diff > 0 else "-") * min(int(abs(diff)), 30)))

    print("\nKONTROLA LOOKAHEADU (skip=0 vs skip=1 — ten sam okno, sygnal o dzien wczesniej)")
    s0, s1 = stats_for(px, lookback=252, skip=0), stats_for(px, lookback=252, skip=1)
    print("  skip=0: CAGR %.2f%%   skip=1: CAGR %.2f%%   roznica %+.2f p.p."
          % (s0["CAGR"] * 100, s1["CAGR"] * 100, (s0["CAGR"] - s1["CAGR"]) * 100))


if __name__ == "__main__":
    main()
