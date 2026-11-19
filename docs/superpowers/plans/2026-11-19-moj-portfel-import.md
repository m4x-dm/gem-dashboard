# Mój portfel — moduł 1 (import XTB) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nowa darmowa strona „Mój portfel”: wczytanie eksportu XLSX z XTB (konta zwykłe/IKE/IKZE), pozycje wycenione kursami z Yahoo, kafelki, struktura i panel „Co się dzieje” (Premium: najbliższe raporty kwartalne).

**Architecture:** Trzy czyste moduły bez Streamlita w `data/portfolio/` (parser XLSX → `XtbAccount`, mapowanie tickerów XTB→Yahoo, wycena), zapis w localStorage w `components/portfolio_storage.py` i widok `views/portfel/moj_portfel.py` zarejestrowany w `components/nav.py`. Pozycje pochodzą z arkusza *Open Positions*; ceny z jednego `yf.download` z timeoutem, z fallbackiem na kurs z pliku.

**Tech Stack:** Python 3.11 (venv repo), Streamlit ≥1.55, pandas, openpyxl (nowa zależność), yfinance, streamlit-local-storage, pytest + `streamlit.testing.v1.AppTest`.

**Spec:** `docs/superpowers/specs/2026-11-19-moj-portfel-import-design.md`

---

## Ważne dla wykonawcy (przeczytaj przed Task 1)

- Repo: `C:\Users\m4x\Desktop\AI\gem-dashboard`, gałąź `moj-portfel`. Wszystkie komendy uruchamiaj z katalogu repo. Python: `venv/Scripts/python.exe`.
- **Nie commituj** `ok*adka.png`, `screen2.png`, `screen3.png`, `docs/superpowers/plans/2026-06-02-finanse-kwartalne.md` (nieśledzone pliki użytkownika). Zawsze `git add <konkretne pliki>`, nigdy `git add -A` / `git add .`.
- **Prawdziwy eksport użytkownika** leży w `C:\Users\m4x\Desktop\xtb\11.2026\53853640\`. Nie kopiuj go do repo i nie wklejaj jego liczb do testów ani commitów. Testy używają wyłącznie syntetycznych plików z `tests/xtb_fixtures.py`.
- Odstępstwo od specu (świadome): fikstury XLSX są generowane w pamięci przez `tests/xtb_fixtures.py` (bez binarnych plików w repo).
- Konwencje projektu: teksty UI po polsku opakowane w `tr("...")`; **każdy** literał `tr()` musi mieć wpis w katalogu EN (pilnuje `tests/test_i18n.py`). HTML przez `st.html()`, nie `st.markdown(unsafe_allow_html=True)`. `st.html` wycina `<svg>`. Nie używaj `st.stop()`; na końcu strony zawsze `render_footer()`.
- Commit message: krótki tytuł po angielsku w trybie rozkazującym, na końcu linia `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Format eksportu XTB (zbadany): XLSX z arkuszami `Closed Positions`, `Cash Operations`, `Open Positions`. W `Cash Operations` nagłówek jest w wierszu 5 (`Type, Instrument, Ticker, Category, Time, Amount, ID, Comment, Product, Position ID`). W `Open Positions` wiersz 3 to `Data as of report generated`, nagłówek pozycji w wierszu 9 (`Product, Instrument/Position, Ticker, Category, Type, Volume, Value, Current price, Open price, Open time (UTC), Stop Loss, Take Profit, Net Profit %, Net Profit, Gross Profit, Margin, Open Commission, Swap, Rollover`); pod nim pary „wiersz zbiorczy spółki” (Category wypełnione, Type puste) + „wiersze zakupów” (Type=`BUY`, Category puste, Instrument/Position = ID pozycji). Daty to liczby seryjne Excela (UTC). `Value` i `Gross Profit` są w PLN, ceny w walucie instrumentu.

## Struktura plików

| Plik | Status | Odpowiedzialność |
|---|---|---|
| `requirements.txt` | modyfikacja | + `openpyxl>=3.1` |
| `data/portfolio/__init__.py` | nowy | pusty pakiet |
| `data/portfolio/tickers.py` | nowy | XTB ticker → Yahoo ticker, waluta, dzielnik ceny, ticker kursu walut |
| `data/portfolio/xtb_parser.py` | nowy | `XtbAccount`, `XtbFormatError`, `parse_xtb_xlsx()` |
| `data/portfolio/valuation.py` | nowy | `fetch_live_prices()`, `deposits_net()`, `dividends_net()`, `value_portfolio()` |
| `components/portfolio_storage.py` | nowy | serializacja kont do JSON, zapis/odczyt localStorage |
| `views/portfel/moj_portfel.py` | nowy | strona „Mój portfel” (układ B) |
| `components/nav.py` | modyfikacja | `PageDef("moj-portfel", ...)` na początku sekcji Portfel |
| `components/locales/en_portfel.py` | nowy | tłumaczenia EN tekstów strony |
| `components/locales/en.py` | modyfikacja | `EN.update(PORTFEL)` |
| `tests/xtb_fixtures.py` | nowy | generator syntetycznych XLSX |
| `tests/test_portfolio_tickers.py` | nowy | testy mapowania |
| `tests/test_xtb_parser.py` | nowy | testy parsera |
| `tests/test_portfolio_valuation.py` | nowy | testy wyceny |
| `tests/test_portfolio_storage.py` | nowy | testy zapisu |
| `tests/test_moj_portfel_offline.py` | nowy | AppTest strony (offline) |
| `tests/test_nav.py` | modyfikacja | liczba stron 25→26, `moj-portfel` w darmowych |
| `CLAUDE.md` | modyfikacja | opis strony i pakietu `data/portfolio/` |

---

### Task 1: Zależność openpyxl i generator fikstur

**Files:**
- Modify: `requirements.txt`
- Create: `tests/xtb_fixtures.py`

- [ ] **Step 1: Zainstaluj openpyxl w venv i dopisz do requirements**

Run: `venv/Scripts/python.exe -m pip install "openpyxl>=3.1"`
Expected: `Successfully installed openpyxl-...` (albo „Requirement already satisfied”). Jeśli pip zgłosi `CERTIFICATE_VERIFY_FAILED` (Norton przechwytuje TLS), ustaw przed komendą `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` / `PIP_CERT` na plik łączący `certifi` i `C:\ProgramData\Norton\Antivirus\wscert.pem`.

Dopisz na końcu `requirements.txt` linię:

```
openpyxl>=3.1
```

- [ ] **Step 2: Napisz generator fikstur**

Create `tests/xtb_fixtures.py`:

```python
"""Syntetyczne eksporty XTB (XLSX) do testow — struktura 1:1 z prawdziwym eksportem,
liczby i numery kont zmyslone. Generowane w pamieci, zadnych plikow binarnych w repo."""
from __future__ import annotations

import io

from openpyxl import Workbook

OPEN_HEADER = ["Product", "Instrument/Position", "Ticker", "Category", "Type", "Volume", "Value",
               "Current price", "Open price", "Open time (UTC)", "Stop Loss", "Take Profit",
               "Net Profit %", "Net Profit", "Gross Profit", "Margin", "Open Commission", "Swap",
               "Rollover"]
CASH_HEADER = ["Type", "Instrument", "Ticker", "Category", "Time", "Amount", "ID", "Comment",
               "Product", "Position ID"]
CLOSED_HEADER = ["Instrument", "Ticker", "Category", "Type", "Volume", "Open Price",
                 "Open Time (UTC)", "Close Price", "Close Time (UTC)", "Product", "Profit/Loss"]

REPORT_SERIAL = 46334.5  # 2026-11-08 12:00 UTC


def _agg(product, name, ticker, category, volume, value):
    """Wiersz zbiorczy spolki (Category wypelnione, Type puste)."""
    return [product, name, ticker, category, None, volume, value]


def _lot(product, pos_id, ticker, volume, value, current, open_price, open_serial, gross):
    """Wiersz pojedynczego zakupu (Type=BUY, Category puste)."""
    return [product, pos_id, ticker, None, "BUY", volume, value, current, open_price, open_serial,
            None, None, None, gross, gross]


def _book(account_id: str, main_account_id: str, product: str, open_rows: list, cash_rows: list) -> bytes:
    wb = Workbook()
    closed = wb.active
    closed.title = "Closed Positions"
    closed.append(["Account number", account_id])
    closed.append(["Closed Positions"])
    closed.append(["Date from (UTC)", 38718.0])
    closed.append(["Date to (UTC)", 46334.43])
    closed.append(CLOSED_HEADER)

    cash = wb.create_sheet("Cash Operations")
    cash.append(["Account number", account_id])
    cash.append(["Cash Operations"])
    cash.append(["Date from (UTC)", 38718.0])
    cash.append(["Date to (UTC)", 46334.43])
    cash.append(CASH_HEADER)
    for r in cash_rows:
        cash.append(r)

    op = wb.create_sheet("Open Positions")
    op.append(["Account number", main_account_id])  # XTB wpisuje tu numer konta glownego
    op.append(["Open Positions"])
    op.append(["Data as of report generated", REPORT_SERIAL])
    op.append(["Product", "Metric", "Amount", "Currency"])
    op.append([product, "Open position value", 0.0])
    op.append([product, "Open position profit", 0.0])
    op.append([])
    op.append(["Note", "Summary values and open positions are shown as of the report generation time"])
    op.append(OPEN_HEADER)
    for r in open_rows:
        op.append(r)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_ike_xlsx() -> bytes:
    """Konto IKE 11111111: SNT.PL (2 zakupy), META.US, IS3N.DE (ETF), ABC.XX (nieznana gielda)."""
    p = "IKE"
    open_rows = [
        _agg(p, "Synektik", "SNT.PL", "STOCK", 3, 990.0),
        _lot(p, "1001", "SNT.PL", 2, 660.0, 330.0, 300.0, 46190.5, 60.0),
        _lot(p, "1002", "SNT.PL", 1, 330.0, 330.0, 340.0, 46300.5, -10.0),
        _agg(p, "Meta", "META.US", "STOCK", 0.5, 1200.0),
        _lot(p, "1003", "META.US", 0.5, 1200.0, 600.0, 650.0, 46315.5, -100.0),
        _agg(p, "Core MSCI EM IMI", "IS3N.DE", "ETF", 10, 2001.0),
        _lot(p, "1004", "IS3N.DE", 10, 2001.0, 46.0, 45.0, 46250.5, 43.5),
        _agg(p, "Abc Corp", "ABC.XX", "STOCK", 1, 100.0),
        _lot(p, "1005", "ABC.XX", 1, 100.0, 100.0, 90.0, 46260.5, 10.0),
    ]
    cash_rows = [
        ["IKE deposit", None, None, None, 46300.1, 1000.0, 1, "Transfer in operation", p, None],
        ["IKE deposit", None, None, None, 46310.1, 4000.0, 2, "Transfer in operation", p, None],
        ["Stock purchase", "Meta", "META.US", "STOCK", 46315.5, -1300.0, 3,
         "OPEN BUY META.US 0.5 @ 650.00", p, 1003],
        ["Dividend", "Meta", "META.US", "STOCK", 46320.5, 10.0, 4, "META.US USD 0.5250/ SHR", p, None],
        ["Withholding tax", "Meta", "META.US", "STOCK", 46320.5, -1.5, 5, "META.US USD WHT 15%", p, None],
        ["Free funds interest", None, None, None, 46329.7, 0.12, 6, "Free-funds Interest 2026-10", p, None],
    ]
    return _book("11111111", "99999999", p, open_rows, cash_rows)


def make_zwykle_xlsx() -> bytes:
    """Konto zwykle 22222222 (Product = My Trades): tylko otwarty CFD + wplaty/przelew na IKE."""
    p = "My Trades"
    open_rows = [
        _agg(p, "OIL.WTI", "OIL.WTI", "CFD", 0.01, 350.0),
        _lot(p, "2001", "OIL.WTI", 0.01, 350.0, 88.0, 87.0, 46330.5, 5.0),
    ]
    cash_rows = [
        ["Deposit", None, None, None, 46299.1, 1500.0, 10, "BLIK deposit", p, None],
        ["IKE deposit", None, None, None, 46300.1, -1000.0, 11, "Transfer out operation", p, None],
        ["Withdrawal", None, None, None, 46305.1, -100.0, 12, "Withdrawal to bank", p, None],
    ]
    return _book("22222222", "22222222", p, open_rows, cash_rows)


def make_not_xtb_xlsx() -> bytes:
    """Poprawny XLSX, ale nie eksport XTB."""
    wb = Workbook()
    wb.active.title = "Sheet1"
    wb.active.append(["a", "b"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

- [ ] **Step 3: Sprawdź, że generator działa**

Run: `venv/Scripts/python.exe -c "from tests.xtb_fixtures import make_ike_xlsx, make_zwykle_xlsx, make_not_xtb_xlsx; print(len(make_ike_xlsx()) > 1000, len(make_zwykle_xlsx()) > 1000, len(make_not_xtb_xlsx()) > 500)"`
Expected: `True True True`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt tests/xtb_fixtures.py
git commit -m "Add openpyxl dependency and synthetic XTB export fixtures

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Mapowanie tickerów XTB → Yahoo

**Files:**
- Create: `data/portfolio/__init__.py`, `data/portfolio/tickers.py`
- Test: `tests/test_portfolio_tickers.py`

- [ ] **Step 1: Napisz testy**

Create `tests/test_portfolio_tickers.py`:

```python
import pytest

from data.portfolio.tickers import currency_for, fx_ticker, price_divisor, xtb_to_yahoo


@pytest.mark.parametrize("xtb, yahoo", [
    ("META.US", "META"),
    ("BRK.B.US", "BRK-B"),
    ("SNT.PL", "SNT.WA"),
    ("IS3N.DE", "IS3N.DE"),
    ("ASML.NL", "ASML.AS"),
    ("MC.FR", "MC.PA"),
    ("VOD.UK", "VOD.L"),
    ("ETFBW20TR.PL", "ETFBW20TR.WA"),
])
def test_xtb_to_yahoo(xtb, yahoo):
    assert xtb_to_yahoo(xtb) == yahoo


@pytest.mark.parametrize("xtb", ["ABC.XX", "OIL.WTI", "GOLD", "", "US"])
def test_unknown_suffix_returns_none(xtb):
    assert xtb_to_yahoo(xtb) is None


def test_currency_and_divisor():
    assert currency_for("META.US") == "USD"
    assert currency_for("SNT.PL") == "PLN"
    assert currency_for("IS3N.DE") == "EUR"
    assert currency_for("ASML.NL") == "EUR"
    assert currency_for("VOD.UK") == "GBP"
    assert currency_for("ABC.XX") is None
    assert price_divisor("VOD.UK") == 100.0  # Yahoo notuje LSE w pensach
    assert price_divisor("META.US") == 1.0


def test_fx_ticker():
    assert fx_ticker("PLN") is None
    assert fx_ticker("USD") == "USDPLN=X"
    assert fx_ticker("EUR") == "EURPLN=X"
    assert fx_ticker("GBP") == "GBPPLN=X"
```


- [ ] **Step 2: Uruchom — ma się wywalić**

Run: `venv/Scripts/python.exe -m pytest tests/test_portfolio_tickers.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'data.portfolio'`)

- [ ] **Step 3: Implementacja**

Create `data/portfolio/__init__.py` (pusty plik z docstringiem):

```python
"""Moj portfel — import eksportow brokerow, wycena pozycji."""
```

Create `data/portfolio/tickers.py`:

```python
"""Mapowanie tickerow XTB (np. META.US, SNT.PL) na tickery Yahoo Finance."""
from __future__ import annotations

# przyrostek XTB -> (przyrostek Yahoo, waluta notowan)
_SUFFIX: dict[str, tuple[str, str]] = {
    "US": ("", "USD"),
    "PL": (".WA", "PLN"),
    "DE": (".DE", "EUR"),
    "NL": (".AS", "EUR"),
    "FR": (".PA", "EUR"),
    "UK": (".L", "GBP"),
}


def _split(xtb_ticker: str) -> tuple[str, str] | None:
    base, sep, suffix = (xtb_ticker or "").rpartition(".")
    if not sep or not base or suffix.upper() not in _SUFFIX:
        return None
    return base, suffix.upper()


def xtb_to_yahoo(xtb_ticker: str) -> str | None:
    """META.US -> META, BRK.B.US -> BRK-B, SNT.PL -> SNT.WA; nieznana gielda -> None."""
    parts = _split(xtb_ticker)
    if parts is None:
        return None
    base, suffix = parts
    yahoo_suffix, _ = _SUFFIX[suffix]
    if suffix == "US":
        base = base.replace(".", "-")  # Yahoo: klasy akcji przez myslnik
    return f"{base}{yahoo_suffix}"


def currency_for(xtb_ticker: str) -> str | None:
    parts = _split(xtb_ticker)
    return _SUFFIX[parts[1]][1] if parts else None


def price_divisor(xtb_ticker: str) -> float:
    """Yahoo podaje kursy z LSE w pensach (GBp) — dzielimy przez 100."""
    parts = _split(xtb_ticker)
    return 100.0 if parts and parts[1] == "UK" else 1.0


def fx_ticker(currency: str | None) -> str | None:
    """Ticker Yahoo kursu waluty do PLN (PLN / brak waluty -> None)."""
    if not currency or currency == "PLN":
        return None
    return f"{currency}PLN=X"
```

- [ ] **Step 4: Uruchom testy**

Run: `venv/Scripts/python.exe -m pytest tests/test_portfolio_tickers.py -q`
Expected: wszystkie PASS (16 passed)

- [ ] **Step 5: Commit**

```bash
git add data/portfolio/__init__.py data/portfolio/tickers.py tests/test_portfolio_tickers.py
git commit -m "Add XTB to Yahoo ticker mapping for portfolio import

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Parser XLSX — otwarte pozycje

**Files:**
- Create: `data/portfolio/xtb_parser.py`
- Test: `tests/test_xtb_parser.py`

- [ ] **Step 1: Napisz testy pozycji**

Create `tests/test_xtb_parser.py`:

```python
from datetime import datetime

import pytest

from data.portfolio.xtb_parser import XtbFormatError, parse_xtb_xlsx
from tests.xtb_fixtures import make_ike_xlsx, make_not_xtb_xlsx, make_zwykle_xlsx


def test_ike_lots():
    acc = parse_xtb_xlsx(make_ike_xlsx(), "IKE_11111111_2006-01-01_2026-11-08.xlsx")
    lots = acc.lots
    assert len(lots) == 5
    assert list(lots["xtb_ticker"]) == ["SNT.PL", "SNT.PL", "META.US", "IS3N.DE", "ABC.XX"]
    snt = lots[lots["xtb_ticker"] == "SNT.PL"]
    assert list(snt["name"]) == ["Synektik", "Synektik"]  # nazwa z wiersza zbiorczego
    assert list(snt["category"]) == ["STOCK", "STOCK"]
    assert list(snt["volume"]) == [2.0, 1.0]
    assert list(snt["open_price"]) == [300.0, 340.0]
    assert list(snt["cost_pln"]) == [600.0, 340.0]       # Value - Gross Profit
    assert list(snt["file_price"]) == [330.0, 330.0]
    assert lots.iloc[0]["open_time"] == datetime(2026, 6, 17, 12, 0)
    assert lots[lots["xtb_ticker"] == "IS3N.DE"].iloc[0]["category"] == "ETF"


def test_ike_metadata():
    acc = parse_xtb_xlsx(make_ike_xlsx())
    assert acc.account_id == "11111111"     # z Cash Operations, nie z Open Positions
    assert acc.account_type == "IKE"
    assert acc.report_time == datetime(2026, 11, 8, 12, 0)
    assert acc.skipped_cfd == 0


def test_cfd_skipped_on_regular_account():
    acc = parse_xtb_xlsx(make_zwykle_xlsx())
    assert acc.account_type == "ZWYKLE"
    assert acc.account_id == "22222222"
    assert acc.lots.empty
    assert acc.skipped_cfd == 1


def test_not_xtb_file_raises():
    with pytest.raises(XtbFormatError, match="Open Positions"):
        parse_xtb_xlsx(make_not_xtb_xlsx())


def test_garbage_bytes_raise():
    with pytest.raises(XtbFormatError, match="XLSX"):
        parse_xtb_xlsx(b"to nie jest plik excela")
```

- [ ] **Step 2: Uruchom — ma się wywalić**

Run: `venv/Scripts/python.exe -m pytest tests/test_xtb_parser.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'data.portfolio.xtb_parser'`)

- [ ] **Step 3: Implementacja**

Create `data/portfolio/xtb_parser.py`:

```python
"""Parser eksportu historii konta XTB (xStation -> Historia -> Eksport, plik XLSX).

Jeden plik = jedno konto (zwykle / IKE / IKZE). Pozycje bierzemy z arkusza
'Open Positions' (stan na moment wygenerowania raportu), wplaty i dywidendy
z 'Cash Operations'. Kolumny szukamy po nazwie naglowka, nie po indeksie.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

LOT_COLUMNS = ["xtb_ticker", "name", "category", "volume", "open_price", "open_time",
               "value_pln", "gross_profit_pln", "cost_pln", "file_price"]
CASH_COLUMNS = ["type", "ticker", "time", "amount_pln", "comment"]
_EXCEL_EPOCH = datetime(1899, 12, 30)
_PRODUCT_TO_TYPE = {"IKE": "IKE", "IKZE": "IKZE"}


class XtbFormatError(ValueError):
    """Plik nie wyglada na eksport XTB (komunikat po polsku, do pokazania uzytkownikowi)."""


@dataclass
class XtbAccount:
    account_id: str
    account_type: str            # "IKE" | "IKZE" | "ZWYKLE"
    report_time: datetime | None
    lots: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=LOT_COLUMNS))
    cash_ops: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=CASH_COLUMNS))
    skipped_cfd: int = 0


def excel_to_datetime(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        dt = _EXCEL_EPOCH + timedelta(days=float(value))
    except (TypeError, ValueError):
        return None
    return dt.replace(microsecond=0)


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rows(ws) -> list[tuple]:
    return [tuple(r) for r in ws.iter_rows(values_only=True)]


def _find_header(rows: list[tuple], first_cell: str, sheet: str) -> int:
    for i, r in enumerate(rows):
        if r and r[0] == first_cell:
            return i
    raise XtbFormatError(f"Arkusz '{sheet}' nie ma naglowka zaczynajacego sie od '{first_cell}'.")


def _records(rows: list[tuple], header_idx: int, required: list[str], sheet: str) -> list[dict]:
    header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
    missing = [c for c in required if c not in header]
    if missing:
        raise XtbFormatError(f"Arkusz '{sheet}': brak kolumn {', '.join(missing)}.")
    out = []
    for r in rows[header_idx + 1:]:
        if not r or all(c is None or c == "" for c in r):
            continue
        out.append({h: (r[i] if i < len(r) else None) for i, h in enumerate(header) if h})
    return out


def _account_type(product: str | None) -> str | None:
    if not product:
        return None
    return _PRODUCT_TO_TYPE.get(str(product).strip().upper(), "ZWYKLE")


def _type_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    prefix = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].split("_", 1)[0].upper()
    return {"IKE": "IKE", "IKZE": "IKZE", "PLN": "ZWYKLE"}.get(prefix)


def _parse_open_positions(rows: list[tuple]) -> tuple[pd.DataFrame, int, str | None, datetime | None]:
    report_time = None
    for r in rows[:8]:
        if r and r[0] == "Data as of report generated":
            report_time = excel_to_datetime(r[1] if len(r) > 1 else None)
    hdr = _find_header(rows, "Product", "Open Positions")
    # pierwszy 'Product' to tabela podsumowania (Product, Metric, Amount...) — szukamy tej z 'Ticker'
    while "Ticker" not in rows[hdr]:
        nxt = _find_header(rows[hdr + 1:], "Product", "Open Positions")
        hdr = hdr + 1 + nxt
    recs = _records(rows, hdr, ["Instrument/Position", "Ticker", "Category", "Type", "Volume",
                                "Value", "Current price", "Open price", "Open time (UTC)",
                                "Gross Profit"], "Open Positions")
    lots, skipped, product = [], 0, None
    agg_name, agg_category = None, None
    for rec in recs:
        product = product or rec.get("Product")
        if rec.get("Category") and not rec.get("Type"):     # wiersz zbiorczy spolki
            agg_name, agg_category = rec.get("Instrument/Position"), rec.get("Category")
            continue
        if str(rec.get("Type") or "").upper() != "BUY":
            continue
        category = rec.get("Category") or agg_category
        if str(category or "").upper() == "CFD":
            skipped += 1
            continue
        value = _num(rec.get("Value")) or 0.0
        gross = _num(rec.get("Gross Profit")) or 0.0
        lots.append({
            "xtb_ticker": str(rec.get("Ticker") or "").strip(),
            "name": agg_name or rec.get("Ticker"),
            "category": category,
            "volume": _num(rec.get("Volume")) or 0.0,
            "open_price": _num(rec.get("Open price")),
            "open_time": excel_to_datetime(rec.get("Open time (UTC)")),
            "value_pln": value,
            "gross_profit_pln": gross,
            "cost_pln": value - gross,
            "file_price": _num(rec.get("Current price")),
        })
    return pd.DataFrame(lots, columns=LOT_COLUMNS), skipped, product, report_time


def _parse_cash(rows: list[tuple]) -> tuple[pd.DataFrame, str | None, str | None]:
    account_id = None
    if rows and rows[0] and rows[0][0] == "Account number" and len(rows[0]) > 1:
        raw = rows[0][1]
        account_id = str(int(float(raw))) if _num(raw) is not None else str(raw)
    hdr = _find_header(rows, "Type", "Cash Operations")
    recs = _records(rows, hdr, ["Type", "Ticker", "Time", "Amount", "Comment"], "Cash Operations")
    product = next((r.get("Product") for r in recs if r.get("Product")), None)
    ops = [{
        "type": str(r.get("Type") or "").strip(),
        "ticker": r.get("Ticker"),
        "time": excel_to_datetime(r.get("Time")),
        "amount_pln": _num(r.get("Amount")) or 0.0,
        "comment": r.get("Comment"),
    } for r in recs]
    return pd.DataFrame(ops, columns=CASH_COLUMNS), account_id, product


def parse_xtb_xlsx(data: bytes, filename: str | None = None) -> XtbAccount:
    """Bajty pliku XLSX z XTB -> XtbAccount. XtbFormatError gdy to nie eksport XTB."""
    if filename and filename.lower().endswith(".zip"):
        raise XtbFormatError("To jest archiwum ZIP — rozpakuj je i wczytaj pliki .xlsx ze srodka.")
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except (zipfile.BadZipFile, KeyError, OSError, ValueError) as exc:
        raise XtbFormatError("Nie udalo sie otworzyc pliku — oczekiwany plik XLSX z XTB.") from exc
    for sheet in ("Open Positions", "Cash Operations"):
        if sheet not in wb.sheetnames:
            raise XtbFormatError(f"Brak arkusza '{sheet}' — to nie wyglada na eksport z XTB.")
    lots, skipped, open_product, report_time = _parse_open_positions(_rows(wb["Open Positions"]))
    cash, account_id, cash_product = _parse_cash(_rows(wb["Cash Operations"]))
    wb.close()
    account_type = (_account_type(cash_product) or _account_type(open_product)
                    or _type_from_filename(filename) or "ZWYKLE")
    if not account_id:
        raise XtbFormatError("Brak numeru konta w arkuszu 'Cash Operations'.")
    return XtbAccount(account_id=account_id, account_type=account_type, report_time=report_time,
                      lots=lots, cash_ops=cash, skipped_cfd=skipped)
```

Uwaga do `_parse_open_positions`: pętla `while "Ticker" not in rows[hdr]` przechodzi z tabeli podsumowania (wiersz 4, `Product, Metric, Amount, Currency`) do właściwego nagłówka pozycji (wiersz 9). `_find_header` zwraca indeks względny w wycinku, stąd `hdr + 1 + nxt`.

Daty w testach zweryfikowane: `46190.5` → 2026-06-17 12:00, `46334.5` → 2026-11-08 12:00 (epoka Excela 1899-12-30).

- [ ] **Step 4: Uruchom testy**

Run: `venv/Scripts/python.exe -m pytest tests/test_xtb_parser.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add data/portfolio/xtb_parser.py tests/test_xtb_parser.py
git commit -m "Parse XTB XLSX export: open position lots, account metadata, CFD skip

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Parser — operacje gotówkowe i typ konta z nazwy pliku

**Files:**
- Modify: `tests/test_xtb_parser.py` (dopisz testy)
- (implementacja `_parse_cash` i `_type_from_filename` jest już w Task 3 — ten task ją weryfikuje i domyka przypadki brzegowe)

- [ ] **Step 1: Dopisz testy**

Dopisz na końcu `tests/test_xtb_parser.py`:

```python
from tests.xtb_fixtures import _book  # noqa: E402


def test_cash_operations_parsed():
    acc = parse_xtb_xlsx(make_ike_xlsx())
    ops = acc.cash_ops
    assert len(ops) == 6
    assert list(ops["type"]) == ["IKE deposit", "IKE deposit", "Stock purchase", "Dividend",
                                 "Withholding tax", "Free funds interest"]
    assert ops["amount_pln"].sum() == pytest.approx(1000 + 4000 - 1300 + 10 - 1.5 + 0.12)
    assert ops.iloc[3]["ticker"] == "META.US"
    assert isinstance(ops.iloc[0]["time"], datetime)


def test_regular_account_cash():
    ops = parse_xtb_xlsx(make_zwykle_xlsx()).cash_ops
    assert list(ops["amount_pln"]) == [1500.0, -1000.0, -100.0]


def test_account_type_from_filename_when_no_product():
    """Konto bez operacji i bez pozycji: typ z prefiksu nazwy pliku."""
    data = _book("33333333", "33333333", None, [], [])
    assert parse_xtb_xlsx(data, "IKZE_33333333_2006-01-01_2026-11-08.xlsx").account_type == "IKZE"
    assert parse_xtb_xlsx(data, "PLN_33333333_x.xlsx").account_type == "ZWYKLE"
    assert parse_xtb_xlsx(data, None).account_type == "ZWYKLE"


def test_zip_rejected_with_hint():
    with pytest.raises(XtbFormatError, match="ZIP"):
        parse_xtb_xlsx(b"PK\x03\x04", "53853640_2006-01-01_2026-11-08.zip")


def test_missing_cash_column_raises():
    from openpyxl import Workbook
    import io
    wb = Workbook()
    wb.active.title = "Open Positions"
    wb.active.append(["Product", "Instrument/Position", "Ticker", "Category", "Type", "Volume", "Value",
                      "Current price", "Open price", "Open time (UTC)", "Gross Profit"])
    cash = wb.create_sheet("Cash Operations")
    cash.append(["Account number", "1"])
    cash.append(["Type", "Ticker", "Time"])          # brak Amount i Comment
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(XtbFormatError, match="Amount"):
        parse_xtb_xlsx(buf.getvalue())
```

- [ ] **Step 2: Uruchom testy**

Run: `venv/Scripts/python.exe -m pytest tests/test_xtb_parser.py -q`
Expected: 10 passed. Jeśli `test_account_type_from_filename_when_no_product` nie przechodzi, bo `_book` z `product=None` wpisuje `None` w tabeli podsumowania — to w porządku (wiersze bez Product są ignorowane przez `_account_type`); popraw implementację, nie test.

- [ ] **Step 3: Commit**

```bash
git add tests/test_xtb_parser.py data/portfolio/xtb_parser.py
git commit -m "Cover XTB cash operations, filename account type and format errors

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Wycena — wpłaty, dywidendy, pozycje, podsumowanie

**Files:**
- Create: `data/portfolio/valuation.py`
- Test: `tests/test_portfolio_valuation.py`

- [ ] **Step 1: Napisz testy**

Create `tests/test_portfolio_valuation.py`:

```python
import math

import pandas as pd
import pytest

from data.portfolio.valuation import deposits_net, dividends_net, value_portfolio
from data.portfolio.xtb_parser import parse_xtb_xlsx
from tests.xtb_fixtures import make_ike_xlsx, make_zwykle_xlsx

QUOTES = pd.DataFrame(
    {"last": [335.0, 610.0, 47.0, 4.0, 4.3], "prev": [330.0, 600.0, 46.0, 4.0, 4.3]},
    index=["SNT.WA", "META", "IS3N.DE", "USDPLN=X", "EURPLN=X"],
)


@pytest.fixture
def accounts():
    return [parse_xtb_xlsx(make_ike_xlsx()), parse_xtb_xlsx(make_zwykle_xlsx())]


def test_deposits_net_no_double_counting(accounts):
    ike, zwykle = accounts
    assert deposits_net(ike.cash_ops) == pytest.approx(5000.0)
    assert deposits_net(zwykle.cash_ops) == pytest.approx(400.0)   # 1500 - 1000 przelew na IKE - 100


def test_dividends_net_case_insensitive():
    ops = pd.DataFrame({"type": ["Dividend", "DIVIDENT", "Withholding tax", "Deposit"],
                        "amount_pln": [10.0, 5.0, -2.25, 999.0]})
    assert dividends_net(ops) == pytest.approx(12.75)


def test_positions_live(accounts):
    pos, summary = value_portfolio(accounts, QUOTES)
    by = pos.set_index("xtb_ticker")
    snt = by.loc["SNT.PL"]
    assert snt["volume"] == 3
    assert snt["avg_price"] == pytest.approx((2 * 300 + 340) / 3)
    assert snt["value_pln"] == pytest.approx(1005.0)
    assert snt["cost_pln"] == pytest.approx(940.0)
    assert snt["profit_pln"] == pytest.approx(65.0)
    assert snt["day_pln"] == pytest.approx(15.0)
    assert bool(snt["live"]) is True
    assert snt["yahoo"] == "SNT.WA" and snt["account"] == "IKE"
    meta = by.loc["META.US"]
    assert meta["value_pln"] == pytest.approx(0.5 * 610 * 4.0)
    assert meta["day_pln"] == pytest.approx(0.5 * 10 * 4.0)
    assert by.loc["IS3N.DE"]["value_pln"] == pytest.approx(10 * 47 * 4.3)


def test_unknown_ticker_uses_file_value(accounts):
    pos, _ = value_portfolio(accounts, QUOTES)
    abc = pos.set_index("xtb_ticker").loc["ABC.XX"]
    assert abc["value_pln"] == pytest.approx(100.0)
    assert abc["price"] == pytest.approx(100.0)
    assert bool(abc["live"]) is False
    assert math.isnan(abc["day_pln"])


def test_summary(accounts):
    pos, s = value_portfolio(accounts, QUOTES)
    assert s["value"] == pytest.approx(1005 + 1220 + 2021 + 100)
    assert s["cost"] == pytest.approx(940 + 1300 + 1957.5 + 90)
    assert s["profit"] == pytest.approx(s["value"] - s["cost"])
    assert s["profit_pct"] == pytest.approx(s["profit"] / s["cost"])
    assert s["day"] == pytest.approx(15 + 20 + 43)
    assert s["day_pct"] == pytest.approx(78 / (s["value"] - 78))
    assert s["deposits"] == pytest.approx(5400.0)
    assert s["dividends"] == pytest.approx(8.5)
    assert pos["share"].sum() == pytest.approx(1.0)
    assert list(pos["value_pln"]) == sorted(pos["value_pln"], reverse=True)


def test_account_filter(accounts):
    pos, s = value_portfolio(accounts, QUOTES, account_type="ZWYKLE")
    assert pos.empty
    assert s["value"] == 0.0 and s["deposits"] == pytest.approx(400.0)
    pos, s = value_portfolio(accounts, QUOTES, account_type="IKE")
    assert len(pos) == 4 and s["deposits"] == pytest.approx(5000.0)


def test_no_quotes_falls_back_to_file(accounts):
    pos, s = value_portfolio(accounts, pd.DataFrame(columns=["last", "prev"]))
    assert s["value"] == pytest.approx(990 + 1200 + 2001 + 100)
    assert not pos["live"].any()
    assert s["day"] == 0.0
```

- [ ] **Step 2: Uruchom — ma się wywalić**

Run: `venv/Scripts/python.exe -m pytest tests/test_portfolio_valuation.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'data.portfolio.valuation'`)

- [ ] **Step 3: Implementacja**

Create `data/portfolio/valuation.py`:

```python
"""Wycena portfela: pozycje z eksportu XTB x kursy Yahoo x kursy walut (PLN)."""
from __future__ import annotations

import math

import pandas as pd

from data.portfolio.tickers import currency_for, fx_ticker, price_divisor, xtb_to_yahoo
from data.portfolio.xtb_parser import XtbAccount

DEPOSIT_TYPES = {"deposit", "ike deposit", "ikze deposit", "withdrawal"}
DIVIDEND_TYPES = {"dividend", "divident", "withholding tax"}
POSITION_COLUMNS = ["account", "xtb_ticker", "yahoo", "name", "category", "currency", "volume",
                    "avg_price", "price", "value_pln", "cost_pln", "profit_pln", "profit_pct",
                    "day_pln", "share", "live"]


def _sum_types(cash_ops: pd.DataFrame, types: set[str]) -> float:
    if cash_ops is None or cash_ops.empty:
        return 0.0
    mask = cash_ops["type"].astype(str).str.strip().str.lower().isin(types)
    return float(cash_ops.loc[mask, "amount_pln"].sum())


def deposits_net(cash_ops: pd.DataFrame) -> float:
    """Wplaty - wyplaty. Przelew z konta zwyklego na IKE/IKZE jest ujemny na koncie zwyklym
    i dodatni na IKE/IKZE, wiec suma po wszystkich kontach liczy pieniadze z banku raz."""
    return _sum_types(cash_ops, DEPOSIT_TYPES)


def dividends_net(cash_ops: pd.DataFrame) -> float:
    """Dywidendy po podatku u zrodla."""
    return _sum_types(cash_ops, DIVIDEND_TYPES)


def _quote(quotes: pd.DataFrame, ticker: str | None, col: str) -> float | None:
    if ticker is None or quotes is None or ticker not in quotes.index:
        return None
    v = quotes.at[ticker, col]
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def _fx(quotes: pd.DataFrame, currency: str | None) -> float | None:
    if currency == "PLN":
        return 1.0
    return _quote(quotes, fx_ticker(currency), "last")


def value_portfolio(accounts: list[XtbAccount], quotes: pd.DataFrame,
                    account_type: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Zwraca (tabela pozycji per konto+ticker posortowana malejaco po wartosci, podsumowanie).

    quotes: DataFrame indeksowany tickerem Yahoo, kolumny 'last' i 'prev' (ostatni i
    przedostatni close); zawiera tez kursy walut 'USDPLN=X' itd. Brak tickera -> kurs z pliku.
    account_type: None = wszystkie konta, inaczej 'IKE' / 'IKZE' / 'ZWYKLE'.
    """
    chosen = [a for a in accounts if account_type is None or a.account_type == account_type]
    rows = []
    for acc in chosen:
        if acc.lots.empty:
            continue
        for xtb_ticker, g in acc.lots.groupby("xtb_ticker", sort=False):
            volume = float(g["volume"].sum())
            avg_price = float((g["open_price"] * g["volume"]).sum() / volume) if volume else float("nan")
            cost = float(g["cost_pln"].sum())
            yahoo = xtb_to_yahoo(xtb_ticker)
            currency = currency_for(xtb_ticker) or "PLN"
            div = price_divisor(xtb_ticker)
            last, prev = _quote(quotes, yahoo, "last"), _quote(quotes, yahoo, "prev")
            fx = _fx(quotes, currency)
            if last is not None and fx is not None:
                price = last / div
                value = volume * price * fx
                day = volume * (last - prev) / div * fx if prev is not None else float("nan")
                live = True
            else:
                price = float(g["file_price"].iloc[-1]) if g["file_price"].notna().any() else float("nan")
                value = float(g["value_pln"].sum())
                day = float("nan")
                live = False
            profit = value - cost
            rows.append({
                "account": acc.account_type, "xtb_ticker": xtb_ticker, "yahoo": yahoo,
                "name": g["name"].iloc[0], "category": g["category"].iloc[0], "currency": currency,
                "volume": volume, "avg_price": avg_price, "price": price, "value_pln": value,
                "cost_pln": cost, "profit_pln": profit,
                "profit_pct": profit / cost if cost > 0 else float("nan"),
                "day_pln": day, "share": 0.0, "live": live,
            })
    pos = pd.DataFrame(rows, columns=POSITION_COLUMNS)
    total = float(pos["value_pln"].sum()) if not pos.empty else 0.0
    if total > 0:
        pos["share"] = pos["value_pln"] / total
    pos = pos.sort_values("value_pln", ascending=False, ignore_index=True)

    cost = float(pos["cost_pln"].sum()) if not pos.empty else 0.0
    day = float(pos["day_pln"].fillna(0.0).sum()) if not pos.empty else 0.0
    reports = [a.report_time for a in chosen if a.report_time is not None]
    summary = {
        "value": total,
        "cost": cost,
        "profit": total - cost,
        "profit_pct": (total - cost) / cost if cost > 0 else float("nan"),
        "day": day,
        "day_pct": day / (total - day) if total - day > 0 else float("nan"),
        "deposits": sum(deposits_net(a.cash_ops) for a in chosen),
        "dividends": sum(dividends_net(a.cash_ops) for a in chosen),
        "report_time": min(reports) if reports else None,
    }
    return pos, summary
```

- [ ] **Step 4: Uruchom testy**

Run: `venv/Scripts/python.exe -m pytest tests/test_portfolio_valuation.py -q`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add data/portfolio/valuation.py tests/test_portfolio_valuation.py
git commit -m "Value portfolio positions with live quotes, FX and file-price fallback

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Kursy na żywo — jedno `yf.download`

**Files:**
- Modify: `data/portfolio/valuation.py` (dopisz `fetch_live_prices`)
- Modify: `tests/test_portfolio_valuation.py` (dopisz testy)

- [ ] **Step 1: Dopisz testy**

Dopisz na końcu `tests/test_portfolio_valuation.py`:

```python
import numpy as np  # noqa: E402

from data.portfolio import valuation  # noqa: E402


def _fake_download(tickers, **kwargs):
    names = tickers.split()
    idx = pd.bdate_range("2026-11-03", periods=4)
    close = pd.DataFrame({t: [10.0, 11.0, 12.0, 13.0] for t in names}, index=idx)
    if "GONE" in close:
        close["GONE"] = np.nan
    if "LATE" in close:
        close.loc[idx[-1], "LATE"] = np.nan   # brak ostatniej sesji -> bierzemy ostatnie dostepne
    if len(names) == 1:
        return pd.concat({"Close": close}, axis=1).droplevel(1, axis=1)
    return pd.concat({"Close": close}, axis=1)


def test_fetch_live_prices(monkeypatch):
    import yfinance as yf
    calls = []
    monkeypatch.setattr(yf, "download", lambda t, **k: calls.append(k) or _fake_download(t, **k))
    q = valuation.fetch_live_prices(("META", "GONE", "LATE"))
    assert len(calls) == 1 and calls[0]["timeout"] == 20 and calls[0]["progress"] is False
    assert q.loc["META", "last"] == 13.0 and q.loc["META", "prev"] == 12.0
    assert q.loc["LATE", "last"] == 12.0 and q.loc["LATE", "prev"] == 11.0
    assert "GONE" not in q.index


def test_fetch_live_prices_single_ticker(monkeypatch):
    import yfinance as yf
    monkeypatch.setattr(yf, "download", lambda t, **k: _fake_download(t, **k))
    q = valuation.fetch_live_prices(("META",))
    assert q.loc["META", "last"] == 13.0


def test_fetch_live_prices_failure_returns_empty(monkeypatch):
    import yfinance as yf

    def boom(*a, **k):
        raise RuntimeError("Yahoo down")
    monkeypatch.setattr(yf, "download", boom)
    assert valuation.fetch_live_prices(("META",)).empty
    assert valuation.fetch_live_prices(()).empty
```

- [ ] **Step 2: Uruchom — ma się wywalić**

Run: `venv/Scripts/python.exe -m pytest tests/test_portfolio_valuation.py -q -k fetch`
Expected: FAIL (`AttributeError: module 'data.portfolio.valuation' has no attribute 'fetch_live_prices'`)

- [ ] **Step 3: Implementacja**

Dopisz do `data/portfolio/valuation.py` (pod importami, przed `value_portfolio`):

```python
def fetch_live_prices(tickers: tuple[str, ...]) -> pd.DataFrame:
    """Ostatni i przedostatni close dla tickerow Yahoo (akcje + kursy walut).

    Celowo JEDNO yf.download z timeoutem, bez download_prices(): fallback per ticker
    (retry + stooq) trwal >5 min przy throttlingu Yahoo (lekcja z Pulpitu, 2026-11-15).
    Brak tickera w wyniku -> wycena kursem z pliku. Blad sieci -> pusty DataFrame.
    """
    empty = pd.DataFrame(columns=["last", "prev"])
    if not tickers:
        return empty
    try:
        import yfinance as yf
        data = yf.download(" ".join(tickers), period="5d", auto_adjust=True,
                           progress=False, threads=True, timeout=20)
    except Exception:
        return empty
    if data is None or data.empty or "Close" not in data.columns.get_level_values(0):
        return empty
    close = data["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    out = {}
    for t in close.columns:
        s = close[t].dropna()
        if s.empty:
            continue
        out[t] = {"last": float(s.iloc[-1]), "prev": float(s.iloc[-2]) if len(s) > 1 else float(s.iloc[-1])}
    return pd.DataFrame.from_dict(out, orient="index", columns=["last", "prev"]) if out else empty
```

- [ ] **Step 4: Uruchom testy**

Run: `venv/Scripts/python.exe -m pytest tests/test_portfolio_valuation.py -q`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add data/portfolio/valuation.py tests/test_portfolio_valuation.py
git commit -m "Fetch portfolio quotes with a single bounded yf.download

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Zapis portfela w localStorage

**Files:**
- Create: `components/portfolio_storage.py`
- Test: `tests/test_portfolio_storage.py`

- [ ] **Step 1: Napisz testy**

Create `tests/test_portfolio_storage.py`:

```python
import json
from datetime import datetime, timedelta

import pandas as pd
import pytest

from components import portfolio_storage as ps
from data.portfolio.xtb_parser import parse_xtb_xlsx
from tests.xtb_fixtures import make_ike_xlsx, make_zwykle_xlsx


class DictLS:
    """Atrapa streamlit_local_storage.LocalStorage (getItem/setItem)."""

    def __init__(self, items=None):
        self.items = dict(items or {})

    def getItem(self, itemKey):
        return self.items.get(itemKey)

    def setItem(self, itemKey=None, itemValue=None, key=None):
        self.items[itemKey] = itemValue


def test_roundtrip():
    ls = DictLS()
    ike = parse_xtb_xlsx(make_ike_xlsx())
    zw = parse_xtb_xlsx(make_zwykle_xlsx())
    accounts = {ike.account_id: ike, zw.account_id: zw}
    assert ps.save_portfolio(ls, accounts) is False          # nie przycinano
    loaded, corrupt = ps.load_portfolio(ls)
    assert corrupt is False
    assert set(loaded) == {"11111111", "22222222"}
    a = loaded["11111111"]
    assert a.account_type == "IKE" and a.report_time == ike.report_time and a.skipped_cfd == 0
    pd.testing.assert_frame_equal(a.lots, ike.lots, check_dtype=False)
    pd.testing.assert_frame_equal(a.cash_ops, ike.cash_ops, check_dtype=False)
    assert loaded["22222222"].lots.empty and loaded["22222222"].skipped_cfd == 1


def test_stored_json_shape():
    ls = DictLS()
    ike = parse_xtb_xlsx(make_ike_xlsx())
    ps.save_portfolio(ls, {ike.account_id: ike})
    data = json.loads(ls.items[ps.PORTFOLIO_KEY])
    assert data["v"] == 1 and list(data["accounts"]) == ["11111111"]


def test_empty_and_corrupt():
    assert ps.load_portfolio(DictLS()) == ({}, False)
    assert ps.load_portfolio(DictLS({ps.PORTFOLIO_KEY: "{nie json"})) == ({}, True)
    assert ps.load_portfolio(DictLS({ps.PORTFOLIO_KEY: json.dumps({"v": 99})})) == ({}, True)


def test_clear():
    ls = DictLS()
    ike = parse_xtb_xlsx(make_ike_xlsx())
    ps.save_portfolio(ls, {ike.account_id: ike})
    ps.clear_portfolio(ls)
    assert ps.load_portfolio(ls) == ({}, False)


def test_large_cash_history_trimmed(monkeypatch):
    monkeypatch.setattr(ps, "MAX_BYTES", 2000)
    ike = parse_xtb_xlsx(make_ike_xlsx())
    old = datetime(2015, 1, 1)
    ike.cash_ops = pd.DataFrame([{"type": "Deposit", "ticker": None, "time": old + timedelta(days=i),
                                  "amount_pln": 1.0, "comment": "x" * 50} for i in range(200)]
                                + ike.cash_ops.to_dict("records"))
    ls = DictLS()
    assert ps.save_portfolio(ls, {ike.account_id: ike}) is True
    loaded, _ = ps.load_portfolio(ls)
    assert loaded["11111111"].cash_ops["time"].min() >= datetime(2021, 1, 1)
```

- [ ] **Step 2: Uruchom — ma się wywalić**

Run: `venv/Scripts/python.exe -m pytest tests/test_portfolio_storage.py -q`
Expected: FAIL (`ImportError: cannot import name 'portfolio_storage'`)

- [ ] **Step 3: Implementacja**

Create `components/portfolio_storage.py`:

```python
"""Zapis portfela (wczytane konta XTB) w localStorage przegladarki.

Format: {"v": 1, "accounts": {"<account_id>": {...}}}. Surowy plik XLSX nie jest
zapisywany — tylko sparsowane pozycje i operacje gotowkowe. localStorage ma ~5 MB
na domene, wiec przy duzej historii operacji przycinamy ja do ostatnich 5 lat.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from data.portfolio.xtb_parser import CASH_COLUMNS, LOT_COLUMNS, XtbAccount

if TYPE_CHECKING:
    from streamlit_local_storage import LocalStorage

PORTFOLIO_KEY = "gem_dashboard_portfolio_v1"
SCHEMA_VERSION = 1
MAX_BYTES = 1_500_000
KEEP_YEARS = 5


def _iso(v):
    return v.isoformat() if isinstance(v, datetime) else None


def _df_to_records(df: pd.DataFrame, time_cols: tuple[str, ...]) -> list[dict]:
    out = []
    for rec in df.to_dict("records"):
        for c in time_cols:
            rec[c] = _iso(rec.get(c))
        out.append({k: (None if isinstance(v, float) and v != v else v) for k, v in rec.items()})
    return out


def _records_to_df(recs: list[dict], columns: list[str], time_cols: tuple[str, ...]) -> pd.DataFrame:
    df = pd.DataFrame(recs, columns=columns)
    for c in time_cols:
        df[c] = [datetime.fromisoformat(v) if v else None for v in df[c]]
    return df


def account_to_dict(acc: XtbAccount) -> dict:
    return {
        "account_id": acc.account_id,
        "account_type": acc.account_type,
        "report_time": _iso(acc.report_time),
        "skipped_cfd": acc.skipped_cfd,
        "lots": _df_to_records(acc.lots, ("open_time",)),
        "cash_ops": _df_to_records(acc.cash_ops, ("time",)),
    }


def account_from_dict(d: dict) -> XtbAccount:
    return XtbAccount(
        account_id=str(d["account_id"]),
        account_type=d["account_type"],
        report_time=datetime.fromisoformat(d["report_time"]) if d.get("report_time") else None,
        lots=_records_to_df(d.get("lots", []), LOT_COLUMNS, ("open_time",)),
        cash_ops=_records_to_df(d.get("cash_ops", []), CASH_COLUMNS, ("time",)),
        skipped_cfd=int(d.get("skipped_cfd", 0)),
    )


def _dump(accounts: dict[str, XtbAccount]) -> str:
    return json.dumps({"v": SCHEMA_VERSION,
                       "accounts": {k: account_to_dict(a) for k, a in accounts.items()}},
                      ensure_ascii=False, separators=(",", ":"))


def save_portfolio(ls: "LocalStorage", accounts: dict[str, XtbAccount]) -> bool:
    """Zapisuje wszystkie konta. Zwraca True, gdy historie operacji przycieto (za duzy JSON)."""
    payload = _dump(accounts)
    trimmed = False
    if len(payload.encode("utf-8")) > MAX_BYTES:
        cutoff = datetime.now() - timedelta(days=365 * KEEP_YEARS)
        for acc in accounts.values():
            ops = acc.cash_ops
            if not ops.empty:
                acc.cash_ops = ops[ops["time"].map(lambda t: t is not None and t >= cutoff)].reset_index(drop=True)
        payload = _dump(accounts)
        trimmed = True
    ls.setItem(PORTFOLIO_KEY, payload, key="pf_set")
    return trimmed


def load_portfolio(ls: "LocalStorage") -> tuple[dict[str, XtbAccount], bool]:
    """(konta, czy_dane_uszkodzone). Brak danych -> ({}, False)."""
    raw = ls.getItem(PORTFOLIO_KEY)
    if not raw:
        return {}, False
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get("v") != SCHEMA_VERSION:
            return {}, True
        return {k: account_from_dict(v) for k, v in data.get("accounts", {}).items()}, False
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        return {}, True


def clear_portfolio(ls: "LocalStorage") -> None:
    ls.setItem(PORTFOLIO_KEY, _dump({}), key="pf_set")
```

Uwaga: atrapa `DictLS.setItem` ma tę samą sygnaturę co prawdziwe `LocalStorage.setItem(itemKey, itemValue, key="set")` używa `key` jako identyfikatora komponentu — stały `"pf_set"` jest OK (jedno wywołanie na rerun). Pusty portfel po `clear_portfolio` ma `"accounts": {}`, więc `load_portfolio` zwraca `({}, False)`.

- [ ] **Step 4: Uruchom testy**

Run: `venv/Scripts/python.exe -m pytest tests/test_portfolio_storage.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add components/portfolio_storage.py tests/test_portfolio_storage.py
git commit -m "Persist imported portfolio accounts in browser localStorage

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Rejestr strony, szkielet widoku (stan pusty) i tłumaczenia

**Files:**
- Modify: `components/nav.py` (sekcja `# --- Portfel ---`, ok. linii 73)
- Create: `views/portfel/moj_portfel.py`
- Create: `components/locales/en_portfel.py`
- Modify: `components/locales/en.py` (po `EN.update(PREMIUM)`, ok. linii 386)
- Modify: `tests/test_nav.py`
- Create: `tests/test_moj_portfel_offline.py`

- [ ] **Step 1: Zaktualizuj testy rejestru i napisz test stanu pustego**

W `tests/test_nav.py`:
- w `test_free_pages` zamień zbiór na `{"pulpit", "sygnal", "ranking-etf", "o-strategii", "karta", "moj-portfel"}`,
- w `test_page_count` zamień `25` na `26`.

Create `tests/test_moj_portfel_offline.py`:

```python
"""Offline: strona Moj portfel (Free / Premium, pusta / z portfelem) — zero sieci."""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from components import portfolio_storage as ps
from data.portfolio.xtb_parser import parse_xtb_xlsx
from tests.xtb_fixtures import make_ike_xlsx, make_zwykle_xlsx

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGE = "views/portfel/moj_portfel.py"
STORED: dict[str, str] = {}


class _FakeLocalStorage:
    def __init__(self, *a, **k):
        pass

    def getItem(self, itemKey, *a, **k):
        return STORED.get(itemKey)

    def setItem(self, itemKey=None, itemValue=None, key=None):
        STORED[itemKey] = itemValue


def _fake_quotes(tickers):
    base = {"SNT.WA": (335.0, 330.0), "META": (610.0, 600.0), "IS3N.DE": (47.0, 46.0),
            "USDPLN=X": (4.0, 4.0), "EURPLN=X": (4.3, 4.3)}
    rows = {t: base[t] for t in tickers if t in base}
    return pd.DataFrame.from_dict(rows, orient="index", columns=["last", "prev"])


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    STORED.clear()
    import streamlit_local_storage
    monkeypatch.setattr(streamlit_local_storage, "LocalStorage", _FakeLocalStorage)
    import components.financials_ui as fui
    if hasattr(fui, "LocalStorage"):
        monkeypatch.setattr(fui, "LocalStorage", _FakeLocalStorage)
    from data.portfolio import valuation
    monkeypatch.setattr(valuation, "fetch_live_prices", _fake_quotes)
    import data.financials as fin
    monkeypatch.setattr(fin, "fetch_earnings_dates", lambda t: None)


def _seed():
    ike, zw = parse_xtb_xlsx(make_ike_xlsx()), parse_xtb_xlsx(make_zwykle_xlsx())
    ps.save_portfolio(_FakeLocalStorage(), {ike.account_id: ike, zw.account_id: zw})


def _run(premium: bool):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["_auth_retries"] = 3
    if premium:
        at.session_state["premium"] = True
    at.switch_page(PAGE).run()
    return at


def _text(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [str(e.proto.body) for e in at.get("html")]
    return " ".join(parts)


def test_empty_state_free():
    at = _run(False)
    assert not at.exception, at.exception
    t = _text(at)
    assert "Mój portfel" in t
    assert "Jak pobrać eksport z XTB" in t
```

- [ ] **Step 2: Uruchom — ma się wywalić**

Run: `venv/Scripts/python.exe -m pytest tests/test_nav.py tests/test_moj_portfel_offline.py -q`
Expected: FAIL (`test_free_pages`, `test_page_count`, `test_empty_state_free` — strony nie ma)

- [ ] **Step 3: Zarejestruj stronę**

W `components/nav.py`, bezpośrednio pod linią `# --- Portfel ---` (przed `PageDef("portfolio-builder", ...)`), dodaj:

```python
    PageDef("moj-portfel", "views/portfel/moj_portfel.py", "Mój portfel", ":material/account_balance_wallet:", "Portfel", True,
            "Wczytaj eksport z XTB: pozycje, zysk, struktura, nadchodzace raporty"),
```

- [ ] **Step 4: Szkielet widoku (stan pusty + wczytywanie plików)**

Create `views/portfel/moj_portfel.py`:

```python
"""Moj portfel — import eksportu XTB (XLSX), pozycje, struktura, panel 'Co sie dzieje'.

Spec: docs/superpowers/specs/2026-11-19-moj-portfel-import-design.md
Dane portfela zyja w localStorage przegladarki (components/portfolio_storage.py);
w sesji trzymamy je w st.session_state["portfolio_accounts"], bo LocalStorage.getItem
czyta stan z chwili zamontowania komponentu (po setItem bylby nieaktualny).
"""
import streamlit as st

from components.i18n import tr
from components.portfolio_storage import clear_portfolio, load_portfolio, save_portfolio
from components.sidebar import render_footer
from data.portfolio.xtb_parser import XtbFormatError, parse_xtb_xlsx

ACCOUNT_LABELS = {"Wszystkie": "Wszystkie", "IKE": "IKE", "IKZE": "IKZE", "ZWYKLE": "Zwykłe"}


def _storage():
    from streamlit_local_storage import LocalStorage
    return LocalStorage()


def _accounts(ls) -> dict:
    if "portfolio_accounts" not in st.session_state:
        accounts, corrupt = load_portfolio(ls)
        if corrupt:
            st.warning(tr("Zapisany portfel był uszkodzony — wczytaj eksport z XTB ponownie."))
        st.session_state["portfolio_accounts"] = accounts
    return st.session_state["portfolio_accounts"]


def _handle_uploads(ls, accounts: dict) -> None:
    files = st.file_uploader(tr("Pliki .xlsx z XTB (możesz wybrać kilka: zwykłe, IKE, IKZE)"),
                             type=["xlsx", "zip"], accept_multiple_files=True, key="pf_upload")
    done = st.session_state.setdefault("pf_done_files", set())
    changed = False
    for f in files or []:
        if f.file_id in done:
            continue
        done.add(f.file_id)
        try:
            acc = parse_xtb_xlsx(f.getvalue(), f.name)
        except XtbFormatError as exc:
            st.error(f"{f.name}: {exc}")
            continue
        accounts[acc.account_id] = acc
        changed = True
        st.success(tr("Wczytano konto {typ} ({n} pozycji).",
                      typ=tr(ACCOUNT_LABELS[acc.account_type]), n=len(acc.lots)))
        if acc.skipped_cfd:
            st.info(tr("Pominięto {n} pozycji CFD — portfel pokazuje akcje i ETF-y.", n=acc.skipped_cfd))
    if changed and save_portfolio(ls, accounts):
        st.warning(tr("Historia operacji była bardzo długa — zapisano ostatnie 5 lat."))


def _howto() -> None:
    st.markdown(tr("#### Jak pobrać eksport z XTB"))
    st.markdown(tr("1. W xStation otwórz **Historia konta** i wybierz zakres dat od początku konta.\n"
                   "2. Kliknij **Eksport** i wybierz format **XLSX**.\n"
                   "3. XTB pobiera archiwum ZIP — rozpakuj je i wczytaj pliki `.xlsx` (osobny plik dla "
                   "każdego konta: zwykłe, IKE, IKZE)."))


def _privacy() -> None:
    with st.expander(tr("Prywatność danych")):
        st.markdown(tr("Plik jest przetwarzany tylko w pamięci i nie jest zapisywany na serwerze. "
                       "Wczytane pozycje zostają w tej przeglądarce (localStorage) — na innym urządzeniu "
                       "trzeba wczytać plik ponownie. Przycisk „Usuń portfel” kasuje je całkowicie."))


st.markdown(tr("# Mój portfel"))
st.caption(tr("Wczytaj eksport z XTB — zobaczysz pozycje, zysk, strukturę i nadchodzące raporty spółek"))

ls = _storage()
accounts = _accounts(ls)

with st.expander(tr("Wczytaj eksport z XTB"), expanded=not accounts):
    _handle_uploads(ls, accounts)
    if not accounts:
        _howto()

if accounts:
    st.caption(tr("Portfel wczytany — szczegóły w kolejnym kroku."))
else:
    _privacy()

render_footer()
```

Zostaw `clear_portfolio` w imporcie — użyje go Task 9 (do tego czasu `ruff`/flake8 może zgłaszać nieużywany import; nie usuwaj go).

- [ ] **Step 5: Tłumaczenia EN**

Create `components/locales/en_portfel.py`:

```python
"""Katalog EN — strona Moj portfel (views/portfel/moj_portfel.py)."""

PORTFEL: dict[str, str] = {
    "Mój portfel": "My portfolio",
    "# Mój portfel": "# My portfolio",
    "Wczytaj eksport z XTB — zobaczysz pozycje, zysk, strukturę i nadchodzące raporty spółek":
        "Upload your XTB export to see positions, profit, allocation and upcoming company reports",
    "Zapisany portfel był uszkodzony — wczytaj eksport z XTB ponownie.":
        "The saved portfolio was corrupted — please upload your XTB export again.",
    "Pliki .xlsx z XTB (możesz wybrać kilka: zwykłe, IKE, IKZE)":
        "XTB .xlsx files (you can pick several: regular, IKE, IKZE)",
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
        "account: regular, IKE, IKZE).",
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
    "Zwykłe": "Regular",
    "IKE": "IKE",
    "IKZE": "IKZE",
}
```

W `components/locales/en.py`, bezpośrednio pod linią `EN.update(PREMIUM)`, dodaj:

```python

from components.locales.en_portfel import PORTFEL  # noqa: E402

EN.update(PORTFEL)
```

- [ ] **Step 6: Uruchom testy**

Run: `venv/Scripts/python.exe -m pytest tests/test_nav.py tests/test_moj_portfel_offline.py tests/test_i18n.py -q`
Expected: wszystkie PASS. Jeśli `test_every_t_literal_has_english_translation` pokaże brakujące klucze, dopisz je do `PORTFEL` dokładnie w brzmieniu z komunikatu (klucz musi być identyczny z literałem w `tr()`, łącznie ze znakami nowej linii).

- [ ] **Step 7: Commit**

```bash
git add components/nav.py views/portfel/moj_portfel.py components/locales/en_portfel.py components/locales/en.py tests/test_nav.py tests/test_moj_portfel_offline.py
git commit -m "Add Moj portfel page: registry entry, XTB upload and empty state

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Widok portfela — kafelki, tabela, struktura, panel „Co się dzieje”

**Files:**
- Modify: `views/portfel/moj_portfel.py`
- Modify: `components/locales/en_portfel.py`
- Modify: `tests/test_moj_portfel_offline.py`

- [ ] **Step 1: Dopisz testy widoku z portfelem**

Dopisz na końcu `tests/test_moj_portfel_offline.py`:

```python
def test_portfolio_free_shows_positions_and_teaser():
    _seed()
    at = _run(False)
    assert not at.exception, at.exception
    t = _text(at)
    for s in ("SNT.PL", "META.US", "IS3N.DE", "ABC.XX", "Wartość", "Zysk / strata", "Wpłaty netto",
              "Dywidendy", "Co się dzieje"):
        assert s in t, s
    assert "🔒" in t                       # panel Premium jako zajawka
    assert "OIL.WTI" not in t              # CFD pominiete
    assert "4 346" in t                    # wartosc: 1005 + 1220 + 2021 + 100


def test_portfolio_premium_panel_and_account_filter():
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    t = _text(at)
    assert "🔒" not in t
    assert "Brak raportów" in t            # fetch_earnings_dates -> None dla wszystkich
    seg = at.get("segmented_control")[0]
    assert list(seg.proto.options) == ["Wszystkie", "IKE", "Zwykłe"]
    seg.set_value("Zwykłe").run()
    assert not at.exception, at.exception
    assert "SNT.PL" not in _text(at)


def test_delete_portfolio():
    _seed()
    at = _run(False)
    at.button(key="pf_delete_confirm").click().run()
    assert not at.exception, at.exception
    assert "Jak pobrać eksport z XTB" in _text(at)
```

Uwaga: w AppTest `segmented_control` może nie mieć akcesora `at.segmented_control`; stąd `at.get("segmented_control")`. Jeśli `seg.set_value` nie istnieje dla tego typu (zależnie od wersji Streamlit), ustaw wartość przez `at.session_state["pf_account"] = "ZWYKLE"` przed `at.run()` i zmień asercję opcji na sprawdzenie, że `"Zwykłe"` jest w `str(seg.proto)`. Opcje kontrolki to wartości wewnętrzne (`None`/`"IKE"`/`"ZWYKLE"`) wyświetlane przez `format_func` — w `proto.options` są **wyświetlane etykiety**.

- [ ] **Step 2: Uruchom — mają się wywalić**

Run: `venv/Scripts/python.exe -m pytest tests/test_moj_portfel_offline.py -q`
Expected: 3 nowe testy FAIL (brak kafelków / tabeli / przycisku `pf_delete_confirm`)

- [ ] **Step 3: Implementacja widoku**

W `views/portfel/moj_portfel.py`:

(a) Rozszerz importy na górze pliku do:

```python
import plotly.graph_objects as go
import streamlit as st

from components import nav
from components.auth import is_premium, premium_teaser
from components.cards import kpi_card
from components.charts import _base_layout
from components.constants import BG_CARD, BORDER, CHART_COLORS, GOLD, MUTED, SHADOW, TEXT
from components.formatting import GREEN, RED, fmt_number, fmt_pct
from components.i18n import tr
from components.portfolio_storage import clear_portfolio, load_portfolio, save_portfolio
from components.sidebar import render_footer
from data.gpw_universe import GPW_NAMES
from data.portfolio import valuation
from data.portfolio.tickers import currency_for, fx_ticker, xtb_to_yahoo
from data.portfolio.xtb_parser import XtbFormatError, parse_xtb_xlsx
from data.sp500_universe import SP500_NAMES
```

Zweryfikowane nazwy: `components/charts._base_layout(title="", height=450) -> dict`; w `components/constants.py`: `TEXT`, `SHADOW`, `CHART_COLORS` (lista 8 kolorów, stąd modulo przy większej liczbie spółek).

(b) Dodaj funkcje pod `_privacy()`:

```python
@st.cache_data(ttl=900, show_spinner=False)
def _quotes(tickers: tuple[str, ...]):
    return valuation.fetch_live_prices(tickers)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _upcoming_reports(tickers: tuple[str, ...]) -> list[tuple[str, object]]:
    """(ticker, data) raportow kwartalnych w oknie -14..+14 dni, posortowane po dacie."""
    import pandas as pd
    from data import financials as fin
    today = pd.Timestamp.now().normalize()
    out = []
    for t in tickers:
        try:
            df = fin.fetch_earnings_dates(t)
        except Exception:
            df = None
        if df is None or df.empty:
            continue
        for d in df.index:
            if abs((pd.Timestamp(d).normalize() - today).days) <= 14:
                out.append((t, pd.Timestamp(d)))
    return sorted(out, key=lambda x: x[1])


def _has_card(yahoo: str | None) -> bool:
    """Karta spolki istnieje tylko dla S&P 500 i GPW."""
    return bool(yahoo) and (yahoo in SP500_NAMES or yahoo in GPW_NAMES)


def _kpis(s: dict) -> None:
    c = st.columns(5)
    pcolor = GREEN if s["profit"] >= 0 else RED
    dcolor = GREEN if s["day"] >= 0 else RED
    kpi_card(c[0], "Wartość", f"{fmt_number(s['value'])} zł")
    kpi_card(c[1], "Zysk / strata", f"{fmt_number(s['profit'])} zł", fmt_pct(s["profit_pct"]), pcolor)
    kpi_card(c[2], "Dziś", f"{fmt_number(s['day'])} zł", fmt_pct(s["day_pct"]), dcolor)
    kpi_card(c[3], "Wpłaty netto", f"{fmt_number(s['deposits'])} zł")
    kpi_card(c[4], "Dywidendy", f"{fmt_number(s['dividends'])} zł", "po podatku u źródła")


_CLICK_CSS = f"""<style>
[class*="st-key-pfrow_"] {{ position:relative; gap:0; }}
[class*="st-key-pfrow_"] .stElementContainer:has(.stButton) {{ position:absolute; inset:0; z-index:2; }}
[class*="st-key-pfrow_"] .stButton, [class*="st-key-pfrow_"] .stButton button {{
  width:100%; height:100%; min-height:0; }}
[class*="st-key-pfrow_"] .stButton button {{ background:transparent; border:none; color:transparent;
  border-radius:8px; padding:0; box-shadow:none; }}
[class*="st-key-pfrow_"] .stButton button:hover {{ background:rgba(255,255,255,.04); }}
[class*="st-key-pfrow_"] .stButton button:focus-visible {{ outline:1px solid {GOLD}; }}
[class*="st-key-pfrow_"] .stButton button p {{ color:transparent; }}
</style>"""


def _row_html(r) -> str:
    pc = GREEN if (r["profit_pct"] == r["profit_pct"] and r["profit_pct"] >= 0) else RED
    warn = "" if r["live"] else f' <span title="{tr("kurs z dnia raportu")}">⚠</span>'
    badge = (f'<span style="font-size:11px;padding:1px 6px;border-radius:4px;background:{BORDER};'
             f'color:{MUTED};margin-left:6px">{tr(ACCOUNT_LABELS[r["account"]])}</span>')
    return (
        f'<div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid {BORDER};">'
        f'<div style="flex:1;min-width:0;overflow-wrap:anywhere">'
        f'<span style="color:{GOLD};font-weight:650">{r["xtb_ticker"]}</span>{badge}'
        f'<div style="color:{MUTED};font-size:12px">{r["name"]} · {fmt_number(r["volume"], 4).rstrip("0").rstrip(",.")}'
        f' × {fmt_number(r["price"], 2)} {r["currency"]}{warn}</div></div>'
        f'<div style="text-align:right;font-variant-numeric:tabular-nums">'
        f'<div style="color:{TEXT};font-weight:600">{fmt_number(r["value_pln"])} zł</div>'
        f'<div style="font-size:12px"><span style="color:{pc}">{fmt_pct(r["profit_pct"], 1)}</span>'
        f' <span style="color:{MUTED}">· {fmt_pct(r["share"], 0).lstrip("+")}</span></div></div></div>'
    )


def _positions(pos) -> None:
    st.markdown(tr("#### Pozycje"))
    st.html(_CLICK_CSS)
    for i, r in pos.iterrows():
        with st.container(key=f"pfrow_{i}"):
            st.html(_row_html(r))
            if _has_card(r["yahoo"]) and st.button(tr("Otwórz kartę {ticker}", ticker=r["yahoo"]),
                                                   key=f"pfbtn_{i}_{r['yahoo']}"):
                nav.go_company(r["yahoo"])


def _allocation(pos) -> None:
    st.markdown(tr("#### Struktura"))
    by = st.segmented_control(tr("Według"), ["Spółki", "Konta", "Waluty"], default="Spółki",
                              format_func=tr, key="pf_alloc_by") or "Spółki"
    col = {"Spółki": "xtb_ticker", "Konta": "account", "Waluty": "currency"}[by]
    g = pos.groupby(col)["value_pln"].sum().sort_values(ascending=False)
    labels = [tr(ACCOUNT_LABELS.get(k, k)) if col == "account" else k for k in g.index]
    fig = go.Figure(go.Pie(labels=labels, values=g.values, hole=0.6, sort=False,
                           marker=dict(colors=[CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(g))]),
                           textinfo="percent"))
    fig.update_layout(**_base_layout(height=300))
    fig.update_layout(showlegend=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _panel(pos) -> None:
    st.markdown(tr("#### Co się dzieje"))
    if not is_premium():
        premium_teaser(tr("Alerty dla Twojego portfela"),
                       tr("Najbliższe raporty kwartalne, a wkrótce: wyniki lepsze/gorsze od oczekiwań, "
                          "transakcje insiderów, przełamania poziomów technicznych i newsy."))
        return
    tickers = tuple(sorted({t for t in pos["yahoo"] if _has_card(t)}))
    reports = _upcoming_reports(tickers) if tickers else []
    if not reports:
        st.caption(tr("Brak raportów kwartalnych spółek z portfela w ciągu ±14 dni."))
        return
    import pandas as pd
    today = pd.Timestamp.now().normalize()
    for t, d in reports:
        days = (d.normalize() - today).days
        when = tr("za {n} dni", n=days) if days > 0 else (tr("dziś") if days == 0 else tr("{n} dni temu", n=-days))
        st.html(f'<div style="padding:8px 0;border-bottom:1px solid {BORDER}">📅 <b style="color:{GOLD}">{t}</b>'
                f' <span style="color:{MUTED}">{tr("raport kwartalny")} · {d:%d.%m} ({when})</span></div>')


def _delete(ls) -> None:
    with st.popover(tr("Usuń portfel")):
        st.caption(tr("Usuwa wczytane konta z tej przeglądarki. Tej operacji nie można cofnąć."))
        if st.button(tr("Tak, usuń"), key="pf_delete_confirm", type="primary"):
            clear_portfolio(ls)
            st.session_state["portfolio_accounts"] = {}
            st.session_state["pf_done_files"] = set()
            st.rerun()


def _render_portfolio(ls, accounts: dict) -> None:
    present = sorted({a.account_type for a in accounts.values()}, key=["IKE", "IKZE", "ZWYKLE"].index)
    options = ["Wszystkie"] + present
    choice = st.segmented_control(tr("Konto"), options, default="Wszystkie", key="pf_account",
                                  format_func=lambda o: tr(ACCOUNT_LABELS.get(o, o))) or "Wszystkie"
    account_type = None if choice == "Wszystkie" else choice

    tickers = set()
    for a in accounts.values():
        for xt in a.lots["xtb_ticker"]:
            y = xtb_to_yahoo(xt)
            if y:
                tickers.add(y)
            fx = fx_ticker(currency_for(xt))
            if fx:
                tickers.add(fx)
    try:
        quotes = _quotes(tuple(sorted(tickers)))
    except Exception:
        quotes = valuation.fetch_live_prices(())
    pos, s = valuation.value_portfolio(list(accounts.values()), quotes, account_type)

    if s["report_time"] is not None:
        st.caption(tr("Stan pozycji z raportu XTB z {d}; kursy z Yahoo Finance (opóźnione do 15 min).",
                      d=f"{s['report_time']:%d.%m.%Y}"))
    _kpis(s)
    left, right = st.columns([2, 1])
    with left:
        if pos.empty:
            st.info(tr("Brak otwartych pozycji na wybranym koncie."))
        else:
            _positions(pos)
            _allocation(pos)
    with right:
        with st.container(key="pf_panel"):
            _panel(pos)
    _delete(ls)
```

(c) Zastąp końcową część pliku (od `if accounts:` do `render_footer()`) przez:

```python
if accounts:
    _render_portfolio(ls, accounts)
_privacy()

render_footer()
```


- [ ] **Step 4: Dopisz tłumaczenia**

Dopisz do słownika `PORTFEL` w `components/locales/en_portfel.py`:

```python
    "Wszystkie": "All",
    "Wartość": "Value",
    "Zysk / strata": "Profit / loss",
    "Dziś": "Today",
    "Wpłaty netto": "Net deposits",
    "Dywidendy": "Dividends",
    "po podatku u źródła": "after withholding tax",
    "kurs z dnia raportu": "price from report date",
    "#### Pozycje": "#### Positions",
    "Otwórz kartę {ticker}": "Open {ticker} card",
    "#### Struktura": "#### Allocation",
    "Według": "By",
    "Spółki": "Companies",
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
    "za {n} dni": "in {n} days",
    "dziś": "today",
    "{n} dni temu": "{n} days ago",
    "raport kwartalny": "quarterly report",
    "Usuń portfel": "Delete portfolio",
    "Usuwa wczytane konta z tej przeglądarki. Tej operacji nie można cofnąć.":
        "Removes the imported accounts from this browser. This cannot be undone.",
    "Tak, usuń": "Yes, delete",
    "Konto": "Account",
    "Stan pozycji z raportu XTB z {d}; kursy z Yahoo Finance (opóźnione do 15 min).":
        "Positions as of the XTB report from {d}; prices from Yahoo Finance (up to 15 min delayed).",
    "Brak otwartych pozycji na wybranym koncie.": "No open positions in the selected account.",
```

Usuń z `PORTFEL` klucz `"Portfel wczytany — szczegóły w kolejnym kroku."` (tekst zniknął z kodu). Niektóre z powyższych kluczy mogą już istnieć w innych katalogach (`"Spółki"`, `"Wartość"`, `"Dziś"` …) — duplikat w `PORTFEL` nadpisze wartość tym samym znaczeniem; jeśli `tests/test_i18n.py` ma test na sprzeczne duplikaty, usuń zdublowany wpis z `PORTFEL`.

Uwaga: `kpi_card` sam wywołuje `tr(title)`, `tr(value)` i `tr(subtitle)` z **dynamicznych** argumentów — test i18n sprawdza tylko literały w wywołaniach `tr()`, więc tytuły kafelków muszą być w `PORTFEL` (są powyżej), a dynamiczne kwoty wracają z `tr()` bez zmian.

- [ ] **Step 5: Uruchom testy strony i i18n**

Run: `venv/Scripts/python.exe -m pytest tests/test_moj_portfel_offline.py tests/test_i18n.py tests/test_nav.py -q`
Expected: wszystkie PASS. Typowe poprawki:
- brakujące tłumaczenie → dopisz do `PORTFEL` dokładnie w brzmieniu z komunikatu testu,
- `"4 346"` nie znalezione → wydrukuj `_text(at)` w teście lokalnie i sprawdź, jak `fmt_number` formatuje (spacja zwykła vs twarda) — popraw asercję tylko co do rodzaju spacji, wartość musi wynosić 4346.

- [ ] **Step 6: Commit**

```bash
git add views/portfel/moj_portfel.py components/locales/en_portfel.py tests/test_moj_portfel_offline.py
git commit -m "Moj portfel: KPI tiles, clickable positions, allocation and Premium reports panel

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Weryfikacja całości, zrzuty, dokumentacja

**Files:**
- Modify: `CLAUDE.md` (repo gem-dashboard)

- [ ] **Step 1: Pełna suita offline**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: wszystko PASS (przed zmianami było 373 passed + skipped sieciowe; teraz ok. 373 + ~45 nowych). Każdy czerwony test napraw przed przejściem dalej.

- [ ] **Step 2: Test na prawdziwym eksporcie (tylko lokalnie, nic nie commitować)**

Run:

```bash
venv/Scripts/python.exe -c "
from pathlib import Path
from data.portfolio.xtb_parser import parse_xtb_xlsx
from data.portfolio.valuation import value_portfolio
import pandas as pd
d = Path(r'C:/Users/m4x/Desktop/xtb/11.2026/53853640')
accs = [parse_xtb_xlsx(p.read_bytes(), p.name) for p in sorted(d.glob('*.xlsx'))]
for a in accs: print(a.account_type, len(a.lots), 'lotow, CFD pominiete:', a.skipped_cfd)
pos, s = value_portfolio(accs, pd.DataFrame(columns=['last','prev']))
print(len(pos), 'pozycji; wartosc z pliku', round(s['value'], 2))
"
```

Expected: trzy konta (`IKE`, `IKZE`, `ZWYKLE`), bez wyjątków. **Wartość z pliku dla IKE i IKZE musi się zgadzać z wierszem `Open position value` w arkuszu Open Positions każdego pliku** (sprawdź `value_portfolio(accs, ..., account_type="IKE")` osobno). Nie wklejaj tych liczb do commitów ani do CLAUDE.md. Zgłoś użytkownikowi tylko „zgodne / niezgodne o X zł”.

- [ ] **Step 3: Zrzuty ekranu do akceptacji**

Uruchom aplikację: `venv/Scripts/python.exe -m streamlit run app.py --server.port 8599 --server.headless true` (w tle). Zrób zrzuty narzędziem repo (`venv/Scripts/python.exe scripts/screenshot.py URL OUT.png W H WAIT`) do katalogu scratchpad sesji (nie do repo):
- `http://localhost:8599/moj_portfel` — stan pusty, 1400×1000 i 390×900.
Widok z portfelem wymaga wczytania pliku w przeglądarce (AppTest tego nie pokaże) — poproś użytkownika, żeby sam otworzył `http://localhost:8599/moj_portfel`, wczytał swoje pliki i ocenił wygląd (desktop + telefon w trybie responsywnym). Panel Premium lokalnie: tymczasowy `_shot_app.py` w katalogu repo z `st.session_state["premium"] = True` + `exec(open("app.py", encoding="utf-8").read())`, uruchomiony przez `streamlit run _shot_app.py`; **usuń `_shot_app.py` po zrzutach**.

- [ ] **Step 4: Dokumentacja**

W `CLAUDE.md` repo gem-dashboard dopisz w opisie stron/sekcji Portfel (zachowaj styl sąsiednich wpisów):

```markdown
- **Mój portfel** (`views/portfel/moj_portfel.py`, darmowa; panel „Co się dzieje” Premium) — import eksportu XLSX z XTB (konto zwykłe/IKE/IKZE, osobny plik na konto), pozycje z arkusza *Open Positions* wyceniane kursami Yahoo (jedno `yf.download`, fallback na kurs z pliku ⚠), kafelki, struktura, najbliższe raporty ±14 dni. Pakiet `data/portfolio/` (parser `xtb_parser.py`, mapowanie `tickers.py`: .US→bez przyrostka, .PL→.WA, .NL→.AS, .FR→.PA, .UK→.L /100; wycena `valuation.py`). Zapis w localStorage (`components/portfolio_storage.py`, klucz `gem_dashboard_portfolio_v1`); w sesji `st.session_state["portfolio_accounts"]`, bo `LocalStorage.getItem` jest nieaktualny po `setItem`. CFD pomijane. Spec: `docs/superpowers/specs/2026-11-19-moj-portfel-import-design.md`. Moduły 2–4 (alerty fundamentalne, technika, newsy) — osobne specy.
```

Zaktualizuj też liczbę stron w CLAUDE.md, jeśli jest tam podana (25 → 26).

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "Document Moj portfel page and data/portfolio package

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Stop — decyzja użytkownika**

NIE merguj i NIE pushuj. Pokaż użytkownikowi: wynik pełnej suity, wynik zgodności z prawdziwym plikiem (Step 2), zrzuty. Merge do `main` + push tylko po wyraźnym „tak”; po pushu przypomnij o **Reboot** aplikacji na Streamlit Cloud (nowe moduły w `data/` i `components/` — lekcja z 19.11) oraz o tym, że Cloud zainstaluje `openpyxl` z `requirements.txt`.
