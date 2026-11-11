"""Strona 6 (premium, id 26): Stopy zwrotu dlugoterminowe — porownanie ETF-ow do 30 lat."""

import math

import pandas as pd
import streamlit as st

from components.auth import require_premium
from components.charts import growth_chart, rolling_returns_chart, yearly_returns_heatmap
from components.formatting import fmt_pct
from components.sidebar import get_risk_free, render_footer, setup_sidebar
from data.etf_universe import ALL_TICKERS, ETF_NAMES
from data.long_returns import (
    PERIOD_YEARS, PROXY_MAP, SINCE_START,
    align_end, annual_volatility, calendar_year_returns, common_window,
    convert_to_pln, data_since_label, fetch_usdpln_monthly, load_monthly,
    period_label, period_returns, rolling_cagr, rolling_summary,
)
from data.momentum import calc_stats

st.set_page_config(page_title="Stopy zwrotu", page_icon="📏", layout="wide")
setup_sidebar()
if not require_premium(26):
    st.stop()


def _fmt_ratio(value) -> str:
    """Wskaznik (Sharpe/Sortino/Calmar) po polsku; '—' dla NaN/inf/None."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    if math.isnan(v) or math.isinf(v):
        return "—"
    return f"{v:.2f}".replace(".", ",")


def _cagr_monthly(s: pd.Series) -> float:
    """CAGR z szeregu miesiecznego: liczba lat = liczba miesiecy miedzy pierwszym a ostatnim punktem / 12."""
    if len(s) < 2 or s.iloc[0] <= 0:
        return float("nan")
    yrs = (s.index[-1].to_period("M") - s.index[0].to_period("M")).n / 12
    if yrs <= 0:
        return float("nan")
    return float((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1)


st.markdown("# 📏 Stopy zwrotu dlugoterminowe")
st.caption(
    "Porownanie ETF-ow na horyzoncie do 30 lat: stopy skumulowane i srednioroczne (CAGR), "
    "lata kalendarzowe, okna kroczace oraz wzrost kapitalu z miarami ryzyka. Dane miesieczne."
)

DEFAULT = [t for t in ["SPY", "VEA", "EEM", "AGG", "GLD"] if t in ALL_TICKERS]

c1, c2, c3 = st.columns([3, 1.4, 1])
with c1:
    selected = st.multiselect(
        "ETF-y (2-8)", options=ALL_TICKERS, default=DEFAULT, max_selections=8,
        format_func=lambda t: f"{t} — {ETF_NAMES.get(t, t)}", key="lr_selected",
    )
with c2:
    use_proxy = st.toggle("Wydluz historie o fundusze proxy", value=False, key="lr_proxy",
                          help="Przed startem ETF-u stopy zwrotu starego funduszu indeksowego "
                               "na ten sam rynek (np. SPY ← VFINX od 1980).")
with c3:
    currency = st.radio("Waluta", ["USD", "PLN"], horizontal=True, key="lr_ccy")

# --- Dane --------------------------------------------------------------------------
series: dict[str, pd.Series] = {}
proxy_info: dict[str, tuple[str | None, pd.Timestamp | None]] = {}
for t in selected:
    s, proxy_t, proxy_end = load_monthly(t, use_proxy)
    if s is None or len(s) < 13:
        st.warning(f"Brak wystarczajacych danych dla {t} — pomijam.")
        continue
    if use_proxy and t in PROXY_MAP and proxy_t is None:
        st.caption(f"{t}: nie udalo sie doloczyc proxy {PROXY_MAP[t]} — pokazuje prawdziwa historie ETF-u.")
    series[t] = s
    proxy_info[t] = (proxy_t, proxy_end)

if currency == "PLN" and series:
    fx, fx_source = fetch_usdpln_monthly()
    if fx is None:
        st.warning("Nie udalo sie pobrac kursu USD/PLN — pokazuje wyniki w USD.")
        currency = "USD"
    else:
        if fx_source == "yfinance":
            st.info("Kurs USD/PLN z FRED niedostepny — tryb PLN obejmuje dane od grudnia 2003.")
        converted = {t: convert_to_pln(s, fx) for t, s in series.items()}
        for t, s in converted.items():
            if len(s) < 13:
                st.warning(f"{t}: za malo danych po przeliczeniu na PLN — pominiety.")
        series = {t: s for t, s in converted.items() if len(s) >= 13}
        # Kurs PLN moze uciac caly odcinek proxy (np. kurs z yfinance od 12.2003) — wtedy bez etykiety proxy.
        for t, s in series.items():
            p_end = proxy_info[t][1]
            if p_end is not None and s.index[0] > p_end:
                proxy_info[t] = (None, None)

before_align = list(series)
series = align_end(series)
for t in before_align:
    if t not in series:
        st.warning(f"{t}: brak danych we wspolnym okresie — pominiety.")

if len(series) < 2:
    st.info("Wybierz co najmniej 2 ETF-y z dostepnymi danymi.")
else:
    end_month = next(iter(series.values())).index[-1]
    st.caption(f"Okresy koncza sie na {end_month:%m.%Y} (ostatni pelny miesiac). Waluta: {currency}.")
    proxy_end_map = {t: proxy_info[t][1] for t in series}

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tabela okresow", "🗓️ Stopy roczne",
                                      "🔁 Stopy kroczace", "📈 Wzrost i ryzyko"])

    # --- 1. Tabela okresow ---------------------------------------------------------
    with tab1:
        mode = st.radio("Pokaz", ["Srednioroczna (CAGR)", "Skumulowana"], horizontal=True,
                        key="lr_mode")
        col = "cagr" if mode.startswith("Sred") else "total"
        rows = []
        for t, s in series.items():
            pr = period_returns(s)
            row = {"ETF": t}
            for y in PERIOD_YEARS:
                row[period_label(y)] = fmt_pct(pr.loc[period_label(y), col])
            row[SINCE_START] = fmt_pct(pr.loc[SINCE_START, col])
            row["Dane od"] = data_since_label(s, *proxy_info[t])
            rows.append(row)
        st.dataframe(pd.DataFrame(rows).set_index("ETF"), width="stretch")
        st.caption("„—” = historia krotsza niz okres. CAGR „Od startu” liczony dla historii od 1 roku.")

    # --- 2. Stopy roczne -----------------------------------------------------------
    with tab2:
        yearly, ytd_years = {}, set()
        for t, s in series.items():
            y, ytd = calendar_year_returns(s)
            yearly[t] = y
            if ytd is not None:
                ytd_years.add(ytd)
        ydf = pd.DataFrame(yearly).sort_index().dropna(how="all")
        if ydf.empty:
            st.info("Zaden z wybranych ETF-ow nie ma jeszcze pelnego roku kalendarzowego.")
        else:
            ytd_year = max(ytd_years) if ytd_years else None
            st.plotly_chart(yearly_returns_heatmap(ydf, ytd_year=ytd_year), width="stretch")
            full = ydf.drop(index=ytd_year) if ytd_year in ydf.index else ydf
            summary = []
            for t in ydf.columns:
                col_full = full[t].dropna()
                if col_full.empty:
                    continue
                summary.append({
                    "ETF": t,
                    "Najlepszy rok": f"{int(col_full.idxmax())}: {fmt_pct(col_full.max())}",
                    "Najgorszy rok": f"{int(col_full.idxmin())}: {fmt_pct(col_full.min())}",
                    "Lata na plusie": fmt_pct(float((col_full > 0).mean()), 0).lstrip("+"),
                    "Liczba lat": len(col_full),
                })
            if summary:
                st.dataframe(pd.DataFrame(summary).set_index("ETF"), width="stretch")
            st.caption("Pierwszy niepelny rok historii pominiety. Podsumowanie bez roku YTD.")

    # --- 3. Stopy kroczace ---------------------------------------------------------
    with tab3:
        win = st.select_slider("Okno (lata)", options=[1, 3, 5, 10, 15, 20], value=10, key="lr_win")
        rolling, rsum = {}, []
        for t, s in series.items():
            r = rolling_cagr(s, win)
            sm = rolling_summary(r)
            if sm["count"] == 0:
                rsum.append({"ETF": t, "Min": "—", "25%": "—", "Mediana": "—", "75%": "—",
                             "Max": "—", "Okna ze strata": "—",
                             "Liczba okien": f"historia < {period_label(win)}"})
                continue
            rolling[t] = r
            rsum.append({
                "ETF": t, "Min": fmt_pct(sm["min"]), "25%": fmt_pct(sm["p25"]),
                "Mediana": fmt_pct(sm["median"]), "75%": fmt_pct(sm["p75"]),
                "Max": fmt_pct(sm["max"]),
                "Okna ze strata": fmt_pct(sm["pct_negative"], 0).lstrip("+"),
                "Liczba okien": str(sm["count"]),
            })
        if rolling:
            st.plotly_chart(rolling_returns_chart(rolling, win), width="stretch")
        else:
            st.info(f"Zaden z wybranych ETF-ow nie ma historii dluzszej niz {period_label(win)}.")
        st.dataframe(pd.DataFrame(rsum).set_index("ETF"), width="stretch")
        st.caption(f"Kazdy punkt to CAGR z {period_label(win)} konczacych sie w danym miesiacu. "
                   "Okna nakladaja sie, wiec nie sa niezalezne.")

    # --- 4. Wzrost i ryzyko --------------------------------------------------------
    with tab4:
        same = st.toggle("Wspolny okres", value=True, key="lr_common",
                         help="Przycina wszystkie ETF-y do najpozniejszego startu, zeby porownanie bylo uczciwe.")
        view = common_window(series) if same else series
        view = {t: s for t, s in view.items() if len(s) >= 2}
        if not view:
            st.info("Wybrane ETF-y nie maja wspolnego okresu notowan. "
                    "Wylacz „Wspolny okres”, aby zobaczyc pelna historie kazdego z nich.")
        else:
            rf_decimal = get_risk_free() / 100.0
            st.plotly_chart(growth_chart(view, proxy_end_map, start_value=10_000,
                                         currency="zl" if currency == "PLN" else "USD"),
                            width="stretch")
            risk = []
            for t, s in view.items():
                stats = calc_stats(s, trading_days=12, rf_decimal=rf_decimal)
                cagr = _cagr_monthly(s)
                mdd = stats["Max Drawdown"]
                calmar = cagr / abs(mdd) if mdd < 0 and not math.isnan(cagr) else float("nan")
                risk.append({
                    "ETF": t, "Od": f"{s.index[0]:%m.%Y}",
                    "CAGR": fmt_pct(cagr),
                    "Zmiennosc roczna": fmt_pct(annual_volatility(s)).lstrip("+"),
                    "Max drawdown": fmt_pct(float(mdd)),
                    "Sharpe": _fmt_ratio(stats["Sharpe"]),
                    "Sortino": _fmt_ratio(stats["Sortino"]),
                    "Calmar": _fmt_ratio(calmar),
                })
            st.dataframe(pd.DataFrame(risk).set_index("ETF"), width="stretch")
            rf_txt = f"{rf_decimal * 100:.2f}".replace(".", ",")
            st.caption("Max drawdown liczony z zamkniec miesiecznych — glebokosc spadkow wewnatrz miesiaca "
                       "jest wieksza. Linia przerywana = odcinek z funduszu proxy. "
                       f"Sharpe/Sortino ze stopa wolna {rf_txt}% (biezaca).")

st.caption(
    "Zrodla: Yahoo Finance (ceny skorygowane o dywidendy), FRED/OECD (kurs USD/PLN — srednia miesieczna; "
    "w trybie PLN dane od 1996 (po denominacji i stabilizacji zlotego)). "
    "Fundusze proxy maja wyzsze oplaty niz ETF-y, wiec odcinek z proxy jest lekko zanizony. "
    "Wyniki historyczne nie gwarantuja przyszlych."
)

render_footer()
