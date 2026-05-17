"""Karty sygnalowe i metrykowe (HTML/CSS)."""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from components.formatting import (
    fmt_pct, fmt_number, color_for_value,
    GOLD, GREEN, RED, MUTED, BG, BG2, BG_CARD, BORDER,
)
from components.constants import CHART_COLORS
from data.financials import format_currency, format_large_number


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
    """Tabela statystyk backtestu. Pokazuje Sortino/Calmar/Win Rate/Profit Factor
    gdy sa w dict (backwards compat — brakujace kolumny po prostu pokazuja —)."""
    has_sortino = any("Sortino" in s for s in stats.values())
    has_calmar = any("Calmar" in s for s in stats.values())
    has_winrate = any("Win Rate" in s for s in stats.values())
    has_pf = any("Profit Factor" in s for s in stats.values())

    headers = ['<th style="text-align:left;padding:clamp(4px,1vw,8px);color:%s">Strategia</th>' % GOLD]
    for label in ["CAGR", "Max DD", "Sharpe"]:
        headers.append(f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">{label}</th>')
    if has_sortino:
        headers.append(f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">Sortino</th>')
    if has_calmar:
        headers.append(f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">Calmar</th>')
    if has_winrate:
        headers.append(f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">Win Rate</th>')
    if has_pf:
        headers.append(f'<th style="text-align:right;padding:clamp(4px,1vw,8px);color:{GOLD}">PF</th>')

    html = (
        f'<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:clamp(0.65rem,1.8vw,0.8rem)">'
        f'<thead><tr style="border-bottom:2px solid {BORDER}">'
        + "".join(headers)
        + f'</tr></thead><tbody>'
    )

    def _fmt(val, decimals=2):
        if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
            return "—"
        return f"{val:.{decimals}f}"

    for name, s in stats.items():
        cagr_color = color_for_value(s.get("CAGR"))
        max_dd = s.get("Max Drawdown", 0)
        dd_color = RED if max_dd < -0.15 else "#F59E0B" if max_dd < -0.05 else GREEN
        row = (
            f'<tr style="border-bottom:1px solid {BORDER}">'
            f'<td style="padding:clamp(4px,1vw,8px);font-weight:600">{name}</td>'
            f'<td style="text-align:right;padding:clamp(4px,1vw,8px);color:{cagr_color};font-weight:600">{fmt_pct(s.get("CAGR"))}</td>'
            f'<td style="text-align:right;padding:clamp(4px,1vw,8px);color:{dd_color}">{fmt_pct(max_dd)}</td>'
            f'<td style="text-align:right;padding:clamp(4px,1vw,8px)">{_fmt(s.get("Sharpe"))}</td>'
        )
        if has_sortino:
            row += f'<td style="text-align:right;padding:clamp(4px,1vw,8px)">{_fmt(s.get("Sortino"))}</td>'
        if has_calmar:
            row += f'<td style="text-align:right;padding:clamp(4px,1vw,8px)">{_fmt(s.get("Calmar"))}</td>'
        if has_winrate:
            wr = s.get("Win Rate")
            wr_color = color_for_value((wr - 0.5) if wr is not None else None)
            wr_str = fmt_pct(wr) if wr is not None else "—"
            row += f'<td style="text-align:right;padding:clamp(4px,1vw,8px);color:{wr_color}">{wr_str}</td>'
        if has_pf:
            pf = s.get("Profit Factor")
            if pf is None:
                pf_str = "—"
                pf_color = MUTED
            elif pf == float("inf"):
                pf_str = "∞"
                pf_color = GREEN
            else:
                pf_str = f"{pf:.2f}"
                pf_color = GREEN if pf >= 1.5 else "#F59E0B" if pf >= 1.0 else RED
            row += f'<td style="text-align:right;padding:clamp(4px,1vw,8px);color:{pf_color}">{pf_str}</td>'
        row += '</tr>'
        html += row
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


def data_status_card() -> None:
    """Kompaktowa karta statusu danych — traffic light + breakdown zrodel."""
    from datetime import datetime
    sources = st.session_state.get("_data_sources", {})
    failures = st.session_state.get("_data_failures", [])

    total = len(sources) + len(failures)
    if total == 0:
        return

    fail_pct = len(failures) / total * 100
    if fail_pct == 0:
        color, icon, label = GREEN, "🟢", "Wszystkie dane OK"
    elif fail_pct < 20:
        color, icon, label = "#F59E0B", "🟡", f"{len(failures)} brak danych"
    else:
        color, icon, label = RED, "🔴", f"{len(failures)} brak danych"

    # Breakdown zrodel
    source_counts = {}
    for src in sources.values():
        source_counts[src] = source_counts.get(src, 0) + 1

    breakdown_parts = []
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        breakdown_parts.append(f"{src}: {cnt}")
    breakdown = " · ".join(breakdown_parts)

    now_str = datetime.now().strftime("%H:%M")

    fail_list = f' · <span style="color:{MUTED};font-size:0.7rem">{", ".join(failures)}</span>' if failures else ""

    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;'
        f'padding:10px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px">'
        f'<span style="font-size:1.2rem">{icon}</span>'
        f'<div style="flex:1;min-width:200px">'
        f'<span style="color:{color};font-weight:600;font-size:0.85rem">{label}</span>'
        f'<span style="color:{MUTED};font-size:0.75rem;margin-left:12px">{breakdown}</span>'
        f'{fail_list}'
        f'</div>'
        f'<span style="color:{MUTED};font-size:0.7rem">{now_str}</span>'
        f'</div>'
    )


def alert_banner(ticker: str, condition: str, threshold: float,
                 period: str, actual_change: float) -> None:
    """Kolorowy banner alertu cenowego."""
    triggered = (condition == "spadek" and actual_change * 100 <= -threshold) or \
                (condition == "wzrost" and actual_change * 100 >= threshold)

    if not triggered:
        return

    if condition == "spadek":
        color, icon = RED, "🔻"
        desc = f"spadl o {abs(actual_change)*100:.1f}%"
    else:
        color, icon = GREEN, "🔺"
        desc = f"wzrosl o {actual_change*100:.1f}%"

    st.html(
        f'<div style="background:{color}15;border:1px solid {color}40;border-radius:10px;'
        f'padding:12px 16px;display:flex;align-items:center;gap:10px;margin-bottom:8px">'
        f'<span style="font-size:1.3rem">{icon}</span>'
        f'<div>'
        f'<span style="color:{color};font-weight:700;font-size:0.95rem">{ticker}</span>'
        f'<span style="color:{MUTED};font-size:0.85rem;margin-left:8px">'
        f'{desc} ({period}), prog: {threshold:.1f}%</span>'
        f'</div>'
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


# ===========================================================================
# Tab "Finanse spolki" — 4 cards (ratios, forward consensus, history, recos)
# Spec: docs/superpowers/specs/2026-05-14-finanse-spolki-design.md
# ===========================================================================

def _finance_empty(message: str = "Brak danych ze zrodla yfinance") -> None:
    """Wspolny pusty stan dla 4 finance cards."""
    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
        f'border-radius:12px;padding:32px;text-align:center;color:{MUTED};'
        f'font-size:0.9rem;min-height:140px;display:flex;align-items:center;'
        f'justify-content:center">{message}</div>'
    )


def _ratio_cell(label: str, value: str, value_color: str = "#E5E7EB") -> str:
    """Pojedyncza komorka w grid ratios."""
    return (
        f'<div style="background:{BG};border:1px solid {BORDER};border-radius:8px;'
        f'padding:10px 12px">'
        f'<div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:4px">{label}</div>'
        f'<div style="font-size:0.95rem;font-weight:700;color:{value_color}">{value}</div>'
        f'</div>'
    )


def ratios_card(snapshot: dict, is_bank: bool = False) -> None:
    """Grid 4x3 wskaznikow finansowych z yfinance Ticker.info.

    Dla bankow (is_bank=True) ukrywa EBITDA / EV-EBITDA / FCF (label "N/A bank").
    Pusty snapshot -> info "Brak danych".
    """
    if not snapshot:
        _finance_empty("Brak danych finansowych dla tej spolki")
        return

    name = snapshot.get("name") or ""
    sector = snapshot.get("sector") or ""
    price = snapshot.get("current_price")
    currency_sym = "zl" if str(snapshot.get("currency", "")).upper() == "PLN" else "$"

    # Header
    header_html = (
        f'<div style="margin-bottom:12px">'
        f'<div style="color:{GOLD};font-size:0.7rem;text-transform:uppercase;'
        f'letter-spacing:0.08em;font-weight:600;margin-bottom:4px">Ratios snapshot</div>'
        f'<div style="font-size:0.95rem;color:#E5E7EB;font-weight:600">{name}</div>'
        f'<div style="font-size:0.75rem;color:{MUTED}">'
        f'{sector or "—"}'
        + (f' · {currency_sym}{price:,.2f}' if price else "")
        + (f' · cap {format_large_number(snapshot.get("market_cap"))}' if snapshot.get("market_cap") else "")
        + '</div></div>'
    )

    # Build 12 cells (4 cols x 3 rows). Bank-blocked metryki: ebitda, ev_ebitda, fcf.
    bank_block = {"ebitda", "ev_ebitda", "fcf"} if is_bank else set()

    def _cell_for(key: str) -> str:
        label_map = {
            "pe":             ("PE",         lambda v: fmt_number(v, 1)),
            "fwd_pe":         ("Fwd PE",     lambda v: fmt_number(v, 1)),
            "ev_ebitda":      ("EV/EBITDA",  lambda v: fmt_number(v, 1)),
            "ebitda":         ("EBITDA",     lambda v: format_large_number(v)),
            "roe":            ("ROE",        lambda v: fmt_pct(v, 1)),
            "roa":            ("ROA",        lambda v: fmt_pct(v, 1)),
            "profit_margin":  ("Profit M.",  lambda v: fmt_pct(v, 1)),
            "gross_margin":   ("Gross M.",   lambda v: fmt_pct(v, 1)),
            "fcf":            ("FCF",        lambda v: format_large_number(v)),
            "debt_to_equity": ("Debt/E",     lambda v: fmt_number(v, 1)),
            "price_to_book":  ("P/B",        lambda v: fmt_number(v, 1)),
            "dividend_yield": ("Div Yld",    lambda v: f"{v:.2f}%" if (v is not None and not (isinstance(v, float) and (np.isnan(v) or np.isinf(v)))) else "—"),
            "revenue_growth": ("Rev Gr.",    lambda v: fmt_pct(v, 1)),
            "earnings_growth":("EPS Gr.",    lambda v: fmt_pct(v, 1)),
        }
        label, fmt = label_map[key]
        if key in bank_block:
            return _ratio_cell(label, "N/A bank", MUTED)
        value = snapshot.get(key)
        formatted = fmt(value) if value is not None else "—"
        color = "#E5E7EB"
        if key in ("revenue_growth", "earnings_growth") and value is not None:
            color = color_for_value(value)
        return _ratio_cell(label, formatted, color)

    keys_grid = [
        "pe", "fwd_pe", "ev_ebitda", "roe",
        "ebitda", "fcf", "debt_to_equity", "price_to_book",
        "profit_margin", "gross_margin", "revenue_growth", "dividend_yield",
    ]
    cells_html = "".join(_cell_for(k) for k in keys_grid)

    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
        f'border-radius:12px;padding:18px">'
        f'{header_html}'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">'
        f'{cells_html}'
        f'</div></div>'
    )


def forward_consensus_card(df: pd.DataFrame | None) -> None:
    """Plotly bar chart forward konsensusu EPS analitykow.

    df cols: avg, low, high, num_analysts, growth.
    Slupek = avg, error bars = low/high, hover = num_analysts + growth %.
    """
    if df is None or df.empty:
        _finance_empty("Brak konsensusu analitykow dla tej spolki")
        return

    periods = df.index.tolist()
    avg = df["avg"].fillna(0).tolist()
    low = df["low"].fillna(df["avg"]).tolist() if "low" in df.columns else avg
    high = df["high"].fillna(df["avg"]).tolist() if "high" in df.columns else avg
    n_analysts = df["num_analysts"].fillna(0).astype(int).tolist() if "num_analysts" in df.columns else [0] * len(avg)
    growth = df["growth"].fillna(0).tolist() if "growth" in df.columns else [0] * len(avg)

    hover = [
        f"<b>{p}</b><br>Avg: {a:.2f}<br>Low: {l:.2f}<br>High: {h:.2f}<br>"
        f"Analitykow: {n}<br>Growth: {g*100:+.1f}%"
        for p, a, l, h, n, g in zip(periods, avg, low, high, n_analysts, growth)
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=periods,
        y=avg,
        marker=dict(color=GOLD, line=dict(color=BORDER, width=1)),
        error_y=dict(
            type="data",
            symmetric=False,
            array=[h - a for h, a in zip(high, avg)],
            arrayminus=[a - l for a, l in zip(avg, low)],
            color=MUTED, thickness=1.5, width=8,
        ),
        text=[f"{a:.2f}" for a in avg],
        textposition="outside",
        textfont=dict(color="#E5E7EB", size=11),
        hovertext=hover,
        hoverinfo="text",
        name="EPS estimate",
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_CARD,
        title=dict(text="Forward konsensus EPS", font=dict(size=13, color=GOLD)),
        font=dict(color="#9CA3AF", size=11),
        xaxis=dict(showgrid=False, color=MUTED),
        yaxis=dict(gridcolor=BORDER, showgrid=True, color=MUTED, title="EPS estimate"),
        height=300,
        margin=dict(l=50, r=20, t=50, b=40),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def earnings_history_card(df: pd.DataFrame | None) -> None:
    """Tabela ostatnich N kwartalow: Estimate / Actual / Surprise%."""
    if df is None or df.empty:
        _finance_empty("Brak historii earnings dla tej spolki")
        return

    if "surprise_pct" in df.columns:
        avg_surprise = df["surprise_pct"].dropna().mean()
        if not pd.isna(avg_surprise):
            avg_color = color_for_value(avg_surprise / 100)
            avg_sign = "+" if avg_surprise > 0 else ""
            avg_label = (
                f'<span style="color:{MUTED};font-size:0.7rem">Avg surprise: </span>'
                f'<span style="color:{avg_color};font-weight:700;font-size:0.85rem">'
                f'{avg_sign}{avg_surprise:.1f}%</span>'
            )
        else:
            avg_label = ""
    else:
        avg_label = ""

    header_html = (
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'
        f'<div style="color:{GOLD};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'font-weight:600">Earnings history</div>{avg_label}</div>'
    )

    rows_html = ""
    for idx, row in df.iloc[::-1].iterrows():
        quarter_label = str(idx)
        est = row.get("eps_estimate")
        act = row.get("eps_actual")
        surp = row.get("surprise_pct")

        est_str = fmt_number(est, 2) if est is not None and not pd.isna(est) else "—"
        act_str = fmt_number(act, 2) if act is not None and not pd.isna(act) else "—"
        if surp is not None and not pd.isna(surp):
            surp_color = color_for_value(surp / 100)
            surp_str = f"+{surp:.1f}%" if surp > 0 else f"{surp:.1f}%"
        else:
            surp_color = MUTED
            surp_str = "—"

        rows_html += (
            f'<tr style="border-top:1px solid {BORDER}">'
            f'<td style="padding:7px 6px;color:#E5E7EB;font-size:0.85rem">{quarter_label}</td>'
            f'<td style="padding:7px 6px;text-align:right;color:{MUTED};font-size:0.85rem">{est_str}</td>'
            f'<td style="padding:7px 6px;text-align:right;color:#E5E7EB;font-size:0.85rem">{act_str}</td>'
            f'<td style="padding:7px 6px;text-align:right;color:{surp_color};font-weight:600;font-size:0.85rem">{surp_str}</td>'
            f'</tr>'
        )

    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:18px">'
        f'{header_html}'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="color:{MUTED};font-size:0.7rem;text-transform:uppercase">'
        f'<th style="text-align:left;padding:4px 6px;font-weight:500">Quarter</th>'
        f'<th style="text-align:right;padding:4px 6px;font-weight:500">Estimate</th>'
        f'<th style="text-align:right;padding:4px 6px;font-weight:500">Actual</th>'
        f'<th style="text-align:right;padding:4px 6px;font-weight:500">Surprise</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>'
    )


def analyst_recos_card(recos: dict) -> None:
    """Karta z target price + recommendation badge.

    Pusty dict -> "Brak rekomendacji".
    """
    if not recos or (recos.get("target_mean") is None and (recos.get("num_analysts") or 0) == 0):
        _finance_empty("Brak rekomendacji analitykow dla tej spolki")
        return

    target_mean = recos.get("target_mean")
    target_median = recos.get("target_median")
    target_high = recos.get("target_high")
    target_low = recos.get("target_low")
    upside = recos.get("upside_pct")
    reco_key = (recos.get("recommendation_key") or "").lower()
    num_analysts = recos.get("num_analysts") or 0
    # Waluta z yfinance.info — PLN dla GPW, USD dla SP500
    currency_sym = "zl" if str(recos.get("currency", "")).upper() == "PLN" else "$"

    reco_map = {
        "strong_buy":   ("STRONG BUY",   GREEN),
        "buy":          ("BUY",          GREEN),
        "hold":         ("HOLD",         "#F59E0B"),
        "sell":         ("SELL",         RED),
        "strong_sell":  ("STRONG SELL",  RED),
        "underperform": ("UNDERPERFORM", RED),
        "outperform":   ("OUTPERFORM",   GREEN),
        "none":         ("—",            MUTED),
    }
    reco_label, reco_color = reco_map.get(reco_key, ("—", MUTED))

    target_mean_str = f"{currency_sym}{target_mean:,.2f}" if target_mean is not None else "—"
    upside_str = ""
    if upside is not None:
        upside_color = color_for_value(upside / 100)
        upside_sign = "+" if upside > 0 else ""
        upside_str = (
            f'<div style="color:{upside_color};font-size:0.85rem;font-weight:600;margin-top:2px">'
            f'{upside_sign}{upside:.1f}% upside</div>'
        )

    def _row(label: str, val: float | None) -> str:
        val_str = f"{currency_sym}{val:,.2f}" if val is not None else "—"
        return (
            f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;padding:3px 0">'
            f'<span style="color:{MUTED}">{label}</span>'
            f'<span style="color:#E5E7EB">{val_str}</span></div>'
        )

    targets_html = _row("High", target_high) + _row("Median", target_median) + _row("Low", target_low)

    badge_html = (
        f'<div style="background:{BG};border:1px solid {reco_color};border-radius:6px;'
        f'padding:10px;text-align:center;margin-top:12px">'
        f'<div style="color:{reco_color};font-size:0.95rem;font-weight:700;letter-spacing:0.05em">{reco_label}</div>'
        f'<div style="color:{MUTED};font-size:0.65rem;margin-top:4px">'
        f'Recommendation key (yfinance) · {num_analysts} analitykow</div></div>'
    )

    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:18px">'
        f'<div style="color:{GOLD};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'font-weight:600;margin-bottom:12px">Analyst recos</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start">'
        f'<div>'
        f'<div style="color:{MUTED};font-size:0.7rem">Target mean</div>'
        f'<div style="font-size:1.5rem;font-weight:700;color:#E5E7EB">{target_mean_str}</div>'
        f'{upside_str}'
        f'</div>'
        f'<div>{targets_html}</div>'
        f'</div>'
        f'{badge_html}'
        f'</div>'
    )
