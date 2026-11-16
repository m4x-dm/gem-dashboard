"""Karta spolki — zakladka Dywidendy: stopa, historia, kalkulator po podatku."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.cards import card_html
from components.charts import _base_layout
from components.constants import TEXT, MUTED, GOLD
from components.formatting import fmt_pct
from data import company as co
from data import financials as fin

NUM = "font-variant-numeric:tabular-nums;"
ACC = {"Zwykłe": "zwykle", "IKE": "ike", "IKZE": "ikze"}


def _ok(x) -> bool:
    try:
        return x is not None and bool(np.isfinite(float(x)))
    except (TypeError, ValueError):
        return False


def _tile(label, value) -> str:
    return card_html(
        f'<div style="font-size:12px;color:{MUTED};margin-bottom:6px">{label}</div>'
        f'<div style="font-size:22px;font-weight:650;color:{TEXT};{NUM}">{value}</div>')


def _money(x, ccy) -> str:
    return f"{x:,.2f} {ccy}".replace(",", " ").replace(".", ",").strip()


def _tiles(s):
    pct = lambda v: fmt_pct(float(v), 2).lstrip("+") if _ok(v) else "—"
    cols = st.columns(4)
    items = [("Stopa dywidendy", pct(s.get("yield"))),
             ("Wskaźnik wypłaty", pct(s.get("payout"))),
             ("Lata z rzędu", str(s.get("years_paid", 0))),
             ("Wzrost 5 lat (CAGR)", pct(s.get("cagr5")))]
    for c, (lbl, val) in zip(cols, items):
        with c:
            st.html(_tile(lbl, val))


def _chart(s):
    annual = s["annual"]
    fig = go.Figure(go.Bar(x=[str(y) for y in annual.index], y=annual.values, marker_color=GOLD))
    fig.update_layout(**_base_layout(height=260))
    st.markdown("##### Dywidendy roczne")
    st.plotly_chart(fig, use_container_width=True, key="kdv_annual")


def _table(s, ccy):
    last8 = s["last8"]
    df = pd.DataFrame({
        "Data": [pd.Timestamp(d).strftime("%d.%m.%Y") for d in last8.index],
        "Kwota": [f"{v:,.4f}".replace(",", " ").replace(".", ",") for v in last8.values],
        "Waluta": ccy,
    }).iloc[::-1]
    st.markdown("##### Ostatnie wypłaty")
    st.dataframe(df, hide_index=True, use_container_width=True)


def _calc(s, market, ccy):
    st.markdown("##### Kalkulator dywidendy po podatku")
    if not _ok(s.get("yield")):
        st.caption("Brak aktualnej stopy dywidendy.")
        return
    if market not in ("GPW", "SP500"):
        st.caption("Kalkulator podatku dostępny dla spółek z S&P 500 i GPW")
        return
    amount = st.number_input(f"Kwota inwestycji ({ccy})" if ccy else "Kwota inwestycji", min_value=0.0, value=10000.0, step=1000.0, key="kdv_amount")
    acc = st.segmented_control("Konto", list(ACC), default="Zwykłe", key="kdv_acc") or "Zwykłe"
    r = co.dividend_after_tax(amount, s["yield"], market, ACC[acc])
    c1, c2, c3 = st.columns(3)
    c1.metric("Brutto / rok", _money(r["gross"], ccy))
    c2.metric("Podatek", _money(r["tax"], ccy))
    c3.metric("Netto / rok", _money(r["net"], ccy))
    st.caption(r["note"])


def _safe(fn, label, *a):
    try:
        fn(*a)
    except Exception:
        st.caption(f"{label}: dane chwilowo niedostępne")


def render(ticker, market):
    try:
        divs = co.dividend_history(ticker)
        info = fin._fetch_info(ticker) or {}
        price = (fin.get_ratios_snapshot(ticker) or {}).get("current_price")
        s = co.dividend_summary(divs, price, info, today=pd.Timestamp.now())
        ccy = (co.company_profile(ticker) or {}).get("currency") or ""
    except Exception:
        st.caption("Dywidendy: dane chwilowo niedostępne")
        return
    if not s["pays"]:
        st.info("Spółka nie wypłaca dywidendy.")
        return
    _safe(_tiles, "Wskaźniki dywidendy", s)
    _safe(_chart, "Wykres dywidend", s)
    _safe(_table, "Tabela dywidend", s, ccy)
    _safe(_calc, "Kalkulator", s, market, ccy)
