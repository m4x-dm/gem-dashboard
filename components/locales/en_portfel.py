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
    "Portfel wczytany — szczegóły w kolejnym kroku.": "Portfolio loaded — details in the next step.",
    "IKE": "IKE",
    "IKZE": "IKZE",
}
