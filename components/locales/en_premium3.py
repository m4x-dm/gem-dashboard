"""Katalog EN — strony Premium, czesc 3: spolki (S&P 500, GPW, Top Picks, ...) i strategie."""

SPOLKI: dict[str, str] = {
    # GPW
    "# Polskie Akcje GPW": "# Polish stocks (Warsaw, GPW)",
    "📊 Screening": "📊 Screening",
    "📈 Sprawozdania Q": "📈 Quarterly reports",
    "### Wykresy — spolki GPW": "### Charts — Warsaw stocks",
    "Wybierz spolki (maks. 5)": "Choose stocks (max. 5)",
    "### Porownanie spolek GPW": "### Warsaw stock comparison",
    "### Relative Strength vs WIG20": "### Relative strength vs WIG20",
    "RS > 100 = spolka outperformuje WIG20 (benchmark: ETF Beta WIG20TR)":
        "RS > 100 = the stock is outperforming the WIG20 (benchmark: Beta WIG20TR ETF)",
    "### Ranking momentum — spolki GPW": "### Momentum ranking — Warsaw stocks",
    "Wybierz co najmniej 1 spolke.": "Choose at least 1 stock.",
    "Wybierz 2-4 spolek / indeksow do porownania": "Choose 2-4 stocks / indices to compare",
    "Wybierz co najmniej 2 spolki / indeksy.": "Choose at least 2 stocks / indices.",
    "### Backtest rotacji momentum — GPW": "### Momentum rotation backtest — Warsaw",
    "Co miesiac kupuj top N spolek wg wyniku kompozytowego. Porownanie z equal-weight buy & hold.":
        "Each month buy the top N stocks by composite score. Compared with equal-weight buy & hold.",
    "### Screening fundamentalny — WIG20 + mWIG40": "### Fundamental screening — WIG20 + mWIG40",
    "Pelna tabela 11 wskaznikow. Banki (PKO, PEO, SPL, MBK, BHW, BNP, MIL, ING, ALR) pokazuja „N/A bank” w EV/EBITDA "
    "— nie raportuja klasycznego EBITDA. Dane z yfinance, cache 24h.":
        "Full table of 11 ratios. Banks (PKO, PEO, SPL, MBK, BHW, BNP, MIL, ING, ALR) show “N/A bank” for EV/EBITDA "
        "— they do not report classic EBITDA. Data from yfinance, cached for 24h.",
    "**Filtry glowne**": "**Main filters**",
    "P/E max": "P/E max",
    "ROE min (%)": "ROE min (%)",
    "EV/EBITDA max": "EV/EBITDA max",
    "Sektory": "Sectors",
    "Market cap min (mld zl)": "Market cap min (PLN bn)",
    "Tylko BUY": "BUY only",
    "Sortuj wg": "Sort by",
    "📥 Eksport CSV": "📥 Export CSV",
    "💡 Spolki z brakujacym wskaznikiem sa odfiltrowane gdy filtr aktywny.":
        "💡 Stocks missing a ratio are filtered out while that filter is active.",
    "🏦 Banki nie raportuja klasycznego EBITDA — kolumna EV/EBITDA pokazuje „N/A bank”. Filtr EV/EBITDA max wyklucza banki z tabeli.":
        "🏦 Banks do not report classic EBITDA — the EV/EBITDA column shows “N/A bank”. The EV/EBITDA max filter excludes banks from the table.",
    "### 📈 Sprawozdania finansowe — kwartalne + beat/miss vs consensus":
        "### 📈 Financial reports — quarterly + beat/miss vs consensus",
    "⚠️ Czesc spolek GPW (small-cap) nie ma pelnych danych w yfinance — gaps to oczekiwane.":
        "⚠️ Some Warsaw small caps lack complete data in yfinance — gaps are expected.",
    "Indeks": "Index",
    "Brak tickerow dla wybranego indeksu.": "No tickers for the selected index.",
    "Top N spolek": "Top N stocks",
    "Kapital (PLN)": "Capital (PLN)",
    "Nie udalo sie pobrac danych WIG20.": "Could not download WIG20 data.",
    "Pobieram dane fundamentalne universe...": "Downloading fundamental data for the universe...",
    "Nie udalo sie pobrac danych z yfinance. Sprobuj odswiezyc strone.": "Could not download data from yfinance. Try refreshing the page.",
    "Zaawansowane filtry": "Advanced filters",
    "Div Yield min (%)": "Div yield min (%)",
    "Revenue Growth min (%)": "Revenue growth min (%)",
    "Debt/E max": "Debt/E max",
    "Profit Margin min (%)": "Profit margin min (%)",
    "P/B max": "P/B max",
    "Brak wynikow po zastosowaniu filtrow. Sprobuj rozluznic kryteria.": "No results with these filters. Try loosening the criteria.",
    "Wybierz spółkę:": "Choose a company:",
    "Pobieram dane GPW...": "Downloading Warsaw data...",
    "Za malo danych dla widoku Strategia 12-1.": "Not enough data for the 12-1 strategy view.",
    "Zamiast wazonej sumy surowych zwrotow, rankuje tickery per okres (0-1). 1M flipowany jako anti-signal "
    "(short-term reversal). Odporny na outliery i skew miedzy aktywami.":
        "Instead of a weighted sum of raw returns, ranks tickers per period (0-1). 1M is flipped as an anti-signal "
        "(short-term reversal). Robust to outliers and skew between assets.",
    "Gdy mniej niz X% spolek w indeksie jest powyzej SMA200 → strategia przechodzi do cash. Chroni GPW przed trendami spadkowymi (2008, 2022).":
        "When fewer than X% of the index's stocks are above their SMA200 → the strategy moves to cash. Protects against Warsaw downtrends (2008, 2022).",
    "Prog breadth (% > SMA200)": "Breadth threshold (% > SMA200)",
    "Top 15 — wynik momentum GPW": "Top 15 — Warsaw momentum score",
    "Podatek rozliczany od frakcji portfela rotowanej przy rebalansie.": "Tax is applied to the fraction of the portfolio rotated at each rebalance.",
    "GPW: prowizja Bossa/XTB ~0.1-0.2%, spread dla mid-capow 0.2-0.5%. Default 0.2%.":
        "Warsaw: Bossa/XTB commission ~0.1-0.2%, mid-cap spread 0.2-0.5%. Default 0.2%.",
    # S&P 500
    "# Amerykanskie Akcje S&P 500": "# US stocks — S&P 500",
    "### Wykresy — S&P 500": "### Charts — S&P 500",
    "### Porownanie spolek S&P 500": "### S&P 500 stock comparison",
    "### Relative Strength vs SPY": "### Relative strength vs SPY",
    "RS > 100 = spolka outperformuje benchmark (SPY)": "RS > 100 = the stock is outperforming the benchmark (SPY)",
    "### Ranking momentum — S&P 500": "### Momentum ranking — S&P 500",
    "Wybierz 2-4 spolki do porownania": "Choose 2-4 stocks to compare",
    "Wybierz co najmniej 2 spolki.": "Choose at least 2 stocks.",
    "### Backtest rotacji momentum — S&P 500": "### Momentum rotation backtest — S&P 500",
    "Co miesiac kupuj top N spolek wg wyniku kompozytowego. Porownanie z equal-weight B&H i SPY B&H.":
        "Each month buy the top N stocks by composite score. Compared with equal-weight B&H and SPY B&H.",
    "### Screening fundamentalny — top 100 S&P 500": "### Fundamental screening — top 100 S&P 500",
    "Pelna tabela 11 wskaznikow (P/E, ROE, EV/EBITDA, marze, FCF, div yield, target). Filtruj + sortuj wg kryteriow. Dane z yfinance, cache 24h.":
        "Full table of 11 ratios (P/E, ROE, EV/EBITDA, margins, FCF, div yield, target). Filter and sort by your criteria. Data from yfinance, cached for 24h.",
    "Market cap min ($B)": "Market cap min ($B)",
    "💡 Spolki z brakujacym wskaznikiem sa odfiltrowane gdy filtr aktywny (np. spolka bez P/E nie pojawi sie gdy P/E max < 100).":
        "💡 Stocks missing a ratio are filtered out while that filter is active (e.g. a stock without a P/E won't appear when P/E max < 100).",
    "Brak tickerow dla wybranego sektora.": "No tickers for the selected sector.",
    "Nie udalo sie pobrac danych SPY.": "Could not download SPY data.",
    "Tylko spolki z rekomendacja BUY/STRONG_BUY/OUTPERFORM": "Only stocks rated BUY/STRONG_BUY/OUTPERFORM",
    "Pobieram dane S&P 500...": "Downloading S&P 500 data...",
    "Koszt transakcji skalowany turnoverem (frakcja tickerow wymienionych przy rebalansie) + Belka 19% od zyskownych segmentow.":
        "Transaction cost scaled by turnover (the fraction of tickers replaced at rebalance) + 19% Polish capital gains tax (Belka) on profitable segments.",
    "Gdy mniej niz X% spolek w universum jest powyzej SMA200 → strategia przechodzi do cash (pomija rebalans). "
    "Chroni przed bessa. Default 40% = Faber-style breadth filter.":
        "When fewer than X% of stocks in the universe are above their SMA200 → the strategy moves to cash (skips the rebalance). "
        "Protects against bear markets. Default 40% = Faber-style breadth filter.",
    "Top 15 — wynik momentum S&P 500": "Top 15 — S&P 500 momentum score",
    "Rozliczany od frakcji portfela faktycznie rotowanej w rebalansie.": "Applied to the fraction of the portfolio actually rotated at the rebalance.",
    "US akcje: IBKR ~0.02-0.05%, ale + spread ~0.05-0.1% dla mid-capow. Default 0.1%.":
        "US stocks: IBKR ~0.02-0.05%, plus a ~0.05-0.1% spread for mid caps. Default 0.1%.",
    # Insiderzy
    "# Bulk Insider Screener": "# Insider screener",
    "Bulk insider activity dla SP500 (456 spolek). Window: ostatnie 6 mc. ETF wykluczone (no insider data). "
    "GPW pominiete (yfinance nie ma SEC Form 4 dla PL).":
        "Insider activity across the S&P 500 (456 companies). Window: last 6 months. ETFs excluded (no insider data). "
        "Warsaw skipped (yfinance has no SEC Form 4 data for Poland).",
    "Spolek z danymi": "Companies with data",
    "Net Buyers 🟢": "Net buyers 🟢",
    "Net Sellers 🔴": "Net sellers 🔴",
    "Avg Net 6mc": "Avg net 6m",
    "### 📈 Top movers": "### 📈 Top movers",
    "### 🏭 Net insider activity per sektor": "### 🏭 Net insider activity by sector",
    "### 🏢 Karta spółki": "### 🏢 Company profile",
    "Brak danych insider — yfinance moze byc globalnie blocked dla insider endpointow. Sprobuj ponownie za kilka minut (cache 24h).":
        "No insider data — yfinance may be blocking insider endpoints globally. Try again in a few minutes (24h cache).",
    "Brak danych sektorowych po filtrach.": "No sector data after filtering.",
    "Sektor": "Sector",
    "Status": "Status",
    "Min |Net Value| ($)": "Min |net value| ($)",
    "Min beat streak (mc 0-6)": "Min beat streak (months 0-6)",
    "Min Market Cap": "Min market cap",
    "🔄 Refresh cache": "🔄 Refresh cache",
    "Brak net buyers po filtrach.": "No net buyers after filtering.",
    "Brak net sellers po filtrach.": "No net sellers after filtering.",
    "Sum net insider value 6 mc per sektor": "Sum of net insider value over 6 months by sector",
    "Sum Net Value USD": "Sum net value USD",
    "Filter abs(net_value_6m). 0 = bez filtra.": "Filter on abs(net_value_6m). 0 = no filter.",
    "Top 10 Net Buyers (6 mc)": "Top 10 net buyers (6 months)",
    "Net Value USD": "Net value USD",
    "Top 10 Net Sellers (6 mc)": "Top 10 net sellers (6 months)",
    # Kalendarz wynikow
    "# Earnings Calendar": "# Earnings calendar",
    "Nadchodzace i niedawne raporty (±28 dni) dla SP500 + GPW. Kliknij ⭐ aby dodac spolke do watchlistu. ETF wykluczone — nie maja earnings.":
        "Upcoming and recent reports (±28 days) for the S&P 500 + Warsaw. Click ⭐ to add a company to your watchlist. ETFs excluded — they have no earnings.",
    "Total ±28d": "Total ±28d",
    "Future (nadchodzace)": "Upcoming",
    "Past Beat / Miss": "Past beat / miss",
    "### 📋 Tabela raportow": "### 📋 Report table",
    "Brak danych earnings w wybranym oknie ±28 dni.": "No earnings data in the selected ±28-day window.",
    "Kalendarz miesiecy — 8 tygodni (T-3 do T+4)": "Calendar — 8 weeks (W-3 to W+4)",
    "Brak wynikow po filtrach.": "No results after filtering.",
    "Market": "Market",
    "Sektor (multiselect)": "Sector (multi-select)",
    "Sort": "Sort",
    "Raporty": "Reports",
    # Screener cross-asset
    "# Cross-Asset Screener": "# Cross-asset screener",
    "Jednolity ranking momentum ze wszystkich klas aktywow": "A single momentum ranking across all asset classes",
    "### Wynik kompozytowy — top aktywa": "### Composite score — top assets",
    "Klasy aktywow": "Asset classes",
    "Min. wynik kompozytowy (%)": "Min. composite score (%)",
    "Wybierz co najmniej jedna klase aktywow.": "Choose at least one asset class.",
    "Pobieram dane i buduje ranking...": "Downloading data and building the ranking...",
    "Nie udalo sie pobrac danych dla zadnej klasy aktywow.": "Could not download data for any asset class.",
    "Brak wynikow po zastosowaniu filtrow.": "No results with these filters.",
    "Top aktywa wg wyniku kompozytowego": "Top assets by composite score",
    # Top Picks
    "# Top Picks — piatka miesiaca": "# Top Picks — this month's five",
    "Piec niezaleznych regul wybiera po piatce spolek pierwszego dnia miesiaca. Kazda patrzy na co innego: cenowe momentum, "
    "jakosc wynikow kwartalnych, jakosc biznesu albo konsensus analitykow. Sklad nie jest recznie korygowany.":
        "Five independent rules each pick five stocks on the first day of the month. Each looks at something different: price momentum, "
        "quarterly earnings quality, business quality or analyst consensus. The picks are never adjusted by hand.",
    "## Wyniki live": "## Live results",
    "📈 Momentum": "📈 Momentum",
    "📊 Earnings Momentum": "📊 Earnings momentum",
    "🏛️ Jakosc biznesu": "🏛️ Business quality",
    "🎯 Polecane przez analitykow": "🎯 Analyst favourites",
    "💹 Potencjal do ceny docelowej": "💹 Upside to target price",
    "Kolumny fundamentalne (P/E, Fwd P/E, ROE, dywidenda) sa **kontekstem do samodzielnej oceny** — nie biora udzialu w wyborze spolek. "
    "Regula patrzy wylacznie na momentum, plynnosc i limit sektorowy.":
        "The fundamental columns (P/E, Fwd P/E, ROE, dividend) are **context for your own judgement** — they play no part in the selection. "
        "The rule looks only at momentum, liquidity and the sector limit.",
    "🔬 Symulacja reguly wstecz — przeczytaj zastrzezenie": "🔬 Backward simulation of the rule — read the caveat",
    "**To nie jest track record.** Sklad historyczny liczony z DZISIEJSZEGO universe (SP500_TOP100 i obecne sklady WIG20/mWIG40/sWIG80). "
    "Spolki, ktore wypadly z indeksow, w danych nie istnieja — survivorship bias zawyza wynik. Traktuj to jako test spojnosci reguly, "
    "nie jako obietnice zwrotu.":
        "**This is not a track record.** The historical picks are calculated from TODAY's universe (SP500_TOP100 and the current WIG20/mWIG40/sWIG80). "
        "Companies that dropped out of the indices are missing from the data — survivorship bias inflates the result. Treat it as a consistency "
        "test of the rule, not as a promise of returns.",
    "**Tylko S&P 500.** yfinance nie ma historii wynikow kwartalnych dla ok. 80% spolek z GPW (pomiar na probce 30 spolek, 2026-08-07), "
    "wiec regula nie mialaby z czego wybierac. To samo ograniczenie dotyczy strony Insider Screener.":
        "**S&P 500 only.** yfinance has no quarterly earnings history for about 80% of Warsaw companies (measured on a sample of 30, 2026-08-07), "
        "so the rule would have nothing to choose from. The same limitation applies to the Insider screener page.",
    "**Bez symulacji wstecz.** Ta strategia opiera sie na danych fundamentalnych, ktore yfinance udostepnia wylacznie w wersji „na dzis\" — "
    "nie da sie odtworzyc, jak wygladaly rok temu. Symulacja liczylaby historyczne miesiace dzisiejszymi danymi (lookahead bias), wiec "
    "swiadomie jej nie ma. Track record narasta od pierwszego snapshotu.":
        "**No backward simulation.** This strategy relies on fundamental data that yfinance only provides “as of today” — "
        "there is no way to reconstruct what it looked like a year ago. A simulation would compute past months with today's data (lookahead bias), "
        "so it is deliberately left out. The track record builds up from the first snapshot.",
    "Dla bankow z GPW komponent zadluzenia jest pomijany — struktura bilansu banku nie jest porownywalna ze spolka przemyslowa. "
    "Wagi pozostalych trzech skladnikow sa wtedy renormalizowane do 100%.":
        "For Warsaw banks the debt component is skipped — a bank's balance sheet is not comparable with an industrial company's. "
        "The weights of the remaining three components are then rescaled to 100%.",
    "**Zrodlo: konsensus analitykow z Yahoo Finance** (srednia rekomendacja, liczba analitykow, srednia cena docelowa) — stan z dnia wyboru. "
    "Na GPW konsensus ma ok. 1/3 spolek (pomiar 2026-11-16), stad nizszy prog i mozliwy krotszy sklad. Pierwszy sklad wybrany 16.11.2026, "
    "czyli w polowie miesiaca. To nie jest rekomendacja inwestycyjna.":
        "**Source: analyst consensus from Yahoo Finance** (mean recommendation, number of analysts, mean target price) — as of the selection date. "
        "On the Warsaw exchange only about 1/3 of companies have a consensus (measured 2026-11-16), hence the lower threshold and possibly fewer picks. "
        "The first picks were made on 16.11.2026, mid-month. This is not an investment recommendation.",
    "Zwrot od rebalansu": "Return since rebalance",
    "Sektory w piatce (limit 2)": "Sectors in the five (limit 2)",
}

STRATEGIE: dict[str, str] = {
    # Backtest
    "# Backtest strategii": "# Strategy backtest",
    "Stopa wolna": "Risk-free rate",
    "### Krzywa kapitalu": "### Equity curve",
    "Brak zmian sygnalu w tym okresie.": "No signal changes in this period.",
    "⚙️ Ustawienia zaawansowane": "⚙️ Advanced settings",
    "Filtr trendu (AND cena > SMA200)": "Trend filter (AND price > SMA200)",
    "Volatility targeting": "Volatility targeting",
    "Filtr regime (VIX)": "Regime filter (VIX)",
    "Filtr regime (VIX) ": "Regime filter (VIX) ",
    "Filtr regime (VIX)  ": "Regime filter (VIX)  ",
    "Prog VIX": "VIX threshold",
    "Prog VIX ": "VIX threshold ",
    "Prog VIX  ": "VIX threshold  ",
    "Za malo danych do przeprowadzenia backtestu. Sprobuj dluzszy okres.": "Not enough data to run the backtest. Try a longer period.",
    "ℹ️ O strategii GEM Klasyczny": "ℹ️ About classic GEM",
    "Dodatkowo wymaga aby wybrane aktywo akcyjne bylo powyzej SMA200. Redukuje whipsawy, obniza CAGR o 1-2pp, poprawia win rate i drawdown.":
        "Also requires the chosen equity asset to be above its SMA200. Reduces whipsaws, lowers CAGR by 1-2 pp, improves win rate and drawdown.",
    "Skaluj pozycje do zadanej rocznej zmiennosci: pos = cel / realizowana_vol. Redukuje wahania portfela — Sharpe rosnie, DD maleje "
    "kosztem CAGR w trendach. Dziala tylko gdy sygnal to akcje (nie AGG).":
        "Scale the position to a target annual volatility: pos = target / realised_vol. Reduces portfolio swings — Sharpe rises, DD falls "
        "at the cost of CAGR in trends. Only applies when the signal is stocks (not AGG).",
    "Maks. dzwignia": "Max. leverage",
    "Maks. dzwignia ": "Max. leverage ",
    "Dodaj: (1) koszt roundtrip przy kazdej zmianie sygnalu (spread+prowizja), (2) podatek Belki 19% od zyskownych segmentow "
    "(zrealizowany zysk = rozliczany przy sprzedazy).":
        "Add: (1) a round-trip cost at every signal change (spread + commission), (2) the 19% Polish capital gains tax (Belka) on profitable "
        "segments (realised gain = taxed on sale).",
    "Gdy VIX > progu, ignoruje momentum i siedzi w AGG. Historycznie VIX>30 markuje panike (2008, 2020, 2022). Obniza CAGR w normalnym "
    "rynku, ale drastycznie ratuje drawdown w stressie.":
        "When VIX is above the threshold, ignores momentum and stays in AGG. Historically VIX>30 marks panic (2008, 2020, 2022). Lowers CAGR in "
        "normal markets but sharply limits drawdown under stress.",
    "30 = klasyczny prog paniki. 25 = ostrozniej (wiecej dni w AGG).": "30 = the classic panic threshold. 25 = more cautious (more days in AGG).",
    "ℹ️ O strategii QQQ + SMA 200": "ℹ️ About QQQ + SMA 200",
    "Cel zmiennosci (%)": "Volatility target (%)",
    "Cel zmiennosci (%) ": "Volatility target (%) ",
    "1.0 = bez dzwigni (tylko skalowanie w dol). 1.5-2.0 wymaga konta margin i dolicza koszt finansowania ~rf.":
        "1.0 = no leverage (scaling down only). 1.5-2.0 requires a margin account and adds a financing cost of ~rf.",
    "Podatek od zyskow kapitalowych (PL). Placony per segment: przy kazdej zmianie sygnalu realizowany jest zysk/strata na dotychczasowej pozycji.":
        "Polish capital gains tax. Paid per segment: every signal change realises the gain/loss on the previous position.",
    "Sprawdzanie miesięczne": "Monthly check",
    "Skaluj pozycje QQQ do zadanej rocznej zmiennosci: pos = cel / realizowana_vol. Redukuje wahania portfela — Sharpe rosnie, DD maleje "
    "kosztem CAGR w trendach. Gdy sygnal = AGG, brak skalowania.":
        "Scale the QQQ position to a target annual volatility: pos = target / realised_vol. Reduces portfolio swings — Sharpe rises, DD falls "
        "at the cost of CAGR in trends. When the signal is AGG, no scaling.",
    "Dodaj: (1) koszt roundtrip przy zmianie sygnalu, (2) podatek Belki 19% od zyskownych segmentow. SMA z dziennym checkiem ma duzo "
    "whipsawow — realistyczne koszty znaczaco obnizaja CAGR.":
        "Add: (1) a round-trip cost at each signal change, (2) the 19% Polish capital gains tax (Belka) on profitable segments. A daily SMA check "
        "produces many whipsaws — realistic costs reduce CAGR significantly.",
    "Belka 19% ": "Belka tax 19% ",
    "Belka 19%  ": "Belka tax 19%  ",
    "VIX > progu → AGG niezaleznie od sygnalu SMA. Przydatne gdy rynek oscyluje wokol SMA200 w okresie wysokiej niepewnosci.":
        "VIX above the threshold → AGG regardless of the SMA signal. Useful when the market hovers around its SMA200 in times of high uncertainty.",
    "Koszty transakcji + Belka": "Transaction costs + Belka tax",
    "ℹ️ O strategii TQQQ + Momentum": "ℹ️ About TQQQ + Momentum",
    "### Porownanie strategii — Krzywa kapitalu": "### Strategy comparison — equity curve",
    "Typowe cele: 10-12% bardzo ostroznie, 15% standard, 20% agresywnie.": "Typical targets: 10-12% very cautious, 15% standard, 20% aggressive.",
    "IBKR/Bossa ~0.02-0.1%, XTB ETF ~0.05-0.2%. Polska stawka plus spread.": "IBKR/Bossa ~0.02-0.1%, XTB ETFs ~0.05-0.2%. Polish broker rates plus spread.",
    "Bufor / histereza (%)": "Buffer / hysteresis (%)",
    "Sprawdzaj sygnal co ~21 dni zamiast codziennie. Dalej redukuje whipsawy, ale opozni reakcje na gwaltowne zmiany trendu.":
        "Check the signal every ~21 days instead of daily. Further reduces whipsaws but delays the reaction to sudden trend changes.",
    "1.0 = bez dzwigni. >1 wymaga konta margin, w tle doliczany koszt ~rf.": "1.0 = no leverage. >1 requires a margin account; a ~rf cost is added.",
    "Koszt roundtrip (%) ": "Round-trip cost (%) ",
    "Koszt roundtrip (%)  ": "Round-trip cost (%)  ",
    "Podatek od zyskow kapitalowych (PL) rozliczany per segment.": "Polish capital gains tax settled per segment.",
    "Dzwignia": "Leverage",
    "Realistyczne koszty TQQQ": "Realistic TQQQ costs",
    "Dodaj koszt roundtrip przy zmianie sygnalu (TQQQ<->AGG) i podatek Belki 19% od zyskownych segmentow.":
        "Add a round-trip cost at each signal change (TQQQ<->AGG) and the 19% Polish capital gains tax (Belka) on profitable segments.",
    "KRYTYCZNY dla TQQQ — leveraged ETF giną w regime'ach paniki (2008, 2020, 2022 spadki 50-80%). VIX>30 → AGG ratuje konto od katastrofy.":
        "CRITICAL for TQQQ — leveraged ETFs get wiped out in panic regimes (2008, 2020, 2022: drops of 50-80%). VIX>30 → AGG saves the account from disaster.",
    "Rolling in-sample / out-of-sample — dla kazdego okna IS siatka parametrow (trend_filter × vol_target) oceniana po wybranej metryce, "
    "najlepszy zestaw uruchamiany na OOS. Wyniki OOS lancuchowane w jedna krzywa. Wymaga >=6 lat danych (domyslnie 5 IS + 1 OOS). "
    "Uwaga: okres powyzej musi byc wystarczajaco dlugi.":
        "Rolling in-sample / out-of-sample — for each IS window a parameter grid (trend_filter × vol_target) is scored on the chosen metric "
        "and the best set is run out of sample. OOS results are chained into a single curve. Requires >=6 years of data (default 5 IS + 1 OOS). "
        "Note: the period selected above must be long enough.",
    "### Krzywa kapitalu (OOS chain)": "### Equity curve (OOS chain)",
    "### Podsumowanie OOS vs QQQ": "### OOS summary vs QQQ",
    "### Stabilnosc parametrow": "### Parameter stability",
    "Switch do AGG tylko gdy cena < SMA × (1 − bufor); do QQQ tylko gdy cena > SMA × (1 + bufor). Faber rekomenduje 2%. "
    "Redukuje whipsawy w rynku bocznym (2015, 2022).":
        "Switch to AGG only when price < SMA × (1 − buffer); to QQQ only when price > SMA × (1 + buffer). Faber recommends 2%. "
        "Reduces whipsaws in sideways markets (2015, 2022).",
    "Spread + prowizja przy kazdej zmianie QQQ<->AGG.": "Spread + commission at every QQQ<->AGG switch.",
    "Mnoznik dzwigni. 3.0 = TQQQ, 2.0 = QLD/SSO, 1.5 = CSNDX 1.5x, 1.0 = brak dzwigni.":
        "Leverage multiplier. 3.0 = TQQQ, 2.0 = QLD/SSO, 1.5 = CSNDX 1.5x, 1.0 = no leverage.",
    "Dodaj do dziennego zwrotu: koszt finansowania pozyczonej dzwigni ((L-1)·(rf+spread)/252) oraz expense ratio. Naiwny syntetyk "
    "3×QQQ przeszacowuje TQQQ o 2-4pp rocznie — realistyczny model dopasowuje sie do prawdziwego TQQQ do ~0.5pp.":
        "Add to the daily return: the financing cost of borrowed leverage ((L-1)·(rf+spread)/252) and the expense ratio. A naive synthetic "
        "3×QQQ overstates TQQQ by 2-4 pp a year — the realistic model tracks the real TQQQ to within ~0.5 pp.",
    "Expense ratio (%)": "Expense ratio (%)",
    "Spread ponad rf (%)": "Spread over rf (%)",
    "Podatek od zyskow kapitalowych rozliczany per segment.": "Capital gains tax settled per segment.",
    "⚙️ Ustawienia walk-forward": "⚙️ Walk-forward settings",
    "Gdy jedna kombinacja dominuje (>=60% foldow) — parametry sa stabilne historycznie. Rozproszenie (3+ roznych po ~20%) sugeruje ze "
    "kazdy rezim rynkowy preferuje inne ustawienia — rozwazyc regime-aware alokacje.":
        "When one combination dominates (>=60% of folds), the parameters are historically stable. A spread (3+ different ones at ~20%) suggests "
        "each market regime prefers different settings — consider a regime-aware allocation.",
    "TQQQ: 0.88%, QLD: 0.95%, SSO: 0.89%, SPXL: 0.91%. 0 = naiwny.": "TQQQ: 0.88%, QLD: 0.95%, SSO: 0.89%, SPXL: 0.91%. 0 = naive.",
    "Spread jaki ETF placi za dzwignie ponad stope wolna. 0.3-0.7% realistycznie.":
        "The spread the ETF pays for leverage above the risk-free rate. 0.3-0.7% is realistic.",
    "Spread + prowizja. TQQQ ma duzy spread srodsesyjny (0.05-0.15%).": "Spread + commission. TQQQ has a wide intraday spread (0.05-0.15%).",
    "Dlugosc IS (lat)": "IS length (years)",
    "Dlugosc OOS (lat)": "OOS length (years)",
    "Krok (lat)": "Step (years)",
    "Metryka wyboru": "Selection metric",
    "In-sample window — na nim dobierane sa parametry.": "In-sample window — parameters are fitted here.",
    "Out-of-sample window — na nim liczone realne zwroty.": "Out-of-sample window — real returns are calculated here.",
    "O ile rolujemy okna. 1.0 = nowy fold co rok.": "How far the windows roll. 1.0 = a new fold every year.",
    "Po czym wybieramy 'najlepsze parametry' na IS.": "How the 'best parameters' are chosen in sample.",
    # GEM Extended
    "# GEM Extended — backtest rozszerzonego universe": "# GEM Extended — backtest on an extended universe",
    "Klasyczny GEM (Antonacci 2014) trzyma 100% w jednym aktywie z 5 ETF (QQQ/VEA/EEM/ACWI/AGG). GEM Extended pozwala dodac wiecej "
    "kandydatow (GLD, TLT, VNQ, IWM, BTC) i trzymac top N equal-weight — wiekszy CAGR za cene wiekszego drawdownu.":
        "Classic GEM (Antonacci 2014) holds 100% in one of 5 ETFs (QQQ/VEA/EEM/ACWI/AGG). GEM Extended lets you add more "
        "candidates (GLD, TLT, VNQ, IWM, BTC) and hold the top N equal-weight — a higher CAGR at the cost of a deeper drawdown.",
    "## 📈 Equity curve": "## 📈 Equity curve",
    "## 🔄 Historia rotacji (kazda zmiana holdings)": "## 🔄 Rotation history (every change in holdings)",
    "Preset universe": "Universe preset",
    "Okres backtestu": "Backtest period",
    "Kapital poczatkowy ($)": "Starting capital ($)",
    "Risk assets (aktywa ryzykowne — kandydaci do top N)": "Risk assets (candidates for the top N)",
    "Safe asset (fallback)": "Safe asset (fallback)",
    "Top N (ile aktywow equal-weight)": "Top N (number of equal-weight assets)",
    "Lookback momentum (dni)": "Momentum lookback (days)",
    "Skip (dni od konca)": "Skip (days from the end)",
    "Benchmark B&H": "B&H benchmark",
    "Koszty transakcji i podatek Belki": "Transaction costs and Belka tax",
    "❌ Wybierz przynajmniej 1 risk asset.": "❌ Choose at least 1 risk asset.",
    "❌ Nie udalo sie pobrac danych. Sprobuj odswiezyc strone.": "❌ Could not download data. Try refreshing the page.",
    "Licze backtest...": "Running the backtest...",
    "⚠️ Wazne ostrzezenia (kliknij)": "⚠️ Important warnings (click)",
    "Wybierz gotowy zestaw albo Custom dla wlasnej konfiguracji.": "Pick a ready-made set or Custom for your own configuration.",
    "Z tych aktywow strategia wybiera top N po momentum 12M.": "The strategy picks the top N from these assets by 12M momentum.",
    "Gdy zaden risk asset nie ma momentum > rf, portfel idzie tu.": "When no risk asset has momentum above rf, the portfolio goes here.",
    "Koszt transakcji (%)": "Transaction cost (%)",
    "Podatek Belki (%)": "Belka tax (%)",
    "Roundtrip cost, skalowany frakcja zmienionych aktywow (turnover).": "Round-trip cost, scaled by the fraction of assets changed (turnover).",
    "Pobierany od zysku segmentu przy zmianie holdings (uproszczenie — brak rolowania strat).":
        "Charged on a segment's gain when holdings change (simplified — losses are not carried forward).",
    # GEM Gold Momentum
    "# GEM Gold Momentum": "# GEM Gold Momentum",
    "Momentum ze zlotem wg inwestomat.eu, w wersji GEM: momentum 12M wybiera miedzy Nasdaq-100 (QQQ), zlotem i bonami 3M, a w galezi "
    "akcji najsilniejszy z QQQ, rynkow rozwinietych ex-US (EFA) i rynkow wschodzacych (EEM). Autor artykulu uzywa S&P 500 zamiast QQQ.":
        "Gold momentum after inwestomat.eu, GEM style: 12M momentum chooses between the Nasdaq-100 (QQQ), gold and 3M T-bills, and in the "
        "equity branch the strongest of QQQ, developed ex-US markets (EFA) and emerging markets (EEM). The article's author uses the S&P 500 instead of QQQ.",
    "ETF na zloto": "Gold ETF",
    "Okno momentum (miesiace)": "Momentum window (months)",
    "Stopa wolna (dla GEM)": "Risk-free rate (for GEM)",
    "Pobieram pelna historie (od 2004)...": "Downloading the full history (from 2004)...",
    "Poczatek backtestu": "Backtest start",
    "GLD (od XI 2004) i IAU (od I 2005) sledza cene zlota; IAU ma nizsze TER.":
        "GLD (since Nov 2004) and IAU (since Jan 2005) track the gold price; IAU has a lower TER.",
    "Autor testowal 3–15 mies.; w dlugim okresie najlepiej wypadlo 12M.": "The author tested 3–15 months; over the long run 12M did best.",
    "Koszt przy zmianie aktywa (%)": "Cost per asset switch (%)",
    "Wspolna historia ETF-ow zaczyna sie pod koniec 2004 (GLD) — wczesniejsze lata nie sa dostepne w yfinance.":
        "The ETFs' common history starts at the end of 2004 (GLD) — earlier years are not available in yfinance.",
    "❌ Za malo danych dla wybranego okna i poczatku backtestu.": "❌ Not enough data for the selected window and start date.",
    "🎯 Sygnal teraz": "🎯 Signal now",
    "📈 Backtest": "📈 Backtest",
    "🆚 vs GEM klasyczny": "🆚 vs classic GEM",
    "📅 Zwroty roczne": "📅 Annual returns",
    "🔧 Wrazliwosc na okno": "🔧 Window sensitivity",
    "🔄 Historia sygnalow": "🔄 Signal history",
    "Krzywe na wykresie": "Curves on the chart",
    "Skala logarytmiczna": "Log scale",
    "### Statystyki (dane miesieczne)": "### Statistics (monthly data)",
    "Strategie": "Strategies",
    "Drawdown z danych miesiecznych — dzienne dolki bywaja glebsze.": "Drawdown from monthly data — daily lows can be deeper.",
    "Pierwszy i ostatni rok sa niepelne. GEM klasyczny startuje pozniej (ACWI).": "The first and last years are partial. Classic GEM starts later (ACWI).",
    "Autor (1972–2025): akcje ~50% (S&P 500 27,6%, EM 15,4%, World ex-US 6,9%), zloto 38,4%, obligacje 11,6%.":
        "Author (1972–2025): stocks ~50% (S&P 500 27.6%, EM 15.4%, World ex-US 6.9%), gold 38.4%, bonds 11.6%.",
    "ℹ️ Zasady strategii i ograniczenia backtestu": "ℹ️ Strategy rules and backtest limitations",
    "Autor: 0,1% → ok. −0,6 p.p. rocznie, 0,3% → ok. −1,8 p.p.": "Author: 0.1% → about −0.6 pp a year, 0.3% → about −1.8 pp.",
    "Od zysku segmentu przy kazdej zmianie aktywa (bez rozliczania strat). Dotyczy Gold Momentum i GEM; B&H bez podatku.":
        "On a segment's gain at every asset switch (losses not offset). Applies to Gold Momentum and GEM; B&H untaxed.",
    "Za krotka historia do policzenia biezacego sygnalu.": "History too short to calculate the current signal.",
    "Sygnal biezacy liczony od dzisiejszego zamkniecia; strategia handluje raz w miesiacu, na podstawie zamkniecia ostatniej sesji miesiaca.":
        "The current signal is calculated from today's close; the strategy trades once a month, based on the close of the month's last session.",
    "📌 Skad w artykule ~20% rocznie, a tu mniej?": "📌 Why does the article show ~20% a year, but less here?",
    "Brak danych do GEM klasycznego (QQQ/VEA/EEM/ACWI/AGG) dla tego okresu.": "No data for classic GEM (QQQ/VEA/EEM/ACWI/AGG) in this period.",
    "Za krotki okres do porownania okien 3–15 mies.": "Period too short to compare 3–15 month windows.",
    "Wszystkie okna liczone na tym samym okresie (start wyznacza okno 15M), bez kosztow i podatku.":
        "All windows are calculated over the same period (the 15M window sets the start), without costs or tax.",
    "Autor: w latach 1972–2025 najlepsze bylo 12M (potem 15M i 11M), ale w 2006–2025 wygrywalo 4M. Wybor okna po fakcie to data snooping. "
    "Rozrzut wynikow miedzy sasiednimi oknami pokazuje, jak mocno wynik zalezy od tego parametru.":
        "Author: in 1972–2025 12M was best (then 15M and 11M), but in 2006–2025 4M won. Picking the window after the fact is data snooping. "
        "The spread of results between neighbouring windows shows how much the result depends on this parameter.",
    "Zwroty kalendarzowe": "Calendar-year returns",
    "Okno (miesiace)": "Window (months)",
    "CAGR": "CAGR",
    "Max DD": "Max DD",
    "CAGR i Max DD wg okna momentum": "CAGR and max DD by momentum window",
    "Czas w aktywach": "Time in each asset",
    "Czas w galeziach": "Time in each branch",
}

PREMIUM3: dict[str, str] = {**SPOLKI, **STRATEGIE}
