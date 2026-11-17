"""Katalog EN: polski tekst zrodlowy -> angielskie tlumaczenie.

Klucz musi byc IDENTYCZNY z tekstem w tr("...") (lacznie z brakiem polskich znakow
w starszych napisach typu "Wyczysc"). tests/test_i18n.py wylapuje braki.
Sekcje wg miejsca uzycia; teksty dynamiczne (etykiety z danych) tez musza tu byc.
"""

EN: dict[str, str] = {
    # ------------------------------------------------------------------
    # Nawigacja: sekcje, tytuly i opisy stron (components/nav.py)
    # ------------------------------------------------------------------
    "Strategia GEM": "GEM strategy",
    "ETF": "ETF",
    "Spółki": "Stocks",
    "Portfel": "Portfolio",
    "Rynek": "Markets",
    "Krypto": "Crypto",
    "Pulpit": "Dashboard",
    "Sygnał GEM": "GEM signal",
    "Backtest": "Backtest",
    "GEM Extended": "GEM Extended",
    "GEM Gold Momentum": "GEM Gold Momentum",
    "O strategii": "About the strategy",
    "Ranking momentum": "Momentum ranking",
    "Porównaj": "Compare",
    "Stopy zwrotu": "Long-term returns",
    "Drawdowny": "Drawdowns",
    "Karta spółki": "Company profile",
    "S&P 500": "S&P 500",
    "GPW": "Warsaw (GPW)",
    "Top Picks": "Top Picks",
    "Screener": "Screener",
    "Kalendarz wyników": "Earnings calendar",
    "Insiderzy": "Insiders",
    "Portfolio Builder": "Portfolio Builder",
    "Monte Carlo": "Monte Carlo",
    "Makro": "Macro",
    "Rotacja sektorowa": "Sector rotation",
    "Intermarket": "Intermarket",
    "Sezonowość": "Seasonality",
    "Waluta PLN/USD": "USD/PLN currency",
    "Kryptowaluty": "Cryptocurrencies",
    "Ta strona wymaga dostępu Premium.": "This page requires Premium access.",
    "Centrum dowodzenia: sygnal GEM, regime, rynek, watchlista, wyniki tygodnia":
        "Command centre: GEM signal, market regime, markets, watchlist, this week's earnings",
    "Aktualny sygnal GEM, top 5 ETF oraz pelna historia zmian sygnalu":
        "Current GEM signal, top 5 ETFs and the full history of signal changes",
    "GEM vs Buy&Hold — krzywa kapitalu, Sharpe, MDD i wiecej":
        "GEM vs Buy & Hold — equity curve, Sharpe, max drawdown and more",
    "Backtest GEM z dowolnym universe (do 10 ETF + krypto), top N equal-weight":
        "GEM backtest on any universe (up to 10 ETFs + crypto), top N equal-weight",
    "Momentum ze zlotem w wersji GEM: Nasdaq-100 / zloto / obligacje, backtest od 2005 vs GEM klasyczny":
        "Gold momentum, GEM style: Nasdaq-100 / gold / bonds, backtest since 2005 vs classic GEM",
    "Opis strategii GEM Gary'ego Antonacciego": "Gary Antonacci's GEM strategy explained",
    "Tabela rankingowa 30+ ETF-ow z wynikiem momentum": "Ranking table of 30+ ETFs with a momentum score",
    "Wykresy, head-to-head 2–4 ETF-ow z korelacjami oraz side-by-side dwoch aktywow":
        "Charts, head-to-head of 2–4 ETFs with correlations, and side-by-side of two assets",
    "Stopy zwrotu ETF-ow do 30 lat: okresy, lata, okna kroczace, PLN i proxy":
        "ETF returns over up to 30 years: periods, calendar years, rolling windows, PLN and proxies",
    "Analiza spadkow od szczytu — glebokosc, czas trwania, odbudowa":
        "Peak-to-trough declines — depth, duration, recovery",
    "Jedna spolka: przeglad, finanse, wyniki, akcjonariat, dywidendy, konkurencja":
        "One company: overview, financials, earnings, ownership, dividends, peers",
    "Ranking, wykresy, sprawozdania (screener) i backtest ~500 spolek z indeksu S&P 500":
        "Ranking, charts, financials (screener) and backtest of ~500 S&P 500 companies",
    "140 spolek z WIG20, mWIG40 i sWIG80 — momentum, sprawozdania (screener) i backtest":
        "140 Warsaw-listed companies from WIG20, mWIG40 and sWIG80 — momentum, financials (screener) and backtest",
    "Trzy miesieczne piatki spolek: momentum cenowe, jakosc wynikow kwartalnych i jakosc biznesu":
        "Monthly top-5 stock picks: price momentum, quarterly earnings quality and business quality",
    "Cross-asset ranking momentum ze wszystkich klas aktywow":
        "Cross-asset momentum ranking across all asset classes",
    "Kalendarz nadchodzacych i niedawnych raportow SP500 + GPW (±28 dni) z watchlista":
        "Upcoming and recent earnings reports, S&P 500 + Warsaw (±28 days), with watchlist",
    "Bulk insider activity SP500 — top kupujacy/sprzedajacy, sektory":
        "S&P 500 insider activity — top buyers/sellers, sectors",
    "Zbuduj portfel, ustaw wagi, backtest i analiza korelacji":
        "Build a portfolio, set weights, backtest it and analyse correlations",
    "Symulacja przyszlych zwrotow — ile mozesz miec za N lat?":
        "Simulate future returns — how much could you have in N years?",
    "VIX, yield curve, DXY, S&P+200MA, zloto, ropa": "VIX, yield curve, DXY, S&P + 200-day MA, gold, oil",
    "Ktory sektor GICS prowadzi? Heatmapa momentum sektorow":
        "Which GICS sector is leading? Sector momentum heatmap",
    "Relacje miedzy klasami aktywow: akcje, obligacje, zloto, dolar":
        "Relationships between asset classes: stocks, bonds, gold, the dollar",
    "Heatmapa miesiecznych zwrotow i wzorce sezonowe": "Monthly returns heatmap and seasonal patterns",
    "Wplyw kursu USD/PLN na zwroty ETF-ow w zlotowkach": "How the USD/PLN rate affects ETF returns in Polish zloty",
    "Top 200 kryptowalut — ranking, alt/BTC ratio, backtest": "Top 200 cryptocurrencies — ranking, alt/BTC ratio, backtest",

    # ------------------------------------------------------------------
    # Premium (components/auth.py)
    # ------------------------------------------------------------------
    "Odblokuj Premium": "Unlock Premium",
    "Odblokuj wszystkie strony Premium": "Unlock all Premium pages",
    "Jednorazowy dostęp &middot; 49 zł &middot; Lifetime": "One-time payment &middot; PLN 49 &middot; Lifetime access",
    "Kup dostep Premium": "Buy Premium access",
    "Po zakupie otrzymasz kod aktywacyjny w pliku PDF.": "After purchase you will receive an activation code in a PDF file.",
    "Wpisz go w panelu bocznym (sidebar), aby odblokować dostęp.": "Enter it in the sidebar to unlock access.",

    # ------------------------------------------------------------------
    # Sidebar i stopka (components/sidebar.py)
    # ------------------------------------------------------------------
    "Global Equity Momentum — analiza ETF-ow": "Global Equity Momentum — ETF analysis",
    "Poradniki o inwestowaniu: inwestowanie.edu.pl ↗": "Investing guides (in Polish): inwestowanie.edu.pl ↗",
    "Premium aktywny": "Premium active",
    "Wyloguj Premium": "Log out of Premium",
    "Aktywuj Premium": "Activate Premium",
    "Kod aktywacyjny": "Activation code",
    "Aktywuj": "Activate",
    "Premium aktywowany!": "Premium activated!",
    "Nieprawidlowy kod.": "Invalid code.",
    "Wpisz kod aktywacyjny.": "Enter your activation code.",
    "Kup dostep Premium (49 zl)": "Buy Premium access (PLN 49)",
    "Ulubione": "Favourites",
    "np. AAPL, BTC-USD": "e.g. AAPL, BTC-USD",
    "Dodaj do ulubionych": "Add to favourites",
    "Maks. 8 ulubionych.": "Max. 8 favourites.",
    "Wyczysc ulubione": "Clear favourites",
    "Alerty": "Alerts",
    "Dodaj alert": "Add alert",
    "np. QQQ": "e.g. QQQ",
    "Warunek": "Condition",
    "spadek": "drop",
    "wzrost": "rise",
    "Prog (%)": "Threshold (%)",
    "Okres": "Period",
    "Maks. 5 alertow.": "Max. 5 alerts.",
    "Wyczysc alerty": "Clear alerts",
    "Ustawienia": "Settings",
    "Reczna stopa wolna od ryzyka": "Manual risk-free rate",
    "Stopa wolna (%)": "Risk-free rate (%)",
    "Dodaj ticker": "Add a ticker",
    "Ticker (np. ARKK)": "Ticker (e.g. ARKK)",
    "Dodaj": "Add",
    "Nieprawidlowy format tickera.": "Invalid ticker format.",
    "Dodano {ticker}": "Added {ticker}",
    "Mozesz dodac maksymalnie 10 wlasnych tickerow.": "You can add up to 10 custom tickers.",
    "{ticker} juz jest na liscie": "{ticker} is already on the list",
    "Dodane": "Added",
    "Wyczysc dodane": "Clear added",
    "Odswiez dane": "Refresh data",
    "Cache wyczyszczony — dane zostana pobrane od nowa.": "Cache cleared — data will be downloaded again.",
    "Dane: Yahoo Finance (yfinance)": "Data: Yahoo Finance (yfinance)",
    "Strategia: Gary Antonacci — GEM": "Strategy: Gary Antonacci — GEM",
    "Nie udalo sie pobrac stopy wolnej. Uzywam domyslnej: 4,5%":
        "Could not fetch the risk-free rate. Using the default: 4.5%",
    "Dashboard ma charakter edukacyjny i informacyjny. Nie stanowi porady inwestycyjnej, "
    "finansowej ani prawnej. Wyniki historyczne i symulacje nie gwarantują przyszłych zwrotów. "
    "Przed podjęciem decyzji inwestycyjnych skonsultuj się z licencjonowanym doradcą finansowym.":
        "This dashboard is for educational and informational purposes only. It is not investment, "
        "financial or legal advice. Past performance and simulations do not guarantee future returns. "
        "Consult a licensed financial adviser before making investment decisions.",
    "Wszelkie prawa zastrzeżone": "All rights reserved",
    "wersja": "version",
    "Jak działa strategia GEM i jak inwestować w ETF-y: inwestowanie.edu.pl ↗":
        "How the GEM strategy works and how to invest in ETFs (in Polish): inwestowanie.edu.pl ↗",

    # ------------------------------------------------------------------
    # Formatowanie, karty, wykresy (components/formatting.py, cards.py, charts.py)
    # ------------------------------------------------------------------
    "Akcje miedzynar.": "International stocks",
    "TAK": "YES",
    "NIE": "NO",
    "12M zwrot vs RF {rf}": "12M return vs RF {rf}",
    "12M zwrot": "12M return",
    "Rynki rozwi. (VEA)": "Developed mkts (VEA)",
    "Rynki wsch. (EEM)": "Emerging mkts (EEM)",
    "Globalne (ACWI)": "Global (ACWI)",
    "Obligacje (AGG)": "Bonds (AGG)",
    "Stopa wolna (T-bill)": "Risk-free rate (T-bill)",
    "Roczna, 13-week": "Annual, 13-week",
    "spadl o {pct}%": "fell {pct}%",
    "wzrosl o {pct}%": "rose {pct}%",
    "prog": "threshold",
    "Wszystkie dane OK": "All data OK",
    "{n} brak danych": "{n} missing",
    "Strategia": "Strategy",
    "Neutralny": "Neutral",
    "Sygnał TA": "TA signal",
    "Siła": "Strength",
    "KUP": "BUY",
    "SPRZEDAJ": "SELL",
    "NEUTRALNY": "NEUTRAL",
    "Wynik kompozytowy (%)": "Composite score (%)",
    "Top 10 — wynik momentum": "Top 10 — momentum score",
    "Rozklad kategorii": "Category breakdown",
    "Cena (baza = 100)": "Price (base = 100)",
    "Krzywa kapitalu": "Equity curve",

    # ------------------------------------------------------------------
    # Sygnal GEM — etykiety z danych (data/momentum.py, market_status.py)
    # ------------------------------------------------------------------
    "Brak danych do obliczenia sygnalu": "Not enough data to compute the signal",
    "OBLIGACJE (AGG) — momentum absolutny ujemny": "BONDS (AGG) — absolute momentum negative",
    "AKCJE USA (QQQ) — momentum relatywny na korzysc USA": "US STOCKS (QQQ) — relative momentum favours the US",
    "AKCJE MIEDZYNARODOWE (VEA) — momentum relatywny na korzysc rynkow rozwi.":
        "INTERNATIONAL STOCKS (VEA) — relative momentum favours developed markets",
    "RYNKI WSCHODZACE (EEM) — momentum relatywny na korzysc EM":
        "EMERGING MARKETS (EEM) — relative momentum favours EM",
    "AKCJE GLOBALNE (ACWI) — momentum relatywny na korzysc rynku globalnego":
        "GLOBAL STOCKS (ACWI) — relative momentum favours the global market",
    "Akcje USA": "US stocks",
    "Rynki rozwinięte": "Developed markets",
    "Rynki wschodzące": "Emerging markets",
    "Rynki wschodzace": "Emerging markets",
    "Akcje globalne": "Global stocks",
    "Globalne": "Global",
    "Obligacje": "Bonds",
    "Risk-On": "Risk-On",
    "Risk-Off": "Risk-Off",
    "Srodowisko sprzyjajace akcjom": "Environment favourable to stocks",
    "Awersja do ryzyka — rozwazyc obligacje": "Risk aversion — consider bonds",
    "Mieszane sygnaly miedzy klasami aktywow": "Mixed signals across asset classes",
    "Obligacje USA 10Y": "US 10Y Treasury",
    "Złoto": "Gold",
    "WIG20 (ETF Beta)": "WIG20 (ETF Beta)",

    # ------------------------------------------------------------------
    # Universum ETF: kategorie i nazwy (data/etf_universe.py) — tlumaczone przy wyswietlaniu
    # ------------------------------------------------------------------
    "Obligacje USA": "US bonds",
    "Zloto i surowce": "Gold & commodities",
    "Nieruchomosci (REIT)": "Real estate (REIT)",
    "Sektory USA": "US sectors",
    "Wlasne": "Custom",
    "Wszystkie": "All",
    "S&P 500 (SPDR)": "S&P 500 (SPDR)",
    "Nasdaq 100 (Invesco)": "Nasdaq 100 (Invesco)",
    "Caly rynek USA (Vanguard)": "Total US market (Vanguard)",
    "S&P 500 (Vanguard)": "S&P 500 (Vanguard)",
    "Russell 2000 male spolki USA": "Russell 2000 US small caps",
    "Rynki rozw. bez USA (Vanguard)": "Developed ex-US (Vanguard)",
    "EAFE — Europa, Azja, Daleki Wsch.": "EAFE — Europe, Australasia, Far East",
    "MSCI All Country World (iShares)": "MSCI All Country World (iShares)",
    "Europa (Vanguard)": "Europe (Vanguard)",
    "Japonia (iShares)": "Japan (iShares)",
    "Wielka Brytania (iShares)": "United Kingdom (iShares)",
    "Rynki wschodzace (iShares)": "Emerging markets (iShares)",
    "Rynki wschodzace (Vanguard)": "Emerging markets (Vanguard)",
    "Chiny large-cap (iShares)": "China large-cap (iShares)",
    "Obligacje zagregowane USA": "US aggregate bonds",
    "Obligacje calkowity rynek USA": "US total bond market",
    "Obligacje dlugot. 20+ lat": "Long-term Treasuries 20+ yr",
    "Obligacje sredniot. 7-10 lat": "Intermediate Treasuries 7-10 yr",
    "Obligacje krotkot. 1-3 lata": "Short-term Treasuries 1-3 yr",
    "Obligacje indeks. inflacja": "Inflation-protected bonds (TIPS)",
    "Zloto (SPDR)": "Gold (SPDR)",
    "Zloto (iShares)": "Gold (iShares)",
    "Surowce (iShares)": "Commodities (iShares)",
    "Surowce (Invesco)": "Commodities (Invesco)",
    "REIT USA (Vanguard)": "US REITs (Vanguard)",
    "REIT miedzynarodowy (Vanguard)": "International REITs (Vanguard)",
    "Sektor technologiczny": "Technology sector",
    "Sektor finansowy": "Financials sector",
    "Sektor energetyczny": "Energy sector",
    "Sektor ochrony zdrowia": "Health care sector",
    "Sektor przemyslowy": "Industrials sector",
    "Sektor konsumpcji cyklicznej": "Consumer discretionary sector",
    "Sektor konsumpcji podstawowej": "Consumer staples sector",
    "Sektor komunikacji": "Communication services sector",
    "Sektor nieruchomosci": "Real estate sector",
    "Sektor uzytecznosci publ.": "Utilities sector",
    "Sektor materialowy": "Materials sector",

    # ------------------------------------------------------------------
    # Ranking momentum (views/etf/ranking.py)
    # ------------------------------------------------------------------
    "Ranking Momentum": "Momentum Ranking",
    "Kategoria": "Category",
    "Momentum absolutny": "Absolute momentum",
    "**{n}** ETF-ow | Stopa wolna: **{rf}%**": "**{n}** ETFs | Risk-free rate: **{rf}%**",
    "Nazwa": "Name",
    "Wynik": "Score",
    "Eksportuj CSV": "Export CSV",
    "ETF-y wg kategorii": "ETFs by category",

    # ------------------------------------------------------------------
    # Pulpit (views/start/pulpit.py)
    # ------------------------------------------------------------------
    "Dzień dobry": "Hello",
    "Dobry wieczór": "Good evening",
    "dane z zamknięcia ostatniej sesji": "data as of the last session close",
    "dane chwilowo niedostępne": "data temporarily unavailable",
    "Szukaj spółki (S&P 500 i GPW)": "Search for a company (S&P 500 and Warsaw)",
    "Wpisz nazwę lub ticker…": "Type a name or ticker…",
    "Przegląd spółki za darmo, pozostałe zakładki w Premium.": "Company overview is free; the other tabs are Premium.",
    "od {n} dni": "for {n} days",
    "Następne przeliczenie: {date}": "Next recalculation: {date}",
    "Regime rynku": "Market regime",
    "Metryki 12M": "12M metrics",
    "Niski strach": "Low fear",
    "Umiarkowany": "Moderate",
    "Wysoki strach": "High fear",
    "Wskaźniki rynku": "Market indicators",
    "dziś": "today",
    "jutro": "tomorrow",
    "za {n} dni": "in {n} days",
    "Otwórz kartę {ticker}": "Open {ticker} profile",
    "Karta spółki {ticker}": "{ticker} company profile",
    "brak danych": "no data",
    "Wyniki w tym tygodniu": "Earnings this week",
    "Brak nadchodzących raportów w ciągu 7 dni dla watchlisty i największych spółek.":
        "No earnings reports in the next 7 days for your watchlist or the largest companies.",
    "Wygrani / przegrani": "Gainers / losers",
    "Liczę zmiany {market}…": "Calculating {market} moves…",
    "Wzrosty": "Gainers",
    "Spadki": "Losers",
    "Top 5 ETF wg momentum": "Top 5 ETFs by momentum",
    "Ranking ETF": "ETF ranking",
    "Wyniki strategii (5 lat)": "Strategy performance (5 years)",
    "Wyniki strategii": "Strategy performance",
    "Za malo danych do backtestu GEM (wymagane 252+ sesji).": "Not enough data for the GEM backtest (252+ sessions required).",
    "Eksport raportu PDF": "Export PDF report",
    "Wybierz sekcje do wlaczenia w raport": "Choose the sections to include in the report",
    "Sygnal GEM": "GEM signal",
    "Regime rynkowy": "Market regime",
    "Top 5 ETF-ow": "Top 5 ETFs",
    "Kluczowe aktywa": "Key assets",
    "Statystyki strategii": "Strategy statistics",
    "Ranking ETF top 10": "ETF ranking top 10",
    "Generuj raport PDF": "Generate PDF report",
    "Pobierz PDF": "Download PDF",
    "Wybierz co najmniej jedna sekcje.": "Select at least one section.",
    "Moja watchlista": "My watchlist",
    "Pusta. Dodaj spółki gwiazdką ⭐ w S&P 500 / GPW albo w sidebarze (Ulubione).":
        "Empty. Add companies with the ⭐ star on the S&P 500 / Warsaw pages or in the sidebar (Favourites).",
    "Watchlista": "Watchlist",
    "Dodaj tickery w panelu bocznym (Ulubione).": "Add tickers in the sidebar (Favourites).",
    "Watchlista ze spółek S&P 500 / GPW (gwiazdki ⭐) — w Premium.":
        "A watchlist of S&P 500 / Warsaw companies (⭐ stars) — in Premium.",
    "Kto raportuje w tym tygodniu — najpierw Twoje spółki.": "Who reports this week — your companies first.",
    "Wygrani i przegrani": "Gainers and losers",
    "Największe zmiany dnia w S&P 500 i na GPW.": "Biggest daily moves in the S&P 500 and on the Warsaw exchange.",
    "Status danych": "Data status",

    # ------------------------------------------------------------------
    # Sygnal GEM (views/strategia/sygnal.py)
    # ------------------------------------------------------------------
    "Teraz": "Now",
    "Historia": "History",
    "Statystyki": "Statistics",
    "Kalendarz": "Calendar",
    "Klasyczny GEM (QQQ / VEA / EEM / ACWI / AGG)": "Classic GEM (QQQ / VEA / EEM / ACWI / AGG)",
    "Top 5 ETF-ow — rozszerzony ranking momentum": "Top 5 ETFs — extended momentum ranking",
    "Top 10 — wykres momentum": "Top 10 — momentum chart",
    "Brak danych do wyswietlenia rankingu.": "No data to display the ranking.",
    "Jak czytac sygnal GEM?": "How to read the GEM signal",
    "Pobieram dane i obliczam sygnaly...": "Downloading data and calculating signals...",
    "Od {n} dni": "For {n} days",
    "Data ostatniej zmiany": "Last change",
    "Poprzednie sygnaly": "Previous signals",
    "{n} dni": "{n} days",
    "dni": "days",
    "Timeline sygnalow GEM": "GEM signal timeline",
    "Historia sygnalow GEM": "GEM signal history",
    "Pelna lista zmian sygnalu": "Full list of signal changes",
    "Poczatek": "Start",
    "Koniec": "End",
    "Sygnal": "Signal",
    "Czas trwania (dni)": "Duration (days)",
    "Statystyki sygnalow": "Signal statistics",
    "% czasu w kazdym sygnale": "% of time in each signal",
    "{pct}% czasu · {n} wystapien · sredni czas: {avg} dni": "{pct}% of the time · {n} occurrences · average duration: {avg} days",
    "Kalendarz sygnalow (rok × miesiac)": "Signal calendar (year × month)",
    "Kalendarz sygnalow GEM": "GEM signal calendar",
    "Rok": "Year",
    "Miesiac": "Month",
    "Sty": "Jan", "Lut": "Feb", "Mar": "Mar", "Kwi": "Apr", "Maj": "May", "Cze": "Jun",
    "Lip": "Jul", "Sie": "Aug", "Wrz": "Sep", "Paz": "Oct", "Lis": "Nov", "Gru": "Dec",
    "Brak wystarczajacych danych do obliczenia historii sygnalow.": "Not enough data to calculate the signal history.",
    "Historia sygnałów": "Signal history",
    "Statystyki sygnałów": "Signal statistics",
    "Kalendarz sygnałów": "Signal calendar",
    "Pełna historia zmian sygnału GEM, czas trwania pozycji i alokacja w czasie.":
        "The full history of GEM signal changes, how long each position lasted and allocation over time.",

    # ------------------------------------------------------------------
    # O strategii (views/strategia/o_strategii.py)
    # ------------------------------------------------------------------
    "O strategii GEM": "About the GEM strategy",
}


# Strony Premium (etap 2) — osobny plik, zeby en.py nie rosl w nieskonczonosc
from components.locales.en_premium import PREMIUM  # noqa: E402

EN.update(PREMIUM)


DOCS: dict[str, str] = {
    "sygnal_jak_czytac": """
        **Classic GEM** looks at 5 assets:
        1. If QQQ's 12M return < the risk-free rate → **buy bonds (AGG)**
        2. If momentum is positive → **buy the best of QQQ / VEA / EEM / ACWI** (relative comparison)

        **12M momentum (no skip) for ETFs — since 2026-05-23:** the return is calculated as
        `price(t) / price(t-252) - 1` (a full 12 months). A 14-year backtest on the
        QQQ/VEA/EEM/ACWI/AGG basket showed +4.6 pp CAGR per year vs the previous skip-month (12-1).
        Skip-month works for individual stocks, but on index ETFs delaying the signal
        by a month hurts.

        **The extended ranking** calculates a composite score:
        `12M × 50% + 6M × 25% + 3M × 15% + 1M × 10%`

        **Absolute momentum:** YES = 12M return > the risk-free rate

        **Note:** stock rankings (S&P 500, Warsaw, crypto) still use 12-1
        skip-month — the reversal effect matters for individual companies.
        """,

    "o_strategii": """
## What is GEM?

**Global Equity Momentum (GEM)** is an investment strategy developed by **Gary Antonacci**
and described in his book *"Dual Momentum Investing"* (2014). It combines two kinds of momentum:

### 1. Absolute momentum
- Compares an asset's return with the **risk-free rate** (e.g. T-bills)
- If the 12M return > the risk-free rate → **uptrend**, worth investing
- If the 12M return < the risk-free rate → **downtrend**, better to move into bonds
- **12M window (no skip):** the return is calculated as `price(t) / price(t-252) - 1` — a full 12 months back. **Change on 2026-05-23:** we previously used skip-month (12-1) — `price(t-21)/price(t-273)-1`, but a 14-year backtest on an ETF basket (QQQ/VEA/EEM/ACWI/AGG) showed +4.6 pp CAGR per year for plain 12M (skip-month works for individual stocks, but on index ETFs the delayed signal hurts). **Stock** rankings (S&P 500, Warsaw, crypto) still use skip-month (Jegadeesh & Titman 1993).

### 2. Relative momentum
- Compares the returns of **two (or more) assets** with each other
- You invest in the asset with **stronger momentum** (the higher return over the period)
- In classic GEM: the US (QQQ) vs developed markets (VEA) vs emerging markets (EEM) vs the world (ACWI)

---

## How does classic GEM work?

The strategy makes one decision a month, in these steps:

| Step | Condition | Action |
|------|-----------|--------|
| 1 | QQQ 12M return < risk-free rate | → Buy bonds (AGG) |
| 2 | Compare QQQ vs VEA vs EEM vs ACWI | → Buy the asset with the highest 12M momentum |

**You are always 100% in one asset** — it is an "all-in/all-out" strategy.
Four equity markets are compared: the US (QQQ), developed (VEA), emerging (EEM) and the world (ACWI).

---

## Extended GEM in this dashboard

This dashboard extends classic GEM to **30+ ETFs** in 7 categories:
- US stocks, developed markets, emerging markets, bonds, gold, REITs, sectors

### Composite score
Each ETF gets a score based on a weighted average of its returns:

```
Score = 12M × 50% + 6M × 25% + 3M × 15% + 1M × 10%
```

The weights favour the **long-term trend** (12M = 50%) but also take shorter periods into account.
**12M for ETFs** = a plain 12 months (no skip, since 2026-05-23). **12M for stocks** (S&P 500, Warsaw, crypto rotation) = 12-1 skip-month (skips the last month to neutralise short-term reversal).

---

## How to read the signals

### Absolute momentum: YES / NO
- **YES** = 12M return > risk-free rate → uptrend, worth considering
- **NO** = 12M return < risk-free rate → downtrend, be cautious

### Composite score
- **A higher score = a stronger uptrend**
- A negative score = a downtrend in most periods

### GEM signal (classic)
- 🟢 **QQQ** = US stocks lead
- 🔵 **VEA** = developed markets lead
- 🟣 **EEM** = emerging markets lead
- 🌐 **ACWI** = the global market leads
- 🟡 **AGG** = the market is in a downtrend, shelter in bonds

---

## Advantages of GEM

- **Simple** — one decision a month is enough
- **Systematic** — takes emotions out of investing
- **Historical results** — in backtests, a higher return than buy & hold with a smaller drawdown
- **Diversification** — moves between asset classes depending on the trend
- **Protection in bear markets** — absolute momentum flags a downtrend and moves you into bonds

## Drawbacks and limitations

- **Lagging signals** — based on 12M data, so it reacts with a delay
- **Whipsaws** — can give false signals in a sideways market
- **No diversification** — classic GEM holds 100% in a single asset
- **Transaction costs** — frequent signal changes mean commissions and taxes
- **Past results ≠ future results** — backtests do not guarantee future profits

---

## Sources

- **Gary Antonacci** — *Dual Momentum Investing* (2014, McGraw-Hill)
- [OptimalMomentum.com](https://www.optimalmomentum.com/) — the author's website
- **Jegadeesh & Titman (1993)** — "Returns to Buying Winners and Selling Losers" — the academic foundation of momentum
- **Asness et al. (2014)** — "Fact, Fiction and Momentum Investing" — AQR Capital

---

> **Important:** this dashboard is for educational purposes only. It is not an investment recommendation.
> Consult a licensed financial adviser before making investment decisions.
""",
}

# Dlugie opisy na stronach Premium (etap 2)
from components.locales.en_docs_premium import DOCS_PREMIUM  # noqa: E402

DOCS.update(DOCS_PREMIUM)
