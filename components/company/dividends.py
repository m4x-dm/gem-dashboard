"""Karta spolki — zakladka Dywidendy: stopa, historia, kalkulator po podatku."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.cards import card_html
from components.charts import _base_layout
from components.constants import TEXT, MUTED, GOLD
from components.formatting import fmt_pct, fmt_number, money
from data import company as co
from data import financials as fin
from components.i18n import tr

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
    return money(fmt_number(x, 2), ccy)


def _tiles(s):
    pct = lambda v: fmt_pct(float(v), 2).lstrip("+") if _ok(v) else "—"
    cols = st.columns(4)
    items = [(tr("Stopa dywidendy"), pct(s.get("yield"))),
             (tr("Wskaźnik wypłaty"), pct(s.get("payout"))),
             (tr("Lata z rzędu"), str(s.get("years_paid", 0))),
             (tr("Wzrost 5 lat (CAGR)"), pct(s.get("cagr5")))]
    for c, (lbl, val) in zip(cols, items):
        with c:
            st.html(_tile(lbl, val))


def _chart(s):
    annual = s["annual"]
    fig = go.Figure(go.Bar(x=[str(y) for y in annual.index], y=annual.values, marker_color=GOLD))
    fig.update_layout(**_base_layout(height=260))
    st.markdown(tr("##### Dywidendy roczne"))
    st.plotly_chart(fig, width="stretch", key="kdv_annual")


def _table(s, ccy):
    last8 = s["last8"]
    df = pd.DataFrame({
        tr("Data"): [pd.Timestamp(d).strftime("%d.%m.%Y") for d in last8.index],
        tr("Kwota"): [fmt_number(v, 4) for v in last8.values],
        tr("Waluta"): ccy,
    }).iloc[::-1]
    st.markdown(tr("##### Ostatnie wypłaty"))
    st.dataframe(df, hide_index=True, width="stretch")


def _calc(s, market, ccy):
    st.markdown(tr("##### Kalkulator dywidendy po podatku"))
    if not _ok(s.get("yield")):
        st.caption(tr("Brak aktualnej stopy dywidendy."))
        return
    if market not in ("GPW", "SP500"):
        st.caption(tr("Kalkulator podatku dostępny dla spółek z S&P 500 i GPW"))
        return
    amount = st.number_input(tr("Kwota inwestycji") + (f" ({ccy})" if ccy else ""), min_value=0.0, value=10000.0, step=1000.0, key="kdv_amount")
    acc = st.segmented_control(tr("Konto"), list(ACC), default="Zwykłe", key="kdv_acc",
                               format_func=tr) or "Zwykłe"
    r = co.dividend_after_tax(amount, s["yield"], market, ACC[acc])
    c1, c2, c3 = st.columns(3)
    c1.metric(tr("Brutto / rok"), _money(r["gross"], ccy))
    c2.metric(tr("Podatek"), _money(r["tax"], ccy))
    c3.metric(tr("Netto / rok"), _money(r["net"], ccy))
    st.caption(tr(r["note"]))


def _safe(fn, label, *a):
    try:
        fn(*a)
    except Exception:
        st.caption(f"{label}: " + tr("dane chwilowo niedostępne"))


def render(ticker, market):
    try:
        divs = co.dividend_history(ticker)
        info = fin._fetch_info(ticker) or {}
        price = (fin.get_ratios_snapshot(ticker) or {}).get("current_price")
        s = co.dividend_summary(divs, price, info, today=pd.Timestamp.now())
        ccy = (co.company_profile(ticker) or {}).get("currency") or ""
    except Exception:
        st.caption(tr("Dywidendy: dane chwilowo niedostępne"))
        return
    if not s["pays"]:
        st.info(tr("Spółka nie wypłaca dywidendy."))
        return
    _safe(_tiles, tr("Wskaźniki dywidendy"), s)
    _safe(_chart, tr("Wykres dywidend"), s)
    _safe(_table, tr("Tabela dywidend"), s, ccy)
    _safe(_calc, tr("Kalkulator"), s, market, ccy)
