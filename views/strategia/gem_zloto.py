"""Strona 25: GEM Gold Momentum — momentum ze zlotem (regula z inwestomat.eu) z Nasdaq-100 (QQQ) jak w GEM."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from components.sidebar import get_risk_free, render_footer
from data.downloader import download_prices
from data.momentum import (
    backtest_gem,
    backtest_gold_momentum,
    gold_momentum_now,
    gold_momentum_sensitivity,
    tbill_index,
    annual_returns,
    signal_time_share,
    calc_stats,
)
from components.cards import stats_table, kpi_card
from components.charts import equity_chart, drawdown_chart, _base_layout
from components.formatting import fmt_pct, fmt_number, color_for_value
from components.constants import GOLD, GREEN, RED, CHART_COLORS
from components.i18n import tr


st.markdown(tr("# GEM Gold Momentum"))
st.caption(
    tr("Momentum ze zlotem wg inwestomat.eu, w wersji GEM: momentum 12M wybiera miedzy Nasdaq-100 (QQQ), "
    "zlotem i bonami 3M, a w galezi akcji najsilniejszy z QQQ, rynkow rozwinietych ex-US (EFA) "
    "i rynkow wschodzacych (EEM). Autor artykulu uzywa S&P 500 zamiast QQQ.")
)

ASSET_LABELS = {
    "QQQ": "🇺🇸 Nasdaq-100 (QQQ)", "EFA": "🌍 Rozwiniete ex-US (EFA)", "EEM": "🌏 Wschodzace (EEM)",
    "GLD": "🥇 Zloto (GLD)", "IAU": "🥇 Zloto (IAU)",
    "TBILL": "💵 Bony 3M", "IEF": "📜 Obligacje 7-10Y (IEF)",
}
BRANCH_COLORS = {"Akcje": CHART_COLORS[1], "Zloto": GOLD, "Obligacje": GREEN}
GEM_TICKERS = ["QQQ", "VEA", "EEM", "ACWI", "AGG"]
us = "QQQ"  # akcje USA jak w GEM (autor: SPY)

# ====== Parametry ======
col1, col2, col3, col4 = st.columns(4)
with col1:
    gold = st.selectbox(tr("ETF na zloto"), ["GLD", "IAU"],
                        help=tr("GLD (od XI 2004) i IAU (od I 2005) sledza cene zlota; IAU ma nizsze TER."))
with col2:
    lookback = st.selectbox(tr("Okno momentum (miesiace)"), list(range(3, 16)), index=9,
                            help=tr("Autor testowal 3–15 mies.; w dlugim okresie najlepiej wypadlo 12M."))
with col3:
    start_capital = st.number_input(tr("Kapital poczatkowy (USD)"), value=10000, step=1000, min_value=100)
with col4:
    rf = get_risk_free()
    st.metric(tr("Stopa wolna (dla GEM)"), f"{rf:.2f}%")

with st.expander(tr("Koszty transakcji i podatek Belki")):
    cc1, cc2 = st.columns(2)
    with cc1:
        transaction_cost = st.slider(tr("Koszt przy zmianie aktywa (%)"), 0.0, 0.5, 0.0, 0.05,
                                     help=tr("Autor: 0,1% → ok. −0,6 p.p. rocznie, 0,3% → ok. −1,8 p.p."))
    with cc2:
        tax_belka = st.slider(tr("Podatek Belki (%)"), 0.0, 19.0, 0.0, 1.0,
                              help=tr("Od zysku segmentu przy kazdej zmianie aktywa (bez rozliczania strat). "
                                   "Dotyczy Gold Momentum i GEM; B&H bez podatku."))

# ====== Dane ======
GM_TICKERS = [us, "EFA", "EEM", "IEF", gold]
tickers = list(dict.fromkeys(GM_TICKERS + ["^IRX"] + GEM_TICKERS))
with st.spinner(tr("Pobieram pelna historie (od 2004)...")):
    raw = download_prices(tickers, period="max")

page_ok = raw is not None and not raw.empty
if page_ok:
    missing = [t for t in GM_TICKERS + ["^IRX"] if t not in raw.columns]
    if missing:
        st.error(tr('❌ Brak danych dla: {v0}. Odswiez strone za chwile.', v0=', '.join(missing)))
        page_ok = False
else:
    st.error(tr("❌ Nie udalo sie pobrac danych. Sprobuj odswiezyc strone."))

if page_ok:
    tb_full = tbill_index(raw["^IRX"])
    first_common = raw[GM_TICKERS].dropna().index[0]
    first_year = (first_common + pd.DateOffset(months=lookback + 1)).year
    last_year = raw.index[-1].year - 2
    start_year = st.select_slider(tr("Poczatek backtestu"), list(range(first_year, last_year + 1)),
                                  value=first_year,
                                  help=tr("Wspolna historia ETF-ow zaczyna sie pod koniec 2004 "
                                       "(GLD) — wczesniejsze lata nie sa dostepne w yfinance."))
    cut = pd.Timestamp(f"{start_year}-01-01") - pd.DateOffset(months=lookback + 1)
    prices = raw.loc[cut:]
    tb = tb_full.loc[cut:]

    res = backtest_gold_momentum(prices, tb, gold=gold, lookback_months=lookback,
                                 start_capital=float(start_capital),
                                 transaction_cost=transaction_cost / 100.0,
                                 tax_belka=tax_belka / 100.0, us=us)
    now = gold_momentum_now(raw, tb_full, gold=gold, lookback_months=lookback, us=us)
    if res is None:
        st.error(tr("❌ Za malo danych dla wybranego okna i poczatku backtestu."))
        page_ok = False

if page_ok:
    eq = res["equity"]
    gm = eq["GEM Gold Momentum"]
    gold_bh = f"{gold} B&H"
    us_bh = f"{us} B&H"
    st.caption(tr('Backtest miesieczny: {v0} → {v1} (~{v2} lat). Ostatni miesiac moze byc niepelny. Sharpe liczony wzgledem sredniej stopy bonow 3M z okresu ({v3}/rok).', v0=gm.index[0].date(), v1=gm.index[-1].date(), v2=f'{(len(gm) - 1) / 12:.1f}', v3=fmt_pct(res['rf_decimal'])))

    # GEM klasyczny (dzienny, co 21 sesji) — przeliczony na konce miesiecy
    gem_m = None
    if all(t in prices.columns for t in GEM_TICKERS):
        gem_res = backtest_gem(prices[GEM_TICKERS], rf, start_capital=float(start_capital),
                               transaction_cost=transaction_cost / 100.0, tax_belka=tax_belka / 100.0)
        if gem_res is not None:
            gem_m = gem_res["equity_gem"].resample("ME").last().dropna()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        tr("🎯 Sygnal teraz"), tr("📈 Backtest"), tr("🆚 vs GEM klasyczny"), tr("📉 Drawdown"),
        tr("📅 Zwroty roczne"), tr("🔧 Wrazliwosc na okno"), tr("🔄 Historia sygnalow"),
    ])

    # ─── Tab 1: sygnal teraz ───────────────────────────────────
    with tab1:
        if now is None:
            st.warning(tr("Za krotka historia do policzenia biezacego sygnalu."))
        else:
            r = now["returns"]
            st.markdown(tr('### Sygnal na zamkniecie {v0} (momentum {lookback}M)', v0=now['date'].date(), lookback=lookback))
            c1, c2, c3 = st.columns(3)
            kpi_card(c1, "Galaz", tr(now["branch"]), tr("najwyzsze momentum: {us} / zloto / bony 3M", us=us),
                     color=BRANCH_COLORS[now["branch"]])
            kpi_card(c2, "Aktywo do trzymania", tr(ASSET_LABELS.get(now["asset"], now["asset"])),
                     f"{lookback}M: {fmt_pct(r[now['asset']])}", color=GOLD)
            last_sig = res["signals"][-1]
            kpi_card(c3, "Ostatni sygnal miesieczny", tr(ASSET_LABELS.get(last_sig[1], last_sig[1])),
                     tr("od {date} (decyzja na koniec miesiaca)", date=last_sig[0].date()))

            def _bars(names, title):
                vals = [r[n] * 100 for n in names]
                fig = go.Figure(go.Bar(
                    x=[tr(ASSET_LABELS.get(n, n)) for n in names], y=vals,
                    marker_color=[GOLD if n == now["asset"] else (GREEN if v > 0 else RED)
                                  for n, v in zip(names, vals)],
                    text=[fmt_pct(r[n], 1) for n in names], textposition="outside",
                ))
                fig.update_layout(**_base_layout(title, height=340))
                fig.update_yaxes(title_text="%")
                return fig

            a, b = st.columns(2)
            a.plotly_chart(_bars([us, gold, "TBILL"], "Krok 1 — momentum absolutne (wybor galezi)"),
                           width="stretch")
            if now["branch"] == "Akcje":
                b.plotly_chart(_bars([us, "EFA", "EEM"], "Krok 2 — najlepszy indeks akcji"), width="stretch")
            elif now["branch"] == "Obligacje":
                b.plotly_chart(_bars(["TBILL", "IEF"], "Krok 2 — bony 3M czy obligacje 7-10Y"), width="stretch")
            else:
                b.plotly_chart(_bars([us, "EFA", "EEM", "TBILL", "IEF"],
                                     "Pozostale aktywa (dla kontekstu)"), width="stretch")
            st.caption(tr("Sygnal biezacy liczony od dzisiejszego zamkniecia; strategia handluje raz w miesiacu, "
                       "na podstawie zamkniecia ostatniej sesji miesiaca."))

    # ─── Tab 2: backtest ───────────────────────────────────────
    with tab2:
        shown = st.multiselect(tr("Krzywe na wykresie"), list(eq),
                               default=["GEM Gold Momentum", us_bh, gold_bh])
        log_y = st.toggle(tr("Skala logarytmiczna"), value=True)
        if shown:
            fig = equity_chart({n: eq[n] for n in shown})
            if log_y:
                fig.update_yaxes(type="log")
            st.plotly_chart(fig, width="stretch")

        st.markdown(tr("### Statystyki (dane miesieczne)"))
        stats_table(res["stats"])
        cols = st.columns(len(eq))
        for col, (name, s) in zip(cols, eq.items()):
            kpi_card(col, name, f"${fmt_number(s.iloc[-1], 0)}",
                     f"{fmt_pct(s.iloc[-1] / start_capital - 1)} lacznie",
                     color=GOLD if name == "GEM Gold Momentum" else "#E6E8EC")

        with st.expander(tr("📌 Skad w artykule ~20% rocznie, a tu mniej?")):
            st.markdown(tr('\nAutor podaje **19,97% rocznie dla lat 1972–2025**, liczone na danych indeksowych (S&P 500 z dywidendami,\nMSCI World ex-US, MSCI EM od 1988, cena zlota). Ten wynik w duzej mierze robi **hossa zlota z lat 70.**\n(z 35 do ok. 850 USD/oz), kiedy strategia trzymala zloto przez wieksza czesc dekady.\n\nTen backtest korzysta z **ETF-ow z yfinance**, wiec moze zaczac sie najwczesniej pod koniec 2005\n(GLD jest od XI 2004, do tego {lookback} mies. na pierwsze momentum).\n\nRegula zostala sprawdzona na wersji autora (z S&P 500): dla lat 2006–2025 autor podaje\n**7469 USD z 1000 USD, obsuniecie ok. −29% i 58 zmian**, a ta sama regula na ETF-ach daje 6444 USD,\n−28,6% i 52 zmiany. Roznice wynikaja z uzycia EFA zamiast MSCI World ex-US, kosztow ETF-ow i innych\ndni konca miesiaca. Ta strona uzywa **Nasdaq-100 (QQQ)** zamiast S&P 500, tak jak klasyczny GEM.\n\nSam autor zaznacza, ze ETF-y na zloto powstaly w XXI wieku, wiec wczesniej strategia byla w praktyce\nniewykonalna, a w latach 2011–2025 wygrywaja zwykle indeksy akcji.\n', lookback=lookback))

    # ─── Tab 3: vs GEM klasyczny ───────────────────────────────
    with tab3:
        if gem_m is None or gem_m.empty:
            st.warning(tr("Brak danych do GEM klasycznego (QQQ/VEA/EEM/ACWI/AGG) dla tego okresu."))
        else:
            start = max(gem_m.index[0], gm.index[0])
            common = {
                "GEM Gold Momentum": gm.loc[start:],
                "GEM klasyczny": gem_m.loc[start:],
                us_bh: eq[us_bh].loc[start:],
                gold_bh: eq[gold_bh].loc[start:],
            }
            common = {k: v / v.iloc[0] * start_capital for k, v in common.items()}
            st.caption(tr('Wspolny okres od {v0}: GEM wymaga ACWI (notowany od 2008) i roku historii na pierwszy sygnal. GEM liczony jest dziennie z rebalansem co 21 sesji, a tu pokazany na koncach miesiecy.', v0=start.date()))
            fig = equity_chart(common)
            fig.update_yaxes(type="log")
            st.plotly_chart(fig, width="stretch")
            stats_table({k: calc_stats(v, 12, res["rf_decimal"]) for k, v in common.items()})

            mg = common["GEM Gold Momentum"].pct_change().dropna()
            mc = common["GEM klasyczny"].pct_change().dropna()
            c1, c2, c3 = st.columns(3)
            kpi_card(c1, "Korelacja miesiecznych zwrotow", f"{mg.corr(mc):.2f}".replace(".", ","),
                     "Gold Momentum vs GEM klasyczny")
            half = (common["GEM Gold Momentum"] + common["GEM klasyczny"]) / 2
            half_stats = calc_stats(half, 12, res["rf_decimal"])
            kpi_card(c2, "Portfel 50/50 obu strategii", fmt_pct(half_stats["CAGR"]),
                     f"CAGR · Max DD {fmt_pct(half_stats['Max Drawdown'])} (bez rebalansu)",
                     color=color_for_value(half_stats["CAGR"]))
            yr = annual_returns({"GM": common["GEM Gold Momentum"], "GEM": common["GEM klasyczny"]})
            wins = int((yr["GM"] > yr["GEM"]).sum())
            kpi_card(c3, "Lata, gdy Gold Momentum > GEM", f"{wins} / {len(yr)}",
                     "pierwszy i ostatni rok niepelne")

    # ─── Tab 4: drawdown ───────────────────────────────────────
    with tab4:
        dd_names = st.multiselect(tr("Strategie"), list(eq), default=["GEM Gold Momentum", us_bh, gold_bh],
                                  key="dd_names")
        if dd_names:
            st.plotly_chart(drawdown_chart(pd.DataFrame({n: eq[n] for n in dd_names})), width="stretch")
        rows = []
        for name, s in eq.items():
            dd = s / s.cummax() - 1
            trough = dd.idxmin()
            peak = s.loc[:trough].idxmax()
            rec = s.loc[trough:][s.loc[trough:] >= s.loc[peak]]
            rows.append({
                "Strategia": name, "Max DD": fmt_pct(dd.min()),
                "Szczyt": str(peak.date()), "Dolek": str(trough.date()),
                "Odrobione": str(rec.index[0].date()) if len(rec) else "jeszcze nie",
                "Najdluzej pod woda (mies.)": int((dd < 0).astype(int).groupby((dd == 0).cumsum()).sum().max()),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(tr("Drawdown z danych miesiecznych — dzienne dolki bywaja glebsze."))

    # ─── Tab 5: zwroty roczne ──────────────────────────────────
    with tab5:
        curves = {"GEM Gold Momentum": gm, us_bh: eq[us_bh], gold_bh: eq[gold_bh]}
        if gem_m is not None and not gem_m.empty:
            curves["GEM klasyczny"] = gem_m.loc[gm.index[0]:]
        yr = annual_returns(curves)
        fig = go.Figure()
        for i, name in enumerate(yr.columns):
            fig.add_trace(go.Bar(x=yr.index.astype(str), y=yr[name] * 100, name=name,
                                 marker_color=GOLD if name == "GEM Gold Momentum"
                                 else CHART_COLORS[(i + 1) % len(CHART_COLORS)]))
        fig.update_layout(**_base_layout(tr("Zwroty kalendarzowe"), height=420), barmode="group")
        fig.update_yaxes(title_text="%")
        st.plotly_chart(fig, width="stretch")
        st.caption(tr("Pierwszy i ostatni rok sa niepelne. GEM klasyczny startuje pozniej (ACWI)."))
        st.dataframe(
            yr.rename_axis("Rok").style.format(lambda v: fmt_pct(v, 1))
            .map(lambda v: f"color:{color_for_value(v)}"),
            width="stretch",
        )

    # ─── Tab 6: wrazliwosc na okno ─────────────────────────────
    with tab6:
        sens = gold_momentum_sensitivity(prices, tb, gold=gold, windows=range(3, 16), us=us)
        if sens.empty:
            st.warning(tr("Za krotki okres do porownania okien 3–15 mies."))
        else:
            st.caption(tr("Wszystkie okna liczone na tym samym okresie (start wyznacza okno 15M), "
                       "bez kosztow i podatku."))
            fig = go.Figure()
            fig.add_trace(go.Bar(x=sens.index, y=sens["CAGR"] * 100, name=tr("CAGR"),
                                 marker_color=[GOLD if w == lookback else CHART_COLORS[1] for w in sens.index],
                                 text=[fmt_pct(v, 1) for v in sens["CAGR"]], textposition="outside"))
            fig.add_trace(go.Scatter(x=sens.index, y=sens["Max Drawdown"] * 100, name=tr("Max DD"),
                                     mode="lines+markers", line=dict(color=RED, width=2)))
            fig.update_layout(**_base_layout(tr("CAGR i Max DD wg okna momentum"), height=400))
            fig.update_xaxes(title_text=tr("Okno (miesiace)"), dtick=1)
            fig.update_yaxes(title_text="%")
            st.plotly_chart(fig, width="stretch")
            tbl = sens.copy()
            tbl["CAGR"] = tbl["CAGR"].map(fmt_pct)
            tbl["Max Drawdown"] = tbl["Max Drawdown"].map(fmt_pct)
            tbl["Sharpe"] = tbl["Sharpe"].map(lambda v: f"{v:.2f}".replace(".", ","))
            st.dataframe(tbl, width="stretch")
            st.caption(tr("Autor: w latach 1972–2025 najlepsze bylo 12M (potem 15M i 11M), ale w 2006–2025 "
                       "wygrywalo 4M. Wybor okna po fakcie to data snooping. Rozrzut wynikow miedzy "
                       "sasiednimi oknami pokazuje, jak mocno wynik zalezy od tego parametru."))

    # ─── Tab 7: historia sygnalow ──────────────────────────────
    with tab7:
        share = signal_time_share(res["signals"], gm.index[:-1])
        branch_share = res["branches"].value_counts(normalize=True)
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Pie(
                labels=[tr(ASSET_LABELS.get(a, a)) for a in share.index], values=share.values, hole=0.5,
                marker=dict(colors=[GOLD if a == gold else CHART_COLORS[(i + 1) % len(CHART_COLORS)]
                                    for i, a in enumerate(share.index)])))
            fig.update_layout(**_base_layout(tr("Czas w aktywach"), height=340))
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig = go.Figure(go.Pie(labels=[tr(b) for b in branch_share.index], values=branch_share.values, hole=0.5,
                                   marker=dict(colors=[BRANCH_COLORS[b] for b in branch_share.index])))
            fig.update_layout(**_base_layout(tr("Czas w galeziach"), height=340))
            st.plotly_chart(fig, width="stretch")
        st.caption(tr("Autor (1972–2025): akcje ~50% (S&P 500 27,6%, EM 15,4%, World ex-US 6,9%), "
                   "zloto 38,4%, obligacje 11,6%."))

        sigs = res["signals"]
        holds = [((sigs[i + 1][0] if i + 1 < len(sigs) else gm.index[-1]) - d).days / 30.44
                 for i, (d, _) in enumerate(sigs)]
        years = (len(gm) - 1) / 12
        c1, c2, c3 = st.columns(3)
        kpi_card(c1, "Zmiany aktywa", str(len(sigs) - 1), f"~{(len(sigs) - 1) / years:.1f} rocznie")
        kpi_card(c2, "Sredni czas trzymania", f"{sum(holds) / len(holds):.1f} mies.".replace(".", ","),
                 "autor: ok. 4,7 mies.")
        kpi_card(c3, "Mediana czasu trzymania", f"{pd.Series(holds).median():.1f} mies.".replace(".", ","),
                 "autor: 2 mies.")

        rows = []
        for i, (d, a) in enumerate(sigs):
            end = sigs[i + 1][0] if i + 1 < len(sigs) else gm.index[-1]
            seg = gm.loc[d:end]
            rows.append({"Decyzja (koniec mies.)": str(d.date()), "Do": str(end.date()),
                         "Aktywo": tr(ASSET_LABELS.get(a, a)),
                         "Zwrot segmentu": fmt_pct(seg.iloc[-1] / seg.iloc[0] - 1) if len(seg) > 1 else "—"})
        st.dataframe(pd.DataFrame(rows[::-1]), hide_index=True, width="stretch")

    st.divider()
    with st.expander(tr("ℹ️ Zasady strategii i ograniczenia backtestu")):
        st.markdown(tr('\n**Regula (raz w miesiacu, na zamkniecie ostatniej sesji):**\n1. Policz {lookback}-miesieczny zwrot akcji USA ({us}), zlota ({gold}) i bonow 3M. Najwyzszy z nich wybiera galaz.\n2. **Akcje** → kup najsilniejszy z: akcje USA ({us}), rynki rozwiniete ex-US (EFA), rynki wschodzace (EEM).\n3. **Obligacje** → bony 3M albo obligacje USA 7-10Y (IEF), w zaleznosci od tego, co ma wyzsze momentum.\n4. **Zloto** → {gold}.\n\n**Ograniczenia:**\n- Bony 3M odtworzone z rentownosci ^IRX (bez ETF-u), obligacje 7-10Y = IEF (od 2002).\n- EFA to MSCI EAFE (bez Kanady), a autor uzywa MSCI World ex-US, wiec sklad nieco sie rozni.\n- Ceny w USD. Dla inwestora z PLN dochodzi kurs USD/PLN; {gold} nie jest dostepny w polskich IKE/IKZE\n  (odpowiedniki UCITS: zloto IGLN/SGLD/4GLD, S&P 500 CSPX/VUAA, EM EIMI, ex-US EXUS).\n- Brak slippage i spreadu; podatek uproszczony (bez rozliczania strat).\n- **QQQ to wybor po fakcie** — Nasdaq-100 byl najlepszym duzym indeksem ostatnich 20 lat, wiec wariant\n  z QQQ ma wbudowana przewage, ktorej nikt nie znal w 2005. Autor testowal S&P 500.\n', lookback=lookback, us=us, gold=gold))

render_footer()
