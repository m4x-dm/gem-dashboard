"""Katalog EN — strony Premium, czesc 5: teksty dynamiczne (wartosci slownikow, opcje,
etykiety kart i naglowki tabel tlumaczone przy wyswietlaniu)."""

DYNAMIC: dict[str, str] = {
    # Opcje okresow (components/constants.py i lokalne mapy okresow)
    "Strategia 12-1": "12-1 strategy",
    "1 miesiac": "1 month", "2 miesiace": "2 months", "3 miesiace": "3 months", "6 miesiecy": "6 months",
    "1 rok": "1 year", "2 lata": "2 years", "3 lata": "3 years", "5 lat": "5 years", "7 lat": "7 years",
    "10 lat": "10 years", "15 lat": "15 years", "20 lat": "20 years", "Maksymalny": "Max",
    # Backtest
    "GEM Klasyczny": "Classic GEM",
    "QQQ + SMA 200": "QQQ + SMA 200",
    "TQQQ + Momentum": "TQQQ + Momentum",
    "Porownanie wszystkich": "Compare all",
    "Walk-forward GEM": "Walk-forward GEM",
    "Historia zmian sygnalu": "Signal change history",
    "Historia zmian sygnalu GEM": "GEM signal change history",
    "Historia zmian sygnalu SMA 200": "SMA 200 signal change history",
    "Historia zmian sygnalu TQQQ+Momentum": "TQQQ+Momentum signal change history",
    "🟢 Akcje USA": "🟢 US stocks", "🔵 Akcje miedzynar.": "🔵 International stocks",
    "🟣 Rynki wsch.": "🟣 Emerging mkts", "🌐 Akcje globalne": "🌐 Global stocks", "🟡 Obligacje": "🟡 Bonds",
    "🟢 QQQ (cena > SMA200)": "🟢 QQQ (price > SMA200)", "🟡 AGG (cena < SMA200)": "🟡 AGG (price < SMA200)",
    "🟢 TQQQ (momentum > rf)": "🟢 TQQQ (momentum > rf)", "🟡 AGG (momentum < rf)": "🟡 AGG (momentum < rf)",
    "Opis": "Description",
    "IS od": "IS from", "IS do": "IS to", "OOS od": "OOS from", "OOS do": "OOS to",
    "zysku": "gain", "straty": "loss",
    # Wykresy (components/charts.py)
    "Drawdown (spadek od szczytu)": "Drawdown (decline from peak)",
    "Sezonowosc — miesięczne zwroty (%)": "Seasonality — monthly returns (%)",
    "Stopy zwrotu w latach kalendarzowych (%)": "Calendar-year returns (%)",
    "Wzrost kapitalu w skali log. Odcinek z proxy (do proxy_end wlacznie) linia przerywana.":
        "Capital growth on a log scale. The proxy segment (up to proxy_end inclusive) is dashed.",
    "Wzrost {v} {currency}": "Growth of {v} {currency}",
    "Kroczacy CAGR — okno {years} lat (%)": "Rolling CAGR — {years}-year window (%)",
    "okno do": "window ending",
    "rocznie": "a year",
    "Spadek (dni)": "Decline (days)",
    "Srednia (%)": "Mean (%)",
    "Zwrot": "Return",
    "Wartosc": "Value",
    "Okres": "Period",
    "Mom 3M": "Mom 3M",
    # Stopy zwrotu — tabele
    "Dane od": "Data from", "Najlepszy rok": "Best year", "Najgorszy rok": "Worst year",
    "Lata na plusie": "Positive years", "Liczba lat": "Number of years", "Liczba okien": "Number of windows",
    "Od": "From", "Do": "To", "Od startu": "Since inception",
    "Max drawdown liczony z zamkniec miesiecznych — glebokosc spadkow wewnatrz miesiaca jest wieksza. "
    "Linia przerywana = odcinek z funduszu proxy. Sharpe/Sortino ze stopa wolna USD (biezaca) {rf}%":
        "Max drawdown is calculated from monthly closes — intra-month declines are deeper. "
        "Dashed line = the proxy fund segment. Sharpe/Sortino use the current USD risk-free rate of {rf}%",
    "; w trybie PLN Sharpe/Sortino tylko orientacyjnie.": "; in PLN mode Sharpe/Sortino are only indicative.",
    # Porownaj
    "Nieaktualne dane indeksow: {v}. Porownanie moze wprowadzac w blad.": "Stale index data: {v}. The comparison may be misleading.",
    "Cena znormalizowana (baza = 100)": "Normalised price (base = 100)",
    # Intermarket
    "Zloto": "Gold", "Dolar (DXY)": "Dollar (DXY)", "Ropa WTI": "WTI crude", "Obligacje USA (10Y yield)": "US Treasuries (10Y yield)",
    "Srodowisko sprzyjajace akcjom. Momentum pozytywny, apetyt na ryzyko.":
        "An environment favourable to stocks. Positive momentum, appetite for risk.",
    "Srodowisko awersji do ryzyka. Rozwazyc obligacje lub zloto.": "A risk-averse environment. Consider bonds or gold.",
    "Mieszane sygnaly. Brak wyraznego kierunku miedzy klasami aktywow.": "Mixed signals. No clear direction across asset classes.",
    "Srednia:": "Average:",
    # Makro
    "Brak danych": "No data", "Ekstremum": "Extreme", "Powyzej 200MA": "Above 200MA", "Ponizej 200MA": "Below 200MA",
    "Inwersja": "Inverted", "Plaszczenie": "Flattening", "Normalna": "Normal",
    "Silny dolar": "Strong dollar", "Slaby dolar": "Weak dollar",
    "Silny trend": "Strong trend", "Wzrostowy": "Rising", "Spadkowy": "Falling",
    "Wysoka cena": "High price", "Umiarkowana": "Moderate", "Niska cena": "Low price",
    "pkt": "pts",
    # Monte Carlo / Portfolio Builder
    "Zysk > 0%": "Gain > 0%", "Podwojenie kapitalu": "Capital doubles", "Potrojenie kapitalu": "Capital triples",
    "Calkowity zwrot": "Total return", "Portfel custom": "Custom portfolio", "Portfel": "Portfolio",
    "Alokacja portfela": "Portfolio allocation", "Krzywa kapitalu — portfel vs equal-weight": "Equity curve — portfolio vs equal-weight",
    "Drawdown — spadek od szczytu": "Drawdown — decline from peak",
    # Krypto TA — szczegoly wskaznikow
    "(brak danych EMA200)": "(no EMA200 data)", "(cross+ hist rosnacy)": "(cross+ hist rising)",
    "(cross- hist malejacy)": "(cross- hist falling)", "(brak potwierdzenia)": "(no confirmation)",
    "({v}, rosnacy)": "({v}, rising)", "({v}, malejacy)": "({v}, falling)", "({v}, brak potw.)": "({v}, no conf.)",
    # GPW / S&P / Insiderzy / Kalendarz / GEM Extended
    "Net Buyers 🟢": "Net buyers 🟢", "Net Sellers 🔴": "Net sellers 🔴", "Mixed 🟡": "Mixed 🟡",
    "Brak": "None",
    "Future": "Upcoming", "Past": "Past",
    "0 (no skip — default dla ETF)": "0 (no skip — default for ETFs)",
    "21 (skip-month — klasyczny Jegadeesh)": "21 (skip-month — classic Jegadeesh)",
    # GEM Gold Momentum
    "🇺🇸 Nasdaq-100 (QQQ)": "🇺🇸 Nasdaq-100 (QQQ)", "🌍 Rozwiniete ex-US (EFA)": "🌍 Developed ex-US (EFA)",
    "🌏 Wschodzace (EEM)": "🌏 Emerging (EEM)", "🥇 Zloto (GLD)": "🥇 Gold (GLD)", "🥇 Zloto (IAU)": "🥇 Gold (IAU)",
    "💵 Bony 3M": "💵 3M T-bills", "📜 Obligacje 7-10Y (IEF)": "📜 7-10Y Treasuries (IEF)",
    "Akcje": "Stocks",
    "Galaz": "Branch", "Aktywo do trzymania": "Asset to hold", "Ostatni sygnal miesieczny": "Last monthly signal",
    "najwyzsze momentum: {us} / zloto / bony 3M": "highest momentum: {us} / gold / 3M T-bills",
    "od {date} (decyzja na koniec miesiaca)": "since {date} (decided at month end)",
    "Krok 1 — momentum absolutne (wybor galezi)": "Step 1 — absolute momentum (choosing the branch)",
    "Krok 2 — najlepszy indeks akcji": "Step 2 — the best equity index",
    "Krok 2 — bony 3M czy obligacje 7-10Y": "Step 2 — 3M T-bills or 7-10Y Treasuries",
    "Pozostale aktywa (dla kontekstu)": "Other assets (for context)",
    "Korelacja miesiecznych zwrotow": "Correlation of monthly returns",
    "Portfel 50/50 obu strategii": "50/50 portfolio of both strategies",
    "(bez rebalansu)": "(no rebalancing)",
    "pierwszy i ostatni rok niepelne": "first and last years are partial",
    "jeszcze nie": "not yet",
    "Zwrot segmentu": "Segment return",
    "Sredni czas trzymania": "Average holding period",
    # Top Picks
    "Momentum": "Momentum", "Earnings Momentum": "Earnings momentum", "Jakosc biznesu": "Business quality",
    "Polecane przez analitykow": "Analyst favourites", "Potencjal do ceny docelowej": "Upside to target price",
    "Ranking po momentum cenowym (12M/6M/3M/1M z anti-1M), maks. 2 spolki na sektor, prog plynnosci.":
        "Ranked by price momentum (12M/6M/3M/1M with anti-1M), max. 2 stocks per sector, liquidity threshold.",
    "Ranking po jakosci wynikow: seria pobic konsensusu (0-4 kwartaly), wielkosc zaskoczenia EPS i rewizje prognoz analitykow w oknie 90 dni.":
        "Ranked by earnings quality: consensus beat streak (0-4 quarters), size of the EPS surprise and analyst estimate revisions over 90 days.",
    "Ranking po ROE, marzy netto, wzroscie przychodow i niskim zadluzeniu. Dla bankow komponent zadluzenia jest pomijany, a wagi renormalizowane.":
        "Ranked by ROE, net margin, revenue growth and low debt. For banks the debt component is skipped and the weights rescaled.",
    "5 spolek z najlepsza srednia rekomendacja analitykow (skala Yahoo: 1 = Strong Buy, 5 = Strong Sell). Min. 5 analitykow dla S&P 500 i 3 dla GPW, "
    "przy remisie wygrywa spolka z wieksza liczba analitykow; maks. 2 na sektor.":
        "The 5 stocks with the best mean analyst recommendation (Yahoo scale: 1 = Strong Buy, 5 = Strong Sell). Min. 5 analysts for the S&P 500 and 3 "
        "for Warsaw; ties go to the stock with more analysts; max. 2 per sector.",
    "5 spolek z najwiekszym potencjalem do sredniej ceny docelowej analitykow — tylko sposrod tych, ktore analitycy polecaja kupic "
    "(konsensus co najmniej Buy). Progi analitykow jak w strategii Polecane; maks. 2 na sektor.":
        "The 5 stocks with the largest upside to the mean analyst target price — only among those analysts recommend buying "
        "(consensus of at least Buy). Analyst thresholds as in the Analyst favourites strategy; max. 2 per sector.",
    "Skład na": "Picks as of", "{n} spolek": "{n} stocks", "regula": "rule", "nastepny rebalans": "next rebalance",
    "rynki": "markets", "rynek": "market",
    "konsensus {v}": "consensus {v}", "potencjal {v}": "upside {v}",
    "{market}: tylko {n} spolek spelnia warunki (min. liczba analitykow": "{market}: only {n} stocks meet the criteria (min. number of analysts",
    ", konsensus co najmniej Buy": ", consensus of at least Buy",
    ") — piatka nie jest dobierana na sile.": ") — the five is not filled up artificially.",
    "policzone na zamkniecie {date}": "calculated at the close on {date}",
    "Wejscie ({currency})": "Entry ({currency})",
    "Nazwa": "Name", "Score": "Score", "Teraz": "Now",
    "Dyw. %": "Div. %", "Marza %": "Margin %", "Wzrost przych. %": "Rev. growth %", "Debt/Eq": "Debt/Eq",
    "Konsensus": "Consensus", "Cena docelowa": "Target price", "Potencjal %": "Upside %", "Potencjal": "Upside",
    "Zwrot od startu": "Return since start", "kapital 10 000 {currency}": "capital 10,000 {currency}",
    "brak danych benchmarku": "no benchmark data", "{v} p.p.": "{v} pp",
    "Rebalansow": "Rebalances", "snapshotow w logu": "snapshots in the log", "start 10 000 {currency}": "start 10,000 {currency}",
    "symulacja — survivorship bias": "simulation — survivorship bias", "Regula {label}": "Rule {label}",
    "srednioroczny zwrot": "annualised return", "najglebszy spadek": "deepest decline", "zwrot / zmiennosc": "return / volatility",
    "Trafnosc vs benchmark": "Hit rate vs benchmark", "% miesiecy lepszych": "% of months better", "brak benchmarku": "no benchmark",
    "🇺🇸 S&P 500": "🇺🇸 S&P 500", "🇵🇱 GPW": "🇵🇱 Warsaw (GPW)",
    # Krypto — kategorie
    "Layer 2 / Skalowanie": "Layer 2 / Scaling", "Memecoiny": "Memecoins", "Prywatnosc": "Privacy",
    "Infrastruktura / Narzedzia": "Infrastructure / Tools", "RWA / Tokenizacja": "RWA / Tokenisation", "Inne": "Other",
    # Raport PDF (components/pdf_report.py)
    "GEM ETF Dashboard — Raport": "GEM ETF Dashboard — Report",
    "Wygenerowano: {now}": "Generated: {now}",
    "Aktualny sygnal: {signal}": "Current signal: {signal}",
    "Zwrot 12M": "12M return",
    "Forward konsensus EPS": "Forward EPS consensus",
    "Statystyki strategii (5 lat)": "Strategy statistics (5 years)",
    "VEA (Rozwin.)": "VEA (Developed)",
    "EEM (Wsch.)": "EEM (Emerging)",
    "AGG (Obligacje)": "AGG (Bonds)",
    "Top 5 ETF-ow wg momentum": "Top 5 ETFs by momentum",
    "Aktywo": "Asset",
    "Zmiana 1M": "1M change",
    "Ranking ETF — Top 10": "ETF ranking — Top 10",
    "Makro Dashboard": "Macro dashboard",
    "Wskaznik": "Indicator",
    "Dashboard ma charakter edukacyjny i informacyjny. Nie stanowi porady inwestycyjnej. "
    "Wyniki historyczne nie gwarantuja przyszlych zwrotow.":
        "This dashboard is for educational and informational purposes only. It is not investment advice. "
        "Past performance does not guarantee future returns.",
    # Kalendarz wynikow — mapa, sortowanie, statusy
    "Pon": "Mon", "Wt": "Tue", "Sr": "Wed", "Cz": "Thu", "Pt": "Fri",
    "Data (najblizej dzis)": "Date (closest to today)", "Data (chronologicznie)": "Date (chronological)",
    "EPS surprise % (past)": "EPS surprise % (past)", "Ticker A-Z": "Ticker A-Z",
    "🔥 DZIŚ": "🔥 TODAY", "🔜 W {n}d": "🔜 In {n}d", "⏰ W {n}d": "⏰ In {n}d",
    "✅ Beat ({n}d temu)": "✅ Beat ({n}d ago)", "❌ Miss ({n}d temu)": "❌ Miss ({n}d ago)", "⚪ {n}d temu": "⚪ {n}d ago",
    # Waluta
    "1M Roznica": "1M difference", "3M Roznica": "3M difference", "6M Roznica": "6M difference", "12M Roznica": "12M difference",
}

PREMIUM5: dict[str, str] = {**DYNAMIC}
