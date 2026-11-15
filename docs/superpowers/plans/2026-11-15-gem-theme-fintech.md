# GEM Dashboard — szata graficzna „B · Nowoczesny fintech”: plan wdrożenia

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Zamienić ciężką oprawę (złote ramki 2 px, emoji, wersaliki, złoto wszędzie) na styl „nowoczesny fintech” z makiety `.superpowers/brainstorm/6758-1794746663/content/szata-graficzna.html` (wariant B), na wszystkich 24 stronach, bez zmiany logiki ani danych.

**Architecture:** (1) motyw Streamlit w `.streamlit/config.toml`, (2) tokeny kolorów w jednym miejscu `components/constants.py` — strony i karty już ich używają, (3) globalny CSS w `components/sidebar.inject_css`, (4) restyling funkcji w `components/cards.py`, `components/auth.py`, `components/charts._base_layout`, (5) ikony Material w rejestrze nawigacji i nagłówki stron bez emoji, (6) Pulpit 1:1 z makietą (w tym równe karty sygnału i regime — uwaga użytkownika).

**Tech:** Streamlit 1.55 (`[theme]`, `[theme.sidebar]`, `baseRadius`, `borderColor`, `showWidgetBorder`, `chartCategoricalColors`, ikony `:material/...:` w `st.Page`), Plotly.

**Gałąź:** `restructure-nav` (przed merge — jedno wdrożenie nawigacji + wyglądu).

**Konwencje:** jak w `docs/superpowers/plans/2026-11-15-gem-nav-restructure.md` (Git Bash, `venv/Scripts/python.exe`, selektywny `git add`, nie dodawać `okładka.png`, `screen2.png`, `screen3.png`, `docs/superpowers/plans/2026-06-02-finanse-kwartalne.md`, `data/cache/`; stopka commitów `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`). Testy offline muszą być zielone po każdym zadaniu: `venv/Scripts/python.exe -m pytest -q` (stan wyjściowy: 297 passed).

## Tokeny (źródło prawdy — makieta B)

| Token | Wartość | Użycie |
|---|---|---|
| `BG` | `#0E1117` | tło aplikacji |
| `BG2` | `#0B0E14` | sidebar, tło wykresów (przezroczyste w praktyce) |
| `BG_CARD` | `#151922` | karty, kafelki |
| `BG_HOVER` | `#1A1F29` | aktywna zakładka / hover |
| `BORDER` | `#232937` | jedyne obramowania (pola, separatory) — NIE złote |
| `TEXT` | `#E6E8EC` | tekst |
| `MUTED` | `#7C8595` | etykiety, podpisy |
| `GOLD` | `#D4B062` | akcent marki: przycisk główny, aktywne elementy, „pill” |
| `GOLD_SOFT` | `rgba(212,176,98,0.12)` | tło „pill” |
| `GREEN` | `#34D399` | wzrost |
| `RED` | `#F87171` | spadek |
| `AMBER` | `#FBBF24` | neutralny |
| `SHADOW` | `0 1px 0 rgba(255,255,255,.03) inset, 0 8px 24px rgba(0,0,0,.25)` | cień kart |
| `RADIUS` | `14px` (karty), `12px` (kafelki), `10px` (pola) | |
| `CHART_COLORS` | `["#D4B062", "#60A5FA", "#34D399", "#F87171", "#A78BFA", "#FBBF24", "#F472B6", "#22D3EE"]` | |

Zasady stylu: brak ramek wokół kart (tylko cień), żadnych `border:2px solid {kolor}`; kolor sygnału/regime jako kolor wartości lub cienki pasek 3 px po lewej, nie ramka; etykiety zwykłą wielkością liter, 12–13 px, kolor `MUTED`; wartości `font-weight:650`, `font-variant-numeric: tabular-nums`; brak emoji w nagłówkach stron, menu i kartach (emoji zostają tylko w treści merytorycznej, np. flagi w tabelach rynków, jeśli są daną).

---

### Task 1: Motyw i tokeny

**Files:** Modify `.streamlit/config.toml`, `components/constants.py`; Create `tests/test_theme.py`

- [ ] Test `tests/test_theme.py`:
```python
"""Tokeny szaty B — jedno zrodlo prawdy, bez zlotych ramek."""
import tomllib
from pathlib import Path

from components import constants as c

ROOT = Path(__file__).resolve().parents[1]


def test_tokens():
    assert c.BG == "#0E1117"
    assert c.BG_CARD == "#151922"
    assert c.GOLD == "#D4B062"
    assert c.BORDER == "#232937"
    assert len(c.CHART_COLORS) == 8 and c.CHART_COLORS[0] == c.GOLD


def test_streamlit_theme_matches_tokens():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    th = cfg["theme"]
    assert th["backgroundColor"] == c.BG
    assert th["secondaryBackgroundColor"] == c.BG_CARD
    assert th["primaryColor"] == c.GOLD
    assert th["textColor"] == c.TEXT


def test_no_hardcoded_old_gold_in_ui_code():
    offenders = []
    for p in list((ROOT / "views").rglob("*.py")) + list((ROOT / "components").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        if "#C9A84C|201,168,76|#141929" views components" in src or "201,168,76" in src or "#141929" in src:
            offenders.append(p.relative_to(ROOT).as_posix())
    assert offenders == []
```
(trzeci test przejdzie dopiero po Task 3 — w Task 1 oznacz go `@pytest.mark.xfail(strict=True, reason="Task 3")`, a w Task 3 usuń marker.)
- [ ] `components/constants.py`: ustaw tokeny z tabeli (dodaj `TEXT`, `BG_HOVER`, `GOLD_SOFT`, `SHADOW`), zachowaj istniejące nazwy (`GOLD, GREEN, RED, MUTED, BG, BG2, BG_CARD, BORDER, GRID, AMBER, CHART_COLORS`) — strony je importują. `GRID = "rgba(255,255,255,0.05)"`.
- [ ] `.streamlit/config.toml` `[theme]`: `base="dark"`, `primaryColor`, `backgroundColor`, `secondaryBackgroundColor`, `textColor` z tokenów; `font = "Inter:https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"` (jeśli 1.55 odrzuci ten format — sprawdź uruchomieniem — użyj `font="sans-serif"` i dodaj Inter przez CSS `@import` w Task 2); `baseRadius = "0.75rem"`, `borderColor = BORDER`, `showWidgetBorder = true`, `linkColor = GOLD`, `chartCategoricalColors = CHART_COLORS`; `[theme.sidebar]` `backgroundColor = BG2`, `secondaryBackgroundColor = BG_CARD`. Zostaw sekcje `[server]`, `[browser]`, `[client]`. Uruchom `streamlit run app.py` na chwilę i sprawdź w logu, że nie ma ostrzeżeń o nieznanych kluczach motywu (usuń klucze, których 1.55 nie zna, i zanotuj to).
- [ ] Testy + commit „Theme B: tokens and Streamlit theme”.

### Task 2: Globalny CSS i wykresy

**Files:** Modify `components/sidebar.py` (`inject_css`), `components/charts.py` (`_base_layout`)

- [ ] `inject_css`: przepisz blok CSS na tokeny (f-string z importem z `components.constants`):
  - `html, body, [class*="st-"]` → `font-variant-numeric: tabular-nums;`
  - `.stMetric` → tło `BG_CARD`, bez ramki, `border-radius:14px`, `box-shadow: SHADOW`, label `MUTED` 12px bez wersalików, value 650
  - zakładki `.stTabs` → segmentowane „pigułki”: lista bez tła, zakładka `border-radius:8px; padding:7px 12px; color: MUTED`, aktywna `background: BG_HOVER; color: TEXT`, bez dolnej złotej kreski (`[data-baseweb="tab-highlight"]{display:none}` i `[data-baseweb="tab-border"]{display:none}`)
  - nagłówki DataFrame → `MUTED`, 11px, bez `text-transform: uppercase`
  - górne menu nawigacji (`[data-testid="stTopNavLink"]` / ich aktywny stan — zidentyfikuj selektory w DevTools-free sposób: `grep -o 'data-testid="stTopNav[A-Za-z]*"'` w `venv/Lib/site-packages/streamlit/static/static/js/*.js`) → link `MUTED` 13px, `border-radius:8px; padding:7px 12px`, aktywny `background: BG_HOVER; color:#fff`
  - linki nawigacji w sidebarze (mobile) → ten sam styl bez złotej lewej kreski
  - `h1` → `font-weight:650; font-size: clamp(1.5rem, 3vw, 1.9rem); letter-spacing:-0.01em`; `h3` → 600, 1.1rem
  - expandery i kontenery z `border=True` → `border-color: BORDER`, `border-radius:14px`
  - zachowaj istniejące reguły ukrywania (`#MainMenu`, `footer`, `stDecoration`, toolbar) i mobilne `@media`.
- [ ] `_base_layout`: `template="plotly_dark"`, `paper_bgcolor="rgba(0,0,0,0)"`, `plot_bgcolor="rgba(0,0,0,0)"`, `font=dict(family="Inter, system-ui, sans-serif", color=MUTED, size=12)`, tytuł `color=TEXT, size=15`, siatka `GRID`, `zeroline=False`, `colorway=CHART_COLORS`, `hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER, font_color=TEXT)`. Sygnatura bez zmian.
- [ ] Testy + commit „Theme B: global CSS and chart layout”.

### Task 3: Karty i ekrany (bez złotych ramek)

**Files:** Modify `components/cards.py`, `components/auth.py`, `components/financials_ui.py`, każdy plik w `views/**` z twardym `#C9A84C` / `"#C9A84C|201,168,76|#141929" views components` / `#141929`; Modify `tests/test_theme.py` (usuń xfail)

- [ ] W `components/cards.py` dodaj helper `card_html(inner: str, accent: str | None = None, pad: str = "16px 18px") -> str` zwracający `<div style="background:BG_CARD;border-radius:14px;padding:..;box-shadow:SHADOW;{'border-left:3px solid '+accent if accent else ''}">{inner}</div>` i użyj go we wszystkich kartach zamiast `border:2px solid`/`border:1px solid {BORDER}`.
- [ ] `signal_card`: bez emoji-ikony 3rem; etykieta „Sygnał GEM” (MUTED, 12px), wartość `"{signal_label} · {signal}"` (28px, 650, kolor sygnału), cienki akcent po lewej w kolorze sygnału. Dodaj parametr `compact: bool = False` (compact → padding 16px, wartość 24px, `margin-bottom:0`) — używany na Pulpicie.
- [ ] Pozostałe karty (`metric_row`/`_metric_card`, `top_etf_cards`, `macro_card`, `stats_table`, `comparison_card`, `ta_signal_card`, `data_status_card`, `alert_banner`, `final_value_card`, `ratios_card`, `forward_consensus_card`, `earnings_history_card`, `analyst_recos_card`, `top_pick_cards`, `section_band`, `kpi_card`): ten sam język — tło `BG_CARD`, cień, etykiety MUTED bez wersalików, kolory wartości GREEN/RED/GOLD, żadnych ramek 2 px, żadnych emoji dekoracyjnych w tytułach kart.
- [ ] `auth.render_lock_screen` i `premium_teaser`: karta w nowym stylu, kłódka jako mały SVG lub znak „🔒” max 18px (teaser musi nadal zawierać „🔒” — testy liczą zaślepki), przycisk CTA w `GOLD` z ciemnym tekstem, `border-radius:10px`.
- [ ] Zamień twarde kolory w `views/**` i `components/**` na tokeny (import z `components.constants`). Sprawdzenie: `grep -rn "#C9A84C\|201,168,76\|#141929" views components` → pusto.
- [ ] Usuń `xfail` z `test_no_hardcoded_old_gold_in_ui_code`; testy offline (w tym `test_pulpit_offline.py`, `test_porownaj_offline.py`) zielone. Commit „Theme B: restyle cards, lock screen and teasers”.

### Task 4: Menu bez emoji

**Files:** Modify `components/nav.py`, wszystkie `views/**` (pierwszy `st.markdown("# …")`), `tests/test_nav.py`

- [ ] `PageDef.icon` → ikony Material (`st.Page(icon=":material/...:")`): pulpit `dashboard`, sygnal `track_changes`, backtest `science`, gem-extended `rocket_launch`, gem-zloto `workspace_premium`, o-strategii `menu_book`, ranking-etf `leaderboard`, porownaj `compare_arrows`, stopy-zwrotu `percent`, drawdowny `trending_down`, sp500 `flag`, gpw `flag`, top-picks `star`, screener `filter_alt`, kalendarz-wynikow `event`, insiderzy `groups`, krypto `currency_bitcoin`, portfolio-builder `pie_chart`, monte-carlo `casino`, makro `public`, sektory `donut_large`, intermarket `hub`, sezonowosc `calendar_month`, waluta `currency_exchange`. Format w rejestrze: `":material/dashboard:"`.
- [ ] `render_lock_screen` dostaje ikonę Material — w HTML nie da się jej wyrenderować; w `app.py` przekaż do lock screena pusty/neutralny znak (lub mapuj na nic) — zmień `render_lock_screen(icon, ...)` tak, by ignorował wartości zaczynające się od `":material/"`.
- [ ] Nagłówki stron: usuń emoji z pierwszego `st.markdown("# …")` w każdej stronie (np. `# 🎯 Sygnał GEM` → `# Sygnał GEM`). Tylko H1; nie ruszaj emoji w treści, tabelach i nazwach zakładek wewnątrz stron w tym zadaniu.
- [ ] Test w `tests/test_nav.py`: każda ikona zaczyna się od `":material/"`; każda strona ma H1 bez znaków spoza BMP-emoji (`not any(ord(ch) > 0x2FFF for ch in h1)`).
- [ ] Commit „Theme B: material icons in menu, emoji-free page titles”.

### Task 5: Pulpit wg makiety (równe karty)

**Files:** Modify `views/start/pulpit.py`; testy `tests/test_pulpit_offline.py`

- [ ] Nagłówek: `# Dzień dobry` (lub „Dobry wieczór” po 18:00) + podpis z datą po polsku i „dane z zamknięcia ostatniej sesji”.
- [ ] **Pasek stanu — uwaga użytkownika: karty sygnału i regime muszą mieć równą szerokość i wysokość.** `st.columns(2)` (równe), oba przez ten sam helper karty o stałej `min-height:132px`: lewa = `Sygnał GEM` + pill „od N dni” (GOLD_SOFT/GOLD) / wartość `"{signal_label} · {signal}"` / podpis „Następne przeliczenie: 1 grudnia”; prawa = `Regime rynku` / wartość `Risk-On` w kolorze / podpis `"{score}/100 · {desc}"`. Duża `signal_card` zostaje tylko na stronie Sygnał. Metryki 12M (`metric_row`) pod spodem bez zmian funkcjonalnych, w nowym stylu.
- [ ] Kafelki rynku jak w makiecie: siatka 4 kolumny, kafelek `BG_CARD` radius 12, etykieta MUTED, wartość 17px 650 tabular, zmiana 1D w kolorze, sparkline cienką linią w kolorze zmiany (Plotly `sparkline_chart` z linią 1.6 px, bez osi, przezroczyste tło, wysokość ~40), VIX z etykietą poziomu strachu jako podpisem.
- [ ] Pozostałe karty Pulpitu (watchlista/ulubione, wyniki tygodnia, wygrani/przegrani, Top 5, wyniki 5 lat) — nagłówki bez emoji, `st.container(border=False)` + helper karty; teasery bez zmian funkcjonalnych (nadal 2 zaślepki dla free).
- [ ] `tests/test_pulpit_offline.py` zielony (zaktualizuj asercje tekstów, jeśli zmieniły się nagłówki — liczba zaślepek bez zmian). Commit „Theme B: Pulpit layout from mockup with equal status cards”.

### Task 6: Weryfikacja wizualna

- [ ] Zrzuty ekranu headless Chrome (`"C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --window-size=1440,1800 --virtual-time-budget=25000 --screenshot=<plik> http://localhost:8502/<strona>`) dla: Pulpit (free), Sygnał, Porównaj, S&P 500, Makro; plus `--window-size=390,1600` dla Pulpitu. Zapisz w scratchpadzie, obejrzyj (Read obrazka), popraw rażące problemy (ucięte karty, kontrast, nachodzące elementy).
- [ ] Pełne testy offline + `RUN_NETWORK=1` smoke dla `pulpit or sygnal or porownaj` (z certyfikatami Norton). Commit poprawek.
