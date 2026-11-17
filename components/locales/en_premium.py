"""Katalog EN — strony Premium (etap 2). Dolaczany do EN w en.py (EN.update(PREMIUM))."""

# --- Karta spolki (views/spolki/karta.py, components/company/*, financials_ui, cards finansowe) ---
KARTA: dict[str, str] = {
    "# Karta spółki": "# Company profile",
    "Sekcja": "Section",
    "Przegląd": "Overview",
    "Finanse": "Financials",
    "Wyniki": "Earnings",
    "Akcjonariat": "Ownership",
    "Dywidendy": "Dividends",
    "Konkurencja": "Peers",
    "Wskaźniki, konsensus EPS, historia wyników i rekomendacje analityków.":
        "Ratios, EPS consensus, earnings history and analyst recommendations.",
    "Wyniki kwartalne vs prognozy, rachunek zysków i strat, bilans, przepływy.":
        "Quarterly results vs estimates, income statement, balance sheet, cash flow.",
    "Główni akcjonariusze, fundusze, transakcje insiderów.": "Major shareholders, funds, insider transactions.",
    "Historia wypłat, stopa, wzrost dywidendy i kalkulator dochodu po podatku.":
        "Payout history, yield, dividend growth and an after-tax income calculator.",
    "Porównanie wskaźników z 5 najbliższymi spółkami z sektora.": "Ratios compared with the 5 closest companies in the sector.",
    "Wybierz spółkę, aby zobaczyć jej kartę.": "Pick a company to see its profile.",
    "Nie znaleziono spółki {ticker} w S&P 500 ani na GPW.": "Company {ticker} was not found in the S&P 500 or on the Warsaw exchange.",
    "Usuń z watchlisty": "Remove from watchlist",
    "Dodaj do watchlisty": "Add to watchlist",
    "Watchlista w Premium": "Watchlist in Premium",
    "zł": "PLN",
    "zl": "PLN ",
    "bln": "tn",
    "mld": "bn",
    "mln": "m",
    "O spółce": "About the company",
    "Rozwiń opis": "Show full description",
    "Wykres": "Chart",
    "Wykres: brak danych": "Chart: no data",
    "Kluczowe dane": "Key data",
    "Kapitalizacja": "Market cap",
    "Stopa dywidendy": "Dividend yield",
    "Zakres 52 tyg.": "52-week range",
    "Analitycy": "Analysts",
    "Brak pokrycia analityków": "No analyst coverage",
    "Kupuj": "Buy",
    "Trzymaj": "Hold",
    "Sprzedaj": "Sell",
    "Cel średni": "Mean target",
    "cena": "price",
    "cel": "target",
    "Następne wyniki": "Next earnings",
    "Dywidenda (ex)": "Dividend (ex-date)",
    "Ostatni beat/miss": "Last beat/miss",
    "Za krótka historia notowań": "Price history too short",
    "#{rank} z {of} w {label}": "#{rank} of {of} in {label}",
    "Liczę ranking momentum…": "Calculating the momentum ranking…",
    "Momentum GEM: dane chwilowo niedostępne": "GEM momentum: data temporarily unavailable",
    # sektory GPW (S&P 500 ma nazwy GICS po angielsku)
    "Banki": "Banks", "Energia": "Energy", "Komunikacja": "Communication",
    "Konsument cykliczny": "Consumer discretionary", "Konsument defensywny": "Consumer staples",
    "Nieruchomosci": "Real estate", "Ochrona zdrowia": "Health care", "Przemysl": "Industrials",
    "Surowce": "Materials", "Technologia": "Technology", "Uzytecznosc publiczna": "Utilities",
    # Finanse
    "### Wskaźniki finansowe i konsensus analityków": "### Financial ratios and analyst consensus",
    "Część wskaźników jest niedostępna dla mniejszych spółek lub sektora bankowego "
    "(EBITDA / EV-EBITDA / FCF). Konsensus analityków jest typowo dostępny dla WIG20 "
    "i większych spółek mWIG40.":
        "Some ratios are unavailable for smaller companies and for banks (EBITDA / EV-EBITDA / FCF). "
        "Analyst consensus is usually available for WIG20 and the larger mWIG40 companies.",
    "Bank — EBITDA, EV/EBITDA i FCF ukryte.": "Bank — EBITDA, EV/EBITDA and FCF hidden.",
    "Dane z yfinance, cache 24h. Brakujące wskaźniki oznaczone „—”.": "Data from yfinance, cached for 24h. Missing ratios are shown as “—”.",
    "Pobieram dane finansowe dla {ticker}...": "Downloading financial data for {ticker}...",
    "Brak danych ze zrodla yfinance": "No data from yfinance",
    "Brak danych finansowych dla tej spolki": "No financial data for this company",
    "Brak konsensusu analitykow dla tej spolki": "No analyst consensus for this company",
    "Brak historii earnings dla tej spolki": "No earnings history for this company",
    "Brak rekomendacji analitykow dla tej spolki": "No analyst recommendations for this company",
    "Wskaźniki spółki": "Company ratios",
    "Historia wyników": "Earnings history",
    "Rekomendacje analityków": "Analyst recommendations",
    "{n} analitykow": "{n} analysts",
    "Analitykow": "Analysts",
    "EPS estimate": "EPS estimate",
    # Wyniki
    "Część spółek GPW (small-cap) nie ma pełnych danych w yfinance — luki są oczekiwane.":
        "Some Warsaw small caps lack complete data in yfinance — gaps are expected.",
    "Ostatni EPS": "Last EPS",
    "vs prognoza {est} ({surprise}%)": "vs estimate {est} ({surprise}%)",
    "Seria wyników powyżej prognoz": "Beat streak",
    "{n} kw.": "{n} qtrs",
    "Prognoza EPS Q+1": "EPS estimate Q+1",
    "r/r {pct}%": "y/y {pct}%",
    "Prognoza przychodów Q+1": "Revenue estimate Q+1",
    "Podsumowanie wyników: dane chwilowo niedostępne": "Earnings summary: data temporarily unavailable",
    "Beat/miss": "Beat/miss",
    "Rachunek zysków i strat": "Income statement",
    "Bilans": "Balance sheet",
    "Przepływy": "Cash flow",
    "EPS: Estimate vs Actual (8Q historia + forward consensus)": "EPS: estimate vs actual (8Q history + forward consensus)",
    "#### Rewizje konsensusu analitykow": "#### Analyst consensus revisions",
    "Rewizja (now vs 30d) %": "Revision (now vs 30d) %",
    "Kwartalne 8Q": "Quarterly 8Q",
    "Roczne 4Y": "Annual 4Y",
    "Brak danych earnings history dla {ticker}.": "No earnings history for {ticker}.",
    "Brak danych {statement} dla {ticker}.": "No {statement} data for {ticker}.",
    "Brak rozpoznawalnych wierszy w {statement}.": "No recognised rows in the {statement}.",
    # Akcjonariat
    "### Akcjonariat i transakcje insiderów": "### Ownership and insider transactions",
    "Dla spółek GPW dane yfinance bywają niepełne; raporty bieżące: gpw.pl/komunikaty-spolek.":
        "yfinance data for Warsaw companies is often incomplete; current reports: gpw.pl/komunikaty-spolek.",
    "⚠️ Brak danych insider/institutional dla tego tickera GPW.\n\n"
    "Raporty biezace polskich spolek ida przez ESPI (poza zakresem yfinance).\n"
    "Sprawdz recznie: https://www.gpw.pl/komunikaty-spolek":
        "⚠️ No insider/institutional data for this Warsaw ticker.\n\n"
        "Polish companies publish current reports via ESPI (outside yfinance's coverage).\n"
        "Check manually: https://www.gpw.pl/komunikaty-spolek",
    "⚠️ yfinance nie zwrocil danych insider/institutional dla {ticker}.\n\n"
    "**Mozliwe przyczyny:**\n"
    "- Yahoo Finance czasowo blokuje insider endpointy (rate limit / API change)\n"
    "- Streamlit Cloud IP jest na czarnej liscie Yahoo\n"
    "- Sproboj ponownie za kilka minut (cache 24h)\n\n"
    "**Alternatywne zrodla:**\n":
        "⚠️ yfinance returned no insider/institutional data for {ticker}.\n\n"
        "**Possible causes:**\n"
        "- Yahoo Finance is temporarily blocking insider endpoints (rate limit / API change)\n"
        "- The Streamlit Cloud IP is blocklisted by Yahoo\n"
        "- Try again in a few minutes (24h cache)\n\n"
        "**Alternative sources:**\n",
    "🔍 Diagnostyka yfinance endpointow": "🔍 yfinance endpoint diagnostics",
    "#### 📊 Major Holders": "#### 📊 Major holders",
    "% Insider": "% Insiders",
    "% Institutional": "% Institutions",
    "# Institutions": "# Institutions",
    "% Float": "% Float",
    "#### 💰 Insider Purchases (6 mc agregat)": "#### 💰 Insider purchases (6-month aggregate)",
    "Brak danych dla Insider Purchases.": "No data for insider purchases.",
    "#### 📈 Historia transakcji insiderow (6 mc)": "#### 📈 Insider transaction history (6 months)",
    "Brak danych dla Insider Transactions.": "No data for insider transactions.",
    "#### 🏢 Roster zarzadu": "#### 🏢 Insider roster",
    "Brak danych dla Insider Roster.": "No data for the insider roster.",
    "#### 🏛️ Top 10 funduszy instytucjonalnych": "#### 🏛️ Top 10 institutional holders",
    "Brak danych dla Institutional Holders.": "No data for institutional holders.",
    "#### 💼 Top 10 mutual funds": "#### 💼 Top 10 mutual funds",
    "Brak danych dla Mutual Fund Holders.": "No data for mutual fund holders.",
    "Net insider activity": "Net insider activity",
    "Net insider buy/sell value per miesiac (6 mc)": "Net insider buy/sell value per month (6 months)",
    "Net USD": "Net USD",
    "Distribution institutional ownership": "Institutional ownership breakdown",
    "Reszta": "Other",
    # Dywidendy
    "Zwykłe": "Taxable",
    "Wskaźnik wypłaty": "Payout ratio",
    "Lata z rzędu": "Consecutive years",
    "Wzrost 5 lat (CAGR)": "5-year growth (CAGR)",
    "##### Dywidendy roczne": "##### Annual dividends",
    "##### Ostatnie wypłaty": "##### Recent payouts",
    "Data": "Date",
    "Kwota": "Amount",
    "Waluta": "Currency",
    "##### Kalkulator dywidendy po podatku": "##### After-tax dividend calculator (Polish tax resident)",
    "Brak aktualnej stopy dywidendy.": "No current dividend yield.",
    "Kalkulator podatku dostępny dla spółek z S&P 500 i GPW": "The tax calculator is available for S&P 500 and Warsaw companies",
    "Kwota inwestycji": "Investment amount",
    "Konto": "Account",
    "Brutto / rok": "Gross / year",
    "Podatek": "Tax",
    "Netto / rok": "Net / year",
    "Podatek Belki 19% pobiera dom maklerski.": "The 19% Polish capital gains tax (Belka tax) is withheld by the broker.",
    "Na IKE dywidendy z polskich spolek sa wolne od podatku.": "In an IKE account, dividends from Polish companies are tax-free.",
    "Na IKZE dywidendy z polskich spolek sa wolne od podatku (podatek przy wyplacie z IKZE).":
        "In an IKZE account, dividends from Polish companies are tax-free (tax is paid on withdrawal from the IKZE).",
    "15% pobiera USA (z formularzem W-8BEN), 4% doplaca sie w Polsce — razem 19%.":
        "The US withholds 15% (with a W-8BEN form) and 4% is paid in Poland — 19% in total.",
    "Na IKE nadal 15% pobiera USA (W-8BEN); polskiego podatku brak.": "In an IKE the US still withholds 15% (W-8BEN); no Polish tax.",
    "Na IKZE nadal 15% pobiera USA (W-8BEN); polskiego podatku brak.": "In an IKZE the US still withholds 15% (W-8BEN); no Polish tax.",
    "Wskaźniki dywidendy": "Dividend ratios",
    "Wykres dywidend": "Dividend chart",
    "Tabela dywidend": "Dividend table",
    "Kalkulator": "Calculator",
    "Spółka nie wypłaca dywidendy.": "The company does not pay a dividend.",
    "Dywidendy: dane chwilowo niedostępne": "Dividends: data temporarily unavailable",
    # Konkurencja
    "Spółka": "Company",
    "Mediana grupy": "Group median",
    "Marża netto": "Net margin",
    "Wzrost przychodów": "Revenue growth",
    "Momentum 12M": "Momentum 12M",
    "Kap.": "Mkt cap",
    "Marża": "Margin",
    "Wzrost przych.": "Rev. growth",
    "Stopa dyw.": "Div. yield",
    "Mom. 12M": "Mom. 12M",
    "Porównaj z": "Compare with",
    "Brak przypisanego sektora": "No sector assigned",
    "Pobieram kapitalizacje sektora…": "Fetching sector market caps…",
    "Mediana liczona dla całej wyświetlanej grupy (łącznie z wybraną spółką). "
    "Zielony = lepiej niż mediana, czerwony = gorzej (dla mnożników: niżej = lepiej). "
    "Ujemne mnożniki (strata) pomijane. Momentum 12M liczone bez ostatniego miesiąca.":
        "The median is calculated for the whole displayed group (including the selected company). "
        "Green = better than the median, red = worse (for multiples: lower = better). "
        "Negative multiples (losses) are skipped. 12M momentum excludes the most recent month.",
    "Porównanie z sektorem: dane chwilowo niedostępne": "Sector comparison: data temporarily unavailable",
    # Screener beat/miss (strony S&P 500 / GPW)
    "### 🔍 Screener — beat/miss ostatniego kwartalu": "### 🔍 Screener — last quarter beat/miss",
    "Filtry": "Filters",
    "Beat status": "Beat status",
    "Beat EPS": "EPS beat",
    "Miss EPS": "EPS miss",
    "Min EPS surprise %": "Min EPS surprise %",
    "Min beat streak (Q)": "Min beat streak (Q)",
    "Top N": "Top N",
    "Sort by": "Sort by",
    "EPS surprise %": "EPS surprise %",
    "Beat streak": "Beat streak",
    "EPS actual": "EPS actual",
    "Ticker": "Ticker",
    "Malejaco": "Descending",
    "🔄 Odswiez cache": "🔄 Refresh cache",
    "⭐ Tylko watchlist": "⭐ Watchlist only",
    "Watchlist pusty — kliknij ⭐ w tabeli aby dodac.": "Your watchlist is empty — click ⭐ in the table to add.",
    "Brak danych dla universe.": "No data for this universe.",
    "Avg surprise %": "Avg surprise %",
    "Avg streak (Q)": "Avg streak (Q)",
    "Wyniki ({n} spolek)": "Results ({n} companies)",
    "Wybierz spółkę": "Choose a company",
    "Otwórz kartę spółki": "Open company profile",
    "📥 Eksport CSV (screener)": "📥 Export CSV (screener)",
}

from components.locales.en_premium2 import PREMIUM2  # noqa: E402
from components.locales.en_premium3 import PREMIUM3  # noqa: E402
from components.locales.en_premium4 import PREMIUM4  # noqa: E402
from components.locales.en_premium5 import PREMIUM5  # noqa: E402

PREMIUM: dict[str, str] = {**KARTA, **PREMIUM2, **PREMIUM3, **PREMIUM4, **PREMIUM5}
