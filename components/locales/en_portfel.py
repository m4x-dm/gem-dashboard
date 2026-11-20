"""Katalog EN — strona Moj portfel (views/portfel/moj_portfel.py)."""

PORTFEL: dict[str, str] = {
    "Mój portfel": "My portfolio",
    "# Mój portfel": "# My portfolio",
    "Wczytaj eksport z XTB — zobaczysz pozycje, zysk, strukturę i nadchodzące raporty spółek":
        "Upload your XTB export to see positions, profit, allocation and upcoming company reports",
    "Zapisany portfel był uszkodzony — wczytaj eksport z XTB ponownie.":
        "The saved portfolio was corrupted — please upload your XTB export again.",
    "Pliki .xlsx z XTB (możesz wybrać kilka: zwykłe, IKE, IKZE)":
        "XTB .xlsx files (you can pick several: taxable, IKE, IKZE)",
    "Wczytano konto {typ} ({n} pozycji).": "Loaded {typ} account ({n} positions).",
    "Pominięto {n} pozycji CFD — portfel pokazuje akcje i ETF-y.":
        "Skipped {n} CFD positions — the portfolio shows stocks and ETFs.",
    "Historia operacji była bardzo długa — zapisano ostatnie 5 lat.":
        "The cash history was very long — only the last 5 years were saved.",
    "#### Jak pobrać eksport z XTB": "#### How to download the XTB export",
    "1. W xStation otwórz **Historia konta** i wybierz zakres dat od początku konta.\n"
    "2. Kliknij **Eksport** i wybierz format **XLSX**.\n"
    "3. XTB pobiera archiwum ZIP — rozpakuj je i wczytaj pliki `.xlsx` (osobny plik dla "
    "każdego konta: zwykłe, IKE, IKZE).":
        "1. In xStation open **Account history** and pick the date range from the account start.\n"
        "2. Click **Export** and choose **XLSX**.\n"
        "3. XTB downloads a ZIP archive — unzip it and upload the `.xlsx` files (one file per "
        "account: taxable, IKE, IKZE).",
    "Prywatność danych": "Data privacy",
    # opis strony w rejestrze (tests/test_i18n.py: test_page_titles_and_descriptions_translated)
    "Wczytaj eksport z XTB: pozycje, zysk, struktura, nadchodzace raporty":
        "Upload your XTB export: positions, profit, allocation, upcoming reports",
    "Plik jest przetwarzany tylko w pamięci i nie jest zapisywany na serwerze. "
    "Wczytane pozycje zostają w tej przeglądarce (localStorage) — na innym urządzeniu "
    "trzeba wczytać plik ponownie. Przycisk „Usuń portfel” kasuje je całkowicie.":
        "The file is processed in memory only and is not stored on the server. "
        "Imported positions stay in this browser (localStorage) — on another device you need to "
        "upload the file again. The “Delete portfolio” button removes them completely.",
    "Wczytaj eksport z XTB": "Upload XTB export",
    # Widok portfela. Celowo BEZ kluczy, ktore juz sa w innych katalogach z innym
    # tlumaczeniem (np. "Spółki" = sekcja menu "Stocks", "Zwykłe" = "Taxable",
    # "Otwórz kartę {ticker}") — EN.update(PORTFEL) nadpisalby je na innych stronach.
    "Wartość": "Value",
    "Zysk / strata": "Profit / loss",
    "Dziś": "Today",
    "Wpłaty netto": "Net deposits",
    "po podatku u źródła": "after withholding tax",
    "kurs z dnia raportu": "price from report date",
    "śr.": "avg",
    "#### Pozycje": "#### Positions",
    "#### Struktura": "#### Allocation",
    "Według": "By",
    "Konta": "Accounts",
    "Waluty": "Currencies",
    "#### Co się dzieje": "#### What's happening",
    "Alerty dla Twojego portfela": "Alerts for your portfolio",
    "wczoraj": "yesterday",
    "{n} dni temu": "{n} days ago",
    "Usuń portfel": "Delete portfolio",
    "Usuwa wczytane konta z tej przeglądarki. Tej operacji nie można cofnąć.":
        "Removes the imported accounts from this browser. This cannot be undone.",
    "Tak, usuń": "Yes, delete",
    "Stan pozycji z raportu XTB z {d}; kursy z Yahoo Finance (opóźnione do 15 min).":
        "Positions as of the XTB report from {d}; prices from Yahoo Finance (up to 15 min delayed).",
    "Brak otwartych pozycji na wybranym koncie.": "No open positions in the selected account.",
    "IKE": "IKE",
    "IKZE": "IKZE",
    # wykresy w czasie (2026-11-20)
    "#### Wartość i wpłaty": "#### Value and deposits",
    "Pobieram historię kursów…": "Loading price history…",
    "Nie udało się pobrać historii kursów — spróbuj ponownie za chwilę.":
        "Could not load price history — please try again in a moment.",
    "Brak operacji na wybranym koncie.": "No transactions in the selected account.",
    "Eksport nie obejmuje całej historii konta — w XTB wybierz zakres dat od początku konta. Wykres może być niedokładny.":
        "The export does not cover the full account history — in XTB pick a date range from the account opening. The chart may be inaccurate.",
    "#### Porównanie z indeksami": "#### Comparison with indices",
    "Twój portfel vs WIG20, mWIG40, S&P 500 i Nasdaq 100": "Your portfolio vs WIG20, mWIG40, S&P 500 and Nasdaq 100",
    "Ile byś miał, gdyby każda Twoja wpłata trafiła tego samego dnia do indeksu.":
        "How much you would have if every deposit had gone into the index on the same day.",
    "Co gdyby: każda wpłata (i wypłata) tego samego dnia kupuje fundusz indeksowy z reinwestycją dywidend — WIG20: ETFBW20TR, mWIG40: ETFBM40TR, S&P 500: SPY, Nasdaq 100: QQQ (w zł).":
        "What if: every deposit (and withdrawal) buys a dividend-reinvesting index fund on the same day — WIG20: ETFBW20TR, mWIG40: ETFBM40TR, S&P 500: SPY, Nasdaq 100: QQQ (in PLN).",
    "Wartość portfela": "Portfolio value",
    "Twój portfel": "Your portfolio",
    # alerty fundamentalne — moduł 2 (2026-11-20)
    "Wyniki lepsze/gorsze od oczekiwań, zmiany rekomendacji analityków, transakcje insiderów i najbliższe raporty — a wkrótce przełamania poziomów technicznych i newsy.":
        "Earnings beats/misses, analyst rating changes, insider transactions and upcoming reports — soon also technical breakouts and news.",
    "Brak spółek w portfelu — alerty dotyczą akcji, nie ETF-ów.": "No stocks in the portfolio — alerts cover stocks, not ETFs.",
    "Sprawdzam wyniki, analityków i insiderów…": "Checking earnings, analysts and insiders…",
    "Brak zdarzeń dla spółek z portfela w ostatnich 30 dniach.": "No events for your stocks in the last 30 days.",
    "Ostatnie 30 dni · wyniki: beat/miss przy niespodziance EPS ≥ 2% · insiderzy: zakupy i sprzedaże ≥ 1 mln USD osobno · dane Yahoo Finance, dla GPW zwykle niedostępne.":
        "Last 30 days · earnings: beat/miss at EPS surprise ≥ 2% · insiders: purchases and sales ≥ USD 1M listed separately · Yahoo Finance data, usually unavailable for WSE stocks.",
    "wynik {q}: EPS {s} vs konsensus": "{q} results: EPS {s} vs consensus",
    "raport kwartalny {d} ({when})": "quarterly report {d} ({when})",
    "{firm}: {frm} → {to}": "{firm}: {frm} → {to}",
    "{firm} rozpoczyna: {to}": "{firm} initiates: {to}",
    "ceny docelowe: {up}↑ {down}↓ (30 dni)": "price targets: {up}↑ {down}↓ (30 days)",
    "zakup akcji przez insidera: {who}": "insider purchase: {who}",
    "sprzedaż akcji przez insidera: {who}": "insider sale: {who}",
    "{n} mniejszych sprzedaży insiderów (30 dni)": "{n} smaller insider sales (30 days)",
    "brak danych Yahoo: {tickers}": "no Yahoo data: {tickers}",
    # diagnostyka zrodel (2026-11-20, blokady Yahoo na Streamlit Cloud)
    "Yahoo nie zwrócił danych: {tickers} — spróbuj ponownie za kilka minut":
        "Yahoo returned no data: {tickers} — please try again in a few minutes",
    "Źródła danych": "Data sources",
    "Spółka": "Stock",
    "Analitycy": "Analysts",
    "Insiderzy": "Insiders",
    "✅ dane pobrane · ❌ Yahoo nie zwrócił danych (bywa chwilowo blokowany — przy kolejnym otwarciu strona spróbuje ponownie) · — źródło niedostępne dla GPW.":
        "✅ data loaded · ❌ Yahoo returned no data (it is sometimes blocked temporarily — the page will retry next time) · — source unavailable for WSE stocks.",
}
