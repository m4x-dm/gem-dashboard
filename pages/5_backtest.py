"""Strona 5: Backtest strategii — GEM, QQQ+SMA200, TQQQ+Momentum."""

import streamlit as st
import pandas as pd
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS
from data.downloader import download_prices
from data.momentum import backtest_gem, backtest_sma200, backtest_tqqq_mom, walk_forward_gem
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
        "Walk-forward GEM",
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

# Pobierz dane (z ^VIX dla regime filtera)
tickers = list(set(ALL_TICKERS + st.session_state.get("custom_tickers", []) + ["^VIX"]))
prices = download_prices(tickers, period=period)

# Wyciagnij VIX jako osobny szereg, usun z prices zeby nie mieszal w backtestach
vix_series = None
if "^VIX" in prices.columns:
    vix_series = prices["^VIX"].dropna()
    prices = prices.drop(columns=["^VIX"])


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
        costs_on_gem = st.checkbox(
            "Koszty i podatki (realistycznie)",
            value=False,
            key="gem_costs_on",
            help="Dodaj: (1) koszt roundtrip przy kazdej zmianie sygnalu (spread+prowizja), "
                 "(2) podatek Belki 19% od zyskownych segmentow (zrealizowany zysk = rozliczany przy sprzedazy).",
        )
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            tc_gem_pct = st.slider(
                "Koszt roundtrip (%)", 0.0, 0.5, 0.05, 0.01,
                disabled=not costs_on_gem,
                key="gem_tc",
                help="IBKR/Bossa ~0.02-0.1%, XTB ETF ~0.05-0.2%. Polska stawka plus spread.",
            ) / 100.0
        with col_c2:
            belka_on_gem = st.checkbox(
                "Belka 19%",
                value=False,
                disabled=not costs_on_gem,
                key="gem_belka",
                help="Podatek od zyskow kapitalowych (PL). Placony per segment: przy kazdej "
                     "zmianie sygnalu realizowany jest zysk/strata na dotychczasowej pozycji.",
            )
        regime_on_gem = st.checkbox(
            "Filtr regime (VIX)",
            value=False,
            disabled=(vix_series is None),
            key="gem_regime",
            help="Gdy VIX > progu, ignoruje momentum i siedzi w AGG. Historycznie VIX>30 "
                 "markuje panike (2008, 2020, 2022). Obniza CAGR w normalnym rynku, "
                 "ale drastycznie ratuje drawdown w stressie.",
        )
        vix_thr_gem = st.slider(
            "Prog VIX", 15.0, 50.0, 30.0, 1.0,
            disabled=not regime_on_gem,
            key="gem_vix_thr",
            help="30 = klasyczny prog paniki. 25 = ostrozniej (wiecej dni w AGG).",
        )
    vol_target_val = vol_target_pct if vol_on else None
    tc_gem = tc_gem_pct if costs_on_gem else 0.0
    tax_gem = 0.19 if (costs_on_gem and belka_on_gem) else 0.0
    rs_gem = vix_series if (regime_on_gem and vix_series is not None) else None
    result = backtest_gem(prices, rf, start_capital=start_capital,
                          trend_filter=trend_filter,
                          vol_target=vol_target_val, max_leverage=max_lev,
                          transaction_cost=tc_gem, tax_belka=tax_gem,
                          regime_series=rs_gem, regime_threshold=vix_thr_gem)
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
        costs_on_sma = st.checkbox(
            "Koszty i podatki (realistycznie)",
            value=False,
            key="sma_costs_on",
            help="Dodaj: (1) koszt roundtrip przy zmianie sygnalu, (2) podatek Belki 19% "
                 "od zyskownych segmentow. SMA z dziennym checkiem ma duzo whipsawow — "
                 "realistyczne koszty znaczaco obnizaja CAGR.",
        )
        col_sc1, col_sc2 = st.columns(2)
        with col_sc1:
            tc_sma_pct = st.slider(
                "Koszt roundtrip (%) ", 0.0, 0.5, 0.05, 0.01,
                disabled=not costs_on_sma,
                key="sma_tc",
                help="Spread + prowizja przy kazdej zmianie QQQ<->AGG.",
            ) / 100.0
        with col_sc2:
            belka_on_sma = st.checkbox(
                "Belka 19% ",
                value=False,
                disabled=not costs_on_sma,
                key="sma_belka",
                help="Podatek od zyskow kapitalowych (PL) rozliczany per segment.",
            )
        regime_on_sma = st.checkbox(
            "Filtr regime (VIX) ",
            value=False,
            disabled=(vix_series is None),
            key="sma_regime",
            help="VIX > progu → AGG niezaleznie od sygnalu SMA. Przydatne gdy rynek "
                 "oscyluje wokol SMA200 w okresie wysokiej niepewnosci.",
        )
        vix_thr_sma = st.slider(
            "Prog VIX ", 15.0, 50.0, 30.0, 1.0,
            disabled=not regime_on_sma,
            key="sma_vix_thr",
        )
    vol_target_val_sma = vol_target_pct_sma if vol_on_sma else None
    tc_sma = tc_sma_pct if costs_on_sma else 0.0
    tax_sma = 0.19 if (costs_on_sma and belka_on_sma) else 0.0
    rs_sma = vix_series if (regime_on_sma and vix_series is not None) else None
    result = backtest_sma200(prices, rf, start_capital=start_capital,
                              buffer_pct=buffer_pct, monthly_check=monthly_check,
                              vol_target=vol_target_val_sma, max_leverage=max_lev_sma,
                              transaction_cost=tc_sma, tax_belka=tax_sma,
                              regime_series=rs_sma, regime_threshold=vix_thr_sma)
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
        costs_on_tqqq = st.checkbox(
            "Koszty transakcji + Belka",
            value=False,
            key="tqqq_costs_on",
            help="Dodaj koszt roundtrip przy zmianie sygnalu (TQQQ<->AGG) i podatek Belki "
                 "19% od zyskownych segmentow.",
        )
        col_tc1, col_tc2 = st.columns(2)
        with col_tc1:
            tc_tqqq_pct = st.slider(
                "Koszt roundtrip (%)  ", 0.0, 0.5, 0.05, 0.01,
                disabled=not costs_on_tqqq,
                key="tqqq_tc",
                help="Spread + prowizja. TQQQ ma duzy spread srodsesyjny (0.05-0.15%).",
            ) / 100.0
        with col_tc2:
            belka_on_tqqq = st.checkbox(
                "Belka 19%  ",
                value=False,
                disabled=not costs_on_tqqq,
                key="tqqq_belka",
                help="Podatek od zyskow kapitalowych rozliczany per segment.",
            )
        regime_on_tqqq = st.checkbox(
            "Filtr regime (VIX)  ",
            value=False,
            disabled=(vix_series is None),
            key="tqqq_regime",
            help="KRYTYCZNY dla TQQQ — leveraged ETF giną w regime'ach paniki (2008, "
                 "2020, 2022 spadki 50-80%). VIX>30 → AGG ratuje konto od katastrofy.",
        )
        vix_thr_tqqq = st.slider(
            "Prog VIX  ", 15.0, 50.0, 30.0, 1.0,
            disabled=not regime_on_tqqq,
            key="tqqq_vix_thr",
        )
    er = expense_ratio_pct if realistic_costs else 0.0
    sp = borrow_spread_pct if realistic_costs else 0.0
    tc_tqqq = tc_tqqq_pct if costs_on_tqqq else 0.0
    tax_tqqq = 0.19 if (costs_on_tqqq and belka_on_tqqq) else 0.0
    rs_tqqq = vix_series if (regime_on_tqqq and vix_series is not None) else None
    result = backtest_tqqq_mom(prices, rf, start_capital=start_capital,
                                leverage=leverage, expense_ratio=er,
                                borrow_spread=sp,
                                transaction_cost=tc_tqqq, tax_belka=tax_tqqq,
                                regime_series=rs_tqqq, regime_threshold=vix_thr_tqqq)
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


# ─── Walk-forward GEM ─────────────────────────────────────────
elif strategy == "Walk-forward GEM":
    st.caption(
        "Rolling in-sample / out-of-sample — dla kazdego okna IS siatka parametrow "
        "(trend_filter × vol_target) oceniana po wybranej metryce, najlepszy zestaw "
        "uruchamiany na OOS. Wyniki OOS lancuchowane w jedna krzywa. Wymaga >=6 lat "
        "danych (domyslnie 5 IS + 1 OOS). Uwaga: okres powyzej musi byc wystarczajaco dlugi."
    )
    with st.expander("⚙️ Ustawienia walk-forward", expanded=True):
        col_wf1, col_wf2, col_wf3, col_wf4 = st.columns(4)
        with col_wf1:
            is_years = st.slider(
                "Dlugosc IS (lat)", 3.0, 8.0, 5.0, 0.5,
                help="In-sample window — na nim dobierane sa parametry.",
            )
        with col_wf2:
            oos_years = st.slider(
                "Dlugosc OOS (lat)", 0.5, 2.0, 1.0, 0.25,
                help="Out-of-sample window — na nim liczone realne zwroty.",
            )
        with col_wf3:
            step_years = st.slider(
                "Krok (lat)", 0.5, 2.0, 1.0, 0.25,
                help="O ile rolujemy okna. 1.0 = nowy fold co rok.",
            )
        with col_wf4:
            select_metric = st.selectbox(
                "Metryka wyboru", ["Sharpe", "Calmar", "CAGR"],
                index=0,
                help="Po czym wybieramy 'najlepsze parametry' na IS.",
            )

    wf = walk_forward_gem(
        prices, rf,
        is_years=is_years, oos_years=oos_years, step_years=step_years,
        select_metric=select_metric,
    )
    if wf is None:
        st.error(
            f"Za malo danych — walk-forward potrzebuje co najmniej "
            f"~{int(is_years + oos_years) + 1} lat historii + bufor momentum 273 dni. "
            "Zwieksz okres lub skroc IS/OOS."
        )
        st.stop()

    folds = wf["folds"]
    st.markdown(f"### Przebieg walk-forward — {len(folds)} foldow")

    fold_rows = []
    for i, f in enumerate(folds, start=1):
        fp = f["best_params"]
        oss = f["oos_stats"]
        fold_rows.append({
            "Fold": i,
            "IS od": f["is_start"].strftime("%Y-%m-%d"),
            "IS do": f["is_end"].strftime("%Y-%m-%d"),
            "OOS od": f["oos_start"].strftime("%Y-%m-%d"),
            "OOS do": f["oos_end"].strftime("%Y-%m-%d"),
            "Trend filter": "T" if fp.get("trend_filter") else "-",
            "Vol target": f"{fp.get('vol_target'):.0%}" if fp.get("vol_target") else "-",
            "OOS CAGR": f"{oss.get('CAGR', 0):.1%}" if oss.get("CAGR") is not None else "-",
            "OOS Sharpe": f"{oss.get('Sharpe', 0):.2f}" if oss.get("Sharpe") is not None else "-",
            "OOS MaxDD": f"{oss.get('Max Drawdown', 0):.1%}" if oss.get("Max Drawdown") is not None else "-",
        })
    fold_df = pd.DataFrame(fold_rows)
    st.dataframe(fold_df, use_container_width=True, hide_index=True)

    # OOS chain chart
    st.markdown("### Krzywa kapitalu (OOS chain)")
    oos_chain = wf["oos_chain"] * start_capital
    charts = {"Walk-forward OOS": oos_chain}
    if wf.get("qqq_oos_chain") is not None:
        charts["QQQ B&H (ten sam zakres)"] = wf["qqq_oos_chain"] * start_capital
    fig_wf = equity_chart(charts)
    st.plotly_chart(fig_wf, use_container_width=True)

    # Aggregated OOS summary
    st.markdown("### Podsumowanie OOS vs QQQ")
    summary = {"Walk-forward OOS": wf["oos_summary"]}
    if wf.get("qqq_oos_summary") is not None:
        summary["QQQ B&H"] = wf["qqq_oos_summary"]
    stats_table(summary)

    st.divider()
    kafelki = [("Walk-forward OOS", oos_chain)]
    if wf.get("qqq_oos_chain") is not None:
        kafelki.append(("QQQ B&H", wf["qqq_oos_chain"] * start_capital))
    _render_final_values(kafelki, start_capital)

    # Param stability
    st.markdown("### Stabilnosc parametrow")
    hits = wf.get("param_hits", {})
    if hits:
        total = sum(hits.values())
        hit_rows = []
        for k, v in sorted(hits.items(), key=lambda x: -x[1]):
            hit_rows.append({
                "Parametry": k,
                "Wybrane w X foldach": v,
                "% foldow": f"{v/total:.0%}",
            })
        st.dataframe(pd.DataFrame(hit_rows), use_container_width=True, hide_index=True)
        st.caption(
            "Gdy jedna kombinacja dominuje (>=60% foldow) — parametry sa stabilne historycznie. "
            "Rozproszenie (3+ roznych po ~20%) sugeruje ze kazdy rezim rynkowy preferuje inne "
            "ustawienia — rozwazyc regime-aware alokacje."
        )

render_footer()
