"""Katalog EN — strony Premium, czesc 2: ETF, krypto, portfel, rynek, spolki (bez Karty).

Uwaga: niektore etykiety roznia sie tylko spacjami na koncu ("Prog VIX ", "Prog VIX  ") —
to celowe (unikalne ID widgetow w Streamlicie). Tlumaczenia zachowuja te same spacje.
"""

CHARTS: dict[str, str] = {
    "Wartosc portfela (USD)": "Portfolio value (USD)",
    "Lata": "Years",
    "Wartosc portfela": "Portfolio value",
    "RS (baza=100)": "RS (base=100)",
    "Zwrot (%)": "Return (%)",
    "Cena": "Price",
    "Histogram": "Histogram",
    "MACD": "MACD",
    "Signal": "Signal",
    "RSI": "RSI",
    "Mediana (P50)": "Median (P50)",
    "BB Upper": "BB upper",
    "BB Lower": "BB lower",
    "RS": "RS",
}

ETF_PAGES: dict[str, str] = {
    # Drawdowny
    "# Analiza Drawdownow": "# Drawdown analysis",
    "Top spadki od szczytu, czas trwania, czas odbudowy": "Largest declines from peak, duration, recovery time",
    "Pobieram dane...": "Downloading data...",
    "📉 Underwater": "📉 Underwater",
    "📋 Tabela": "📋 Table",
    "⚖️ Porownanie": "⚖️ Comparison",
    "📊 Histogram": "📊 Histogram",
    "Porownanie drawdownow": "Drawdown comparison",
    "Wybierz 2-4 tickery": "Choose 2-4 tickers",
    "Aktualnie na szczycie (brak drawdownu)": "Currently at a peak (no drawdown)",
    "Brak drawdownow w wybranym okresie.": "No drawdowns in the selected period.",
    "Wybierz co najmniej 2 tickery.": "Choose at least 2 tickers.",
    "Za malo drawdownow do wyswietlenia histogramu.": "Not enough drawdowns to show a histogram.",
    "Drawdown": "Drawdown",
    "Brak danych dla wybranych tickerow.": "No data for the selected tickers.",
    "Glebia (%)": "Depth (%)",
    "Liczba": "Count",
    "Dni": "Days",
    "Glebia drawdownu": "Drawdown depth",
    "Rozklad glebokosci drawdownow (%)": "Distribution of drawdown depth (%)",
    "Czas trwania": "Duration",
    "Rozklad dlugosci spadkow (dni)": "Distribution of decline length (days)",
    # Porownaj
    "# Porównaj": "# Compare",
    "Wykresy — cena, momentum i drawdown wybranych ETF-ow": "Charts — price, momentum and drawdown of selected ETFs",
    "Wybierz ETF-y (maks. 5)": "Choose ETFs (max. 5)",
    "Porownanie head-to-head 2-4 ETF-ow": "Head-to-head comparison of 2-4 ETFs",
    "### Stopy zwrotu": "### Returns",
    "### Cena znormalizowana (baza = 100)": "### Normalised price (base = 100)",
    "### Statystyki": "### Statistics",
    "### Macierz korelacji (252 dni)": "### Correlation matrix (252 days)",
    "### Relative Strength": "### Relative strength",
    "Benchmark RS": "RS benchmark",
    "Porownaj dwa aktywa obok siebie — cena, drawdown, statystyki i Relative Strength":
        "Compare two assets side by side — price, drawdown, statistics and relative strength",
    "### Porownanie wspolne": "### Combined comparison",
    "📈 Wykresy": "📈 Charts",
    "⚖️ Head-to-head": "⚖️ Head-to-head",
    "🔀 Side-by-side": "🔀 Side-by-side",
    "Wybierz co najmniej 1 ETF.": "Choose at least 1 ETF.",
    "Wybierz 2-4 instrumenty do porownania": "Choose 2-4 instruments to compare",
    "Wybierz co najmniej 2 ETF-y.": "Choose at least 2 ETFs.",
    "Brak danych.": "No data.",
    "Jak czytac korelacje?": "How to read correlation",
    "\n        - **1.0** = doskonala korelacja dodatnia (ruchy w tym samym kierunku)\n"
    "        - **0.0** = brak korelacji (niezalezne ruchy)\n"
    "        - **-1.0** = doskonala korelacja ujemna (ruchy w przeciwnym kierunku)\n\n"
    "        Dobrze zdywersyfikowany portfel powinien zawierac aktywa o **niskiej lub ujemnej korelacji**.\n        ":
        "\n- **1.0** = perfect positive correlation (moves in the same direction)\n"
        "- **0.0** = no correlation (independent moves)\n"
        "- **-1.0** = perfect negative correlation (moves in opposite directions)\n\n"
        "A well-diversified portfolio should contain assets with **low or negative correlation**.\n",
    "Wybierz co najmniej 2 instrumenty.": "Choose at least 2 instruments.",
    "Aktywo A": "Asset A",
    "Aktywo B": "Asset B",
    "Wybierz dwa rozne aktywa.": "Choose two different assets.",
    "Nie udalo sie pobrac danych dla wybranych aktywow.": "Could not download data for the selected assets.",
    "#### Korelacja": "#### Correlation",
    "#### Relative Strength": "#### Relative strength",
    "Nie udalo sie pobrac danych.": "Could not download data.",
    "📈 Cena": "📈 Price",
    "🚀 Momentum": "🚀 Momentum",
    "📉 Drawdown": "📉 Drawdown",
    "Normalizuj (baza = 100)": "Normalise (base = 100)",
    "Okno momentum (dni)": "Momentum window (days)",
    "Za malo danych dla widoku Strategia 12-1. Wyswietlam dostepne dane.":
        "Not enough data for the 12-1 strategy view. Showing the available data.",
    "Macierz korelacji": "Correlation matrix",
    "Za malo wspolnych danych do RS.": "Not enough overlapping data for RS.",
    # Stopy zwrotu
    "# Stopy zwrotu dlugoterminowe": "# Long-term returns",
    "Porownanie ETF-ow na horyzoncie do 30 lat: stopy skumulowane i srednioroczne (CAGR), lata kalendarzowe, "
    "okna kroczace oraz wzrost kapitalu z miarami ryzyka. Dane miesieczne.":
        "ETFs compared over up to 30 years: cumulative and annualised returns (CAGR), calendar years, "
        "rolling windows and capital growth with risk measures. Monthly data.",
    "Zrodla: Yahoo Finance (ceny skorygowane o dywidendy), FRED/OECD (kurs USD/PLN — srednia miesieczna; "
    "w trybie PLN dane od 1996 (po denominacji i stabilizacji zlotego)). Fundusze proxy maja wyzsze oplaty "
    "niz ETF-y, wiec odcinek z proxy jest lekko zanizony. Wyniki historyczne nie gwarantuja przyszlych.":
        "Sources: Yahoo Finance (dividend-adjusted prices), FRED/OECD (USD/PLN — monthly average; in PLN mode "
        "data starts in 1996, after the zloty's redenomination and stabilisation). Proxy funds charge higher fees "
        "than ETFs, so the proxy segment is slightly understated. Past results do not guarantee future ones.",
    "ETF-y (2-8)": "ETFs (2-8)",
    "Wydluz historie o fundusze proxy": "Extend history with proxy funds",
    "Wybierz co najmniej 2 ETF-y z dostepnymi danymi.": "Choose at least 2 ETFs with available data.",
    "Przed startem ETF-u stopy zwrotu starego funduszu indeksowego na ten sam rynek (np. SPY ← VFINX od 1980).":
        "Before the ETF launched, use the returns of an older index fund on the same market (e.g. SPY ← VFINX from 1980).",
    "Nie udalo sie pobrac kursu USD/PLN — pokazuje wyniki w USD.": "Could not fetch the USD/PLN rate — showing results in USD.",
    "📋 Tabela okresow": "📋 Period table",
    "🗓️ Stopy roczne": "🗓️ Annual returns",
    "🔁 Stopy kroczace": "🔁 Rolling returns",
    "📈 Wzrost i ryzyko": "📈 Growth and risk",
    "#### Srednioroczna stopa zwrotu (CAGR)": "#### Annualised return (CAGR)",
    "#### Skumulowana stopa zwrotu": "#### Cumulative return",
    "„—” = historia krotsza niz okres. CAGR „Od startu” liczony dla historii od 1 roku.":
        "“—” = history shorter than the period. “Since inception” CAGR is shown for histories of 1 year or more.",
    "Okno (lata)": "Window (years)",
    "Wspolny okres": "Common period",
    "Kurs USD/PLN z FRED niedostepny — tryb PLN obejmuje dane od grudnia 2003.":
        "USD/PLN from FRED unavailable — PLN mode covers data from December 2003.",
    "Okres do wykresu CAGR": "Period for the CAGR chart",
    "Zaden z wybranych ETF-ow nie ma jeszcze pelnego roku kalendarzowego.":
        "None of the selected ETFs has a full calendar year yet.",
    "Pierwszy niepelny rok historii pominiety. Podsumowanie bez roku YTD.":
        "The first partial year is skipped. The summary excludes the YTD year.",
    "Przycina wszystkie ETF-y do najpozniejszego startu, zeby porownanie bylo uczciwe.":
        "Trims all ETFs to the latest start date so the comparison is fair.",
    "Wybrane ETF-y nie maja wspolnego okresu notowan. Wylacz „Wspolny okres”, aby zobaczyc pelna historie kazdego z nich.":
        "The selected ETFs have no overlapping trading period. Turn off “Common period” to see each one's full history.",
}

KRYPTO: dict[str, str] = {
    "# Kryptowaluty — Top 200": "# Cryptocurrencies — Top 200",
    "📊 Ranking momentum": "📊 Momentum ranking",
    "₿ Alt/BTC — sila vs Bitcoin": "₿ Alt/BTC — strength vs Bitcoin",
    "📉 Wykresy": "📉 Charts",
    "🧪 Backtest momentum": "🧪 Momentum backtest",
    "🔔 Sygnaly TA": "🔔 TA signals",
    "💪 Relative Strength": "💪 Relative strength",
    "### Alt/BTC — sila altcoinow wzgledem Bitcoina": "### Alt/BTC — altcoin strength relative to Bitcoin",
    "Ktore altcoiny najlepiej performuja w relacji do BTC? Ratio alt/BTC rosnie = altcoin bije Bitcoina.":
        "Which altcoins perform best relative to BTC? A rising alt/BTC ratio = the altcoin is beating Bitcoin.",
    "### Wykresy — kryptowaluty": "### Charts — cryptocurrencies",
    "Wybierz kryptowaluty (maks. 5)": "Choose cryptocurrencies (max. 5)",
    "### Porownanie kryptowalut": "### Cryptocurrency comparison",
    "### Sygnaly analizy technicznej": "### Technical analysis signals",
    "Trend-following: 5 wskaznikow z filtrem trendu EMA 200. Sygnaly generowane tylko w kierunku trendu.":
        "Trend following: 5 indicators with an EMA 200 trend filter. Signals are generated only in the trend's direction.",
    "### Relative Strength vs BTC": "### Relative strength vs BTC",
    "RS > 100 = kryptowaluta outperformuje Bitcoin": "RS > 100 = the coin is outperforming Bitcoin",
    "Wybierz krypto (maks. 5)": "Choose coins (max. 5)",
    "### Ranking momentum — kryptowaluty": "### Momentum ranking — cryptocurrencies",
    "Filtr": "Filter",
    "Okres wykresu": "Chart period",
    "Brak altcoinow do analizy (wybrana kategoria zawiera tylko BTC).": "No altcoins to analyse (the selected category contains only BTC).",
    "Wybierz co najmniej 1 kryptowalute.": "Choose at least 1 cryptocurrency.",
    "Wybierz 2-4 kryptowaluty do porownania": "Choose 2-4 cryptocurrencies to compare",
    "Wybierz co najmniej 2 kryptowaluty.": "Choose at least 2 cryptocurrencies.",
    "### Backtest rotacji momentum — kryptowaluty": "### Momentum rotation backtest — cryptocurrencies",
    "Co miesiac kupuj top N krypto wg wyniku kompozytowego. Porownanie z BTC buy & hold i equal-weight B&H.":
        "Each month buy the top N coins by composite score. Compared with BTC buy & hold and equal-weight B&H.",
    "Kryptowaluta": "Cryptocurrency",
    "Parametry wskaznikow": "Indicator parameters",
    "#### Wykres cenowy + wskazniki": "#### Price chart + indicators",
    "Brak tickerow dla wybranej kategorii.": "No tickers for the selected category.",
    "Pobieram dane kryptowalut i BTC...": "Downloading crypto and BTC data...",
    "Nie udalo sie pobrac danych BTC.": "Could not download BTC data.",
    "Brak danych altcoinow.": "No altcoin data.",
    "Za malo danych do obliczenia ratio alt/BTC.": "Not enough data to calculate the alt/BTC ratio.",
    "Brak wystarczajacych danych do obliczenia ratio. Sprobuj inna kategorie.":
        "Not enough data to calculate the ratio. Try another category.",
    "#### Wynik kompozytowy ratio alt/BTC — top 20": "#### Alt/BTC ratio composite score — top 20",
    "#### Ratio alt/BTC — top 5 (baza = 100)": "#### Alt/BTC ratio — top 5 (base = 100)",
    "#### Stopy zwrotu": "#### Returns",
    "#### Cena znormalizowana (baza = 100)": "#### Normalised price (base = 100)",
    "#### Statystyki": "#### Statistics",
    "#### Macierz korelacji (252 dni)": "#### Correlation matrix (252 days)",
    "Top N kryptowalut": "Top N cryptocurrencies",
    "Kapital (USD)": "Capital (USD)",
    "⚙️ Metoda scoringu + koszty": "⚙️ Scoring method + costs",
    "Rank-based score (percentyle + anty-1M)": "Rank-based score (percentiles + anti-1M)",
    "Koszty i podatki (realistycznie)": "Costs and taxes (realistic)",
    "Filtr breadth (regime)": "Breadth filter (regime)",
    "EMA krotka": "Short EMA",
    "EMA dluga": "Long EMA",
    "RSI okres": "RSI period",
    "MACD fast": "MACD fast",
    "MACD slow": "MACD slow",
    "MACD signal": "MACD signal",
    "BB okres": "BB period",
    "BB odch. std.": "BB std. dev.",
    "Za malo danych do analizy technicznej (min. 50 sesji).": "Not enough data for technical analysis (min. 50 sessions).",
    "#### Historia sygnalow": "#### Signal history",
    "Brak sygnalow kupna/sprzedazy w wybranym okresie — rynek neutralny wg wybranych parametrow.":
        "No buy/sell signals in the selected period — the market is neutral under these parameters.",
    "Jak interpretowac sygnaly?": "How to interpret the signals",
    "Pobieranie danych dla ~200 kryptowalut moze potrwac dluzej. Mozesz wybrac konkretna kategorie.":
        "Downloading data for ~200 cryptocurrencies may take a while. You can pick a specific category.",
    "Pobieram dane kryptowalut...": "Downloading crypto data...",
    "📥 Eksportuj CSV": "📥 Export CSV",
    "Zamiast wazonej sumy surowych zwrotow (_flexible_score), rankuje tickery per okres (0-1). 1M flipowany jako "
    "anti-signal. Szczegolnie odporny dla krypto — duze wahania 1M nie dominuja juz scoringu.":
        "Instead of a weighted sum of raw returns (_flexible_score), ranks tickers per period (0-1). 1M is flipped "
        "as an anti-signal. Especially robust for crypto — large 1M swings no longer dominate the score.",
    "Koszt transakcji skalowany turnoverem + Belka 19% od zyskownych segmentow.":
        "Transaction cost scaled by turnover + 19% Polish capital gains tax (Belka) on profitable segments.",
    "Belka 19%": "Belka tax 19%",
    "Gdy mniej niz X% coinow jest powyzej SMA100 → strategia przechodzi do cash. Krypto ma czeste bessy >70%, "
    "filtr regime ratuje kapital.":
        "When fewer than X% of coins are above their SMA100 → the strategy moves to cash. Crypto often has "
        "bear markets of >70%; the regime filter protects capital.",
    "Prog breadth (% > SMA100)": "Breadth threshold (% > SMA100)",
    "Pobieram dane i licze backtest...": "Downloading data and running the backtest...",
    "Za malo danych do backtestu. Sprobuj dluzszy okres.": "Not enough data for the backtest. Try a longer period.",
    "Za malo danych do backtestu (potrzeba min. 63 dni historii).": "Not enough data for the backtest (at least 63 days of history needed).",
    "Za malo danych do backtestu.": "Not enough data for the backtest.",
    "#### Krzywa kapitalu": "#### Equity curve",
    "Zmiana ratio (%)": "Ratio change (%)",
    "Koszt roundtrip (%)": "Round-trip cost (%)",
    "PIT-38 rozliczany rocznie. Model liczy od frakcji rotowanej przy rebalansie.":
        "Polish PIT-38 tax is settled annually. The model applies it to the fraction rotated at each rebalance.",
    "Top 15 — wynik momentum kryptowalut": "Top 15 — crypto momentum score",
    "Ratio alt/BTC — wynik kompozytowy (%)": "Alt/BTC ratio — composite score (%)",
    "Krypto: Binance/Zonda 0.1-0.25% per stronie, spread altcoinow 0.1-0.5%. Default 0.3%.":
        "Crypto: Binance/Zonda 0.1-0.25% per side, altcoin spread 0.1-0.5%. Default 0.3%.",
}

PORTFEL: dict[str, str] = {
    "# Monte Carlo": "# Monte Carlo",
    "Kapital poczatkowy (USD)": "Starting capital (USD)",
    "Zrodlo danych": "Data source",
    "Horyzont (lata)": "Horizon (years)",
    "Liczba symulacji": "Number of simulations",
    "Wybierz ETF": "Choose an ETF",
    "Za malo danych historycznych do symulacji (min. 1 rok).": "Not enough historical data for the simulation (min. 1 year).",
    "📈 Fan Chart": "📈 Fan chart",
    "📊 Rozklad koncowy": "📊 Final distribution",
    "🎯 Prawdopodobienstwa": "🎯 Probabilities",
    "Ciemniejszy pas = P25-P75 (50% sciezek). Jasniejszy = P5-P95 (90% sciezek). Linia = mediana.":
        "Darker band = P25-P75 (50% of paths). Lighter = P5-P95 (90% of paths). Line = median.",
    "Rozklad wartosci koncowej": "Distribution of the final value",
    "Prawdopodobienstwa": "Probabilities",
    "Obliczam krzywa kapitalu GEM...": "Calculating the GEM equity curve...",
    "📖 Jak interpretowac wyniki Monte Carlo?": "📖 How to interpret the Monte Carlo results",
    "Brak danych do backtestu GEM.": "No data for the GEM backtest.",
    "# Portfolio Builder": "# Portfolio Builder",
    "Zbuduj portfel z dowolnych aktywow, ustaw wagi i przeanalizuj wyniki":
        "Build a portfolio from any assets, set the weights and analyse the results",
    "### 1. Wybor aktywow": "### 1. Choose assets",
    "Wybierz aktywa (max 20)": "Choose assets (max 20)",
    "### 2. Wagi portfela": "### 2. Portfolio weights",
    "### 3. Analiza portfela": "### 3. Portfolio analysis",
    "#### Macierz korelacji": "#### Correlation matrix",
    "#### Backtest portfela": "#### Portfolio backtest",
    "Wybierz co najmniej 2 aktywa, aby rozpoczac analize.": "Choose at least 2 assets to start the analysis.",
    "Equal-weight": "Equal-weight",
    "Risk Parity": "Risk parity",
    "Reset": "Reset",
    "Co najmniej 2 aktywa musza miec niezerowa wage.": "At least 2 assets must have a non-zero weight.",
    "Pobieram dane i analizuje portfel...": "Downloading data and analysing the portfolio...",
    "#### Zwroty holdingsow": "#### Holding returns",
    "Za malo danych do przeprowadzenia backtestu (wymagane min. 10 dni wspolnych danych).":
        "Not enough data to run the backtest (at least 10 days of overlapping data required).",
    "Obliczam wagi risk parity...": "Calculating risk-parity weights...",
    "Nie udalo sie pobrac danych — uzywam equal-weight.": "Could not download data — using equal weights.",
}

RYNEK: dict[str, str] = {
    # Intermarket
    "# Analiza Intermarket": "# Intermarket analysis",
    "Relacje miedzy klasami aktywow: akcje, obligacje, zloto, dolar, ropa":
        "Relationships between asset classes: stocks, bonds, gold, the dollar, oil",
    "Okres danych": "Data period",
    "Pobieram dane intermarket...": "Downloading intermarket data...",
    "Za malo danych intermarket.": "Not enough intermarket data.",
    "📈 Overlay": "📈 Overlay",
    "📊 Ratio": "📊 Ratio",
    "🔄 Korelacja rolling": "🔄 Rolling correlation",
    "🗺️ Macierz korelacji": "🗺️ Correlation matrix",
    "🚦 Regime": "🚦 Regime",
    "📊 Korelacja strategii": "📊 Strategy correlation",
    "Wszystkie aktywa znormalizowane (baza=100)": "All assets normalised (base=100)",
    "Ratio miedzy aktywami": "Ratio between assets",
    "Wybierz pare": "Choose a pair",
    "Rolling korelacja (63 dni)": "Rolling correlation (63 days)",
    "Okno korelacji (dni)": "Correlation window (days)",
    "Okres korelacji (dni)": "Correlation period (days)",
    "Regime: Risk-On vs Risk-Off": "Regime: Risk-On vs Risk-Off",
    "#### Sygnaly per klasa aktywow": "#### Signals by asset class",
    "Rolling korelacja miedzy strategiami": "Rolling correlation between strategies",
    "Porownanie equity curves: GEM Klasyczny, QQQ+SMA200, TQQQ+Momentum":
        "Equity curves compared: classic GEM, QQQ+SMA200, TQQQ+Momentum",
    "Aktywo 1": "Asset 1",
    "Aktywo 2": "Asset 2",
    "Za malo danych dla wybranego okresu korelacji.": "Not enough data for the selected correlation period.",
    "📖 Jak czytac analilze intermarket?": "📖 How to read the intermarket analysis",
    "\n**Kluczowe relacje:**\n\n| Para | Typowa korelacja | Znaczenie |\n|---|---|---|\n"
    "| SPY vs 10Y yield | Pozytywna | Rosnace rentownosci = risk-on (obie rosna) |\n"
    "| SPY vs Zloto | Slaba/zmienna | Zloto to hedge, ale nie zawsze odwrotny |\n"
    "| Zloto vs DXY | Negatywna | Slaby dolar → droge zloto |\n"
    "| SPY vs CL=F | Pozytywna | Ropa rosnie z gospodarka (ale szoki sa negatywne) |\n"
    "| 10Y yield vs DXY | Pozytywna | Rosnace stopy przyciagaja kapital → silny dolar |\n\n"
    "**Dla strategii GEM:**\n- Risk-On: GEM prawdopodobnie wskazuje QQQ/VEA/EEM/ACWI\n"
    "- Risk-Off: GEM prawdopodobnie przechodzi na obligacje (AGG)\n"
    "- Zwracaj uwage na divergencje — np. SPY rosnie ale zloto tez (niepewnosc)\n\n"
    "**Ratio SPY / 10Y yield:**\n- Rosnace = akcje wygrywaja vs obligacje (risk-on)\n"
    "- Spadajace = rentownosci rosna szybciej niz akcje (zaostrzanie polityki monetarnej)\n        ":
        "\n**Key relationships:**\n\n| Pair | Typical correlation | Meaning |\n|---|---|---|\n"
        "| SPY vs 10Y yield | Positive | Rising yields = risk-on (both rise) |\n"
        "| SPY vs gold | Weak/variable | Gold is a hedge, but not always inverse |\n"
        "| Gold vs DXY | Negative | Weak dollar → expensive gold |\n"
        "| SPY vs CL=F | Positive | Oil rises with the economy (but shocks are negative) |\n"
        "| 10Y yield vs DXY | Positive | Rising rates attract capital → strong dollar |\n\n"
        "**For the GEM strategy:**\n- Risk-On: GEM likely points to QQQ/VEA/EEM/ACWI\n"
        "- Risk-Off: GEM likely moves to bonds (AGG)\n"
        "- Watch for divergences — e.g. SPY rising but gold rising too (uncertainty)\n\n"
        "**SPY / 10Y yield ratio:**\n- Rising = stocks beating bonds (risk-on)\n"
        "- Falling = yields rising faster than stocks (monetary tightening)\n",
    "Pobieram dane do backtestow strategii...": "Downloading data for the strategy backtests...",
    "#### Aktualne korelacje": "#### Current correlations",
    "Za malo danych do obliczenia korelacji strategii (wymagane 252+ sesji + okno korelacji).":
        "Not enough data to calculate strategy correlations (252+ sessions plus the correlation window required).",
    "Intermarket — baza = 100": "Intermarket — base = 100",
    "Za malo danych dla wybranego okna korelacji.": "Not enough data for the selected correlation window.",
    "Korelacja": "Correlation",
    "📖 Jak interpretowac korelacje strategii?": "📖 How to interpret strategy correlations",
    "\n**GEM vs QQQ+SMA200:**\n- Obie strategie uzywaja QQQ i AGG, wiec korelacja jest zazwyczaj umiarkowana-wysoka\n"
    "- Roznica: GEM rebalansuje miesiecznie (momentum 12M no-skip), SMA200 dziennie (trend)\n"
    "- Niska korelacja = strategie uzupelniaja sie (dywersyfikacja)\n\n**GEM vs TQQQ+Momentum:**\n"
    "- TQQQ uzywa 3x lewara — wieksze wahania\n- Wysoka korelacja w trendzie wzrostowym (obie w akcjach)\n"
    "- Niska korelacja w trendzie bocznym (rozne progi wejscia/wyjscia)\n\n**SMA200 vs TQQQ+Momentum:**\n"
    "- SMA200 reaguje dziennie, TQQQ+Mom miesiecznie\n- Rozne czestotliwosci rebalansu = rozne momenty przelaczen\n\n"
    "**Praktyczne wnioski:**\n- Korelacja < 0.5 → warto rozwazyc alokacje do obu strategii (dywersyfikacja)\n"
    "- Korelacja > 0.8 → strategie zachowuja sie podobnie — mala wartosc laczenia\n            ":
        "\n**GEM vs QQQ+SMA200:**\n- Both strategies use QQQ and AGG, so correlation is usually moderate to high\n"
        "- Difference: GEM rebalances monthly (12M no-skip momentum), SMA200 daily (trend)\n"
        "- Low correlation = the strategies complement each other (diversification)\n\n**GEM vs TQQQ+Momentum:**\n"
        "- TQQQ uses 3x leverage — bigger swings\n- High correlation in uptrends (both in stocks)\n"
        "- Low correlation in sideways markets (different entry/exit thresholds)\n\n**SMA200 vs TQQQ+Momentum:**\n"
        "- SMA200 reacts daily, TQQQ+Mom monthly\n- Different rebalancing frequencies = switches at different times\n\n"
        "**Practical takeaways:**\n- Correlation < 0.5 → worth considering an allocation to both strategies (diversification)\n"
        "- Correlation > 0.8 → the strategies behave alike — little value in combining them\n",
    "Ratio": "Ratio",
    # Makro
    "# Makro Dashboard": "# Macro dashboard",
    "Kluczowe wskazniki makroekonomiczne — kontekst dla strategii GEM": "Key macroeconomic indicators — context for the GEM strategy",
    "Pobieram dane makro...": "Downloading macro data...",
    "📖 Interpretacja makro dla GEM": "📖 Macro interpretation for GEM",
    "\n**VIX (Fear Index)**\n- < 15: Rynek spokojny, niski strach — sprzyjajace warunki dla akcji\n- 15-25: Normalna zmiennosc\n"
    "- 25-35: Wysoki strach — mozliwa korekta, rozwazyc obligacje\n- &gt; 35: Panika rynkowa — historycznie czesto dno rynku\n\n"
    "**Yield Curve (10Y - 13W)**\n- Dodatni spread: Normalna krzywa — zdrowa gospodarka\n- Bliski zeru: Splaszczenie — spowolnienie gospodarcze\n"
    "- Ujemny (inwersja): Historycznie poprzedza recesje o 6-18 miesiecy\n- Dla GEM: inwersja → sygnaly ostrzegawcze, momentum moze sie pogorszyc\n\n"
    "**US Dollar (DXY)**\n- Silny dolar (>105): Negatywny dla rynkow wschodzacych i surowcow\n- Slaby dolar (<95): Pozytywny dla VEA, VWO, zlota, surowcow\n"
    "- Dla GEM: silny dolar sprzyja SPY vs VEA\n\n**S&P 500 vs 200MA**\n- Powyzej 200MA: Trend wzrostowy — utrzymuj pozycje w akcjach\n"
    "- Ponizej 200MA: Trend spadkowy — rozwazyc przejscie na obligacje (AGG)\n- Kluczowy wskaznik dla momentum absolutnego w GEM\n\n"
    "**Zloto (USD/oz)**\n- Rosnie przy: niskich realnych stopach, slabym dolarze, niepewnosci\n- Safe haven w okresach paniki rynkowej\n"
    "- Dla GEM: silne zloto moze sygnalizowac slabe momentum akcji\n\n**Ropa WTI**\n- Wysoka cena (>$90): Ryzyko inflacji → wyzsze stopy → presja na akcje\n"
    "- Niska cena (<$60): Spowolnienie gospodarcze lub nadpodaz\n- Dla GEM: szoki naftowe historycznie poprzedzaly zmiany sygnalow\n    ":
        "\n**VIX (fear index)**\n- < 15: calm market, low fear — favourable conditions for stocks\n- 15-25: normal volatility\n"
        "- 25-35: high fear — a correction is possible, consider bonds\n- &gt; 35: market panic — historically often near a market bottom\n\n"
        "**Yield curve (10Y - 13W)**\n- Positive spread: normal curve — a healthy economy\n- Close to zero: flattening — economic slowdown\n"
        "- Negative (inversion): historically precedes recessions by 6-18 months\n- For GEM: inversion → warning signs, momentum may weaken\n\n"
        "**US Dollar (DXY)**\n- Strong dollar (>105): negative for emerging markets and commodities\n- Weak dollar (<95): positive for VEA, VWO, gold, commodities\n"
        "- For GEM: a strong dollar favours SPY over VEA\n\n**S&P 500 vs 200-day MA**\n- Above the 200MA: uptrend — stay in stocks\n"
        "- Below the 200MA: downtrend — consider moving to bonds (AGG)\n- A key indicator for absolute momentum in GEM\n\n"
        "**Gold (USD/oz)**\n- Rises with: low real rates, a weak dollar, uncertainty\n- A safe haven during market panics\n"
        "- For GEM: strong gold can signal weak equity momentum\n\n**WTI crude oil**\n- High price (>$90): inflation risk → higher rates → pressure on stocks\n"
        "- Low price (<$60): economic slowdown or oversupply\n- For GEM: oil shocks have historically preceded signal changes\n",
    "VIX — Fear Index": "VIX — fear index",
    "Brak danych VIX": "No VIX data",
    "Yield Curve (10Y - 13W)": "Yield curve (10Y - 13W)",
    "Brak danych yield curve": "No yield curve data",
    "US Dollar Index (DXY)": "US Dollar Index (DXY)",
    "Brak danych DXY": "No DXY data",
    "Brak danych S&P 500": "No S&P 500 data",
    "Zloto (USD/oz)": "Gold (USD/oz)",
    "Brak danych zlota (GC=F)": "No gold data (GC=F)",
    "Ropa WTI (CL=F)": "WTI crude oil (CL=F)",
    "Brak danych ropy WTI": "No WTI crude data",
    "200MA": "200MA",
    # Sektory
    "# Rotacja Sektorowa": "# Sector rotation",
    "Momentum 11 sektorow GICS — ktory sektor prowadzi?": "Momentum of the 11 GICS sectors — which sector is leading?",
    "Pobieram dane sektorowe...": "Downloading sector data...",
    "Za malo danych sektorowych.": "Not enough sector data.",
    "🗺️ Heatmapa": "🗺️ Heatmap",
    "📊 Ranking": "📊 Ranking",
    "📖 Cykl koniunkturalny": "📖 Business cycle",
    "📈 Porownanie": "📈 Comparison",
    "Heatmapa momentum sektorow": "Sector momentum heatmap",
    "Ranking biezacy sektorow": "Current sector ranking",
    "Cykl koniunkturalny a rotacja sektorowa": "The business cycle and sector rotation",
    "\n**Wczesna ekspansja** (po recesji):\n- Liderzy: **Technologia** (XLK), **Konsumpcja cykliczna** (XLY), **Finanse** (XLF)\n"
    "- Niska inflacja, obnizki stop, odbudowa zaufania\n\n**Srodkowa ekspansja:**\n- Liderzy: **Przemysl** (XLI), **Materialy** (XLB), **Energia** (XLE)\n"
    "- Rosnaacy popyt, inwestycje w infrastrukture, rosnace ceny surowcow\n\n**Pozna ekspansja** (przed szczytem):\n"
    "- Liderzy: **Energia** (XLE), **Materialy** (XLB)\n- Wysokia inflacja, rosnace stopy procentowe\n- Defensywne sektory zaczynaja sie umacniac\n\n"
    "**Recesja / spowolnienie:**\n- Liderzy: **Uzytecznosc publ.** (XLU), **Ochrona zdrowia** (XLV), **Konsumpcja podstawowa** (XLP)\n"
    "- Inwestorzy szukaja bezpieczenstwa i dywidend\n- Nieruchomosci (XLRE) moga ucierpiec przez wyzsze stopy\n\n"
    "**Jak to laczyc z GEM?**\n- Gdy GEM wskazuje AGG (obligacje), rynek czesto jest w poznej ekspansji lub recesji\n"
    "- Sektory defensywne (XLU, XLV, XLP) potwierdzaja trend spadkowy\n- Powrot QQQ/VEA w GEM czesto pokrywa sie z rotacja do sektorow cyklicznych\n    ":
        "\n**Early expansion** (after a recession):\n- Leaders: **Technology** (XLK), **Consumer discretionary** (XLY), **Financials** (XLF)\n"
        "- Low inflation, rate cuts, returning confidence\n\n**Mid expansion:**\n- Leaders: **Industrials** (XLI), **Materials** (XLB), **Energy** (XLE)\n"
        "- Rising demand, infrastructure investment, rising commodity prices\n\n**Late expansion** (before the peak):\n"
        "- Leaders: **Energy** (XLE), **Materials** (XLB)\n- High inflation, rising interest rates\n- Defensive sectors start to strengthen\n\n"
        "**Recession / slowdown:**\n- Leaders: **Utilities** (XLU), **Health care** (XLV), **Consumer staples** (XLP)\n"
        "- Investors look for safety and dividends\n- Real estate (XLRE) can suffer from higher rates\n\n"
        "**How does this tie in with GEM?**\n- When GEM points to AGG (bonds), the market is often in late expansion or recession\n"
        "- Defensive sectors (XLU, XLV, XLP) confirm the downtrend\n- GEM's return to QQQ/VEA often coincides with rotation into cyclical sectors\n",
    "Porownanie sektorow": "Sector comparison",
    "Wybierz 2-4 sektory": "Choose 2-4 sectors",
    "Za malo danych do heatmapy.": "Not enough data for the heatmap.",
    "Wybierz co najmniej 2 sektory.": "Choose at least 2 sectors.",
    "Momentum 3M sektorow w czasie (%)": "Sector 3M momentum over time (%)",
    "Ranking sektorow — wynik momentum": "Sector ranking — momentum score",
    "Porownanie sektorow (baza=100)": "Sector comparison (base=100)",
    # Sezonowosc
    "# Sezonowosc": "# Seasonality",
    "Heatmapa miesięcznych zwrotow, wzorce sezonowe, analiza Sell in May":
        "Monthly returns heatmap, seasonal patterns, Sell in May analysis",
    "Wybierz ticker": "Choose a ticker",
    "Za malo danych do analizy sezonowosci.": "Not enough data for seasonality analysis.",
    "📊 Heatmapa": "📊 Heatmap",
    "📈 Sredni miesiac": "📈 Average month",
    "🏖️ Sell in May": "🏖️ Sell in May",
    "### Sell in May and Go Away": "### Sell in May and Go Away",
    "Porownanie zwrotow Maj-Pazdziernik vs Listopad-Kwiecien": "May-October vs November-April returns",
    "Sredni zwrot Maj-Paz": "Average return May-Oct",
    "Sredni zwrot Lis-Kwi": "Average return Nov-Apr",
    "Lis-Kwi wygrywa": "Nov-Apr wins",
    "Za malo danych do analizy Sell in May.": "Not enough data for the Sell in May analysis.",
    "Srednia": "Mean",
    "Mediana": "Median",
    "Maj-Paz": "May-Oct",
    "Lis-Kwi": "Nov-Apr",
    # Waluta
    "# Waluta PLN/USD": "# USD/PLN currency",
    "Wplyw kursu USD/PLN na zwroty ETF-ow — realne zwroty polskiego inwestora":
        "How USD/PLN affects ETF returns — real returns for a Polish investor",
    "ETF-y do porownania": "ETFs to compare",
    "Wybierz przynajmniej jeden ETF.": "Choose at least one ETF.",
    "Brak danych kursu USD/PLN.": "No USD/PLN data.",
    "📈 Kurs USD/PLN": "📈 USD/PLN rate",
    "📊 Zwroty USD vs PLN": "📊 Returns USD vs PLN",
    "🔀 Overlay": "🔀 Overlay",
    "📖 Hedging": "📖 Hedging",
    "Kurs USD/PLN": "USD/PLN rate",
    "Zwroty USD vs PLN": "Returns in USD vs PLN",
    "ret_PLN = (1 + ret_USD) × (1 + ret_USDPLN) − 1": "ret_PLN = (1 + ret_USD) × (1 + ret_USDPLN) − 1",
    "Overlay: ETF vs USD/PLN": "Overlay: ETF vs USD/PLN",
    "Koszt hedgingu walutowego": "Cost of currency hedging",
    "\n**Czym jest hedging walutowy?**\n\nPolski inwestor kupujacy ETF-y denominowane w USD jest narazony na ryzyko walutowe.\n"
    "Gdy zloty sie umacnia (USD/PLN spada), zwrot w PLN jest nizszy niz w USD.\n\n**Forward spread (koszt hedgingu)**\n\n"
    "Zabezpieczenie walutowe przez kontrakty forward kosztuje okolo **roznica stop procentowych** miedzy USA a Polska.\n"
    "Przy wyzszych stopach w Polsce, hedging jest \"darmowy\" lub nawet korzystny.\n\n**Hedged vs Unhedged — kiedy co sie oplaca?**\n\n"
    "| Scenariusz | Unhedged | Hedged |\n|---|---|---|\n| USD/PLN rosnie (zloty slabnie) | Lepszy | Gorszy |\n"
    "| USD/PLN spada (zloty sie umacnia) | Gorszy | Lepszy |\n| USD/PLN stabilny | Podobny | Koszt hedgingu |\n\n"
    "**Dla strategii GEM:**\n- GEM nie uwzglednia ryzyka walutowego w sygnalach\n- Dlugoterminowo, roznice walutowe czesto sie uśredniaja\n"
    "- Hedging ma sens gdy PLN systematycznie sie umacnia\n- Alternatywa: ETF-y hedged (np. z suffiksem PLN-H)\n\n"
    "**Praktyczna wskazowka:**\nJesli inwestujesz >5 lat, ryzyko walutowe ma mniejsze znaczenie.\n"
    "Przy krotszym horyzoncie, wahania USD/PLN moga dominowac nad zwrotem z ETF-a.\n    ":
        "\n**What is currency hedging?**\n\nA Polish investor buying USD-denominated ETFs is exposed to currency risk.\n"
        "When the zloty strengthens (USD/PLN falls), the return in PLN is lower than in USD.\n\n**Forward spread (hedging cost)**\n\n"
        "Hedging with forward contracts costs roughly the **interest-rate differential** between the US and Poland.\n"
        "With higher rates in Poland, hedging is \"free\" or even beneficial.\n\n**Hedged vs unhedged — when does each pay off?**\n\n"
        "| Scenario | Unhedged | Hedged |\n|---|---|---|\n| USD/PLN rises (zloty weakens) | Better | Worse |\n"
        "| USD/PLN falls (zloty strengthens) | Worse | Better |\n| USD/PLN stable | Similar | Hedging cost |\n\n"
        "**For the GEM strategy:**\n- GEM does not account for currency risk in its signals\n- Over the long term, currency moves often average out\n"
        "- Hedging makes sense when the PLN strengthens systematically\n- Alternative: hedged ETFs (e.g. with a PLN-H suffix)\n\n"
        "**Practical tip:**\nIf you invest for more than 5 years, currency risk matters less.\n"
        "Over shorter horizons, USD/PLN swings can dominate the ETF's return.\n",
    "PLN za 1 USD": "PLN per 1 USD",
    "Za malo wspolnych danych.": "Not enough overlapping data.",
    "USD/PLN": "USD/PLN",
    "Za malo wspolnych dat.": "Not enough overlapping dates.",
    "USD/PLN (baza=100)": "USD/PLN (base=100)",
}

PREMIUM2: dict[str, str] = {**CHARTS, **ETF_PAGES, **KRYPTO, **PORTFEL, **RYNEK}
