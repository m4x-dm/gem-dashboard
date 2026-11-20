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
    "Najbliższe raporty kwartalne, a wkrótce: wyniki lepsze/gorsze od oczekiwań, "
    "transakcje insiderów, przełamania poziomów technicznych i newsy.":
        "Upcoming quarterly reports and soon: earnings beats/misses, insider transactions, "
        "technical level breaks and news.",
    "Brak raportów kwartalnych spółek z portfela w ciągu ±14 dni.":
        "No quarterly reports for portfolio companies within ±14 days.",
    "wczoraj": "yesterday",
    "{n} dni temu": "{n} days ago",
    "raport kwartalny": "quarterly report",
    "Usuń portfel": "Delete portfolio",
    "Usuwa wczytane konta z tej przeglądarki. Tej operacji nie można cofnąć.":
        "Removes the imported accounts from this browser. This cannot be undone.",
    "Tak, usuń": "Yes, delete",
    "Stan pozycji z raportu XTB z {d}; kursy z Yahoo Finance (opóźnione do 15 min).":
        "Positions as of the XTB report from {d}; prices from Yahoo Finance (up to 15 min delayed).",
    "Brak otwartych pozycji na wybranym koncie.": "No open positions in the selected account.",
    "IKE": "IKE",
    "IKZE": "IKZE",
}
