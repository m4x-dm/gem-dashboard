"""Katalog EN — strony Premium, czesc 4: komunikaty z wartosciami (dawne f-stringi)."""

FSTRINGS: dict[str, str] = {
    "Wartosc ({currency})": "Value ({currency})",
    # Drawdowny
    "Brak danych dla {ticker}": "No data for {ticker}",
    "Drawdown — {ticker}": "Drawdown — {ticker}",
    "Top 10 drawdownow — {ticker}": "Top 10 drawdowns — {ticker}",
    "Rozklad drawdownow — {ticker}": "Drawdown distribution — {ticker}",
    "Aktualny drawdown: **{v0}%**": "Current drawdown: **{v0}%**",
    "{ticker} — spadki od szczytu": "{ticker} — declines from peak",
    "Max DD {t}": "Max DD {t}",
    # Porownaj
    "Porownanie cenowe — {period_label}": "Price comparison — {period_label}",
    "Cena — {ticker_a}": "Price — {ticker_a}",
    "Drawdown — {ticker_a}": "Drawdown — {ticker_a}",
    "Cena — {ticker_b}": "Price — {ticker_b}",
    "Drawdown — {ticker_b}": "Drawdown — {ticker_b}",
    "Momentum {window}D (rolling)": "Momentum {window}D (rolling)",
    # Stopy zwrotu
    "Okresy koncza sie na {v0} (ostatni pelny miesiac). Waluta: {currency}.":
        "Periods end in {v0} (the last full month). Currency: {currency}.",
    "Brak wystarczajacych danych dla {t} — pomijam.": "Not enough data for {t} — skipping.",
    "{t}: nie udalo sie doloczyc proxy {v1} — pokazuje prawdziwa historie ETF-u.":
        "{t}: could not attach the {v1} proxy — showing the ETF's real history.",
    "{t}: brak danych we wspolnym okresie — pominiety.": "{t}: no data in the common period — skipped.",
    "Kazdy punkt to CAGR z {v0} konczacych sie w danym miesiacu. Okna nakladaja sie, wiec nie sa niezalezne. "
    "Liczba okien zalezy od dlugosci historii — przy porownaniu % okien ze strata zwroc uwage na kolumne 'Liczba okien'.":
        "Each point is the CAGR over {v0} ending in that month. The windows overlap, so they are not independent. "
        "The number of windows depends on the length of history — when comparing the % of losing windows, check the 'Number of windows' column.",
    "Zaden z wybranych ETF-ow nie ma historii dluzszej niz {v0}.": "None of the selected ETFs has a history longer than {v0}.",
    "{t}: za malo danych po przeliczeniu na PLN — pominiety.": "{t}: not enough data after converting to PLN — skipped.",
    "Bez danych dla okresu {bar_period}: {v1}.": "No data for the {bar_period} period: {v1}.",
    "CAGR — {bar_period}": "CAGR — {bar_period}",
    # Krypto
    "Pobieranie danych dla {v0} kryptowalut moze potrwac dluzej. Wybierz mniejszy filtr, aby przyspieszyc.":
        "Downloading data for {v0} cryptocurrencies may take a while. Choose a narrower filter to speed it up.",
    "#### Top 20 altcoinow vs BTC (ratio momentum) — {v0} altcoinow z danymi":
        "#### Top 20 altcoins vs BTC (ratio momentum) — {v0} altcoins with data",
    "Za malo kryptowalut ({v0}) dla top {top_n}.": "Not enough cryptocurrencies ({v0}) for top {top_n}.",
    "{v0} — analiza techniczna ({ta_period_label})": "{v0} — technical analysis ({ta_period_label})",
    "\n**5 wskaznikow trend-following (kazdy -1 / 0 / +1):**\n\n"
    "1. **Trend (EMA 200):** Cena > EMA(200) = bullish, ponizej = bearish. Glowny filtr kierunku — nie kupuj w downtrend.\n"
    "2. **EMA crossover:** EMA({ema_short}) > EMA({ema_long}) = bullish momentum, ponizej = bearish.\n"
    "3. **MACD + histogram:** Crossover MACD/Signal potwierdzony kierunkiem histogramu. Wymaga zgodnosci obu — eliminuje falszywe crossovery.\n"
    "4. **RSI momentum:** RSI > 50 i rosnacy = byki kontroluja, RSI < 50 i malejacy = niedzwiedzie. Nie uzywamy ekstremalnych poziomow 30/70 (lapanie spadajacych nozy).\n"
    "5. **Bollinger %B:** Pozycja ceny w wstedze. %B > 0.5 (powyzej srodka) = trend up, < 0.5 = trend down.\n\n"
    "**Agregat:** Suma {n_indicators} sygnalow. >= {threshold} = **KUP**, <= -{threshold} = **SPRZEDAJ**, reszta = **NEUTRALNY**\n\n"
    "**Roznice vs prosta analiza:**\n- Filtr trendu EMA(200) zapobiega kupowaniu w downtrend\n"
    "- MACD wymaga potwierdzenia histogramem (mniej falszywych sygnalow)\n"
    "- RSI oparty o momentum, nie o extreme levels (unikamy lapania spadajacych nozy)\n"
    "- Bollinger mierzy pozycje w wstedze, nie dotkniecia band\n\n"
    "*Sygnaly TA maja charakter informacyjny i nie stanowia rekomendacji inwestycyjnej.*\n":
        "\n**5 trend-following indicators (each -1 / 0 / +1):**\n\n"
        "1. **Trend (EMA 200):** price > EMA(200) = bullish, below = bearish. The main direction filter — don't buy in a downtrend.\n"
        "2. **EMA crossover:** EMA({ema_short}) > EMA({ema_long}) = bullish momentum, below = bearish.\n"
        "3. **MACD + histogram:** a MACD/signal crossover confirmed by the histogram's direction. Both must agree — filters out false crossovers.\n"
        "4. **RSI momentum:** RSI > 50 and rising = bulls in control, RSI < 50 and falling = bears. We don't use the extreme 30/70 levels (catching falling knives).\n"
        "5. **Bollinger %B:** the price's position within the band. %B > 0.5 (above the middle) = uptrend, < 0.5 = downtrend.\n\n"
        "**Aggregate:** the sum of {n_indicators} signals. >= {threshold} = **BUY**, <= -{threshold} = **SELL**, otherwise **NEUTRAL**\n\n"
        "**How this differs from a simple analysis:**\n- The EMA(200) trend filter prevents buying in a downtrend\n"
        "- MACD needs histogram confirmation (fewer false signals)\n"
        "- RSI is momentum-based, not extreme-level based (we avoid catching falling knives)\n"
        "- Bollinger measures the position within the band, not band touches\n\n"
        "*TA signals are for information only and are not an investment recommendation.*\n",
    "**{v0}** kryptowalut | Stopa wolna: **{v1}%**": "**{v0}** cryptocurrencies | Risk-free rate: **{v1}%**",
    "Porownanie cenowe — {cmp_period_label}": "Price comparison — {cmp_period_label}",
    "Tylko {v0} kryptowalut ma wystarczajaco dlugie dane. Potrzeba min. {top_n}.":
        "Only {v0} cryptocurrencies have a long enough history. At least {top_n} needed.",
    "RSI ({rsi_period})": "RSI ({rsi_period})",
    "Ratio alt/BTC (baza = 100) — {altbtc_display_label}": "Alt/BTC ratio (base = 100) — {altbtc_display_label}",
    # Monte Carlo / Portfolio
    "Uruchamiam Monte Carlo ({n_sims} symulacji, {years} lat)...": "Running Monte Carlo ({n_sims} simulations, {years} years)...",
    "Pobieram dane {ticker}...": "Downloading {ticker} data...",
    "\n**Metodologia:** Bootstrap dziennych zwrotow historycznych. Kazda symulacja losuje dzienne zwroty\n"
    "z rozkladem historycznym i buduje sciezke ceny do przodu na {years} lat.\n\n"
    "**Ograniczenia:**\n- Zaklada, ze przyszlosc bedzie \"podobna\" do historii\n- Nie uwzglednia zmian rezimu rynkowego\n"
    "- Nie uwzglednia kosztow transakcyjnych ani podatkow\n- Rozklad zwrotow moze byc niestacjonarny\n\n"
    "**Kapital poczatkowy:** {v1} USD\n**Medianowa wartosc koncowa:** {v2} USD\n**Medianowy calkowity zwrot:** {v3}%\n        ":
        "\n**Methodology:** a bootstrap of historical daily returns. Each simulation samples daily returns\n"
        "from the historical distribution and builds a price path forward over {years} years.\n\n"
        "**Limitations:**\n- Assumes the future will be \"similar\" to the past\n- Ignores changes in market regime\n"
        "- Ignores transaction costs and taxes\n- The distribution of returns may be non-stationary\n\n"
        "**Starting capital:** {v1} USD\n**Median final value:** {v2} USD\n**Median total return:** {v3}%\n",
    "Monte Carlo — {equity_label} ({n_sims} symulacji, {years} lat)": "Monte Carlo — {equity_label} ({n_sims} simulations, {years} years)",
    "Rozklad wartosci koncowej po {years} latach": "Distribution of the final value after {years} years",
    "Suma wag: **{v0}%** — powinna wynosic 100%. Roznica: {v1}%": "Sum of weights: **{v0}%** — should be 100%. Difference: {v1}%",
    "Suma wag: {v0}% ✓": "Sum of weights: {v0}% ✓",
    # Intermarket
    "Ratio {v0} — powyzej sredniej ({v1}). {name1} relatywnie drogi vs {name2}.":
        "Ratio {v0} — above its average ({v1}). {name1} is relatively expensive vs {name2}.",
    "Aktualna korelacja: **{v0}** — silna pozytywna": "Current correlation: **{v0}** — strongly positive",
    "Macierz korelacji ({corr_period} dni)": "Correlation matrix ({corr_period} days)",
    "Rolling {strat_window}D korelacja miedzy strategiami": "Rolling {strat_window}D correlation between strategies",
    "Ratio {name1} / {name2}": "Ratio {name1} / {name2}",
    "Ratio {v0} — ponizej sredniej ({v1}). {name1} relatywnie tani vs {name2}.":
        "Ratio {v0} — below its average ({v1}). {name1} is relatively cheap vs {name2}.",
    "Ratio {v0} — blisko sredniej ({v1}).": "Ratio {v0} — close to its average ({v1}).",
    "Korelacja {v0} vs {v1}": "Correlation {v0} vs {v1}",
    "Rolling {window}D korelacja: {v1} vs {v2}": "Rolling {window}D correlation: {v1} vs {v2}",
    "Aktualna korelacja: **{v0}** — silna negatywna": "Current correlation: **{v0}** — strongly negative",
    "Aktualna korelacja: **{v0}** — slaba/umiarkowana": "Current correlation: **{v0}** — weak/moderate",
    # Sezonowosc / Waluta
    "Sezonowosc {ticker} — miesięczne zwroty (%)": "{ticker} seasonality — monthly returns (%)",
    "{ticker} — sredni zwrot miesięczny (%)": "{ticker} — average monthly return (%)",
    "{ticker} — Sell in May vs Winter": "{ticker} — Sell in May vs winter",
    "Zmiana {p}": "Change {p}",
    "Zmiana kursu USD/PLN (12M): **{sign}{v1}%** — wplyw {impact} dla polskiego inwestora":
        "USD/PLN change (12M): **{sign}{v1}%** — {impact} impact for a Polish investor",
    "{overlay_ticker} (baza=100)": "{overlay_ticker} (base=100)",
    "{overlay_ticker} vs USD/PLN (baza=100)": "{overlay_ticker} vs USD/PLN (base=100)",
    # GPW / S&P 500 / spolki
    "**Wynikow:** {v0}/{v1}": "**Results:** {v0}/{v1}",
    "**{v0}** spolek | Stopa wolna: **{v1}%**": "**{v0}** stocks | Risk-free rate: **{v1}%**",
    "Za malo spolek ({v0}) dla top {top_n}.": "Not enough stocks ({v0}) for top {top_n}.",
    "WIG20 ma ostatnie notowanie z {v0} ({v1} dni temu). Sila wzgledna liczona wobec nieaktualnego benchmarku jest mylaca.":
        "The WIG20's last quote is from {v0} ({v1} days ago). Relative strength against a stale benchmark is misleading.",
    "⚠️ Pobrano dane dla {v0}/{v1} spolek. yfinance ma dziury w pokryciu GPW — to normalne dla mniejszych spolek.":
        "⚠️ Data downloaded for {v0}/{v1} stocks. yfinance has gaps in its Warsaw coverage — normal for smaller companies.",
    "### 📋 Tabela screener ({v0} spolek)": "### 📋 Screener table ({v0} companies)",
    "{n_this_week} w tym tyg.": "{n_this_week} this week",
    "Karta spolki niedostepna dla ETF/UNKNOWN ({ticker}).": "No company profile for ETF/UNKNOWN ({ticker}).",
    "⚠️ Pobrano dane dla {v0}/{v1} spolek. Yahoo Finance moze byc throttled. Sprobuj odswiezyc za chwile.":
        "⚠️ Data downloaded for {v0}/{v1} stocks. Yahoo Finance may be throttling. Try refreshing in a moment.",
    # Top Picks
    "Track record narasta od pierwszego snapshotu ({v0}). Krzywa kapitalu pojawi sie po pierwszym rebalansie — wroc za miesiac.":
        "The track record builds up from the first snapshot ({v0}). The equity curve will appear after the first rebalance — come back in a month.",
    "Wygenerowano: {v0} · regula v{v1} · koszty {v2} + Belka {v3}": "Generated: {v0} · rule v{v1} · costs {v2} + Belka tax {v3}",
    "Brak pliku `{v0}`. Uruchom `python scripts/update_top_picks.py --only {strategy}`, zeby wygenerowac pierwszy snapshot.":
        "File `{v0}` is missing. Run `python scripts/update_top_picks.py --only {strategy}` to generate the first snapshot.",
    "⚠️ Log zawiera snapshoty z roznych wersji reguly ({v0}). Wyniki sprzed zmiany nie sa porownywalne z obecnymi (aktualna: v{v1}).":
        "⚠️ The log contains snapshots from different rule versions ({v0}). Results from before the change are not comparable with current ones (current: v{v1}).",
    "📋 Szczegoly fundamentalne — {market_name}": "📋 Fundamental details — {market_name}",
    "Brak pliku `{v0}`. Uruchom `python scripts/update_top_picks.py`.": "File `{v0}` is missing. Run `python scripts/update_top_picks.py`.",
    "{v0}: brak spolek spelniajacych warunki w tym miesiacu.": "{v0}: no companies meet the criteria this month.",
    "Brak danych benchmarku {bench} - ponizsze porownanie jest niepelne.": "No data for the {bench} benchmark — the comparison below is incomplete.",
    "Benchmark {bench} ma ostatnie notowanie z {v1} ({v2} dni temu). Porownanie 'vs {bench}' jest nieaktualne - zrodlo danych wymaga sprawdzenia.":
        "The {bench} benchmark's last quote is from {v1} ({v2} days ago). The 'vs {bench}' comparison is stale — the data source needs checking.",
    "Top Picks {label} vs {bench}": "Top Picks {label} vs {bench}",
    "Symulacja reguly — {label}": "Rule simulation — {label}",
    # Backtest / GEM Extended / GEM Gold
    "Laczna liczba zmian sygnalu: **{v0}**": "Total signal changes: **{v0}**",
    "### Przebieg walk-forward — {v0} foldow": "### Walk-forward run — {v0} folds",
    "Za malo danych — walk-forward potrzebuje co najmniej ~{v0} lat historii + bufor momentum 252 dni. Zwieksz okres lub skroc IS/OOS.":
        "Not enough data — walk-forward needs at least ~{v0} years of history plus a 252-day momentum buffer. Extend the period or shorten IS/OOS.",
    "✅ Backtest gotowy — {v0} dni handlowych, od {v1} do {v2} (~{v3} lat)": "✅ Backtest done — {v0} trading days, from {v1} to {v2} (~{v3} years)",
    "## 📊 Statystyki ({v0} risk + {safe_asset}, Top-{top_n}, momentum {lookback}d skip={skip})":
        "## 📊 Statistics ({v0} risk + {safe_asset}, top-{top_n}, momentum {lookback}d skip={skip})",
    "❌ Musisz wybrac co najmniej {top_n} risk asset (obecnie wybrane: {v1}).": "❌ You must choose at least {top_n} risk assets (currently selected: {v1}).",
    "Pobieram dane ({v0} aktywow, {period})...": "Downloading data ({v0} assets, {period})...",
    "⚠️ Brakuje danych dla: {v0}. Pomijam te aktywa.": "⚠️ Data missing for: {v0}. Skipping these assets.",
    "❌ Za malo danych. Wybrany okres ({period}) ma mniej niz {v1} sesji dla wszystkich wybranych aktywow. "
    "Wybierz dluzszy okres lub usun aktywa z krotka historia (np. BTC-USD od 2014, ETH-USD od 2017).":
        "❌ Not enough data. The selected period ({period}) has fewer than {v1} sessions for all selected assets. "
        "Choose a longer period or remove assets with a short history (e.g. BTC-USD from 2014, ETH-USD from 2017).",
    "Lacznie {v0} zmian holdings w {v1}-letnim oknie (~{v2} zmian/rok).": "{v0} changes in holdings over a {v1}-year window (~{v2} changes/year).",
    "❌ Brak danych dla safe asset {safe_asset}. Wybierz inny.": "❌ No data for the safe asset {safe_asset}. Choose another one.",
    "❌ Po pominieciu brakujacych aktywow zostalo {v0} < top_n={top_n}.": "❌ After skipping missing assets, {v0} remain < top_n={top_n}.",
    "Backtest miesieczny: {v0} → {v1} (~{v2} lat). Ostatni miesiac moze byc niepelny. Sharpe liczony wzgledem sredniej stopy bonow 3M z okresu ({v3}/rok).":
        "Monthly backtest: {v0} → {v1} (~{v2} years). The last month may be partial. Sharpe is calculated against the period's average 3M T-bill rate ({v3}/year).",
    "❌ Brak danych dla: {v0}. Odswiez strone za chwile.": "❌ No data for: {v0}. Refresh the page in a moment.",
    "\n**Regula (raz w miesiacu, na zamkniecie ostatniej sesji):**\n"
    "1. Policz {lookback}-miesieczny zwrot akcji USA ({us}), zlota ({gold}) i bonow 3M. Najwyzszy z nich wybiera galaz.\n"
    "2. **Akcje** → kup najsilniejszy z: akcje USA ({us}), rynki rozwiniete ex-US (VEA), rynki wschodzace (EEM).\n"
    "3. **Obligacje** → bony 3M albo obligacje USA 7-10Y (IEF), w zaleznosci od tego, co ma wyzsze momentum.\n"
    "4. **Zloto** → {gold}.\n\n**Ograniczenia:**\n"
    "- Bony 3M odtworzone z rentownosci ^IRX (bez ETF-u), obligacje 7-10Y = IEF (od 2002).\n"
    "- Rynki rozwiniete ex-US = VEA (z Kanada), jak w GEM klasycznym; przed VII 2007 zwroty EFA. Autor uzywa MSCI World ex-US, wiec sklad nieco sie rozni.\n"
    "- Ceny w USD. Dla inwestora z PLN dochodzi kurs USD/PLN; {gold} nie jest dostepny w polskich IKE/IKZE\n"
    "  (odpowiedniki UCITS: zloto IGLN/SGLD/4GLD, S&P 500 CSPX/VUAA, EM EIMI, ex-US EXUS).\n"
    "- Brak slippage i spreadu; podatek uproszczony (bez rozliczania strat).\n"
    "- **QQQ to wybor po fakcie** — Nasdaq-100 byl najlepszym duzym indeksem ostatnich 20 lat, wiec wariant\n"
    "  z QQQ ma wbudowana przewage, ktorej nikt nie znal w 2005. Autor testowal S&P 500.\n":
        "\n**Rule (once a month, at the close of the last session):**\n"
        "1. Calculate the {lookback}-month return of US stocks ({us}), gold ({gold}) and 3M T-bills. The highest picks the branch.\n"
        "2. **Stocks** → buy the strongest of: US stocks ({us}), developed ex-US markets (VEA), emerging markets (EEM).\n"
        "3. **Bonds** → 3M T-bills or 7-10Y US Treasuries (IEF), whichever has higher momentum.\n"
        "4. **Gold** → {gold}.\n\n**Limitations:**\n"
        "- 3M T-bills are rebuilt from the ^IRX yield (no ETF); 7-10Y Treasuries = IEF (since 2002).\n"
        "- Developed ex-US = VEA (incl. Canada), as in classic GEM; before Jul 2007 EFA returns. The author uses MSCI World ex-US, so the composition differs slightly.\n"
        "- Prices in USD. A PLN-based investor also faces USD/PLN; {gold} is not available in Polish IKE/IKZE accounts\n"
        "  (UCITS equivalents: gold IGLN/SGLD/4GLD, S&P 500 CSPX/VUAA, EM EIMI, ex-US EXUS).\n"
        "- No slippage or spread; tax simplified (losses not offset).\n"
        "- **QQQ is a hindsight choice** — the Nasdaq-100 was the best large index of the last 20 years, so the QQQ\n"
        "  variant has a built-in advantage nobody knew about in 2005. The author tested the S&P 500.\n",
    "### Sygnal na zamkniecie {v0} (momentum {lookback}M)": "### Signal at the close on {v0} ({lookback}M momentum)",
    "\nAutor podaje **19,97% rocznie dla lat 1972–2025**, liczone na danych indeksowych (S&P 500 z dywidendami,\n"
    "MSCI World ex-US, MSCI EM od 1988, cena zlota). Ten wynik w duzej mierze robi **hossa zlota z lat 70.**\n"
    "(z 35 do ok. 850 USD/oz), kiedy strategia trzymala zloto przez wieksza czesc dekady.\n\n"
    "Ten backtest korzysta z **ETF-ow z yfinance**, wiec moze zaczac sie najwczesniej pod koniec 2005\n"
    "(GLD jest od XI 2004, do tego {lookback} mies. na pierwsze momentum).\n\n"
    "Regula zostala sprawdzona na wersji autora (z S&P 500): dla lat 2006–2025 autor podaje\n"
    "**7469 USD z 1000 USD, obsuniecie ok. −29% i 58 zmian**, a ta sama regula na ETF-ach daje 6259 USD,\n"
    "−29,1% i 52 zmiany (z EFA zamiast VEA: 6444 USD i −28,6%). Roznice wynikaja z uzycia VEA/EFA zamiast MSCI World ex-US, kosztow ETF-ow i innych\n"
    "dni konca miesiaca. Ta strona uzywa **Nasdaq-100 (QQQ)** zamiast S&P 500, tak jak klasyczny GEM.\n\n"
    "Sam autor zaznacza, ze ETF-y na zloto powstaly w XXI wieku, wiec wczesniej strategia byla w praktyce\n"
    "niewykonalna, a w latach 2011–2025 wygrywaja zwykle indeksy akcji.\n":
        "\nThe author reports **19.97% a year for 1972–2025**, calculated on index data (S&P 500 with dividends,\n"
        "MSCI World ex-US, MSCI EM from 1988, the gold price). That result is largely driven by **the 1970s gold bull market**\n"
        "(from 35 to about 850 USD/oz), when the strategy held gold for most of the decade.\n\n"
        "This backtest uses **ETFs from yfinance**, so it can start at the end of 2005 at the earliest\n"
        "(GLD exists since Nov 2004, plus {lookback} months for the first momentum reading).\n\n"
        "The rule was checked against the author's version (with the S&P 500): for 2006–2025 the author reports\n"
        "**7,469 USD from 1,000 USD, a drawdown of about −29% and 58 switches**, while the same rule on ETFs gives 6,259 USD,\n"
        "−29.1% and 52 switches (with EFA instead of VEA: 6,444 USD and −28.6%). The differences come from using VEA/EFA instead of MSCI World ex-US, ETF costs and different\n"
        "month-end dates. This page uses the **Nasdaq-100 (QQQ)** instead of the S&P 500, like classic GEM.\n\n"
        "The author also notes that gold ETFs appeared only in the 21st century, so before that the strategy was\n"
        "impractical, and in 2011–2025 plain stock indices usually win.\n",
    "Wspolny okres od {v0}: GEM wymaga ACWI (notowany od 2008) i roku historii na pierwszy sygnal. "
    "GEM liczony jest dziennie z rebalansem co 21 sesji, a tu pokazany na koncach miesiecy.":
        "Common period from {v0}: GEM needs ACWI (listed since 2008) and a year of history for its first signal. "
        "GEM is calculated daily with a rebalance every 21 sessions and shown here at month ends.",
}

PREMIUM4: dict[str, str] = {**FSTRINGS}
