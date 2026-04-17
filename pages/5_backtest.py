"""Strona 5: Backtest strategii — GEM, QQQ+SMA200, TQQQ+Momentum."""

import streamlit as st
import pandas as pd
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS
from data.downloader import download_prices
from data.momentum import backtest_gem, backtest_sma200, backtest_tqqq_mom
from components.cards import stats_table
from components.charts import equity_chart
from components.formatting import fmt_number, GOLD, BG_CARD, BORDER, MUTED, GREEN, RED
from components.auth import require_premium

st.set_page_config(page_title="Backtest strategii", page_icon="🧪", layout="wide")
setup_sidebar()
if not require_premium(5): st.stop()

st.markdown("# 🧪 Backtest strategii")

# Parametry
col1, col2, col3, col4 = st.columns(4)
with col1:
    strategy_options = [
        "GEM Klasyczny",
        "QQQ + SMA 200",
        "TQQQ + Momentum",
        "Porownanie wszystkich",
    ]
    strategy = st.selectbox("Strategia", strategy_options)
with col2:
    period_map = {
        "1 miesiac": "1mo", "2 miesiace": "3mo", "3 miesiace": "3mo",
        "6 miesiecy": "6mo", "1 rok": "1y",
        "2 lata": "2y", "3 lata": "3y", "5 lat": "5y", "7 lat": "7y",
        "10 lat": "10y", "15 lat": "15y", "20 lat": "20y", "Maksymalny": "max",
    }
    period_label = st.selectbox("Okres", list(period_map.keys()), index=7)
    period = period_map[period_label]
with col3:
    start_capital = st.number_input("Kapital poczatkowy (USD)", value=10000, step=1000, min_value=100)
with col4:
    rf = get_risk_free()
    st.metric("Stopa wolna", f"{rf:.2f}%")

# Pobierz dane
tickers = list(set(ALL_TICKERS + st.session_state.get("custom_tickers", [])))
prices = download_prices(tickers, period=period)


def _render_final_values(curves: list[tuple[str, pd.Series]], capital: float):
    """Wyswietla kafelki z wartosciami koncowymi."""
    n = len(curves)
    cols = st.columns(n)
    for i, (name, eq) in enumerate(curves):
        final = eq.iloc[-1]
        gain = final - capital
        gain_color = GREEN if gain >= 0 else RED
        gain_sign = "+" if gain >= 0 else ""
        gain_label = "zysku" if gain >= 0 else "straty"
        cols[i].html(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:16px;text-align:center">'
            f'<div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase">{name}</div>'
            f'<div style="font-size:1.4rem;font-weight:700;color:{GOLD}">${fmt_number(final, 0)}</div>'
            f'<div style="font-size:0.8rem;color:{gain_color}">{gain_sign}${fmt_number(abs(gain), 0)} {gain_label}</div>'
            f'</div>'
        )


def _render_signals(signals: list, signal_map: dict, title: str = "Historia zmian sygnalu"):
    """Wyswietla timeline zmian sygnalu."""
    st.divider()
    st.markdown(f"### {title}")
    if signals:
        signal_df = pd.DataFrame(signals, columns=["Data", "Sygnal"])
        signal_df["Data"] = signal_df["Data"].dt.strftime("%Y-%m-%d")
        signal_df["Opis"] = signal_df["Sygnal"].map(signal_map)
        st.dataframe(signal_df, use_container_width=True, hide_index=True)
        st.caption(f"Laczna liczba zmian sygnalu: **{len(signals)}**")
    else:
        st.info("Brak zmian sygnalu w tym okresie.")


# ─── GEM Klasyczny ───────────────────────────────────────────
if strategy == "GEM Klasyczny":
    with st.expander("⚙️ Ustawienia zaawansowane", expanded=False):
        trend_filter = st.checkbox(
            "Filtr trendu (AND cena > SMA200)",
            value=False,
            help="Dodatkowo wymaga aby wybrane aktywo akcyjne bylo powyzej SMA200. "
                 "Redukuje whipsawy, obniza CAGR o 1-2pp, poprawia win rate i drawdown.",
        )
        vol_on = st.checkbox(
            "Volatility targeting",
            value=False,
            help="Skaluj pozycje do zadanej rocznej zmiennosci: pos = cel / realizowana_vol. "
                 "Redukuje wahania portfela — Sharpe rosnie, DD maleje kosztem CAGR "
                 "w trendach. Dziala tylko gdy sygnal to akcje (nie AGG).",
        )
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            vol_target_pct = st.slider(
                "Cel zmiennosci (%)", 8.0, 25.0, 15.0, 0.5,
                disabled=not vol_on,
                help="Typowe cele: 10-12% bardzo ostroznie, 15% standard, 20% agresywnie.",
            ) / 100.0
        with col_v2:
            max_lev = st.slider(
                "Maks. dzwignia", 1.0, 3.0, 1.0, 0.25,
                disabled=not vol_on,
                help="1.0 = bez dzwigni (tylko skalowanie w dol). 1.5-2.0 wymaga konta margin "
                     "i dolicza koszt finansowania ~rf.",
            )
    vol_target_val = vol_target_pct if vol_on else None
    result = backtest_gem(prices, rf, start_capital=start_capital,
                          trend_filter=trend_filter,
                          vol_target=vol_target_val, max_leverage=max_lev)
    if result is None:
        st.error("Za malo danych do przeprowadzenia backtestu. Sprobuj dluzszy okres.")
        st.stop()

    with st.expander("ℹ️ O strategii GEM Klasyczny", expanded=False):
        st.markdown("""
**Global Equity Momentum (GEM)** to strategia opracowana przez **Gary'ego Antonacciego**
(*Dual Momentum Investing*, 2014). Laczy momentum absolutny (vs stopa wolna) z momentum
relatywnym (porownanie rynkow).

### Zasady
| Krok | Warunek | Akcja |
|------|---------|-------|
| 1 | QQQ momentum 12-1 < stopa wolna | → Obligacje (AGG) |
| 2 | QQQ 12-1 > stopa wolna | → Porownaj QQQ vs VEA vs EEM vs ACWI, kup najlepszy |

**Rebalans miesięczny** (co 21 dni roboczych). Zawsze 100% w jednym aktywie.
Momentum 12-1 (skip-month) pomija ostatni miesiac — unika efektu krotkoterminowej rewersji.

### Zalety
- **Prosta** — jedna decyzja raz w miesiacu, 5 aktywow
- **Systematyczna** — eliminuje emocje, jasne reguly
- **Ochrona przed bessami** — momentum absolutny sygnalizuje trend spadkowy
- **Dywersyfikacja geograficzna** — przechodzi miedzy USA, rynkami rozwi. i wschodzacymi

### Wady
- **Opoznione sygnaly** — 12M lookback reaguje z opoznieniem na nagle zwroty
- **Whipsaws** — falszywe sygnaly w rynku bocznym
- **Brak dywersyfikacji** — 100% w jednym aktywie (all-in/all-out)
- **Koszty transakcji** — czeste zmiany sygnalu = prowizje + podatki

Pelny opis strategii → strona **O strategii GEM** w menu bocznym.
""")

    st.markdown("### Krzywa kapitalu")
    fig = equity_chart({
        "GEM": result["equity_gem"],
        "QQQ Buy&Hold": result["equity_qqq"],
        "ACWI Buy&Hold": result["equity_acwi"],
        "AGG Buy&Hold": result["equity_agg"],
    })
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Statystyki")
    stats_table(result["stats"])

    st.divider()
    _render_final_values([
        ("GEM", result["equity_gem"]),
        ("QQQ Buy&Hold", result["equity_qqq"]),
        ("ACWI Buy&Hold", result["equity_acwi"]),
        ("AGG Buy&Hold", result["equity_agg"]),
    ], start_capital)

    _render_signals(result["signals"], {
        "QQQ": "🟢 Akcje USA", "VEA": "🔵 Akcje miedzynar.",
        "EEM": "🟣 Rynki wsch.", "ACWI": "🌐 Akcje globalne",
        "AGG": "🟡 Obligacje",
    }, "Historia zmian sygnalu GEM")


# ─── QQQ + SMA 200 ───────────────────────────────────────────
elif strategy == "QQQ + SMA 200":
    with st.expander("⚙️ Ustawienia zaawansowane", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            buffer_pct = st.slider(
                "Bufor / histereza (%)", 0.0, 5.0, 0.0, 0.5,
                help="Switch do AGG tylko gdy cena < SMA × (1 − bufor); do QQQ tylko gdy "
                     "cena > SMA × (1 + bufor). Faber rekomenduje 2%. Redukuje whipsawy "
                     "w rynku bocznym (2015, 2022).",
            ) / 100.0
        with col_b:
            monthly_check = st.checkbox(
                "Sprawdzanie miesięczne",
                value=False,
                help="Sprawdzaj sygnal co ~21 dni zamiast codziennie. Dalej redukuje "
                     "whipsawy, ale opozni reakcje na gwaltowne zmiany trendu.",
            )
        vol_on_sma = st.checkbox(
            "Volatility targeting",
            value=False,
            help="Skaluj pozycje QQQ do zadanej rocznej zmiennosci: pos = cel / realizowana_vol. "
                 "Redukuje wahania portfela — Sharpe rosnie, DD maleje kosztem CAGR "
                 "w trendach. Gdy sygnal = AGG, brak skalowania.",
        )
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            vol_target_pct_sma = st.slider(
                "Cel zmiennosci (%) ", 8.0, 25.0, 15.0, 0.5,
                disabled=not vol_on_sma,
                key="sma_vol_target",
                help="Typowe cele: 10-12% bardzo ostroznie, 15% standard, 20% agresywnie.",
            ) / 100.0
        with col_v2:
            max_lev_sma = st.slider(
                "Maks. dzwignia ", 1.0, 3.0, 1.0, 0.25,
                disabled=not vol_on_sma,
                key="sma_max_lev",
                help="1.0 = bez dzwigni. >1 wymaga konta margin, w tle doliczany koszt ~rf.",
            )
    vol_target_val_sma = vol_target_pct_sma if vol_on_sma else None
    result = backtest_sma200(prices, rf, start_capital=start_capital,
                              buffer_pct=buffer_pct, monthly_check=monthly_check,
                              vol_target=vol_target_val_sma, max_leverage=max_lev_sma)
    if result is None:
        st.error("Za malo danych do przeprowadzenia backtestu. Sprobuj dluzszy okres.")
        st.stop()

    with st.expander("ℹ️ O strategii QQQ + SMA 200", expanded=False):
        st.markdown("""
**SMA 200 (Simple Moving Average)** to jedna z najstarszych i najprostszych strategii trend-following.
200-dniowa srednia kroczaca wyglądza szum cenowy i pokazuje dlugoterminowy kierunek trendu.

### Zasady
| Warunek | Akcja |
|---------|-------|
| Cena QQQ > SMA(200) | → Trzymaj QQQ (trend wzrostowy) |
| Cena QQQ < SMA(200) | → Przejdz do obligacji AGG (trend spadkowy) |

**Rebalans dzienny** — strategia sprawdza warunek codziennie (nie miesiecznie jak GEM),
dzieki czemu reaguje szybciej na zmiany trendu.

### Zalety
- **Prostota** — jeden warunek, zero subiektywnosci
- **Ochrona przed bessami** — historycznie omija wiekszosc duzych spadkow (2008, 2020, 2022)
- **Szybsza reakcja niz GEM** — codzienny check vs miesięczny rebalans

### Wady
- **Whipsaw** — w rynku bocznym generuje wiele falszywych sygnalow (czeste przeskoki ponad/ponizej SMA)
- **Opoznienie** — SMA 200 reaguje z opoznieniem ~2-4 tygodni na nagla zmiane trendu
- **Koszty transakcji** — czeste przelaczanie = wiecej prowizji i zdarzen podatkowych
- **Brak momentum relatywnego** — nie porownuje rynkow miedzy soba (tylko QQQ vs SMA)

### Kontekst historyczny
Strategia SMA 200 jest popularna od lat 1990-tych. Mebane Faber w pracy
*"A Quantitative Approach to Tactical Asset Allocation"* (2007) wykazal,
ze SMA 10-miesieczna (≈200 dni) znaczaco redukuje drawdown przy zachowaniu
wiekszosci zwrotow z rynku akcji.
""")

    st.markdown("### Krzywa kapitalu")
    fig = equity_chart({
        "QQQ+SMA200": result["equity_sma"],
        "QQQ Buy&Hold": result["equity_qqq"],
        "AGG Buy&Hold": result["equity_agg"],
    })
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Statystyki")
    stats_table(result["stats"])

    st.divider()
    _render_final_values([
        ("QQQ+SMA200", result["equity_sma"]),
        ("QQQ Buy&Hold", result["equity_qqq"]),
        ("AGG Buy&Hold", result["equity_agg"]),
    ], start_capital)

    _render_signals(result["signals"], {
        "QQQ": "🟢 QQQ (cena > SMA200)", "AGG": "🟡 AGG (cena < SMA200)",
    }, "Historia zmian sygnalu SMA 200")



# ─── TQQQ + Momentum ─────────────────────────────────────────
elif strategy == "TQQQ + Momentum":
    with st.expander("⚙️ Ustawienia zaawansowane", expanded=False):
        lev_col, cost_col = st.columns(2)
        with lev_col:
            leverage = st.slider(
                "Dzwignia", 1.0, 3.0, 3.0, 0.5,
                help="Mnoznik dzwigni. 3.0 = TQQQ, 2.0 = QLD/SSO, 1.5 = CSNDX 1.5x, 1.0 = brak dzwigni.",
            )
        with cost_col:
            realistic_costs = st.checkbox(
                "Realistyczne koszty TQQQ",
                value=False,
                help="Dodaj do dziennego zwrotu: koszt finansowania pozyczonej dzwigni "
                     "((L-1)·(rf+spread)/252) oraz expense ratio. Naiwny syntetyk 3×QQQ "
                     "przeszacowuje TQQQ o 2-4pp rocznie — realistyczny model dopasowuje "
                     "sie do prawdziwego TQQQ do ~0.5pp.",
            )
        col_er, col_sp = st.columns(2)
        with col_er:
            expense_ratio_pct = st.slider(
                "Expense ratio (%)", 0.0, 2.0, 0.88, 0.01,
                disabled=not realistic_costs,
                help="TQQQ: 0.88%, QLD: 0.95%, SSO: 0.89%, SPXL: 0.91%. 0 = naiwny.",
            ) / 100.0
        with col_sp:
            borrow_spread_pct = st.slider(
                "Spread ponad rf (%)", 0.0, 2.0, 0.50, 0.05,
                disabled=not realistic_costs,
                help="Spread jaki ETF placi za dzwignie ponad stope wolna. 0.3-0.7% realistycznie.",
            ) / 100.0
    er = expense_ratio_pct if realistic_costs else 0.0
    sp = borrow_spread_pct if realistic_costs else 0.0
    result = backtest_tqqq_mom(prices, rf, start_capital=start_capital,
                                leverage=leverage, expense_ratio=er,
                                borrow_spread=sp)
    if result is None:
        st.error("Za malo danych do przeprowadzenia backtestu. Sprobuj dluzszy okres.")
        st.stop()

    with st.expander("ℹ️ O strategii TQQQ + Momentum", expanded=False):
        st.markdown("""
**TQQQ + Momentum** laczy 3-krotnie lewarowany NASDAQ 100 z timing momentum, zeby uniknac
trzymania lewaru w bessie. TQQQ jest **syntetyzowany** z QQQ (daily return × 3), co pozwala
testowac strategie dalej niz 2010 (rok powstania prawdziwego TQQQ).

### Zasady
| Warunek | Akcja |
|---------|-------|
| QQQ momentum 12-1 > stopa wolna | → Trzymaj TQQQ (3x QQQ) |
| QQQ momentum 12-1 < stopa wolna | → Przejdz do obligacji AGG |

**Rebalans miesięczny** (co 21 dni roboczych) — identyczny timing jak GEM klasyczny.
Sygnal oparty na momentum 12-1 (skip-month) QQQ vs stopa wolna od ryzyka.

### Zalety
- **Potencjal ekstremalnych zyskow** — 3x lewar w silnym trendzie wzrostowym
- **Ochrona momentum** — wychodzi z lewaru gdy trend sie odwraca
- **Prosty sygnal** — ten sam momentum 12-1 co GEM, bez dodatkowej zlozonosci

### Wady i ryzyka
- **Ekstremalny drawdown** — nawet z timingiem, max DD moze przekroczyc -50% do -80%
- **Volatility decay** — 3x lewar dziennie ≠ 3x zwrot w dluzszym okresie (erozja w rynku bocznym)
- **Opozniony sygnal** — momentum 12-1 reaguje z opoznieniem, lewar poteguje straty w tym oknie
- **Syntetyczny TQQQ** — nie uwzglednia kosztow lewaru (financing, tracking error rzeczywistego ETF). Model `daily_return × 3` zawyza zwroty w zmiennych okresach — rzeczywisty TQQQ osiaga gorsze wyniki z powodu volatility drag
- **Nie dla kazdego** — wymaga wysokiej tolerancji na ryzyko i dlugiego horyzontu inwestycyjnego

### TQQQ Buy&Hold vs TQQQ+Momentum
TQQQ Buy&Hold historycznie daje ekstremalnie wysokie zwroty w hossie, ale drawdowny
-70% do -80% sa nie do zniesienia dla wiekszosci inwestorow. Momentum timing znaczaco
redukuje drawdown kosztem czesci zyskow — pytanie czy ta wymiana sie oplaca zalezy
od indywidualnej tolerancji na ryzyko.

> **UWAGA:** Ta strategia jest eksperymentalna i ekstremalnie ryzykowna.
> 3x lewar nie jest odpowiedni dla wiekszosci inwestorow.
""")

    st.markdown("### Krzywa kapitalu")
    fig = equity_chart({
        "TQQQ+Momentum": result["equity_tqqq_mom"],
        "TQQQ Buy&Hold": result["equity_tqqq_bh"],
        "QQQ Buy&Hold": result["equity_qqq"],
        "AGG Buy&Hold": result["equity_agg"],
    })
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Statystyki")
    stats_table(result["stats"])

    st.divider()
    _render_final_values([
        ("TQQQ+Momentum", result["equity_tqqq_mom"]),
        ("TQQQ Buy&Hold", result["equity_tqqq_bh"]),
        ("QQQ Buy&Hold", result["equity_qqq"]),
        ("AGG Buy&Hold", result["equity_agg"]),
    ], start_capital)

    _render_signals(result["signals"], {
        "TQQQ": "🟢 TQQQ (momentum > rf)", "AGG": "🟡 AGG (momentum < rf)",
    }, "Historia zmian sygnalu TQQQ+Momentum")


# ─── Porownanie wszystkich ────────────────────────────────────
elif strategy == "Porownanie wszystkich":
    gem = backtest_gem(prices, rf, start_capital=start_capital)
    sma = backtest_sma200(prices, rf, start_capital=start_capital)
    tqqq = backtest_tqqq_mom(prices, rf, start_capital=start_capital)

    if gem is None and sma is None and tqqq is None:
        st.error("Za malo danych do przeprowadzenia backtestu. Sprobuj dluzszy okres.")
        st.stop()

    # Zbierz krzywe equity — wspolny zakres dat
    curves = {}
    if gem is not None:
        curves["GEM"] = gem["equity_gem"]
    if sma is not None:
        curves["QQQ+SMA200"] = sma["equity_sma"]
    if tqqq is not None:
        curves["TQQQ+Momentum"] = tqqq["equity_tqqq_mom"]
    # Dodaj QQQ B&H jako benchmark (z dowolnego dostepnego)
    for r in [gem, sma, tqqq]:
        if r is not None and "equity_qqq" in r:
            curves["QQQ Buy&Hold"] = r["equity_qqq"]
            break

    # Wspolny zakres dat
    if len(curves) > 1:
        common_start = max(c.index[0] for c in curves.values())
        common_end = min(c.index[-1] for c in curves.values())
        curves_trimmed = {}
        for name, eq in curves.items():
            trimmed = eq.loc[common_start:common_end]
            # Renormalizuj do start_capital
            curves_trimmed[name] = trimmed / trimmed.iloc[0] * start_capital
        curves = curves_trimmed

    st.markdown("### Porownanie strategii — Krzywa kapitalu")
    fig = equity_chart(curves)
    st.plotly_chart(fig, use_container_width=True)

    # Wspolna tabela statystyk
    all_stats = {}
    if gem is not None:
        all_stats["GEM"] = gem["stats"]["GEM"]
    if sma is not None:
        all_stats["QQQ+SMA200"] = sma["stats"]["QQQ+SMA200"]
    if tqqq is not None:
        all_stats["TQQQ+Mom"] = tqqq["stats"]["TQQQ+Mom"]
    for r in [gem, sma, tqqq]:
        if r is not None and "QQQ B&H" in r["stats"]:
            all_stats["QQQ B&H"] = r["stats"]["QQQ B&H"]
            break

    if all_stats:
        st.markdown("### Statystyki")
        stats_table(all_stats)

    # Kafelki koncowe
    if curves:
        st.divider()
        _render_final_values([(n, eq) for n, eq in curves.items()], start_capital)

render_footer()
