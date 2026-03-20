"""Strona 16: Historia Sygnalow GEM — timeline, statystyki, kalendarz."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.downloader import download_prices
from data.momentum import backtest_gem
from components.charts import _base_layout, category_pie, GOLD, BG2, COLORS
from components.formatting import MUTED, BG_CARD, BORDER
from components.constants import GREEN, RED
from components.auth import require_premium

st.set_page_config(page_title="Historia Sygnalow", page_icon="🚦", layout="wide")
setup_sidebar()
if not require_premium(16): st.stop()

st.markdown("# 🚦 Historia Sygnalow GEM")
st.caption("Pelna historia zmian sygnalu GEM, czas trwania pozycji, alokacja w czasie")

rf = get_risk_free()

# Download max data for full history
with st.spinner("Pobieram dane i obliczam sygnaly..."):
    required = ["QQQ", "VEA", "EEM", "ACWI", "AGG"]
    prices = download_prices(required, period="max")
    result = backtest_gem(prices, rf, start_capital=10000)

if result is None:
    st.error("Brak wystarczajacych danych do obliczenia historii sygnalow.")
    render_footer()
    st.stop()

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

SIGNAL_COLORS = {"QQQ": GREEN, "VEA": "#3B82F6", "EEM": "#A855F7", "ACWI": "#06B6D4", "AGG": "#F59E0B"}
SIGNAL_LABELS = {"QQQ": "Akcje USA", "VEA": "Rynki rozwinięte", "EEM": "Rynki wschodzace",
                 "ACWI": "Globalne", "AGG": "Obligacje"}

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Obecny sygnal", "📜 Timeline", "📊 Statystyki", "📅 Kalendarz"])

with tab1:
    current = signal_periods[-1]
    days_in = current["duration_days"]
    sig = current["signal"]
    color = SIGNAL_COLORS.get(sig, MUTED)
    label = SIGNAL_LABELS.get(sig, sig)
    start_str = current["start"].strftime("%Y-%m-%d")

    st.html(
        f'<div style="background:{BG_CARD};border:2px solid {color};border-radius:16px;padding:40px;text-align:center;margin-bottom:24px">'
        f'<div style="font-size:3.5rem;font-weight:800;color:{color}">{sig}</div>'
        f'<div style="font-size:1.2rem;color:{MUTED};margin:8px 0">{label}</div>'
        f'<div style="font-size:2rem;font-weight:700;color:#E5E7EB;margin:16px 0">Od {days_in} dni</div>'
        f'<div style="font-size:0.9rem;color:{MUTED}">Data ostatniej zmiany: {start_str}</div>'
        f'</div>'
    )

    # Previous signals
    if len(signal_periods) >= 2:
        st.markdown("#### Poprzednie sygnaly")
        prev = signal_periods[-5:][::-1] if len(signal_periods) >= 5 else signal_periods[::-1]
        for sp in prev[1:]:  # skip current
            sc = SIGNAL_COLORS.get(sp["signal"], MUTED)
            sl = SIGNAL_LABELS.get(sp["signal"], sp["signal"])
            st.html(
                f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:{sc};font-weight:700;font-size:1.1rem">{sp["signal"]} <span style="font-size:0.8rem;font-weight:400;color:{MUTED}">({sl})</span></span>'
                f'<span style="color:{MUTED};font-size:0.85rem">{sp["start"].strftime("%Y-%m-%d")} → {sp["end"].strftime("%Y-%m-%d")} ({sp["duration_days"]} dni)</span>'
                f'</div>'
            )

with tab2:
    st.subheader("Timeline sygnalow GEM")

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
                f'{sp["duration_days"]} dni<extra></extra>'
            ),
        ))

    # Custom x-axis for dates
    fig.update_layout(**_base_layout("Historia sygnalow GEM", height=150))
    fig.update_xaxes(type="date")
    fig.update_yaxes(visible=False)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=30))
    st.plotly_chart(fig, use_container_width=True)

    # Full table
    st.markdown("#### Pelna lista zmian sygnalu")
    df = pd.DataFrame(signal_periods)
    df["start"] = df["start"].dt.strftime("%Y-%m-%d")
    df["end"] = df["end"].dt.strftime("%Y-%m-%d")
    df_display = df[["start", "end", "signal", "duration_days"]].copy()
    df_display.columns = ["Poczatek", "Koniec", "Sygnal", "Czas trwania (dni)"]
    df_display = df_display.iloc[::-1].reset_index(drop=True)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Statystyki sygnalow")

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
            labels=[SIGNAL_LABELS.get(k, k) for k in time_in],
            values=list(time_in.values()),
            marker=dict(colors=[pie_colors[k] for k in time_in]),
            textfont=dict(size=12),
            hole=0.4,
            hovertemplate="%{label}<br>%{value} dni (%{percent})<extra></extra>",
        ))
        fig.update_layout(**_base_layout("% czasu w kazdym sygnale", height=350))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Stats per signal
        for sig in time_in:
            pct = time_in[sig] / total_days * 100
            avg_dur = np.mean(durations_all[sig])
            color = SIGNAL_COLORS.get(sig, MUTED)
            label = SIGNAL_LABELS.get(sig, sig)
            st.html(
                f'<div style="background:{BG_CARD};border-left:4px solid {color};border-radius:8px;padding:12px;margin-bottom:8px">'
                f'<div style="color:{color};font-weight:700;font-size:1rem">{sig} ({label})</div>'
                f'<div style="color:{MUTED};font-size:0.85rem">'
                f'{pct:.1f}% czasu · {count_in[sig]} wystapien · sredni czas: {avg_dur:.0f} dni'
                f'</div>'
                f'</div>'
            )

with tab4:
    st.subheader("Kalendarz sygnalow (rok × miesiac)")

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
    MONTH_NAMES = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                   "Lip", "Sie", "Wrz", "Paz", "Lis", "Gru"]

    z = np.full((len(years), 12), np.nan)
    text = np.full((len(years), 12), "", dtype=object)
    for (yr, mo), sig in monthly_sig.items():
        if yr in years and 1 <= mo <= 12:
            yi = years.index(yr)
            z[yi, mo - 1] = sig_to_num.get(sig, -1)
            text[yi, mo - 1] = sig

    # Custom colorscale: AGG=amber, EEM=purple, VEA=blue, ACWI=cyan, QQQ=green
    colorscale = [
        [0, "#F59E0B"],    # AGG (0)
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
        hovertemplate="Rok: %{y}<br>Miesiac: %{x}<br>Sygnal: %{text}<extra></extra>",
    ))
    h = max(400, len(years) * 24)
    fig.update_layout(**_base_layout("Kalendarz sygnalow GEM", height=h))
    fig.update_xaxes(side="top")
    st.plotly_chart(fig, use_container_width=True)

    # Legend
    legend_html = '<div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px">'
    for sig, color in SIGNAL_COLORS.items():
        label = SIGNAL_LABELS.get(sig, sig)
        legend_html += (
            f'<span style="display:inline-flex;align-items:center;gap:4px">'
            f'<span style="background:{color};width:14px;height:14px;border-radius:3px;display:inline-block"></span>'
            f'<span style="color:{MUTED};font-size:0.8rem">{sig} ({label})</span>'
            f'</span>'
        )
    legend_html += '</div>'
    st.html(legend_html)

render_footer()
