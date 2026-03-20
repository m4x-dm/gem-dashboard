"""Karty sygnalowe i metrykowe (HTML/CSS)."""

import streamlit as st
import numpy as np
import pandas as pd
from components.formatting import (
    fmt_pct, color_for_value, GOLD, GREEN, RED, MUTED, BG_CARD, BORDER,
)
from components.constants import CHART_COLORS


def signal_card(signal_data: dict) -> None:
    """Duza karta z aktualnym sygnalem GEM."""
    signal = signal_data["signal"]

    color_map = {"QQQ": GREEN, "VEA": "#3B82F6", "EEM": "#A855F7", "ACWI": "#06B6D4", "AGG": "#F59E0B", "BRAK_DANYCH": MUTED}
    icon_map = {"QQQ": "🇺🇸", "VEA": "🌍", "EEM": "🌏", "ACWI": "🌐", "AGG": "📊", "BRAK_DANYCH": "❓"}
    color = color_map.get(signal, MUTED)
    icon = icon_map.get(signal, "")

    st.html(
        f'<div style="background:{BG_CARD};border:2px solid {color};border-radius:16px;padding:clamp(16px,4vw,32px);text-align:center;margin-bottom:24px">'
        f'<div style="font-size:3rem;margin-bottom:8px">{icon}</div>'
        f'<div style="font-size:clamp(1.2rem,5vw,1.6rem);font-weight:800;color:{color};margin-bottom:8px">SYGNAL GEM: {signal}</div>'
        f'<div style="font-size:1rem;color:#9CA3AF">{signal_data["signal_label"]}</div>'
        f'</div>'
    )


def metric_row(qqq_ret: float, vea_ret: float, eem_ret: float,
               acwi_ret: float, agg_ret: float, rf: float) -> None:
    """5 metryk: zwrot USA / Miedzynarodowe / EM / Globalne / Obligacje vs stopa wolna."""
    rf_label = f"{rf:.2f}%" if rf is not None else "—"

    cols = st.columns(6)
    _metric_card(cols[0], "USA (QQQ)", qqq_ret, f"12M zwrot vs RF {rf_label}")
    _metric_card(cols[1], "Rynki rozwi. (VEA)", vea_ret, "12M zwrot")
    _metric_card(cols[2], "Rynki wsch. (EEM)", eem_ret, "12M zwrot")
    _metric_card(cols[3], "Globalne (ACWI)", acwi_ret, "12M zwrot")
    _metric_card(cols[4], "Obligacje (AGG)", agg_ret, "12M zwrot")
    _metric_card(cols[5], "Stopa wolna (T-bill)", rf / 100 if rf is not None else None, "Roczna, 13-week")


def _metric_card(col, title: str, value: float | None, subtitle: str) -> None:
    """Pojedyncza karta metryki."""
    color = color_for_value(value)
    val_str = fmt_pct(value)
    col.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:clamp(8px,2vw,16px);text-align:center">'
        f'<div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">{title}</div>'
        f'<div style="font-size:clamp(1rem,4vw,1.5rem);font-weight:700;color:{color}">{val_str}</div>'
        f'<div style="font-size:0.7rem;color:{MUTED};margin-top:4px">{subtitle}</div>'
        f'</div>'
    )


def top_etf_cards(ranking_df, etf_names: dict, etf_categories: dict, n: int = 5) -> None:
    """Top N ETF-ow jako karty."""
    top = ranking_df.head(n)
    cols = st.columns(n)
    for i, (ticker, row) in enumerate(top.iterrows()):
        name = etf_names.get(ticker, ticker)
        cat = etf_categories.get(ticker, "")
        score = row.get("Wynik", 0)
        mom_abs = row.get("Momentum_abs", "—")
        color = GREEN if mom_abs == "TAK" else RED

        cols[i].html(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:clamp(8px,2vw,16px);text-align:center;height:100%">'
            f'<div style="font-size:0.65rem;color:{GOLD};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px">{cat}</div>'
            f'<div style="font-size:clamp(0.9rem,3vw,1.3rem);font-weight:800;color:{GOLD}">{ticker}</div>'
            f'<div style="font-size:0.72rem;color:{MUTED};margin:4px 0 8px">{name}</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:{color_for_value(score)}">{fmt_pct(score)}</div>'
            f'<div style="font-size:0.65rem;color:{color};margin-top:4px">Mom. abs: {mom_abs}</div>'
            f'</div>'
        )


def macro_card(title: str, current_value: str, unit: str,
               changes: dict, traffic_light_color: str, label: str = "") -> None:
    """Karta makro z wartoscia, zmianami i sygnalem swietlnym.

    Args:
        title: nazwa wskaznika (np. "VIX")
        current_value: sformatowana wartosc (np. "18.42")
        unit: jednostka (np. "pkt", "%", "USD")
        changes: dict z kluczami np. "1D","1W","1M" -> wartosci float (zmiana %)
        traffic_light_color: kolor sygnalu (#22C55E, #F59E0B, #EF4444)
        label: etykieta sygnalu (np. "Niski strach")
    """
    changes_html = ""
    for period, val in changes.items():
        if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
            changes_html += f'<span style="color:{MUTED};font-size:0.75rem;margin-right:10px">{period}: —</span>'
        else:
            c = GREEN if val > 0 else RED if val < 0 else MUTED
            sign = "+" if val > 0 else ""
            changes_html += (
                f'<span style="color:{c};font-size:0.75rem;margin-right:10px">'
                f'{period}: {sign}{val:.1f}%</span>'
            )

    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:16px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
        f'<span style="font-size:0.8rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.05em">{title}</span>'
        f'<span style="background:{traffic_light_color}20;color:{traffic_light_color};padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:600">{label}</span>'
        f'</div>'
        f'<div style="font-size:clamp(1.2rem,4vw,1.6rem);font-weight:700;color:#E5E7EB;margin-bottom:4px">{current_value} <span style="font-size:0.85rem;color:{MUTED}">{unit}</span></div>'
        f'<div>{changes_html}</div>'
        f'</div>'
    )


def stats_table(stats: dict) -> None:
    """Tabela statystyk backtestu."""
    html = (
        f'<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:clamp(0.7rem,2vw,0.85rem)">'
        f'<thead><tr style="border-bottom:2px solid {BORDER}">'
        f'<th style="text-align:left;padding:clamp(4px,1vw,8px);color:{GOLD}">Strategia</th>'
        f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">CAGR</th>'
        f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">Calkowity</th>'
        f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">Max DD</th>'
        f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">Sharpe</th>'
        f'</tr></thead><tbody>'
    )
    for name, s in stats.items():
        cagr_color = color_for_value(s["CAGR"])
        dd_color = RED if s["Max Drawdown"] < -0.15 else "#F59E0B" if s["Max Drawdown"] < -0.05 else GREEN
        html += (
            f'<tr style="border-bottom:1px solid {BORDER}">'
            f'<td style="padding:clamp(4px,1vw,8px);font-weight:600">{name}</td>'
            f'<td style="text-align:right;padding:clamp(4px,1vw,8px);color:{cagr_color};font-weight:600">{fmt_pct(s["CAGR"])}</td>'
            f'<td style="text-align:right;padding:clamp(4px,1vw,8px);color:{color_for_value(s["Calkowity zwrot"])}">{fmt_pct(s["Calkowity zwrot"])}</td>'
            f'<td style="text-align:right;padding:clamp(4px,1vw,8px);color:{dd_color}">{fmt_pct(s["Max Drawdown"])}</td>'
            f'<td style="text-align:right;padding:clamp(4px,1vw,8px)">{s["Sharpe"]:.2f}</td>'
            f'</tr>'
        )
    html += '</tbody></table>'
    st.html(html)


def comparison_card(ticker: str, name: str, category: str,
                    returns: "pd.Series", color_index: int = 0,
                    ticker_display: str | None = None) -> None:
    """Karta porownawcza z ticker/nazwa/kategoria i zwrotami 1M-12M.

    Args:
        ticker: pelny ticker (np. PKO.WA, BTC-USD, AAPL)
        name: nazwa spolki/aktywa
        category: kategoria/sektor
        returns: Series z kluczami 1M, 3M, 6M, 12M
        color_index: indeks koloru z palety CHART_COLORS
        ticker_display: opcjonalny skrocony ticker do wyswietlenia (np. bez .WA / -USD)
    """
    accent = CHART_COLORS[color_index % len(CHART_COLORS)]
    display = ticker_display or ticker
    html = (
        f'<div style="background:{BG_CARD};border:2px solid {accent}40;border-radius:12px;padding:20px;text-align:center">'
        f'<div style="font-size:0.65rem;color:{GOLD};text-transform:uppercase;letter-spacing:0.08em">{category}</div>'
        f'<div style="font-size:1.4rem;font-weight:800;color:{accent};margin:4px 0">{display}</div>'
        f'<div style="font-size:0.72rem;color:{MUTED};margin-bottom:12px">{name}</div>'
    )
    for p in ["1M", "3M", "6M", "12M"]:
        val = returns.get(p) if isinstance(returns, pd.Series) and p in returns.index else None
        c = color_for_value(val)
        html += (
            f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid {BORDER}">'
            f'<span style="color:{MUTED};font-size:0.8rem">{p}</span>'
            f'<span style="color:{c};font-weight:600;font-size:0.85rem">{fmt_pct(val)}</span>'
            f'</div>'
        )
    html += '</div>'
    st.html(html)


def ta_signal_card(ticker: str, name: str, signals: dict) -> None:
    """Karta z sumarycznym sygnalem TA + 5 wskaznikow trend-following.

    Args:
        ticker: ticker krypto (np. BTC-USD)
        name: nazwa krypto
        signals: dict z kluczami 'trend','ema','macd','rsi','bollinger' -> +1/0/-1,
                 oraz 'aggregate' -> suma, 'n_indicators' -> ile wskaznikow aktywnych
    """
    agg = signals.get("aggregate", 0)
    n_ind = signals.get("n_indicators", 5)
    threshold = 3 if n_ind >= 5 else 2
    if agg >= threshold:
        label = "KUP"
        color = GREEN
        icon = "🟢"
    elif agg <= -threshold:
        label = "SPRZEDAJ"
        color = RED
        icon = "🔴"
    else:
        label = "NEUTRALNY"
        color = "#F59E0B"
        icon = "🟡"

    def _indicator_icon(val, detail=""):
        if val > 0:
            return f'<span style="color:{GREEN}">▲ Bullish{detail}</span>'
        elif val < 0:
            return f'<span style="color:{RED}">▼ Bearish{detail}</span>'
        return f'<span style="color:#F59E0B">— Neutralny{detail}</span>'

    indicators = [
        ("Trend (EMA 200)", signals.get("trend", 0), signals.get("trend_detail", "")),
        ("EMA crossover", signals.get("ema", 0), signals.get("ema_detail", "")),
        ("MACD + histogram", signals.get("macd", 0), signals.get("macd_detail", "")),
        ("RSI momentum", signals.get("rsi", 0), signals.get("rsi_detail", "")),
        ("Bollinger %B", signals.get("bollinger", 0), signals.get("bb_detail", "")),
    ]

    ind_html = ""
    for ind_name, ind_val, detail in indicators:
        detail_span = f' <span style="font-size:0.7rem;opacity:0.7">{detail}</span>' if detail else ""
        ind_html += (
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {BORDER}">'
            f'<span style="color:{MUTED};font-size:0.85rem">{ind_name}</span>'
            f'{_indicator_icon(ind_val, detail_span)}'
            f'</div>'
        )

    display_ticker = ticker.replace("-USD", "")
    strength = abs(agg)
    strength_bar = "█" * strength + "░" * (n_ind - strength)
    strength_color = GREEN if agg > 0 else RED if agg < 0 else MUTED
    st.html(
        f'<div style="background:{BG_CARD};border:2px solid {color};border-radius:16px;padding:24px;text-align:center;margin-bottom:16px">'
        f'<div style="font-size:2.5rem;margin-bottom:4px">{icon}</div>'
        f'<div style="font-size:clamp(1rem,4vw,1.4rem);font-weight:800;color:{color};margin-bottom:4px">SYGNAL TA: {label}</div>'
        f'<div style="font-size:1rem;color:{GOLD};font-weight:600">{display_ticker}</div>'
        f'<div style="font-size:0.8rem;color:{MUTED};margin-bottom:16px">{name}</div>'
        f'<div style="text-align:left;max-width:360px;margin:0 auto">{ind_html}</div>'
        f'<div style="margin-top:12px;font-size:0.85rem;color:{strength_color};font-family:monospace;letter-spacing:2px">{strength_bar}</div>'
        f'<div style="font-size:0.75rem;color:{MUTED}">Sila: {agg:+d} / {n_ind}</div>'
        f'</div>'
    )


def final_value_card(name: str, value: float, start_capital: float,
                     currency: str = "USD") -> None:
    """Karta koncowej wartosci portfela."""
    from components.formatting import fmt_number
    gain = value - start_capital
    gain_color = GREEN if gain >= 0 else RED
    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:16px;text-align:center">'
        f'<div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase">{name}</div>'
        f'<div style="font-size:1.4rem;font-weight:700;color:{GOLD}">{fmt_number(value, 0)} {currency}</div>'
        f'<div style="font-size:0.8rem;color:{gain_color}">{"+" if gain >= 0 else ""}{fmt_number(gain, 0)} {currency}</div>'
        f'</div>'
    )
