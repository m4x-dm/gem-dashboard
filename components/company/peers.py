"""Karta spolki — zakladka Porownanie z sektorem (premium)."""
import html as _h

import numpy as np
import streamlit as st

from components.constants import TEXT, MUTED, GREEN, RED, BG_HOVER, BORDER
from components.formatting import fmt_pct
from data import company as co
from data import financials as fin
from components.company.overview import _big
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES
from data.momentum import latest_returns
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES

MEDIAN = "Mediana grupy"
PCT_COLS = ("ROE", "Marża netto", "Wzrost przychodów", "Stopa dywidendy", "Momentum 12M")
SIGNED_COLS = ("Wzrost przychodów", "Momentum 12M")
MULTIPLES = ("P/E", "Forward P/E", "EV/EBITDA")
# Krotkie naglowki, zeby tabela miescila sie w kolumnie na desktopie; pelna nazwa w title=
SHORT = {"Kapitalizacja": "Kap.", "Forward P/E": "Fwd P/E", "Marża netto": "Marża",
         "Wzrost przychodów": "Wzrost przych.", "Stopa dywidendy": "Stopa dyw.",
         "Momentum 12M": "Mom. 12M"}


def build_rows(tickers, snapshots: dict, mom12) -> dict:
    """Wiersze dla peer_table. Jednostki: ROE/marza/wzrost/momentum to ulamki;
    dividend_yield z Yahoo jest w procentach -> ulamek; ujemne mnozniki (strata) -> brak."""
    rows = {}
    for t in tickers:
        r = dict(snapshots.get(t) or {})
        r["dividend_yield"] = co._norm_yield(r.get("dividend_yield"))
        for key in ("pe", "fwd_pe", "ev_ebitda"):
            v = co._f(r.get(key))
            r[key] = v if v > 0 else np.nan
        m = mom12.get(t) if mom12 is not None else None
        r["mom12"] = m
        rows[t] = r
    return rows


def fmt_cell(col: str, v, ccy: str = "$") -> str:
    if v is None or not np.isfinite(v):
        return "—"
    if col == "Kapitalizacja":
        return _big(v, ccy)     # jak w Przegladzie: "3,9 bln $", "880,6 mld $", zl dla GPW
    if col in PCT_COLS:
        s = fmt_pct(v, 1)
        return s if col in SIGNED_COLS else s.lstrip("+")
    return f"{v:.1f}".replace(".", ",")


def cell_color(col: str, v, med) -> str:
    """GREEN gdy lepiej niz mediana, RED gdy gorzej, TEXT gdy brak/rowne/nieporownywalne."""
    if v is None or med is None or not (np.isfinite(v) and np.isfinite(med)) or v == med:
        return TEXT
    if col == "Kapitalizacja":
        return TEXT
    better = v < med if col in co.LOWER_IS_BETTER else v > med
    return GREEN if better else RED


def table_html(df, ticker: str, ccy: str = "$") -> str:
    pad = "padding:6px 7px;"
    th = f"{pad}text-align:right;color:{MUTED};font-weight:500;white-space:nowrap;border-bottom:1px solid {BORDER};"
    head = f'<th style="{th}text-align:left">Spółka</th>' + "".join(
        f'<th style="{th}" title="{_h.escape(c)}">{_h.escape(SHORT.get(c, c))}</th>' for c in df.columns)
    med = df.loc[MEDIAN]
    body = ""
    for idx, r in df.iterrows():
        is_t, is_m = idx == ticker, idx == MEDIAN
        bg = f"background:{BG_HOVER};" if is_t else ""
        wt = "font-weight:700;" if is_t else ""
        lbl_col = MUTED if is_m else TEXT
        cells = f'<td style="{pad}white-space:nowrap;color:{lbl_col};{wt}">{_h.escape(idx)}</td>'
        for c in df.columns:
            v = r[c]
            col = MUTED if is_m else cell_color(c, v, med[c])
            cells += (f'<td style="{pad}text-align:right;white-space:nowrap;color:{col};{wt}'
                      f'font-variant-numeric:tabular-nums">{fmt_cell(c, v, ccy)}</td>')
        body += f'<tr style="{bg}border-bottom:1px solid {BORDER}">{cells}</tr>'
    return (f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:0.85rem">'
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


def render(ticker, market):
    try:
        sector = co.sector_of(ticker, market)
        if not sector:
            st.caption("Brak przypisanego sektora")
            return
        names = SP500_NAMES if market == "SP500" else GPW_NAMES
        with st.spinner("Pobieram kapitalizacje sektora…"):
            caps = co.sector_caps(market, sector)
        default = co.sector_peers(ticker, caps, n=5)
        options = [t for t in co._sector_members(market, sector) if t != ticker]
        chosen = st.multiselect("Porównaj z", options, default=[d for d in default if d in options],
                                max_selections=8, key=f"kpe_sel_{ticker}",
                                format_func=lambda t: f"{t} — {names.get(t, '')}".rstrip(" —"))
        universe = ALL_SP500_TICKERS if market == "SP500" else ALL_GPW_TICKERS
        try:
            mom12 = latest_returns(co.universe_prices(tuple(universe), "2y"), skip_month=True)["12M"]
        except Exception:
            mom12 = None
        tickers = [ticker, *chosen]
        snaps = {t: fin.get_ratios_snapshot(t) or {} for t in tickers}
        df = co.peer_table(build_rows(tickers, snaps, mom12))
        st.html(table_html(df, ticker, "zł" if market == "GPW" else "$"))
        st.caption("Mediana liczona dla całej wyświetlanej grupy (łącznie z wybraną spółką). "
                   "Zielony = lepiej niż mediana, czerwony = gorzej (dla mnożników: niżej = lepiej). "
                   "Ujemne mnożniki (strata) pomijane. Momentum 12M liczone bez ostatniego miesiąca.")
    except Exception:
        st.caption("Porównanie z sektorem: dane chwilowo niedostępne")
