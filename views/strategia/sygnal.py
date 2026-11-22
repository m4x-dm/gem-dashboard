"""Sygnal GEM — aktualny sygnal (darmowe) + historia, statystyki, kalendarz (Premium).

Scalone 2026-11-15 z pages/1_sygnal_gem.py i pages/17_sygnaly.py.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import get_risk_free, render_footer
from components.auth import is_premium, premium_teaser
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.downloader import download_prices
from data.momentum import gem_classic_signal, build_ranking, backtest_gem
from components.cards import signal_card, metric_row, top_etf_cards
from components.charts import ranking_bar_chart, _base_layout
from components.formatting import MUTED, BG_CARD, BORDER
from components.constants import GREEN, SHADOW
from components.i18n import tr, tr_doc

SIGNAL_COLORS = {"QQQ": GREEN, "VEA": "#3B82F6", "EEM": "#A855F7", "ACWI": "#06B6D4", "AGG": "#FBBF24"}
SIGNAL_LABELS = {"QQQ": "Akcje USA", "VEA": "Rynki rozwinięte", "EEM": "Rynki wschodzace",
                 "ACWI": "Globalne", "AGG": "Obligacje"}


def render_now(rf: float) -> None:
    """Tresc dawnej strony 1_sygnal_gem.py."""
    # Pobierz dane
    tickers = list(set(ALL_TICKERS + st.session_state.get("custom_tickers", [])))
    prices = download_prices(tickers)


    # Klasyczny GEM
    gem_data = gem_classic_signal(prices, rf)

    st.markdown("### " + tr("Klasyczny GEM (QQQ / VEA / EEM / ACWI / AGG)"))
    signal_card(gem_data)
    metric_row(gem_data["qqq_12m"], gem_data["vea_12m"], gem_data["eem_12m"], gem_data["acwi_12m"], gem_data["agg_12m"], rf)

    st.divider()

    # Rozszerzony ranking
    st.markdown("### " + tr("Top 5 ETF-ow — rozszerzony ranking momentum"))
    ranking = build_ranking(prices, rf, skip_month=False)

    # Nazwy dla custom tickerow
    custom = st.session_state.get("custom_tickers", [])
    names = dict(ETF_NAMES)
    categories = dict(ETF_CATEGORY_MAP)
    for t in custom:
        names.setdefault(t, t)
        categories.setdefault(t, "Wlasne")

    valid_ranking = ranking.dropna(subset=["Wynik"])
    if not valid_ranking.empty:
        top_etf_cards(valid_ranking, names, categories, n=5)

        st.divider()
        st.markdown("### " + tr("Top 10 — wykres momentum"))
        fig = ranking_bar_chart(valid_ranking, top_n=10, title=tr("Top 10 — wynik momentum"))
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning(tr("Brak danych do wyswietlenia rankingu."))

    # Info
    with st.expander(tr("Jak czytac sygnal GEM?")):
        st.markdown(tr_doc("sygnal_jak_czytac", """
        **Klasyczny GEM** analizuje 5 aktywow:
        1. Wybierz najlepszy z QQQ / VEA / EEM / ACWI wg zwrotu 12M (porownanie relatywne)
        2. Jesli zwrot zwyciezcy 12M > stopa wolna → **kup go**, inaczej → **kup obligacje (AGG)**

        **Momentum 12M (no skip) dla ETF — od 2026-05-23:** zwrot liczony jako
        `price(t) / price(t-252) - 1` (pelne 12 miesiecy). Ponowny test z pazdziernika 2026 na koszyku
        QQQ/VEA/EEM/ACWI/AGG nie potwierdzil przewagi nad poprzednim skip-month (12-1):
        w latach 2012–2026 lepiej wypadal skip-month, a w ostatniej dekadzie roznica
        miesci sie w granicach szumu.

        **Rozszerzony ranking** oblicza wynik kompozytowy:
        `12M × 50% + 6M × 25% + 3M × 15% + 1M × 10%`

        **Momentum absolutny:** TAK = zwrot 12M > stopa wolna od ryzyka

        **Uwaga:** dla rankingu akcji (S&P 500, GPW, krypto) nadal uzywamy 12-1
        skip-month — efekt rewersji ma znaczenie dla pojedynczych spolek.
        """))


def build_signal_periods(rf: float):
    """Z dawnej 17_sygnaly.py: pobranie period='max' + backtest_gem + signal_periods.
    Zwraca (prices, signal_periods) albo None, gdy brak danych."""
    with st.spinner(tr("Pobieram dane i obliczam sygnaly...")):
        required = ["QQQ", "VEA", "EEM", "ACWI", "AGG"]
        prices = download_prices(required, period="max")
        result = backtest_gem(prices, rf, start_capital=10000)

    if result is None:
        return None

    signals = result["signals"]  # list of (date, signal)

    # Build signal periods
    signal_periods = []
    for i, (date, signal) in enumerate(signals):
        end_date = signals[i + 1][0] if i + 1 < len(signals) else prices.index[-1]
        duration = (end_date - date).days
        signal_periods.append({
            "start": date,
            "end": end_date,
            "signal": signal,
            "duration_days": duration,
        })
    return prices, signal_periods


def render_current_position(signal_periods) -> None:
    """Dawny tab1 'Obecny sygnal' z 17_sygnaly.py: karta pozycji + poprzednie sygnaly."""
    current = signal_periods[-1]
    days_in = current["duration_days"]
    sig = current["signal"]
    color = SIGNAL_COLORS.get(sig, MUTED)
    label = tr(SIGNAL_LABELS.get(sig, sig))
    start_str = current["start"].strftime("%Y-%m-%d")

    st.html(
        f'<div style="background:{BG_CARD};border-left:3px solid {color};box-shadow:{SHADOW};border-radius:16px;padding:40px;text-align:center;margin-bottom:24px">'
        f'<div style="font-size:3.5rem;font-weight:800;color:{color}">{sig}</div>'
        f'<div style="font-size:1.2rem;color:{MUTED};margin:8px 0">{label}</div>'
        f'<div style="font-size:2rem;font-weight:700;color:#E6E8EC;margin:16px 0">{tr("Od {n} dni", n=days_in)}</div>'
        f'<div style="font-size:0.9rem;color:{MUTED}">{tr("Data ostatniej zmiany")}: {start_str}</div>'
        f'</div>'
    )

    # Previous signals
    if len(signal_periods) >= 2:
        st.markdown("#### " + tr("Poprzednie sygnaly"))
        prev = signal_periods[-5:][::-1] if len(signal_periods) >= 5 else signal_periods[::-1]
        for sp in prev[1:]:  # skip current
            sc = SIGNAL_COLORS.get(sp["signal"], MUTED)
            sl = tr(SIGNAL_LABELS.get(sp["signal"], sp["signal"]))
            st.html(
                f'<div style="background:{BG_CARD};box-shadow:{SHADOW};border-radius:8px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:{sc};font-weight:700;font-size:1.1rem">{sp["signal"]} <span style="font-size:0.8rem;font-weight:400;color:{MUTED}">({sl})</span></span>'
                f'<span style="color:{MUTED};font-size:0.85rem">{sp["start"].strftime("%Y-%m-%d")} → {sp["end"].strftime("%Y-%m-%d")} ({tr("{n} dni", n=sp["duration_days"])})</span>'
                f'</div>'
            )


def render_history_tab(signal_periods) -> None:
    """Dawny tab2 'Timeline'."""
    st.subheader(tr("Timeline sygnalow GEM"))

    # Colored timeline chart
    fig = go.Figure()
    for sp in signal_periods:
        color = SIGNAL_COLORS.get(sp["signal"], MUTED)
        fig.add_trace(go.Bar(
            x=[(sp["end"] - sp["start"]).days],
            y=["GEM"],
            base=[sp["start"]],
            orientation="h",
            marker_color=color,
            name=sp["signal"],
            showlegend=False,
            hovertemplate=(
                f'{sp["signal"]}<br>'
                f'{sp["start"].strftime("%Y-%m-%d")} → {sp["end"].strftime("%Y-%m-%d")}<br>'
                f'{tr("{n} dni", n=sp["duration_days"])}<extra></extra>'
            ),
        ))

    # Custom x-axis for dates
    fig.update_layout(**_base_layout(tr("Historia sygnalow GEM"), height=150))
    fig.update_xaxes(type="date")
    fig.update_yaxes(visible=False)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=30))
    st.plotly_chart(fig, width="stretch")

    # Full table
    st.markdown("#### " + tr("Pelna lista zmian sygnalu"))
    df = pd.DataFrame(signal_periods)
    df["start"] = df["start"].dt.strftime("%Y-%m-%d")
    df["end"] = df["end"].dt.strftime("%Y-%m-%d")
    df_display = df[["start", "end", "signal", "duration_days"]].copy()
    df_display.columns = [tr("Poczatek"), tr("Koniec"), tr("Sygnal"), tr("Czas trwania (dni)")]
    df_display = df_display.iloc[::-1].reset_index(drop=True)
    st.dataframe(df_display, width="stretch", hide_index=True)


def render_stats_tab(signal_periods) -> None:
    """Dawny tab3 'Statystyki'."""
    st.subheader(tr("Statystyki sygnalow"))

    # % time in each signal
    total_days = sum(sp["duration_days"] for sp in signal_periods)
    time_in = {}
    count_in = {}
    durations_all = {}
    for sp in signal_periods:
        sig = sp["signal"]
        time_in[sig] = time_in.get(sig, 0) + sp["duration_days"]
        count_in[sig] = count_in.get(sig, 0) + 1
        if sig not in durations_all:
            durations_all[sig] = []
        durations_all[sig].append(sp["duration_days"])

    # Pie chart
    col1, col2 = st.columns([1, 1])
    with col1:
        pie_colors = {k: SIGNAL_COLORS.get(k, MUTED) for k in time_in}
        fig = go.Figure(go.Pie(
            labels=[tr(SIGNAL_LABELS.get(k, k)) for k in time_in],
            values=list(time_in.values()),
            marker=dict(colors=[pie_colors[k] for k in time_in]),
            textfont=dict(size=12),
            hole=0.4,
            hovertemplate="%{label}<br>%{value} " + tr("dni") + " (%{percent})<extra></extra>",
        ))
        fig.update_layout(**_base_layout(tr("% czasu w kazdym sygnale"), height=350))
        st.plotly_chart(fig, width="stretch")

    with col2:
        # Stats per signal
        for sig in time_in:
            pct = time_in[sig] / total_days * 100
            avg_dur = np.mean(durations_all[sig])
            color = SIGNAL_COLORS.get(sig, MUTED)
            label = tr(SIGNAL_LABELS.get(sig, sig))
            st.html(
                f'<div style="background:{BG_CARD};border-left:4px solid {color};border-radius:8px;padding:12px;margin-bottom:8px">'
                f'<div style="color:{color};font-weight:700;font-size:1rem">{sig} ({label})</div>'
                f'<div style="color:{MUTED};font-size:0.85rem">'
                + tr("{pct}% czasu · {n} wystapien · sredni czas: {avg} dni",
                     pct=f"{pct:.1f}", n=count_in[sig], avg=f"{avg_dur:.0f}")
                + f'</div>'
                f'</div>'
            )


def render_calendar_tab(prices, signal_periods) -> None:
    """Dawny tab4 'Kalendarz'."""
    st.subheader(tr("Kalendarz sygnalow (rok × miesiac)"))

    # Build year×month matrix of dominant signal
    all_dates = prices.index[prices.index >= signal_periods[0]["start"]]
    sig_by_date = pd.Series(index=all_dates, dtype=str)
    for sp in signal_periods:
        mask = (all_dates >= sp["start"]) & (all_dates < sp["end"])
        sig_by_date.loc[mask] = sp["signal"]
    # Last period includes end
    last = signal_periods[-1]
    mask = all_dates >= last["start"]
    sig_by_date.loc[mask] = last["signal"]

    # Monthly dominant signal
    sig_by_date = sig_by_date.dropna()
    monthly_sig = sig_by_date.groupby([sig_by_date.index.year, sig_by_date.index.month]).agg(
        lambda x: x.value_counts().index[0]
    )

    # Encode signals as numbers for heatmap
    sig_to_num = {"QQQ": 4, "ACWI": 3, "VEA": 2, "EEM": 1, "AGG": 0}
    years = sorted(set(idx[0] for idx in monthly_sig.index))
    months = list(range(1, 13))
    MONTH_NAMES = [tr(m) for m in ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                                   "Lip", "Sie", "Wrz", "Paz", "Lis", "Gru"]]

    z = np.full((len(years), 12), np.nan)
    text = np.full((len(years), 12), "", dtype=object)
    for (yr, mo), sig in monthly_sig.items():
        if yr in years and 1 <= mo <= 12:
            yi = years.index(yr)
            z[yi, mo - 1] = sig_to_num.get(sig, -1)
            text[yi, mo - 1] = sig

    # Custom colorscale: AGG=amber, EEM=purple, VEA=blue, ACWI=cyan, QQQ=green
    colorscale = [
        [0, "#FBBF24"],    # AGG (0)
        [0.25, "#A855F7"],  # EEM (1)
        [0.5, "#3B82F6"],   # VEA (2)
        [0.75, "#06B6D4"],  # ACWI (3)
        [1, "#22C55E"],     # QQQ (4)
    ]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=MONTH_NAMES,
        y=[str(y) for y in years],
        colorscale=colorscale,
        zmin=0, zmax=4,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=10),
        showscale=False,
        hovertemplate=tr("Rok") + ": %{y}<br>" + tr("Miesiac") + ": %{x}<br>" + tr("Sygnal") + ": %{text}<extra></extra>",
    ))
    h = max(400, len(years) * 24)
    fig.update_layout(**_base_layout(tr("Kalendarz sygnalow GEM"), height=h))
    fig.update_xaxes(side="top")
    st.plotly_chart(fig, width="stretch")

    # Legend
    legend_html = '<div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px">'
    for sig, color in SIGNAL_COLORS.items():
        label = tr(SIGNAL_LABELS.get(sig, sig))
        legend_html += (
            f'<span style="display:inline-flex;align-items:center;gap:4px">'
            f'<span style="background:{color};width:14px;height:14px;border-radius:3px;display:inline-block"></span>'
            f'<span style="color:{MUTED};font-size:0.8rem">{sig} ({label})</span>'
            f'</span>'
        )
    legend_html += '</div>'
    st.html(legend_html)


st.markdown("# " + tr("Sygnał GEM"))
rf = get_risk_free()

tab_now, tab_hist, tab_stats, tab_cal = st.tabs(["🎯 " + tr("Teraz"), "📜 " + tr("Historia"), "📊 " + tr("Statystyki"), "📅 " + tr("Kalendarz")])

with tab_now:
    render_now(rf)

if is_premium():
    data = build_signal_periods(rf)
    if data is None:
        for t in (tab_hist, tab_stats, tab_cal):
            with t:
                st.error(tr("Brak wystarczajacych danych do obliczenia historii sygnalow."))
    else:
        prices_hist, periods = data
        with tab_hist:
            render_current_position(periods)
            st.divider()
            render_history_tab(periods)
        with tab_stats:
            render_stats_tab(periods)
        with tab_cal:
            render_calendar_tab(prices_hist, periods)
else:
    for t, name in ((tab_hist, tr("Historia sygnałów")), (tab_stats, tr("Statystyki sygnałów")),
                    (tab_cal, tr("Kalendarz sygnałów"))):
        with t:
            premium_teaser(name, tr("Pełna historia zmian sygnału GEM, czas trwania pozycji i alokacja w czasie."))

render_footer()
