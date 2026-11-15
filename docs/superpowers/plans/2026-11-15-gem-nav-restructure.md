# GEM Dashboard — przebudowa nawigacji: plan wdrożenia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zastąpić płaską listę 27 stron górnym menu z 7 sekcjami, jednym rejestrem stron, bramką Premium w routerze i nowym Pulpitem (centrum dowodzenia), scalając 27 stron w 24.

**Architecture:** `app.py` staje się routerem `st.navigation(position="top")` budowanym z rejestru `components/nav.py` (lista `PageDef`). Router raz wywołuje `setup_sidebar()` i sprawdza dostęp Premium przed `pg.run()`. Strony trafiają do `pages/<sekcja>/` przez `git mv`; scalone strony mają zakładki, a kod dawnych stron jest opakowany w funkcje (`st.stop()` → `return`). Logika liczenia Pulpitu (regime, wygrani/przegrani, terminy sygnału) trafia do czystych, testowalnych funkcji w `data/market_status.py`.

**Tech Stack:** Python 3.14, Streamlit 1.55 (`st.navigation`, `st.Page`, `st.fragment`, `AppTest`), pandas, plotly, yfinance, pytest, `streamlit-local-storage`.

**Spec:** `docs/superpowers/specs/2026-11-15-gem-nav-restructure-design.md`

**Odstępstwa od specyfikacji (do zatwierdzenia przy przeglądzie planu):**
1. Funkcje kalendarza wyników (`bulk_fetch_earnings_calendar`, `_status_badge`, `_detect_market`) już są w `data/financials.py` — nie tworzymy `data/earnings.py`, Pulpit importuje z `data.financials`.
2. Smoke testy wszystkich stron idą konwencją repo: sieciowe, uruchamiane z `RUN_NETWORK=1` (jak `test_stopy_zwrotu_page.py`). Offline testujemy rejestr, bramkę Premium (strona płatna bez Premium nie uruchamia treści → zero sieci) i czyste funkcje `data/market_status.py`.
3. Pulpit zachowuje dwie rzeczy z obecnego Podsumowania, których spec nie wymienił: „⭐ Ulubione” z sidebaru (łączone z watchlistą localStorage w jednej karcie) i „📄 Eksport PDF” (na dole, Premium).

**Konwencje wykonania:**
- Katalog repo: `C:\Users\m4x\Desktop\AI\gem-dashboard`, gałąź `restructure-nav`.
- Python: `venv/Scripts/python.exe` (Git Bash). Testy: `venv/Scripts/python.exe -m pytest -q`.
- Commit po każdym zadaniu, stopka: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- `git add` selektywnie (nigdy `-A`): w katalogu leżą nieśledzone `okładka.png`, `screen2.png`, `screen3.png`, `docs/superpowers/plans/2026-06-02-finanse-kwartalne.md` — nie dodawać.
- Pamięć projektu: nie usuwać importów z `# noqa: F401` (re-eksporty), helpery używane w `@st.fragment` definiować na poziomie modułu przed `with tab:`, nie przypisywać `st.session_state[klucz_widgetu]` po utworzeniu widgetu.

---

## Struktura plików

| Plik | Odpowiedzialność |
|---|---|
| `components/nav.py` (nowy) | Rejestr `PageDef`, `PAGES`, `SECTION_ORDER`, `get`, `by_path`, `build_navigation`, `go`, `link` |
| `components/auth.py` (zmiana) | Usunięte `FREE_PAGES`, `PAGE_INFO`, `require_premium`; publiczne `render_lock_screen(icon, title, desc)`, nowe `premium_teaser(title, desc)` |
| `components/sidebar.py` (zmiana) | Usunięty CSS separatorów `nth-child`; reszta bez zmian |
| `app.py` (przepisany) | Router: config → sidebar → nawigacja → bramka → `pg.run()` |
| `data/market_status.py` (nowy) | `compute_regime`, `signal_since`, `next_rebalance_date`, `daily_change`, `top_movers`, `pulpit_earnings_tickers`, `MARKET_TILES` |
| `pages/start/pulpit.py` (z `0_podsumowanie.py`) | Pulpit |
| `pages/strategia/sygnal.py` (z `1_sygnal_gem.py` + `17_sygnaly.py`) | Sygnał GEM z 4 zakładkami |
| `pages/etf/porownaj.py` (z `3_wykresy.py` + `4_porownanie.py` + `21_side_by_side.py`) | Porównaj z 3 zakładkami |
| 19 pozostałych stron | tylko przeniesione + oczyszczone z boilerplate |
| `tests/test_nav.py` (nowy) | Rejestr i brak starego boilerplate |
| `tests/test_auth_gate.py` (nowy) | Bramka Premium przez router (offline) |
| `tests/test_market_status.py` (nowy) | Czyste funkcje Pulpitu |
| `tests/test_pages_smoke.py` (nowy) | Każda strona z Premium (sieć, `RUN_NETWORK=1`) |
| `tests/test_stopy_zwrotu_page.py` (zmiana) | Usunięte testy kolejności menu/separatorów/kafelka; render przez router |

---

### Task 1: Punkt startowy

**Files:** brak zmian

- [ ] **Step 1: Upewnij się, że jesteś na gałęzi**

Run: `cd /c/Users/m4x/Desktop/AI/gem-dashboard && git branch --show-current`
Expected: `restructure-nav`

- [ ] **Step 2: Uruchom pełną suitę i zapisz wynik**

Run: `venv/Scripts/python.exe -m pytest -q 2>&1 | tail -5`
Expected: wszystkie przechodzą (sieciowe są `skipped`). Zapisz liczbę `passed`/`skipped` — to punkt odniesienia. Jeśli coś pada już teraz, zatrzymaj się i zgłoś (nie naprawiaj w ramach tego planu).

---

### Task 2: Rejestr stron `components/nav.py`

**Files:**
- Create: `components/nav.py`
- Create: `tests/test_nav.py`

- [ ] **Step 1: Napisz testy rejestru**

`tests/test_nav.py`:
```python
"""Rejestr stron (components/nav.py) — spojnosc i brak starego boilerplate."""
from pathlib import Path

import pytest

from components import nav

ROOT = Path(__file__).resolve().parents[1]


def test_keys_unique():
    keys = [p.key for p in nav.PAGES]
    assert len(keys) == len(set(keys))


def test_file_stems_unique():
    # URL strony = nazwa pliku, wiec nazwy plikow musza byc unikalne
    stems = [p.path.rsplit("/", 1)[-1] for p in nav.PAGES]
    assert len(stems) == len(set(stems))


def test_titles_unique():
    # router rozpoznaje strone po tytule
    titles = [p.title for p in nav.PAGES]
    assert len(titles) == len(set(titles))


def test_exactly_one_default_and_it_is_pulpit():
    defaults = [p.key for p in nav.PAGES if p.default]
    assert defaults == ["pulpit"]


def test_free_pages():
    assert {p.key for p in nav.PAGES if p.free} == {"pulpit", "sygnal", "ranking-etf", "o-strategii"}


def test_page_count():
    assert len(nav.PAGES) == 24


def test_sections_known_and_non_empty():
    used = {p.section for p in nav.PAGES}
    assert used <= set(nav.SECTION_ORDER)
    for section in ("Strategia GEM", "ETF", "Spółki", "Portfel", "Rynek"):
        assert any(p.section == section for p in nav.PAGES), section


def test_get_and_by_path():
    p = nav.get("sp500")
    assert p.path == "pages/spolki/sp500.py"
    assert nav.by_path("pages/spolki/sp500.py") is p
    assert nav.by_title("S&P 500") is p
    with pytest.raises(KeyError):
        nav.get("nie-ma-takiej")


def test_descriptions_present():
    for p in nav.PAGES:
        assert p.description.strip(), p.key
```

- [ ] **Step 2: Uruchom — ma paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_nav.py -q`
Expected: FAIL — `ImportError: cannot import name 'nav' from 'components'`

- [ ] **Step 3: Napisz rejestr**

`components/nav.py`:
```python
"""Rejestr stron GEM Dashboard — jedyne zrodlo prawdy o nawigacji.

Nowa strona = plik w pages/<sekcja>/ + jeden wpis w PAGES.
Adres URL = nazwa pliku (bez url_path) — wymagane przez AppTest.switch_page,
ktory liczy hash strony z nazwy pliku. Dlatego nazwy plikow musza byc unikalne.
Router (app.py) buduje z tego st.navigation i bramke Premium.
"""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class PageDef:
    key: str
    path: str
    title: str
    icon: str
    section: str          # "" = link bezposredni w gornym menu
    free: bool
    description: str
    default: bool = False


# Kolejnosc sekcji w gornym menu. "" pojawia sie dwa razy w intencji
# (Pulpit na poczatku, Krypto po Spolkach) — st.navigation laczy strony
# bez sekcji w jedna grupe, wiec kolejnosc stron w "" wynika z PAGES.
SECTION_ORDER = ["", "Strategia GEM", "ETF", "Spółki", "Portfel", "Rynek"]

PAGES: list[PageDef] = [
    # --- Start ---
    PageDef("pulpit", "pages/start/pulpit.py", "Pulpit", "🏠", "", True,
            "Centrum dowodzenia: sygnal GEM, regime, rynek, watchlista, wyniki tygodnia", default=True),
    # --- Strategia GEM ---
    PageDef("sygnal", "pages/strategia/sygnal.py", "Sygnał GEM", "🎯", "Strategia GEM", True,
            "Aktualny sygnal GEM, top 5 ETF oraz pelna historia zmian sygnalu"),
    PageDef("backtest", "pages/strategia/backtest.py", "Backtest", "🔬", "Strategia GEM", False,
            "GEM vs Buy&Hold — krzywa kapitalu, Sharpe, MDD i wiecej"),
    PageDef("gem-extended", "pages/strategia/gem_extended.py", "GEM Extended", "🚀", "Strategia GEM", False,
            "Backtest GEM z dowolnym universe (do 10 ETF + krypto), top N equal-weight"),
    PageDef("gem-zloto", "pages/strategia/gem_zloto.py", "GEM Gold Momentum", "🥇", "Strategia GEM", False,
            "Momentum ze zlotem w wersji GEM: Nasdaq-100 / zloto / obligacje, backtest od 2005 vs GEM klasyczny"),
    PageDef("o-strategii", "pages/strategia/o_strategii.py", "O strategii", "📖", "Strategia GEM", True,
            "Opis strategii GEM Gary'ego Antonacciego"),
    # --- ETF ---
    PageDef("ranking-etf", "pages/etf/ranking.py", "Ranking momentum", "📊", "ETF", True,
            "Tabela rankingowa 30+ ETF-ow z wynikiem momentum"),
    PageDef("porownaj", "pages/etf/porownaj.py", "Porównaj", "⚖️", "ETF", False,
            "Wykresy, head-to-head 2–4 ETF-ow z korelacjami oraz side-by-side dwoch aktywow"),
    PageDef("stopy-zwrotu", "pages/etf/stopy_zwrotu.py", "Stopy zwrotu", "📏", "ETF", False,
            "Stopy zwrotu ETF-ow do 30 lat: okresy, lata, okna kroczace, PLN i proxy"),
    PageDef("drawdowny", "pages/etf/drawdowny.py", "Drawdowny", "📉", "ETF", False,
            "Analiza spadkow od szczytu — glebokosc, czas trwania, odbudowa"),
    # --- Spolki ---
    PageDef("sp500", "pages/spolki/sp500.py", "S&P 500", "🇺🇸", "Spółki", False,
            "Ranking, wykresy, finanse i backtest ~500 spolek z indeksu S&P 500"),
    PageDef("gpw", "pages/spolki/gpw.py", "GPW", "🇵🇱", "Spółki", False,
            "140 spolek z WIG20, mWIG40 i sWIG80 — momentum, finanse i backtest"),
    PageDef("top-picks", "pages/spolki/top_picks.py", "Top Picks", "🎯", "Spółki", False,
            "Trzy miesieczne piatki spolek: momentum cenowe, jakosc wynikow kwartalnych i jakosc biznesu"),
    PageDef("screener", "pages/spolki/screener.py", "Screener", "🔎", "Spółki", False,
            "Cross-asset ranking momentum ze wszystkich klas aktywow"),
    PageDef("kalendarz-wynikow", "pages/spolki/kalendarz_wynikow.py", "Kalendarz wyników", "📅", "Spółki", False,
            "Kalendarz nadchodzacych i niedawnych raportow SP500 + GPW (±28 dni) z watchlista"),
    PageDef("insiderzy", "pages/spolki/insiderzy.py", "Insiderzy", "👥", "Spółki", False,
            "Bulk insider activity SP500 — top kupujacy/sprzedajacy, sektory"),
    # --- Krypto (link bezposredni) ---
    PageDef("krypto", "pages/krypto/kryptowaluty.py", "Krypto", "🪙", "", False,
            "Top 200 kryptowalut — ranking, alt/BTC ratio, backtest"),
    # --- Portfel ---
    PageDef("portfolio-builder", "pages/portfel/portfolio_builder.py", "Portfolio Builder", "🏗️", "Portfel", False,
            "Zbuduj portfel, ustaw wagi, backtest i analiza korelacji"),
    PageDef("monte-carlo", "pages/portfel/monte_carlo.py", "Monte Carlo", "🎲", "Portfel", False,
            "Symulacja przyszlych zwrotow — ile mozesz miec za N lat?"),
    # --- Rynek ---
    PageDef("makro", "pages/rynek/makro.py", "Makro", "🌍", "Rynek", False,
            "VIX, yield curve, DXY, S&P+200MA, zloto, ropa"),
    PageDef("sektory", "pages/rynek/sektory.py", "Rotacja sektorowa", "🔄", "Rynek", False,
            "Ktory sektor GICS prowadzi? Heatmapa momentum sektorow"),
    PageDef("intermarket", "pages/rynek/intermarket.py", "Intermarket", "🔗", "Rynek", False,
            "Relacje miedzy klasami aktywow: akcje, obligacje, zloto, dolar"),
    PageDef("sezonowosc", "pages/rynek/sezonowosc.py", "Sezonowość", "📅", "Rynek", False,
            "Heatmapa miesiecznych zwrotow i wzorce sezonowe"),
    PageDef("waluta", "pages/rynek/waluta.py", "Waluta PLN/USD", "💱", "Rynek", False,
            "Wplyw kursu USD/PLN na zwroty ETF-ow w zlotowkach"),
]

_BY_KEY = {p.key: p for p in PAGES}
_BY_PATH = {p.path: p for p in PAGES}
_BY_TITLE = {p.title: p for p in PAGES}


def get(key: str) -> PageDef:
    return _BY_KEY[key]


def by_path(path: str) -> PageDef | None:
    return _BY_PATH.get(path.replace("\\", "/"))


def by_title(title: str) -> PageDef | None:
    """Router identyfikuje biezaca strone po tytule (st.Page nie udostepnia sciezki)."""
    return _BY_TITLE.get(title)


def build_navigation() -> dict[str, list]:
    """Sekcje dla st.navigation — kolejnosc wg SECTION_ORDER, strony wg PAGES."""
    sections: dict[str, list] = {name: [] for name in SECTION_ORDER}
    for p in PAGES:
        sections[p.section].append(
            st.Page(p.path, title=p.title, icon=p.icon, default=p.default)
        )
    return {name: pages for name, pages in sections.items() if pages}


def go(key: str) -> None:
    """Przejscie na strone po kluczu (zamiast twardej sciezki w st.switch_page)."""
    st.switch_page(get(key).path)


def link(key: str, label: str | None = None, **kwargs) -> None:
    p = get(key)
    st.page_link(p.path, label=label or p.title, icon=p.icon, **kwargs)
```

- [ ] **Step 4: Uruchom — ma przejść**

Run: `venv/Scripts/python.exe -m pytest tests/test_nav.py -q`
Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add components/nav.py tests/test_nav.py
git commit -m "Add page registry for top navigation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Przenieś 21 stron bez scaleń i usuń boilerplate

**Files:**
- Move (`git mv`): 21 plików (lista w kroku 3)
- Create: `scripts/strip_page_boilerplate.py` (jednorazowy, zostaje w repo jako dokumentacja migracji)
- Modify: `pages/spolki/kalendarz_wynikow.py` (linki), `pages/spolki/insiderzy.py` (link)
- Modify: `tests/test_nav.py`

- [ ] **Step 1: Dopisz testy boilerplate do `tests/test_nav.py`**

Dopisz na końcu pliku:
```python
MIGRATED = [p for p in nav.PAGES if p.key not in {"pulpit", "sygnal", "porownaj"}]


@pytest.mark.parametrize("page", MIGRATED, ids=lambda p: p.key)
def test_migrated_page_exists(page):
    assert (ROOT / page.path).is_file()


@pytest.mark.parametrize("page", MIGRATED, ids=lambda p: p.key)
def test_no_legacy_boilerplate(page):
    src = (ROOT / page.path).read_text(encoding="utf-8")
    assert "require_premium" not in src
    assert "setup_sidebar" not in src
    assert "set_page_config" not in src
    assert 'st.switch_page("pages/' not in src
```

- [ ] **Step 2: Uruchom — ma paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_nav.py -q`
Expected: FAIL — `test_migrated_page_exists` dla 21 stron (pliki nie istnieją).

- [ ] **Step 3: Przenieś pliki**

```bash
cd /c/Users/m4x/Desktop/AI/gem-dashboard
mkdir -p pages/start pages/strategia pages/etf pages/spolki pages/krypto pages/portfel pages/rynek
git mv pages/5_backtest.py            pages/strategia/backtest.py
git mv pages/22_gem_extended.py       pages/strategia/gem_extended.py
git mv pages/25_gem_gold_momentum.py  pages/strategia/gem_zloto.py
git mv pages/6_info.py                pages/strategia/o_strategii.py
git mv pages/2_ranking.py             pages/etf/ranking.py
git mv pages/6_stopy_zwrotu.py        pages/etf/stopy_zwrotu.py
git mv pages/16_drawdown.py           pages/etf/drawdowny.py
git mv pages/7_sp500.py               pages/spolki/sp500.py
git mv pages/8_gpw.py                 pages/spolki/gpw.py
git mv pages/9_top_picks.py           pages/spolki/top_picks.py
git mv pages/12_screener.py           pages/spolki/screener.py
git mv pages/23_earnings_calendar.py  pages/spolki/kalendarz_wynikow.py
git mv pages/24_insider_screener.py   pages/spolki/insiderzy.py
git mv pages/10_kryptowaluty.py       pages/krypto/kryptowaluty.py
git mv pages/11_portfolio.py          pages/portfel/portfolio_builder.py
git mv pages/18_monte_carlo.py        pages/portfel/monte_carlo.py
git mv pages/13_makro.py              pages/rynek/makro.py
git mv pages/19_sektory.py            pages/rynek/sektory.py
git mv pages/20_intermarket.py        pages/rynek/intermarket.py
git mv pages/14_sezonowosc.py         pages/rynek/sezonowosc.py
git mv pages/15_waluta.py             pages/rynek/waluta.py
```
(21 przeniesionych. Zostają w `pages/`: `0_podsumowanie`, `1_sygnal_gem`, `3_wykresy`, `4_porownanie`, `17_sygnaly`, `21_side_by_side` — scalane w Task 6–8.)

- [ ] **Step 4: Napisz skrypt czyszczący**

`scripts/strip_page_boilerplate.py`:
```python
"""Jednorazowa migracja 2026-11-15: usuwa z plikow stron boilerplate,
ktory przejal router (app.py): set_page_config, setup_sidebar(), require_premium.

Uzycie: python scripts/strip_page_boilerplate.py pages/etf/ranking.py [...]
"""
import re
import sys
from pathlib import Path

PATTERNS = [
    # st.set_page_config(...) jedno- lub wieloliniowe
    (re.compile(r"^st\.set_page_config\(.*?\)\n", re.S | re.M), ""),
    # setup_sidebar() jako osobna linia
    (re.compile(r"^setup_sidebar\(\)\n", re.M), ""),
    # if not require_premium(N): st.stop()   (jedna linia)
    (re.compile(r"^if not require_premium\(\d+\):\s*st\.stop\(\)\n", re.M), ""),
    # if not require_premium(N):\n    st.stop()
    (re.compile(r"^if not require_premium\(\d+\):\n\s+st\.stop\(\)\n", re.M), ""),
    # import require_premium
    (re.compile(r"^from components\.auth import require_premium\n", re.M), ""),
]


def strip_sidebar_import(src: str) -> str:
    """Usun setup_sidebar z listy importu components.sidebar (zachowaj reszte)."""
    def fix(m: re.Match) -> str:
        names = [n.strip() for n in m.group(1).split(",") if n.strip() != "setup_sidebar"]
        return f"from components.sidebar import {', '.join(names)}\n" if names else ""
    return re.sub(r"^from components\.sidebar import (.+)\n", fix, src, flags=re.M)


def main(paths: list[str]) -> None:
    for path in paths:
        p = Path(path)
        src = p.read_text(encoding="utf-8")
        new = src
        for pattern, repl in PATTERNS:
            new = pattern.sub(repl, new)
        new = strip_sidebar_import(new)
        if new != src:
            p.write_text(new, encoding="utf-8")
            print(f"OK   {path}")
        else:
            print(f"SKIP {path} (bez zmian)")


if __name__ == "__main__":
    main(sys.argv[1:])
```

- [ ] **Step 5: Uruchom skrypt na przeniesionych plikach**

```bash
venv/Scripts/python.exe scripts/strip_page_boilerplate.py pages/strategia/*.py pages/etf/*.py pages/spolki/*.py pages/krypto/*.py pages/portfel/*.py pages/rynek/*.py
```
Expected: 21 linii `OK`.

Sprawdź ręcznie, że nic nie zostało:
```bash
grep -rn "require_premium\|setup_sidebar\|set_page_config" pages/strategia pages/etf pages/spolki pages/krypto pages/portfel pages/rynek
```
Expected: brak wyników.

- [ ] **Step 6: Zamień twarde linki na `nav.go`**

W `pages/spolki/kalendarz_wynikow.py`:
- dodaj import pod pozostałymi `from components...`: `from components import nav`
- zamień `st.switch_page("pages/7_sp500.py")` → `nav.go("sp500")`
- zamień `st.switch_page("pages/8_gpw.py")` → `nav.go("gpw")`

W `pages/spolki/insiderzy.py`:
- dodaj `from components import nav`
- zamień `st.switch_page("pages/7_sp500.py")` → `nav.go("sp500")`

Sprawdź: `grep -rn 'switch_page("pages/' pages/` → brak wyników w przeniesionych katalogach.

- [ ] **Step 7: Sprawdź składnię wszystkich przeniesionych plików**

Run: `venv/Scripts/python.exe -m py_compile pages/*/*.py && echo OK`
Expected: `OK`

- [ ] **Step 8: Uruchom testy rejestru**

Run: `venv/Scripts/python.exe -m pytest tests/test_nav.py -q`
Expected: wszystkie przechodzą (21 × 2 parametryzowanych + 8).

- [ ] **Step 9: Commit**

```bash
git add -u pages/ && git add pages/strategia pages/etf pages/spolki pages/krypto pages/portfel pages/rynek scripts/strip_page_boilerplate.py tests/test_nav.py
git commit -m "Move 21 pages into section folders and strip per-page boilerplate

Router takes over set_page_config, setup_sidebar and premium gating.
Cross-page links use nav.go(key) instead of hard-coded paths.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Auth — publiczny ekran blokady i zaślepka Premium

**Files:**
- Modify: `components/auth.py`
- Create: `tests/test_auth_api.py`

- [ ] **Step 1: Napisz test API**

`tests/test_auth_api.py`:
```python
"""components.auth po migracji: bez numerow stron, z publicznym API blokady."""
import components.auth as auth


def test_legacy_numbered_api_removed():
    assert not hasattr(auth, "FREE_PAGES")
    assert not hasattr(auth, "PAGE_INFO")
    assert not hasattr(auth, "require_premium")


def test_public_api_present():
    assert callable(auth.render_lock_screen)
    assert callable(auth.premium_teaser)
    assert callable(auth.is_premium)
```

- [ ] **Step 2: Uruchom — ma paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_auth_api.py -q`
Expected: FAIL na `test_legacy_numbered_api_removed` i `test_public_api_present`.

- [ ] **Step 3: Zmień `components/auth.py`**

1. Usuń blok `# Strony dostepne za darmo` z `FREE_PAGES = {0, 1, 2, 6}`.
2. Usuń cały słownik `PAGE_INFO = {...}` z komentarzem nad nim.
3. Usuń funkcję `require_premium(page_num)` w całości.
4. Zamień nagłówek i początek `_render_lock_screen` na publiczną funkcję o nowym podpisie (treść HTML bez zmian, poza liczbą stron w nagłówku CTA):

```python
def render_lock_screen(icon: str, title: str, desc: str) -> None:
    """Renderuje ekran blokady z CTA zakupu (wolany przez router)."""
    st.html(f'''
```
— a w HTML zmień `Odblokuj wszystkie 21 stron` na `Odblokuj wszystkie strony Premium`. Usuń linie `info = PAGE_INFO.get(...)` i `icon, title, desc = info`.

5. Dopisz na końcu pliku:
```python
def premium_teaser(title: str, desc: str) -> None:
    """Zaslepka karty/zakladki Premium (Pulpit, Sygnal GEM, pozniej Karta spolki)."""
    st.html(f'''
    <div style="background:#141929;border:1px dashed rgba(201,168,76,0.35);
                border-radius:14px;padding:20px;text-align:center;">
        <div style="font-size:22px;margin-bottom:6px;">🔒</div>
        <div style="color:#E5E7EB;font-weight:700;font-size:15px;margin-bottom:4px;">{title}</div>
        <div style="color:#9CA3AF;font-size:13px;line-height:1.5;margin-bottom:12px;">{desc}</div>
    </div>
    ''')
    st.link_button("Odblokuj Premium", NAFFY_URL, width="stretch")
```
(`st.link_button` poza `st.html`, bo linki z iframe `st.html` nie zawsze się otwierają — ta sama zasada co w `render_footer`.)

- [ ] **Step 4: Uruchom — ma przejść**

Run: `venv/Scripts/python.exe -m pytest tests/test_auth_api.py -q`
Expected: `2 passed`

Sprawdź, że nikt poza starymi stronami nie używa usuniętego API:
```bash
grep -rn "FREE_PAGES\|PAGE_INFO\|require_premium\|_render_lock_screen" --include=*.py . | grep -v venv | grep -v "^./pages/[0-9]"
```
Expected: tylko `app.py` (stary, przepisywany w Task 5) i `scripts/strip_page_boilerplate.py` (wzorce regex).

- [ ] **Step 5: Commit**

```bash
git add components/auth.py tests/test_auth_api.py
git commit -m "Replace numbered premium gating with public lock screen and teaser

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Router `app.py` + bramka Premium + sprzątanie CSS sidebaru

**Files:**
- Rewrite: `app.py`
- Modify: `components/sidebar.py` (usuń 3 reguły separatorów)
- Create: `tests/test_auth_gate.py`

- [ ] **Step 1: Napisz test bramki (offline)**

`tests/test_auth_gate.py`:
```python
"""Bramka Premium w routerze: strona platna bez Premium nie uruchamia tresci.

Offline: przy zablokowanej stronie router nie wola pg.run(), wiec strona
nie pobiera danych. Uzywamy strony bez sieciowego importu na starcie.
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _html_text(at) -> str:
    # st.html w AppTest to UnknownElement; tresc jest w proto.body
    return " ".join(e.proto.body for e in at.get("html"))


def test_paid_page_shows_lock_screen_without_premium():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["premium"] = False
    at.session_state["_auth_retries"] = 3
    at.switch_page("pages/portfel/monte_carlo.py").run()
    assert not at.exception, at.exception
    html = _html_text(at)
    assert "Kup dostep Premium" in html
    assert "Monte Carlo" in html


def test_free_page_runs_without_premium():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["premium"] = False
    at.session_state["_auth_retries"] = 3
    at.switch_page("pages/strategia/o_strategii.py").run()
    assert not at.exception, at.exception
    assert "Kup dostep Premium" not in _html_text(at)
```

- [ ] **Step 2: Uruchom — ma paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_auth_gate.py -q`
Expected: FAIL — stary `app.py` importuje `FREE_PAGES` (ImportError) albo nie zna `st.navigation`.

- [ ] **Step 3: Przepisz `app.py`**

```python
"""GEM ETF Dashboard — router (gorne menu z sekcjami).

Strony definiuje components/nav.py. Router raz ustawia konfiguracje,
sidebar i Premium, a przed uruchomieniem strony sprawdza dostep.
"""
import streamlit as st

from components import nav
from components.auth import is_premium, render_lock_screen
from components.sidebar import setup_sidebar, render_footer

st.set_page_config(
    page_title="GEM ETF Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

setup_sidebar()

pg = st.navigation(nav.build_navigation(), position="top")

page = nav.by_title(pg.title)

if page is not None and not page.free and not is_premium():
    render_lock_screen(page.icon, page.title, page.description)
    render_footer()
else:
    pg.run()
```

Uwaga: `st.Page` nie udostępnia ścieżki pliku, a `pg.url_path` dla strony domyślnej to `""` — dlatego router szuka strony po tytule (unikalność tytułów sprawdza `test_titles_unique`).

- [ ] **Step 4: Usuń separatory `nth-child` z `components/sidebar.py`**

Usuń trzy bloki CSS wraz z komentarzami nad nimi (zaczynają się od `/* Separator between ETF section`, `/* Separator between market sections`, `/* Separator between tools`), czyli reguły `a[data-testid="stSidebarNavLink"]:nth-child(9)`, `(13)`, `(16)`. Style `a[data-testid="stSidebarNavLink"]` (hover/aktywny) zostają — przy `position="top"` na telefonie menu wraca do sidebaru i nadal z nich korzysta.

- [ ] **Step 5: Uruchom testy bramki i rejestru**

Run: `venv/Scripts/python.exe -m pytest tests/test_auth_gate.py tests/test_nav.py -q`
Expected: wszystkie przechodzą.

Jeśli `test_paid_page_shows_lock_screen_without_premium` pada z „page not found”, to strona scalana (Pulpit/Sygnał/Porównaj) jeszcze nie istnieje, a `st.navigation` wymaga istniejących plików. Wtedy utwórz tymczasowe pliki-zaślepki, żeby router się zbudował:
```bash
printf 'import streamlit as st\nst.info("W przebudowie")\n' > pages/start/pulpit.py
printf 'import streamlit as st\nst.info("W przebudowie")\n' > pages/strategia/sygnal.py
printf 'import streamlit as st\nst.info("W przebudowie")\n' > pages/etf/porownaj.py
```
(Task 6–8 je nadpiszą.)

- [ ] **Step 6: Commit**

```bash
git add app.py components/sidebar.py tests/test_auth_gate.py pages/start pages/strategia/sygnal.py pages/etf/porownaj.py
git commit -m "Turn app.py into top-nav router with central premium gate

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Scalenie — Sygnał GEM

**Files:**
- Rewrite: `pages/strategia/sygnal.py` (z `pages/1_sygnal_gem.py` + `pages/17_sygnaly.py`)
- Delete: `pages/1_sygnal_gem.py`, `pages/17_sygnaly.py`

- [ ] **Step 1: Zbuduj plik z dwóch źródeł**

Struktura docelowa `pages/strategia/sygnal.py`:
```python
"""Sygnal GEM — aktualny sygnal (darmowe) + historia, statystyki, kalendarz (Premium).

Scalone 2026-11-15 z pages/1_sygnal_gem.py i pages/17_sygnaly.py.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import get_risk_free, render_footer
from components.auth import is_premium, premium_teaser
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.downloader import download_prices
from data.momentum import gem_classic_signal, build_ranking, backtest_gem
from components.cards import signal_card, metric_row, top_etf_cards
from components.charts import ranking_bar_chart, _base_layout
from components.formatting import MUTED, BG_CARD, BORDER
from components.constants import GREEN

SIGNAL_COLORS = {"QQQ": GREEN, "VEA": "#3B82F6", "EEM": "#A855F7", "ACWI": "#06B6D4", "AGG": "#F59E0B"}
SIGNAL_LABELS = {"QQQ": "Akcje USA", "VEA": "Rynki rozwinięte", "EEM": "Rynki wschodzace",
                 "ACWI": "Globalne", "AGG": "Obligacje"}


def render_now(rf: float) -> None:
    """Tresc dawnej strony 1_sygnal_gem.py (od '# Pobierz dane' do konca expandera)."""
    ...  # wklej tu


def build_signal_periods(rf: float):
    """Z dawnej 17_sygnaly.py: pobranie period='max' + backtest_gem + signal_periods.
    Zwraca (prices, signal_periods) albo None, gdy brak danych."""
    ...  # wklej tu


def render_history_tab(prices, signal_periods) -> None:   # dawny tab2 "Timeline"
    ...
def render_stats_tab(prices, signal_periods) -> None:     # dawny tab3 "Statystyki"
    ...
def render_calendar_tab(prices, signal_periods) -> None:  # dawny tab4 "Kalendarz"
    ...


st.markdown("# 🎯 Sygnał GEM")
rf = get_risk_free()

tab_now, tab_hist, tab_stats, tab_cal = st.tabs(["🎯 Teraz", "📜 Historia", "📊 Statystyki", "📅 Kalendarz"])

with tab_now:
    render_now(rf)

if is_premium():
    data = build_signal_periods(rf)
    if data is None:
        for t in (tab_hist, tab_stats, tab_cal):
            with t:
                st.error("Brak wystarczajacych danych do obliczenia historii sygnalow.")
    else:
        prices_hist, periods = data
        with tab_hist:
            render_history_tab(prices_hist, periods)
        with tab_stats:
            render_stats_tab(prices_hist, periods)
        with tab_cal:
            render_calendar_tab(prices_hist, periods)
else:
    for t, name in ((tab_hist, "Historia sygnałów"), (tab_stats, "Statystyki sygnałów"), (tab_cal, "Kalendarz sygnałów")):
        with t:
            premium_teaser(name, "Pełna historia zmian sygnału GEM, czas trwania pozycji i alokacja w czasie.")

render_footer()
```

Wypełnianie funkcji (mechanicznie, bez zmian logiki):
1. `render_now`: przenieś z `pages/1_sygnal_gem.py` wszystko od `# Pobierz dane` do końca bloku `with st.expander("Jak czytac sygnal GEM?")` (bez `render_footer()`), zmieniając `rf = get_risk_free()` na użycie parametru `rf`. Nagłówek `st.markdown("# 🎯 Sygnal GEM")` nie wchodzi (jest wyżej).
2. `build_signal_periods`: przenieś z `pages/17_sygnaly.py` blok `with st.spinner(...)` oraz budowę `signal_periods`. Zamień:
   ```python
   if result is None:
       st.error("Brak wystarczajacych danych do obliczenia historii sygnalow.")
       render_footer()
       st.stop()
   ```
   na `if result is None: return None`. Na końcu `return prices, signal_periods`.
3. Zawartość dawnego `with tab1:` z 17 („Obecny sygnał”) **nie** jest przenoszona — dubluje zakładkę *Teraz*.
4. Zawartości `with tab2:`, `with tab3:`, `with tab4:` z 17 przenieś do `render_history_tab` / `render_stats_tab` / `render_calendar_tab` (dedent o 4 spacje). Jeżeli treść któregoś taba używa zmiennych z modułu 17 innych niż `prices`, `signal_periods`, `signals`, `result`, `SIGNAL_COLORS`, `SIGNAL_LABELS` — dodaj je jako parametry albo policz w `build_signal_periods` i zwróć w krotce (sprawdź `grep -n` po nazwach zmiennych użytych w tabach).
5. Każde `st.stop()` wewnątrz przeniesionych funkcji zamień na `return` (w `st.tabs` `st.stop()` zabija cały skrypt, w tym pozostałe zakładki).

- [ ] **Step 2: Usuń źródła**

```bash
git rm -q pages/1_sygnal_gem.py pages/17_sygnaly.py
```

- [ ] **Step 3: Sprawdź składnię i brak `st.stop()`**

```bash
venv/Scripts/python.exe -m py_compile pages/strategia/sygnal.py && echo OK
grep -n "st.stop()" pages/strategia/sygnal.py
```
Expected: `OK`, grep bez wyników.

- [ ] **Step 4: Test renderu (sieć)**

Run:
```bash
RUN_NETWORK=1 venv/Scripts/python.exe - <<'EOF'
from streamlit.testing.v1 import AppTest
for prem in (True, False):
    at = AppTest.from_file("app.py", default_timeout=300)
    at.session_state["premium"] = prem; at.session_state["_auth_retries"] = 3
    at.switch_page("pages/strategia/sygnal.py").run()
    print("premium" if prem else "free", "exception:", at.exception, "tabs:", len(at.tabs))
EOF
```
Expected: oba przebiegi `exception: []`, `tabs: 4` (lub więcej, jeśli treść zakładek ma własne podzakładki).

- [ ] **Step 5: Commit**

```bash
git add pages/strategia/sygnal.py
git commit -m "Merge GEM signal and signal history into one tabbed page

Now tab stays free; history, stats and calendar tabs are premium.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Scalenie — Porównaj

**Files:**
- Rewrite: `pages/etf/porownaj.py` (z `pages/3_wykresy.py` + `pages/4_porownanie.py` + `pages/21_side_by_side.py`)
- Delete: te trzy źródła

- [ ] **Step 1: Zbuduj plik**

Struktura docelowa `pages/etf/porownaj.py`:
```python
"""Porownaj — wykresy, head-to-head z korelacjami i side-by-side.

Scalone 2026-11-15 z pages/3_wykresy.py, 4_porownanie.py, 21_side_by_side.py.
Kazda zakladka ma wlasne kontrolki (klucze widgetow z prefiksem wyk_/h2h_/sbs_).
"""
import streamlit as st
import pandas as pd
from components.sidebar import get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES, SP500_SECTOR_MAP
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES, GPW_CATEGORY_MAP
from data.crypto_universe import CRYPTO_BY_MCAP, CRYPTO_NAMES, CRYPTO_CATEGORY_MAP
from data.downloader import (benchmark_status, download_single, download_stooq, STOOQ_TICKERS)
from data.momentum import latest_returns, correlation_matrix, calc_stats, relative_strength
from components.charts import (price_chart, momentum_chart, drawdown_chart,
                               correlation_heatmap, rs_chart)
from components.cards import comparison_card, stats_table


def render_charts_tab() -> None:
    """Tresc dawnej 3_wykresy.py (od '# Wybor ETF-ow' do konca, bez render_footer)."""
    ...


def render_h2h_tab() -> None:
    """Tresc dawnej 4_porownanie.py (od '# Indeksy GPW' do konca, bez render_footer)."""
    ...


def render_side_by_side_tab() -> None:
    """Tresc dawnej 21_side_by_side.py (od '# --- Polaczony universe ---' do konca, bez render_footer)."""
    ...


st.markdown("# ⚖️ Porównaj")
tab_charts, tab_h2h, tab_sbs = st.tabs(["📈 Wykresy", "⚖️ Head-to-head", "🔀 Side-by-side"])
with tab_charts:
    render_charts_tab()
with tab_h2h:
    render_h2h_tab()
with tab_sbs:
    render_side_by_side_tab()

render_footer()
```

Wypełnianie (mechanicznie):
1. Przenieś ciała stron do funkcji (wcięcie +4). Importy ze źródeł są już zebrane wyżej — jeśli kompilacja zgłosi brakującą nazwę, dopisz jej import u góry.
2. Każde `st.stop()` → `return` (źródła: `4_porownanie.py` ×2, `21_side_by_side.py` ×2).
3. Nagłówki stron (`st.markdown("# 📉 Wykresy")`, `"# ⚖️ Porownanie"`, `"# 🔀 Side-by-Side"`) zamień na `st.caption(...)` z jednym zdaniem albo usuń — tytuł jest nad zakładkami.
4. **Klucze widgetów** — dwa widgety o tym samym typie, etykiecie i parametrach na jednej stronie dają `DuplicateWidgetID`. Dodaj `key=` każdemu widgetowi bez klucza:
   - `render_charts_tab`: `st.multiselect("Wybierz ETF-y (maks. 5)", ..., key="wyk_sel")`, `st.selectbox("Okres", ..., key="wyk_period")`, `st.checkbox("Normalizuj (baza = 100)", ..., key="wyk_norm")`, `st.slider("Okno momentum (dni)", ..., key="wyk_window")`
   - `render_h2h_tab`: `st.multiselect("Wybierz 2-4 instrumenty do porownania", ..., key="h2h_sel")`, `st.selectbox("Okres", ..., key="h2h_period")`; `rs_bench` już ma klucz — zmień na `key="h2h_rs_bench"`
   - `render_side_by_side_tab`: klucze `sbs_a`, `sbs_b`, `sbs_period` już są — bez zmian
   Zweryfikuj: `grep -nE "st\.(multiselect|selectbox|radio|slider|checkbox|toggle|number_input|text_input|button)\(" pages/etf/porownaj.py` — każde wystąpienie ma `key=` w swoim wywołaniu (może być w kolejnej linii).

- [ ] **Step 2: Usuń źródła**

```bash
git rm -q pages/3_wykresy.py pages/4_porownanie.py pages/21_side_by_side.py
```

- [ ] **Step 3: Składnia i brak `st.stop()`**

```bash
venv/Scripts/python.exe -m py_compile pages/etf/porownaj.py && echo OK
grep -n "st.stop()" pages/etf/porownaj.py
```
Expected: `OK`, grep pusty.

- [ ] **Step 4: Test renderu (sieć)**

```bash
RUN_NETWORK=1 venv/Scripts/python.exe - <<'EOF'
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=300)
at.session_state["premium"] = True; at.session_state["_auth_retries"] = 3
at.switch_page("pages/etf/porownaj.py").run()
print("exception:", at.exception, "tabs:", len(at.tabs))
EOF
```
Expected: `exception: []`, `tabs` ≥ 3.

- [ ] **Step 5: Commit**

```bash
git add pages/etf/porownaj.py
git commit -m "Merge charts, head-to-head and side-by-side into Porownaj page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Dane Pulpitu — `data/market_status.py`

**Files:**
- Create: `data/market_status.py`
- Create: `tests/test_market_status.py`

- [ ] **Step 1: Napisz testy czystych funkcji**

`tests/test_market_status.py`:
```python
"""Czyste funkcje Pulpitu — bez sieci, na syntetycznych danych."""
import numpy as np
import pandas as pd
import pytest

from data import market_status as ms


def _series(values, start="2026-01-01"):
    idx = pd.bdate_range(start, periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


# --- compute_regime -------------------------------------------------------

def test_regime_risk_on():
    up = _series(np.linspace(100, 130, 80))
    down = _series(np.linspace(100, 80, 80))
    data = {"SPY": up, "^TNX": up, "GC=F": down, "DX-Y.NYB": down, "CL=F": up}
    r = ms.compute_regime(data)
    assert r["label"] == "Risk-On"
    assert r["score"] == pytest.approx(100.0)


def test_regime_risk_off():
    up = _series(np.linspace(100, 130, 80))
    down = _series(np.linspace(100, 80, 80))
    data = {"SPY": down, "^TNX": down, "GC=F": up, "DX-Y.NYB": up, "CL=F": down}
    assert ms.compute_regime(data)["label"] == "Risk-Off"


def test_regime_no_data_is_neutral():
    r = ms.compute_regime({})
    assert r["label"] == "Neutralny"
    assert r["score"] == pytest.approx(50.0)


def test_regime_ignores_short_series():
    short = _series(np.linspace(100, 130, 10))
    assert ms.compute_regime({"SPY": short})["label"] == "Neutralny"


# --- signal_since / next_rebalance_date ------------------------------------

def test_signal_since_returns_last_change():
    signals = [(pd.Timestamp("2025-01-31"), "QQQ"), (pd.Timestamp("2026-08-29"), "VEA")]
    assert ms.signal_since(signals) == (pd.Timestamp("2026-08-29"), "VEA")


def test_signal_since_empty():
    assert ms.signal_since([]) is None


def test_next_rebalance_is_first_business_day_next_month():
    assert ms.next_rebalance_date(pd.Timestamp("2026-11-15")) == pd.Timestamp("2026-12-01")


def test_next_rebalance_skips_weekend():
    # 1 sierpnia 2026 to sobota -> poniedzialek 3 sierpnia
    assert ms.next_rebalance_date(pd.Timestamp("2026-07-20")) == pd.Timestamp("2026-08-03")


# --- daily_change / top_movers ----------------------------------------------

def test_daily_change_uses_last_two_valid_rows():
    prices = pd.DataFrame({"A": [10.0, 11.0], "B": [20.0, 18.0], "C": [np.nan, 5.0]},
                          index=pd.bdate_range("2026-11-12", periods=2))
    chg = ms.daily_change(prices)
    assert chg["A"] == pytest.approx(0.10)
    assert chg["B"] == pytest.approx(-0.10)
    assert "C" not in chg.index  # brak poprzedniej wartosci


def test_daily_change_drops_inf():
    prices = pd.DataFrame({"A": [0.0, 5.0]}, index=pd.bdate_range("2026-11-12", periods=2))
    assert ms.daily_change(prices).empty


def test_top_movers_split():
    chg = pd.Series({"A": 0.05, "B": -0.04, "C": 0.01, "D": -0.10, "E": 0.20})
    gainers, losers = ms.top_movers(chg, n=2)
    assert list(gainers.index) == ["E", "A"]
    assert list(losers.index) == ["D", "B"]


# --- pulpit_earnings_tickers -------------------------------------------------

def test_earnings_tickers_watchlist_first_and_dedup():
    out = ms.pulpit_earnings_tickers({"CDR.WA", "AAPL"})
    assert out[:2] == sorted(["CDR.WA", "AAPL"])
    assert len(out) == len(set(out))
    assert "MSFT" in out
```

- [ ] **Step 2: Uruchom — ma paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_market_status.py -q`
Expected: FAIL — `ImportError: cannot import name 'market_status'`

- [ ] **Step 3: Napisz moduł**

`data/market_status.py`:
```python
"""Dane Pulpitu — czyste funkcje (testowalne offline) + cienkie wrappery pobierajace."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from data.gpw_universe import GPW_CATEGORIES

# Kafelki "Wskazniki rynku": (ticker yfinance, etykieta)
MARKET_TILES = [
    ("^VIX", "VIX"),
    ("^GSPC", "S&P 500"),
    ("WIG20.WA", "WIG20"),
    ("PLN=X", "USD/PLN"),
    ("GC=F", "Złoto"),
    ("BTC-USD", "Bitcoin"),
]

REGIME_TICKERS = {"SPY": "S&P 500", "^TNX": "Obligacje (10Y yield)", "GC=F": "Zloto",
                  "DX-Y.NYB": "Dolar (DXY)", "CL=F": "Ropa WTI"}

# Waga i kierunek: +1 = wzrost 3M oznacza risk-on, -1 = wzrost oznacza risk-off
_REGIME_RULES = {"SPY": (2, +1), "^TNX": (1, +1), "GC=F": (1, -1), "DX-Y.NYB": (1, -1), "CL=F": (1, +1)}

MEGA_CAPS_US = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "JPM", "LLY", "V", "WMT"]


def compute_regime(series_by_ticker: dict[str, pd.Series]) -> dict:
    """Risk-On/Off z momentum 3M (63 sesje) — logika 1:1 z dawnego Podsumowania."""
    on = off = 0
    for ticker, s in series_by_ticker.items():
        rule = _REGIME_RULES.get(ticker)
        if rule is None or s is None or len(s) <= 63:
            continue
        weight, direction = rule
        mom = s.iloc[-1] / s.iloc[-63] - 1
        if not np.isfinite(mom):
            continue
        if (mom > 0) == (direction > 0):
            on += weight
        else:
            off += weight
    total = on + off
    score = on / total * 100 if total > 0 else 50.0
    if score >= 65:
        label, desc = "Risk-On", "Srodowisko sprzyjajace akcjom"
    elif score <= 35:
        label, desc = "Risk-Off", "Awersja do ryzyka — rozwazyc obligacje"
    else:
        label, desc = "Neutralny", "Mieszane sygnaly miedzy klasami aktywow"
    return {"label": label, "desc": desc, "score": float(score)}


def signal_since(signals: list[tuple[pd.Timestamp, str]]) -> tuple[pd.Timestamp, str] | None:
    """Ostatnia zmiana sygnalu z backtest_gem(...)['signals']."""
    return tuple(signals[-1]) if signals else None


def next_rebalance_date(today: pd.Timestamp) -> pd.Timestamp:
    """Pierwszy dzien roboczy (pon–pt) nastepnego miesiaca."""
    first = (pd.Timestamp(today).normalize() + pd.offsets.MonthBegin(1))
    while first.weekday() >= 5:
        first += pd.Timedelta(days=1)
    return first


def daily_change(prices: pd.DataFrame) -> pd.Series:
    """Zmiana ostatniej sesji per kolumna; pomija braki i inf."""
    out = {}
    for col in prices.columns:
        s = prices[col].dropna()
        if len(s) < 2:
            continue
        chg = s.iloc[-1] / s.iloc[-2] - 1
        if np.isfinite(chg):
            out[col] = float(chg)
    return pd.Series(out, dtype=float)


def top_movers(changes: pd.Series, n: int = 5) -> tuple[pd.Series, pd.Series]:
    s = changes.dropna()
    return s.sort_values(ascending=False).head(n), s.sort_values().head(n)


def pulpit_earnings_tickers(watchlist: set[str]) -> list[str]:
    """Watchlista (posortowana) + mega-capy USA + WIG20, bez duplikatow."""
    ordered = sorted(watchlist) + MEGA_CAPS_US + list(GPW_CATEGORIES["WIG20"].keys())
    seen, out = set(), []
    for t in ordered:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def market_movers(universe: tuple[str, ...]) -> pd.Series:
    """Zmiana dzienna dla calego universe — cache 1 h wspolny dla wszystkich uzytkownikow."""
    from data.downloader import download_prices
    prices = download_prices(list(universe), period="5d")
    return daily_change(prices)
```

- [ ] **Step 4: Uruchom — ma przejść**

Run: `venv/Scripts/python.exe -m pytest tests/test_market_status.py -q`
Expected: `13 passed`

- [ ] **Step 5: Sprawdź symbole kafelków (sieć, jednorazowo)**

```bash
venv/Scripts/python.exe - <<'EOF'
from data.downloader import _yfinance_single
for t in ["^VIX","^GSPC","WIG20.WA","PLN=X","GC=F","BTC-USD"]:
    s = _yfinance_single(t, period="1mo")
    print(t, None if s is None else (len(s), round(float(s.iloc[-1]), 2)))
EOF
```
Expected: każdy symbol zwraca dane. Jeśli `WIG20.WA` zwraca `None`, zamień w `MARKET_TILES` na `("ETFBW20TR.WA", "WIG20 (ETF Beta)")` — to samo źródło, którego używa benchmark WIG20 (commit `e7938c2`) — i powtórz. Jeśli `PLN=X` zwraca kurs PLN za USD poniżej 1, zamień na `"USDPLN=X"`.

- [ ] **Step 6: Commit**

```bash
git add data/market_status.py tests/test_market_status.py
git commit -m "Add pure market status helpers for the Pulpit page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Pulpit

**Files:**
- Rewrite: `pages/start/pulpit.py` (z treści `pages/0_podsumowanie.py`)
- Delete: `pages/0_podsumowanie.py`

- [ ] **Step 1: Napisz stronę**

`pages/start/pulpit.py`:
```python
"""Pulpit — centrum dowodzenia (domyslna strona).

Darmowe: wyszukiwarka, pasek stanu, Top 5 ETF.
Premium: watchlista, wyniki tygodnia, wygrani/przegrani, wyniki strategii 5 lat, eksport PDF.
Kazda karta renderuje sie niezaleznie — blad w jednej nie psuje reszty.
"""
import pandas as pd
import streamlit as st
from streamlit_local_storage import LocalStorage

from components import nav
from components.auth import is_premium, premium_teaser
from components.cards import (signal_card, top_etf_cards, stats_table,
                              data_status_card, alert_banner)
from components.charts import sparkline_chart
from components.constants import GREEN, RED
from components.formatting import color_for_value, MUTED, BG_CARD, BORDER
from components.sidebar import get_risk_free, render_footer
from components.watchlist import get_watchlist
from data import market_status as ms
from data.downloader import download_prices, download_single
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.financials import _detect_market, _status_badge, bulk_fetch_earnings_calendar
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES
from data.momentum import gem_classic_signal, build_ranking, backtest_gem
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES

REGIME_COLORS = {"Risk-On": GREEN, "Risk-Off": RED, "Neutralny": "#F59E0B"}
PREMIUM = is_premium()


def unavailable(title: str) -> None:
    st.caption(f"{title}: dane chwilowo niedostępne")


def card(title: str, value: str, sub: str, border: str = BORDER) -> None:
    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {border};border-radius:14px;padding:16px;height:100%">'
        f'<div style="font-size:0.7rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.08em">{title}</div>'
        f'<div style="font-size:1.4rem;font-weight:800;color:#E5E7EB;margin:6px 0">{value}</div>'
        f'<div style="font-size:0.8rem;color:{MUTED}">{sub}</div></div>'
    )


# --- 1. Alerty cenowe (logika z dawnego Podsumowania, F1) --------------------
def render_alerts() -> None:
    periods = {"1D": 1, "1W": 5, "1M": 21}
    for a in st.session_state.get("alerts", []):
        s = download_single(a["ticker"], period="3mo")
        days = periods.get(a["period"], 1)
        if s is not None and len(s) > days:
            alert_banner(a["ticker"], a["condition"], a["threshold"], a["period"],
                         s.iloc[-1] / s.iloc[-1 - days] - 1)


# --- 2. Wyszukiwarka ---------------------------------------------------------
def _on_search() -> None:
    """Callback: ustaw deep-dive i wyczysc pole (w callbacku wolno zmienic stan widgetu)."""
    choice = st.session_state.get("pulpit_search")
    if not choice:
        return
    prefix = "sp500" if _detect_market(choice) == "SP500" else "gpw"
    st.session_state[f"{prefix}_deep_dive_ticker"] = choice
    st.session_state[f"{prefix}_pending_view"] = "deep_dive"
    st.session_state["pulpit_search"] = ""
    st.session_state["_pulpit_go"] = prefix


def render_search() -> None:
    names = {**SP500_NAMES, **GPW_NAMES}
    options = [""] + sorted(names, key=lambda t: names[t])
    st.selectbox(
        "🔎 Szukaj spółki (S&P 500 i GPW)", options, key="pulpit_search", on_change=_on_search,
        format_func=lambda t: "Wpisz nazwę lub ticker…" if not t else f"{t} — {names[t]}",
    )
    target = st.session_state.pop("_pulpit_go", None)
    if target:
        nav.go(target)


# --- 3. Pasek stanu ----------------------------------------------------------
def render_status_bar(prices: pd.DataFrame, rf: float) -> None:
    c_sig, c_reg, c_mkt = st.columns([2, 1, 2])
    with c_sig:
        try:
            signal_card(gem_classic_signal(prices, rf))
            hist = backtest_gem(download_prices(["QQQ", "VEA", "EEM", "ACWI", "AGG"], period="max"), rf)
            since = ms.signal_since(hist["signals"]) if hist else None
            nxt = ms.next_rebalance_date(pd.Timestamp.now())
            if since:
                st.caption(f"Pozycja od {since[0]:%d.%m.%Y} · następne przeliczenie: {nxt:%d.%m.%Y}")
        except Exception:
            unavailable("Sygnał GEM")
    with c_reg:
        try:
            data = {t: download_single(t, period="1y") for t in ms.REGIME_TICKERS}
            r = ms.compute_regime({t: s for t, s in data.items() if s is not None})
            card("Regime rynku", r["label"], f'{r["desc"]} · score {r["score"]:.0f}%',
                 border=REGIME_COLORS[r["label"]])
        except Exception:
            unavailable("Regime rynku")
    with c_mkt:
        cols = st.columns(3)
        for i, (ticker, label) in enumerate(ms.MARKET_TILES):
            with cols[i % 3]:
                s = download_single(ticker, period="1mo")
                chg = ms.daily_change(s.to_frame(ticker)) if s is not None else pd.Series(dtype=float)
                if s is None or chg.empty:
                    unavailable(label)
                    continue
                c = float(chg.iloc[0])
                st.html(
                    f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;'
                    f'padding:8px;text-align:center;margin-bottom:6px">'
                    f'<div style="font-size:0.65rem;color:{MUTED}">{label}</div>'
                    f'<div style="font-weight:700;color:#E5E7EB">{s.iloc[-1]:,.2f}</div>'
                    f'<div style="font-size:0.75rem;color:{color_for_value(c)}">{c*100:+.2f}%</div></div>'
                )


# --- 4. Trzy kolumny (Premium) ------------------------------------------------
def render_watchlist(ls) -> None:
    st.markdown("#### ⭐ Moja watchlista")
    tickers = sorted(get_watchlist(ls) | set(st.session_state.get("favorites", set())))
    if not tickers:
        st.caption("Pusta. Dodaj spółki gwiazdką ⭐ w S&P 500 / GPW albo w sidebarze (Ulubione).")
        return
    for t in tickers[:10]:
        s = download_single(t, period="3mo")
        chg = ms.daily_change(s.to_frame(t)) if s is not None else pd.Series(dtype=float)
        if s is None or chg.empty:
            st.caption(f"{t}: brak danych")
            continue
        c1, c2 = st.columns([1, 1])
        c1.markdown(f"**{t}** {s.iloc[-1]:,.2f}  \n"
                    f"<span style='color:{color_for_value(chg.iloc[0])}'>{chg.iloc[0]*100:+.2f}%</span>",
                    unsafe_allow_html=True)
        c2.plotly_chart(sparkline_chart(s, height=50), width="stretch", key=f"wl_spark_{t}")


def render_week_earnings(ls) -> None:
    st.markdown("#### 📅 Wyniki w tym tygodniu")
    tickers = tuple(ms.pulpit_earnings_tickers(get_watchlist(ls)))
    df = bulk_fetch_earnings_calendar(tickers, window_days=7)
    if df is None or df.empty:
        st.caption("Brak raportów w tym tygodniu dla watchlisty i największych spółek.")
        return
    order = {t: i for i, t in enumerate(tickers)}
    df = df.assign(_o=df["ticker"].map(order)).sort_values(["_o", "date"]).head(10)
    for _, r in df.iterrows():
        st.markdown(f"**{r['ticker']}** · {r['date']:%d.%m} · "
                    f"{_status_badge(r['date'], r.get('eps_actual'), r.get('eps_estimate'))}")


@st.fragment
def render_movers() -> None:
    st.markdown("#### 🔥 Wygrani / przegrani dnia")
    for label, universe in (("S&P 500", ALL_SP500_TICKERS), ("GPW", ALL_GPW_TICKERS)):
        with st.spinner(f"Liczę zmiany {label}…"):
            try:
                gainers, losers = ms.top_movers(ms.market_movers(tuple(universe)), n=5)
            except Exception:
                unavailable(label)
                continue
        if gainers.empty:
            unavailable(label)
            continue
        st.caption(label)
        g, l = st.columns(2)
        g.dataframe((gainers * 100).round(2).rename("% d/d"), width="stretch")
        l.dataframe((losers * 100).round(2).rename("% d/d"), width="stretch")


# --- 5. Top 5 ETF + wyniki 5 lat ------------------------------------------------
def render_top_etf(prices: pd.DataFrame, rf: float):
    st.markdown("### Top 5 ETF wg momentum")
    names, cats = dict(ETF_NAMES), dict(ETF_CATEGORY_MAP)
    for t in st.session_state.get("custom_tickers", []):
        names.setdefault(t, t)
        cats.setdefault(t, "Wlasne")
    ranking = build_ranking(prices, rf, skip_month=False).dropna(subset=["Wynik"])
    if ranking.empty:
        unavailable("Ranking ETF")
    else:
        top_etf_cards(ranking, names, cats, n=5)
    return ranking, names


def render_strategy_5y(rf: float):
    st.markdown("### Wyniki strategii (5 lat)")
    bt = backtest_gem(download_prices(["QQQ", "VEA", "EEM", "ACWI", "AGG"], period="7y"), rf)
    if bt is None:
        st.info("Za malo danych do backtestu GEM (wymagane 252+ sesji).")
        return None
    show = {k: bt["stats"][k] for k in ("GEM", "QQQ B&H", "ACWI B&H", "AGG B&H") if k in bt["stats"]}
    if show:
        stats_table(show)
    return show


# =============================================================================
st.markdown("# 📈 Pulpit")
render_alerts()
render_search()

tickers = list(set(ALL_TICKERS + st.session_state.get("custom_tickers", [])))
prices = download_prices(tickers)
rf = get_risk_free()

render_status_bar(prices, rf)
st.divider()

col_wl, col_earn, col_mov = st.columns(3)
ls = LocalStorage()
if PREMIUM:
    with col_wl:
        render_watchlist(ls)
    with col_earn:
        try:
            render_week_earnings(ls)
        except Exception:
            unavailable("Wyniki w tym tygodniu")
    with col_mov:
        render_movers()
else:
    with col_wl:
        premium_teaser("⭐ Moja watchlista", "Twoje spółki z ceną, zmianą dnia i mini-wykresem.")
    with col_earn:
        premium_teaser("📅 Wyniki w tym tygodniu", "Kto raportuje w tym tygodniu — najpierw Twoje spółki.")
    with col_mov:
        premium_teaser("🔥 Wygrani i przegrani", "Największe zmiany dnia w S&P 500 i na GPW.")

st.divider()
ranking, names = render_top_etf(prices, rf)

if PREMIUM:
    show_stats = render_strategy_5y(rf)
    # Eksport PDF — logika 1:1 z dawnego Podsumowania (sekcja 6), z danymi z funkcji wyzej
    with st.expander("📄 Eksport raportu PDF"):
        st.caption("Raport: sygnał GEM, Top 5 ETF, statystyki strategii, ranking top 10")
        if st.button("Generuj raport PDF", key="pdf_gen_btn"):
            from components.pdf_report import generate_report
            sections = {"gem_signal": gem_classic_signal(prices, rf)}
            if not ranking.empty:
                sections["top_etfs"] = [(t, names.get(t, t), row.get("Wynik", 0))
                                        for t, row in ranking.head(5).iterrows()]
                sections["ranking_top10"] = [(t, names.get(t, t), row.get("Wynik", 0),
                                              row.get("Momentum_abs", "—"))
                                             for t, row in ranking.head(10).iterrows()]
            if show_stats:
                sections["backtest_stats"] = show_stats
            st.download_button("📥 Pobierz PDF", data=generate_report(sections),
                               file_name=f"gem_raport_{pd.Timestamp.now():%Y%m%d}.pdf",
                               mime="application/pdf")
else:
    premium_teaser("Wyniki strategii (5 lat)", "GEM vs QQQ, ACWI i obligacje: CAGR, Sharpe, max drawdown.")

with st.expander("Status danych"):
    data_status_card()

render_footer()
```

- [ ] **Step 2: Usuń źródło**

```bash
git rm -q pages/0_podsumowanie.py
```

- [ ] **Step 3: Składnia**

Run: `venv/Scripts/python.exe -m py_compile pages/start/pulpit.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Test renderu z Premium i bez (sieć)**

```bash
RUN_NETWORK=1 venv/Scripts/python.exe - <<'EOF'
from streamlit.testing.v1 import AppTest
for prem in (True, False):
    at = AppTest.from_file("app.py", default_timeout=600)
    at.session_state["premium"] = prem; at.session_state["_auth_retries"] = 3
    at.run()
    html = " ".join(e.proto.body for e in at.get("html"))
    print("premium" if prem else "free", "| exception:", at.exception, "| teasers:", html.count("🔒"))
EOF
```
Expected: oba `exception: []`; bez Premium `teasers` = 4 (trzy kolumny + wyniki 5 lat), z Premium = 0.

Jeśli `render_week_earnings` sypie się na kolumnie `date` (typ), dodaj na początku `df["date"] = pd.to_datetime(df["date"])`.

- [ ] **Step 5: Commit**

```bash
git add pages/start/pulpit.py
git commit -m "Add command-center Pulpit as the default page

Search, GEM status bar, market tiles and Top 5 ETF are free;
watchlist, weekly earnings, daily movers, 5y stats and PDF export are premium.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Domknięcie testów rejestru i starych testów

**Files:**
- Modify: `tests/test_nav.py`
- Modify: `tests/test_stopy_zwrotu_page.py`

- [ ] **Step 1: Rozszerz testy rejestru na wszystkie strony**

W `tests/test_nav.py` zamień definicję `MIGRATED = [...]` na:
```python
MIGRATED = list(nav.PAGES)
```
i dopisz:
```python
def test_no_top_level_numbered_pages_left():
    assert not list((ROOT / "pages").glob("*.py"))


def test_every_page_file_is_registered():
    on_disk = {p.relative_to(ROOT).as_posix() for p in (ROOT / "pages").glob("*/*.py")}
    assert on_disk == {p.path for p in nav.PAGES}
```

- [ ] **Step 2: Popraw `tests/test_stopy_zwrotu_page.py`**

Usuń `test_menu_order_between_info_and_sp500`, `test_sidebar_separators_shifted`, `test_home_card_before_sp500` oraz nieużywane już importy `page_sort_key` i stałą `PAGES`. W `test_page_renders` zamień uruchomienie strony na router:
```python
APP = Path(__file__).resolve().parents[1] / "app.py"
...
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.session_state["premium"] = True
    at.session_state["_auth_retries"] = 3
    at.switch_page("pages/etf/stopy_zwrotu.py").run()
```
(pierwsze `at.run()` w teście zastępuje `.switch_page(...).run()`; reszta asercji bez zmian). Zaktualizuj docstring modułu na `"""Strona Stopy zwrotu (pages/etf/stopy_zwrotu.py): smoke test renderowania."""`.

- [ ] **Step 3: Sprawdź pozostałe testy pod kątem starych ścieżek**

Run: `grep -rn "pages/[0-9]" tests/`
Expected: tylko docstring w `tests/test_calendar.py` — zmień go na `"""Testy dla pages/spolki/kalendarz_wynikow.py + watchlist + earnings calendar helpers."""`.

- [ ] **Step 4: Pełna suita offline**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: wszystkie przechodzą (sieciowe `skipped`); liczba `passed` = punkt odniesienia z Task 1 − 3 usunięte testy + nowe (`test_nav`, `test_auth_api`, `test_auth_gate`, `test_market_status`).

- [ ] **Step 5: Commit**

```bash
git add tests/test_nav.py tests/test_stopy_zwrotu_page.py tests/test_calendar.py
git commit -m "Align tests with section folders and router

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Smoke test wszystkich stron (sieć)

**Files:**
- Create: `tests/test_pages_smoke.py`

- [ ] **Step 1: Napisz test**

`tests/test_pages_smoke.py`:
```python
"""Smoke test: kazda strona z rejestru renderuje sie przez router z Premium.

Sieciowy (yfinance/stooq) — uruchamiaj: RUN_NETWORK=1 pytest tests/test_pages_smoke.py
"""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from components import nav

APP = str(Path(__file__).resolve().parents[1] / "app.py")

pytestmark = pytest.mark.skipif(os.environ.get("RUN_NETWORK") != "1",
                                reason="smoke test sieciowy: RUN_NETWORK=1")


@pytest.mark.parametrize("page", nav.PAGES, ids=lambda p: p.key)
def test_page_renders_with_premium(page):
    at = AppTest.from_file(APP, default_timeout=900)
    at.session_state["premium"] = True
    at.session_state["_auth_retries"] = 3
    at.switch_page(page.path).run()
    assert not at.exception, f"{page.key}: {at.exception}"
```

- [ ] **Step 2: Uruchom**

Run: `RUN_NETWORK=1 venv/Scripts/python.exe -m pytest tests/test_pages_smoke.py -q`
Expected: `24 passed` (może trwać kilkanaście minut: S&P 500, GPW, Insiderzy i Kalendarz pobierają setki tickerów przy zimnym cache).

Każdy błąd napraw w pliku strony (typowo: nazwa usunięta przez skrypt z Task 3, brakujący import po scaleniu, `DuplicateWidgetID`). Po każdej poprawce uruchom ponownie tylko daną stronę: `RUN_NETWORK=1 venv/Scripts/python.exe -m pytest tests/test_pages_smoke.py -q -k <key>`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_pages_smoke.py
git commit -m "Add network smoke test for every registered page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
(oraz poprawki stron, jeśli były — wymień pliki jawnie w `git add`)

---

### Task 12: Przegląd wizualny z użytkownikiem

**Files:** brak (chyba że wyjdą poprawki)

- [ ] **Step 1: Uruchom aplikację lokalnie**

Run (w tle): `cd /c/Users/m4x/Desktop/AI/gem-dashboard && venv/Scripts/python.exe -m streamlit run app.py --server.port 8502 --server.headless true`

- [ ] **Step 2: Poproś użytkownika o sprawdzenie**

Przekaż adres `http://localhost:8502` i listę do obejrzenia:
1. Górne menu: Pulpit | Strategia GEM ▾ | ETF ▾ | Spółki ▾ | Krypto | Portfel ▾ | Rynek ▾
2. Pulpit bez Premium (zaślepki) i z Premium (kod aktywacyjny w sidebarze)
3. Wyszukiwarka → przejście do S&P 500/GPW na wybraną spółkę
4. Sygnał GEM: zakładka Teraz bez Premium, pozostałe z zaślepkami
5. Porównaj: 3 zakładki, niezależne kontrolki
6. Kalendarz wyników → „Deep dive” przenosi do S&P 500/GPW
7. Widok telefonu (DevTools, szerokość 390 px): menu pod ☰

- [ ] **Step 3: Wprowadź poprawki z uwag**

Każdą uwagę wprowadź w odpowiednim pliku, uruchom testy offline (`venv/Scripts/python.exe -m pytest -q`) i commituj osobno z opisem poprawki. Zatrzymaj serwer po akceptacji.

---

### Task 13: Dokumentacja

**Files:**
- Modify: `CLAUDE.md` (repo gem-dashboard)
- Modify: `C:\Users\m4x\.claude\skills\gem-dashboard-page\SKILL.md`
- Modify: `C:\Users\m4x\.claude\skills\gem-dashboard-audit\SKILL.md`
- Modify: `C:\Users\m4x\.claude\skills\gem-dashboard-deploy\SKILL.md` (tylko jeśli zawiera ścieżki `pages/N_...`)

- [ ] **Step 1: `CLAUDE.md` projektu**

Znajdź sekcje opisujące strony (`grep -n "pages/" CLAUDE.md`) i:
1. Zastąp opis „`pages/N_nazwa.py` + aktualizacja `app.py` i separatorów sidebar” opisem: „strona = plik w `pages/<sekcja>/` + wpis `PageDef` w `components/nav.py` (sekcja, `free`, `description`; adres URL = nazwa pliku); dostęp Premium sprawdza router (`app.py`); strony częściowo darmowe używają `is_premium()` + `premium_teaser()`; linki między stronami tylko przez `nav.go(key)` / `nav.link(key)`”.
2. Dodaj tabelę „stary plik → nowy plik” (z sekcji „Mapa stron” specyfikacji).
3. Usuń wszelkie wzmianki o `FREE_PAGES`, `PAGE_INFO`, `require_premium(N)` i `nth-child` w sidebarze.

- [ ] **Step 2: Skille**

W każdym ze skilli: `grep -n "pages/[0-9]\|require_premium\|FREE_PAGES\|nth-child\|app.py" <SKILL.md>` i zaktualizuj instrukcje do nowej konwencji z kroku 1 (szablon nowej strony: bez `st.set_page_config`, bez `setup_sidebar()`, bez `require_premium`; zaczyna się od importów i `st.markdown("# ...")`, kończy `render_footer()`).

- [ ] **Step 3: Commit (repo)**

```bash
git add CLAUDE.md
git commit -m "Document section folders, page registry and router gating

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
(Skille leżą poza repo — bez commita.)

---

### Task 14: Wdrożenie (po akceptacji użytkownika)

**Files:** brak

- [ ] **Step 1: Ostateczna weryfikacja**

```bash
venv/Scripts/python.exe -m pytest -q
RUN_NETWORK=1 venv/Scripts/python.exe -m pytest tests/test_pages_smoke.py -q
```
Expected: oba zielone.

- [ ] **Step 2: Zapytaj użytkownika o zgodę na merge i push**

Bez wyraźnego „tak” nie scalaj.

- [ ] **Step 3: Merge i push (skill `gem-dashboard-deploy`)**

```bash
git checkout main
git merge --no-ff restructure-nav -m "Merge restructure-nav: top navigation, page registry, Pulpit

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin main
```

- [ ] **Step 4: Weryfikacja na Streamlit Cloud**

Po redeployu (2–5 min) otwórz `https://gem-dashboard.streamlit.app/`: Pulpit ładuje się, każda sekcja menu otwiera strony, strona płatna bez Premium pokazuje ekran blokady. Jeśli Cloud pokazuje ekran logowania `/-/login`, najpierw Reboot aplikacji (pamięć projektu), dopiero potem diagnoza.

- [ ] **Step 5: Wpis do pamięci**

Dodaj wpis w `MEMORY.md` (sekcja „Projekt: gem-dashboard”) z commitem merge, datą i informacją „WGRANE”.
