# Top Picks — Earnings Momentum + Jakość biznesu — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dodać stronie `pages/9_top_picks.py` dwie nowe strategie w osobnych zakładkach — Earnings Momentum (tylko SP500) i Jakość biznesu (SP500 + GPW) — każda z własnym append-only logiem, bez symulacji wstecz.

**Architecture:** `select_picks()` dostaje wymienny `Scorer` (dataclass z flagą `supports_asof`); wspólne pozostają filtr płynności, limit sektorowy i top-5 równych wag. Scorery fundamentalne dostają dane przez wstrzykiwany fetcher, więc testy nie ruszają sieci. Każda strategia ma osobny plik JSON — istniejący log momentum pozostaje nietknięty.

**Tech Stack:** Python 3.14, pandas, pytest, Streamlit 1.55, yfinance.

**Spec:** `docs/superpowers/specs/2026-08-07-top-picks-strategie-design.md`

---

## File Structure

| Plik | Odpowiedzialność | Akcja |
|---|---|---|
| `data/top_picks.py` | Silnik: `Scorer`, trzy scorery, `select_picks`, log, equity, symulacja | Modify |
| `data/financials.py` | Warstwa danych yfinance — dochodzi `bulk_fetch_earnings_trend()` | Modify |
| `scripts/update_top_picks.py` | CLI dla Action — trzy strategie, guard per strategia | Modify |
| `pages/9_top_picks.py` | UI — 3 zakładki, wspólna funkcja renderująca | Modify |
| `components/auth.py` | `PAGE_INFO[9]` — opis wspomina trzy strategie | Modify |
| `tests/test_top_picks.py` | Testy silnika (istniejące 13 nietykalne + nowe) | Modify |
| `tests/test_financials.py` | Testy bulk fetchera rewizji | Modify |
| `CLAUDE.md` | Dokumentacja sekcji Top Picks | Modify |

**Zasada nadrzędna:** istniejące 13 testów w `tests/test_top_picks.py` przechodzi **bez zmiany treści** przez cały plan. To kontrakt, że ścieżka momentum nie drgnęła. Każde zadanie kończy się pełnym `pytest tests/ -q`.

---

## Task 1: Scorer dataclass + wymienny scoring w select_picks

**Files:**
- Modify: `data/top_picks.py:1-20` (importy, stałe), `data/top_picks.py:58-119` (`select_picks`)
- Test: `tests/test_top_picks.py`

- [ ] **Step 1: Napisz failing testy**

Dopisz na końcu `tests/test_top_picks.py`:

```python
# ====== Scorer (2026-08-07) ======

def test_select_picks_bez_scorera_zachowuje_sie_jak_dotad():
    """Kontrakt wstecznej zgodnosci: brak kwargu scorer == MOMENTUM_SCORER."""
    tickers = tuple(f"T{i}" for i in range(8))
    prices = _frame(400, tickers)
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}

    domyslny = tp.select_picks(prices, vols, groups, prices.index[-1], top_n=5)
    jawny = tp.select_picks(prices, vols, groups, prices.index[-1], top_n=5,
                            scorer=tp.MOMENTUM_SCORER)

    assert [p["ticker"] for p in domyslny] == [p["ticker"] for p in jawny]
    assert [p["score"] for p in domyslny] == [p["score"] for p in jawny]


def test_select_picks_uzywa_wstrzyknietego_scorera():
    """Scorer decyduje o kolejnosci; reszta reguly (limit, wagi) bez zmian."""
    tickers = ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")
    prices = _frame(400, tickers)
    vols = _volumes(prices)
    groups = {t: f"S{t}" for t in tickers}

    # Odwrotnosc alfabetu: FFF najlepsze, AAA najgorsze
    def _fake(eligible, px, asof):
        return pd.Series({t: i / 10 for i, t in enumerate(sorted(eligible))})

    scorer = tp.Scorer(name="fake", supports_asof=True, fn=_fake)
    picks = tp.select_picks(prices, vols, groups, prices.index[-1],
                            top_n=3, scorer=scorer)

    assert [p["ticker"] for p in picks] == ["FFF", "EEE", "DDD"]
    assert sum(p["weight"] for p in picks) == pytest.approx(1.0, abs=1e-6)


def test_select_picks_scorer_z_pustym_wynikiem_zwraca_pusta_liste():
    tickers = ("AAA", "BBB")
    prices = _frame(400, tickers)
    vols = _volumes(prices)
    groups = {t: "S" for t in tickers}

    scorer = tp.Scorer(name="pusty", supports_asof=True,
                       fn=lambda eligible, px, asof: pd.Series(dtype=float))
    assert tp.select_picks(prices, vols, groups, prices.index[-1], scorer=scorer) == []


def test_select_picks_scorer_z_nan_pomija_ticker():
    tickers = ("AAA", "BBB", "CCC")
    prices = _frame(400, tickers)
    vols = _volumes(prices)
    groups = {t: f"S{t}" for t in tickers}

    def _z_nanem(eligible, px, asof):
        return pd.Series({"AAA": 0.9, "BBB": float("nan"), "CCC": 0.5})

    scorer = tp.Scorer(name="nan", supports_asof=True, fn=_z_nanem)
    picks = tp.select_picks(prices, vols, groups, prices.index[-1], scorer=scorer)
    assert [p["ticker"] for p in picks] == ["AAA", "CCC"]
```

- [ ] **Step 2: Uruchom testy — muszą paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k scorer`
Expected: FAIL — `AttributeError: module 'data.top_picks' has no attribute 'Scorer'`

- [ ] **Step 3: Dodaj Scorer i przerób select_picks**

W `data/top_picks.py` zamień blok importów (linie 7–14) na:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from data.momentum import latest_returns, rank_based_score
```

Zaraz po stałych `MIN_TURNOVER` (po linii 26), przed `_DATA_DIR`, wstaw:

```python
@dataclass(frozen=True)
class Scorer:
    """Wymienna funkcja rankingujaca dla select_picks().

    Attributes:
        name: identyfikator do logow i komunikatow bledow
        supports_asof: czy scorer potrafi policzyc ranking NA DANY DZIEN.
            False dla scorerow fundamentalnych — yfinance zwraca stan na dzis
            niezaleznie od zadanej daty, wiec uzycie ich w simulate_rule()
            dalo by lookahead bias. simulate_rule() to sprawdza i odmawia.
        fn: (eligible_tickers, prices_do_asof, asof) -> Series ticker -> score.
            Wyzszy score = lepiej. NaN i braki sa pomijane.
    """
    name: str
    supports_asof: bool
    fn: Callable[[list[str], pd.DataFrame, pd.Timestamp], pd.Series]


def _momentum_scores(eligible: list[str], px: pd.DataFrame,
                     asof: pd.Timestamp) -> pd.Series:
    """Regula F18: rank_based_score na zwrotach 12M/6M/3M/1M z anti_1m."""
    rets = latest_returns(px[eligible])
    return rank_based_score(rets, weights=DEFAULT_WEIGHTS, anti_1m=True)


MOMENTUM_SCORER = Scorer(name="momentum", supports_asof=True, fn=_momentum_scores)
```

Zamień ciało `select_picks` (linie 58–119) na:

```python
def select_picks(prices: pd.DataFrame, volumes: pd.DataFrame,
                 groups: dict[str, str], asof,
                 top_n: int = 5, max_per_group: int = 2,
                 min_turnover: float = 0.0,
                 scorer: Scorer | None = None) -> list[dict]:
    """Wybiera top_n spolek na dzien asof.

    1. filtr historii (>= MIN_HISTORY sesji) i plynnosci (mediana obrotu 60d)
    2. scorer.fn() -> ranking (domyslnie MOMENTUM_SCORER)
    3. schodzenie po rankingu z limitem max_per_group na grupe
    4. rowne wagi

    Args:
        prices: ceny close (kolumny = tickery)
        volumes: wolumeny w tym samym ukladzie
        groups: ticker -> grupa (sektor GICS dla SP500, sektor dla GPW)
        asof: data, NA KTORA liczymy — dane po niej sa ignorowane
        top_n: ile pozycji w portfelu
        max_per_group: ile maksymalnie spolek z jednej grupy
        min_turnover: prog mediany dziennego obrotu (w walucie notowania)
        scorer: wymienna regula rankingujaca; None = MOMENTUM_SCORER

    Returns:
        Lista dictow gotowa do serializacji do JSON. Pusta, gdy brak kandydatow.
    """
    scorer = scorer or MOMENTUM_SCORER
    asof = pd.Timestamp(asof)
    px = prices.loc[:asof]
    if px.empty:
        return []

    eligible = _eligible(prices, volumes, asof, min_turnover)
    if not eligible:
        return []

    scores = scorer.fn(eligible, px, asof)
    if scores is None or len(scores) == 0:
        return []
    scores = scores.dropna().sort_values(ascending=False)

    picks: list[dict] = []
    counts: dict[str, int] = {}
    for ticker, score in scores.items():
        if ticker not in px.columns:
            continue
        group = groups.get(ticker, "?")
        if counts.get(group, 0) >= max_per_group:
            continue
        series = px[ticker].dropna()
        if series.empty:
            continue
        picks.append({
            "ticker": ticker,
            "group": group,
            "score": round(float(score), 4),
            "entry_price": round(float(series.iloc[-1]), 4),
            "entry_date": series.index[-1].strftime("%Y-%m-%d"),
            "weight": 0.0,
        })
        counts[group] = counts.get(group, 0) + 1
        if len(picks) == top_n:
            break

    if picks:
        weight = 1.0 / len(picks)
        for pick in picks:
            pick["weight"] = weight
    return picks
```

- [ ] **Step 4: Uruchom pełen pakiet**

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — 70 passed (66 istniejących + 4 nowe). Wszystkie stare testy `select_picks` muszą przejść bez zmiany treści.

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Add Scorer to select_picks (backwards compatible)

Wymienna regula rankingujaca. Flaga supports_asof przygotowuje grunt
pod scorery fundamentalne, ktore nie potrafia liczyc na historyczna date."
```

---

## Task 2: simulate_rule odmawia scorerów bez asof

**Files:**
- Modify: `data/top_picks.py` (`simulate_rule`)
- Test: `tests/test_top_picks.py`

- [ ] **Step 1: Napisz failing test**

Dopisz na końcu `tests/test_top_picks.py`:

```python
def test_simulate_rule_odmawia_scorera_bez_wsparcia_asof():
    """Scorer fundamentalny w symulacji = lookahead bias. Ma paskudnie падать,
    nie liczyc po cichu dzisiejszymi danymi na historycznych datach."""
    tickers = tuple(f"T{i}" for i in range(6))
    prices = _frame(700, tickers, start="2023-01-02")
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}

    scorer = tp.Scorer(name="fundamentalny", supports_asof=False,
                       fn=lambda eligible, px, asof: pd.Series(
                           {t: 1.0 for t in eligible}))

    with pytest.raises(ValueError, match="supports_asof"):
        tp.simulate_rule(prices, vols, groups, start=prices.index[300],
                         scorer=scorer)


def test_simulate_rule_przepuszcza_scorer_z_asof():
    tickers = tuple(f"T{i}" for i in range(8))
    prices = _frame(700, tickers, start="2023-01-02")
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}

    equity = tp.simulate_rule(prices, vols, groups, start=prices.index[300],
                              min_turnover=0.0, scorer=tp.MOMENTUM_SCORER)
    assert isinstance(equity, pd.Series)
    assert len(equity) >= 6
```

Uwaga: w pierwszym teście usuń z docstringa cyrylicę, jeśli edytor ją wstawił — ma być `ma paskudnie padac, nie liczyc po cichu`.

- [ ] **Step 2: Uruchom test — musi paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k simulate_rule_odmawia`
Expected: FAIL — `TypeError: simulate_rule() got an unexpected keyword argument 'scorer'`

- [ ] **Step 3: Dodaj kwarg i guard**

W `data/top_picks.py` zmień sygnaturę `simulate_rule` — dopisz `scorer` na końcu listy argumentów:

```python
def simulate_rule(prices: pd.DataFrame, volumes: pd.DataFrame,
                  groups: dict[str, str], start,
                  min_turnover: float = 0.0,
                  top_n: int = 5, max_per_group: int = 2,
                  transaction_cost: float = 0.001,
                  tax_belka: float = 0.19,
                  start_capital: float = 10000.0,
                  scorer: Scorer | None = None) -> pd.Series:
```

Zaraz po docstringu, jako pierwsze linie ciała:

```python
    scorer = scorer or MOMENTUM_SCORER
    if not scorer.supports_asof:
        raise ValueError(
            f"Scorer '{scorer.name}' ma supports_asof=False — nie potrafi policzyc "
            "rankingu na historyczna date. Symulacja uzylaby dzisiejszych danych "
            "na kazdej dacie wstecz (lookahead bias). Ta strategia jest forward-only."
        )
```

W pętli przekaż scorer do `select_picks`:

```python
        picks = select_picks(prices, volumes, groups, t0,
                             top_n=top_n, max_per_group=max_per_group,
                             min_turnover=min_turnover, scorer=scorer)
```

Dopisz do docstringa `simulate_rule`, po akapicie o survivorship bias:

```
    Dziala wylacznie ze scorerami majacymi supports_asof=True. Scorery
    fundamentalne sa forward-only i podnosza ValueError.
```

- [ ] **Step 4: Uruchom pełen pakiet**

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — 72 passed

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Guard simulate_rule against scorers without asof support

Scorery fundamentalne czytaja stan na dzis niezaleznie od zadanej daty.
W symulacji dalyby cichy lookahead bias, wiec ValueError zamiast liczenia."
```

---

## Task 3: bulk_fetch_earnings_trend w financials.py

**Files:**
- Modify: `data/financials.py` (dopisz po `fetch_earnings_trend`, ~linia 648)
- Test: `tests/test_financials.py`

- [ ] **Step 1: Napisz failing testy**

Dopisz na końcu `tests/test_financials.py`:

**Dlaczego `.__wrapped__`:** `bulk_fetch_earnings_trend` jest opakowany w `@st.cache_data`, co zwraca obiekt `CachedFunc`. Zweryfikowane 2026-08-07: `CachedFunc` wystawia `__wrapped__` z surową funkcją, a wywołanie przez nią omija cache — bez tego drugi test dostałby zapamiętany wynik pierwszego, mimo podmienionego `fetch_earnings_trend`.

```python
# ====== bulk_fetch_earnings_trend (2026-08-07) ======

def test_bulk_earnings_trend_sklada_revision_90d(monkeypatch):
    """Rewizja 90d = (eps_current - eps_90d_ago) / |eps_90d_ago|, wiersz 0q."""
    import data.financials as fin

    def fake_trend(ticker):
        if ticker == "BRAK":
            return None
        base = {"AAA": (2.0, 1.6), "BBB": (1.0, 1.25)}[ticker]
        return pd.DataFrame(
            {"eps_current": [base[0]], "eps_90d_ago": [base[1]]},
            index=["0q"],
        )

    monkeypatch.setattr(fin, "fetch_earnings_trend", fake_trend)
    out = fin.bulk_fetch_earnings_trend.__wrapped__(("AAA", "BBB", "BRAK"))

    assert set(out["ticker"]) == {"AAA", "BBB"}
    aaa = out.set_index("ticker").loc["AAA", "revision_90d_pct"]
    bbb = out.set_index("ticker").loc["BBB", "revision_90d_pct"]
    assert aaa == pytest.approx(25.0)      # (2.0-1.6)/1.6 = +25%
    assert bbb == pytest.approx(-20.0)     # (1.0-1.25)/1.25 = -20%


def test_bulk_earnings_trend_pomija_zerowy_mianownik(monkeypatch):
    import data.financials as fin

    def fake_trend(ticker):
        return pd.DataFrame({"eps_current": [1.0], "eps_90d_ago": [0.0]}, index=["0q"])

    monkeypatch.setattr(fin, "fetch_earnings_trend", fake_trend)
    out = fin.bulk_fetch_earnings_trend.__wrapped__(("AAA",))
    assert out.empty or pd.isna(out.iloc[0]["revision_90d_pct"])


def test_bulk_earnings_trend_pusty_input_daje_pusty_df():
    import data.financials as fin
    out = fin.bulk_fetch_earnings_trend.__wrapped__(())
    assert isinstance(out, pd.DataFrame)
    assert out.empty
```

- [ ] **Step 2: Uruchom testy — muszą paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_financials.py -q -k bulk_earnings_trend`
Expected: FAIL — `AttributeError: module 'data.financials' has no attribute 'bulk_fetch_earnings_trend'`

- [ ] **Step 3: Zaimplementuj bulk fetcher**

W `data/financials.py`, bezpośrednio po funkcji `fetch_earnings_trend` (przed `_fetch_earnings_for_one`), wstaw:

```python
def _trend_row_for_one(ticker: str) -> dict | None:
    """Rewizja konsensusu 90d dla 1 tickera. None gdy brak danych."""
    try:
        df = fetch_earnings_trend(ticker)
    except Exception:
        return None
    if df is None or df.empty or "0q" not in df.index:
        return None

    row = df.loc["0q"]
    current = row.get("eps_current")
    ago = row.get("eps_90d_ago")
    if current is None or ago is None:
        return None
    try:
        current, ago = float(current), float(ago)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(current) or not np.isfinite(ago) or ago == 0:
        return None

    return {
        "ticker": ticker,
        "eps_current": current,
        "eps_90d_ago": ago,
        "revision_90d_pct": (current - ago) / abs(ago) * 100.0,
    }


@st.cache_data(ttl=86400, show_spinner="Pobieram rewizje konsensusu...")
def bulk_fetch_earnings_trend(
    tickers_tuple: tuple[str, ...],
    max_workers: int = 8,
) -> pd.DataFrame:
    """Bulk rewizje konsensusu EPS (okno 90d) dla universe.

    Uzywane przez EARNINGS_SCORER w data/top_picks.py.

    Args:
        tickers_tuple: tuple (hashable dla cache). NIE prefiksowac '_' —
            Streamlit ignoruje argumenty z '_' i doszloby do kolizji cache
            miedzy universe'ami.

    Returns:
        DataFrame z kolumnami: ticker, eps_current, eps_90d_ago,
        revision_90d_pct. Wiersze tylko dla tickerow z kompletem danych.
        Pusty DataFrame gdy zaden ticker nie ma danych.
    """
    if not tickers_tuple:
        return pd.DataFrame(
            columns=["ticker", "eps_current", "eps_90d_ago", "revision_90d_pct"]
        )

    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(_trend_row_for_one, tickers_tuple):
            if result is not None:
                rows.append(result)

    if not rows:
        return pd.DataFrame(
            columns=["ticker", "eps_current", "eps_90d_ago", "revision_90d_pct"]
        )
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Sprawdź, czy ThreadPoolExecutor jest zaimportowany**

Run: `grep -n "ThreadPoolExecutor" data/financials.py | head -2`
Expected: linia z `from concurrent.futures import ThreadPoolExecutor`. Jeśli brak — dopisz do importów na górze pliku.

- [ ] **Step 5: Uruchom pełen pakiet**

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — 75 passed

- [ ] **Step 6: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add bulk_fetch_earnings_trend (90d consensus revisions)

ThreadPool + cache 24h, wzorzec z bulk_fetch_earnings_history.
Okno 90d zamiast istniejacego revision_pct (30d) — mniej szumu."
```

---

## Task 4: EARNINGS_SCORER

**Files:**
- Modify: `data/top_picks.py` (po `MOMENTUM_SCORER`)
- Test: `tests/test_top_picks.py`

**Kontekst dla implementującego:** scorer musi być testowalny bez sieci, więc dane wchodzą przez wstrzykiwane funkcje. `make_earnings_scorer()` bez argumentów używa prawdziwych bulk fetcherów; testy podają własne.

Kształt danych z prawdziwych źródeł:
- `bulk_fetch_earnings_history(tuple)` → DataFrame z kolumnami `ticker`, `beat_streak` (int 0–4), `eps_surprise_pct` (float)
- `bulk_fetch_earnings_trend(tuple)` → DataFrame z kolumnami `ticker`, `revision_90d_pct` (float)

- [ ] **Step 1: Napisz failing testy**

Dopisz na końcu `tests/test_top_picks.py`:

```python
# ====== EARNINGS_SCORER (2026-08-07) ======

def _earnings_frames():
    """Cztery spolki: EEE najlepsza w kazdym komponencie, AAA najgorsza."""
    hist = pd.DataFrame([
        {"ticker": "AAA", "beat_streak": 0, "eps_surprise_pct": -5.0},
        {"ticker": "BBB", "beat_streak": 2, "eps_surprise_pct": 1.0},
        {"ticker": "CCC", "beat_streak": 3, "eps_surprise_pct": 4.0},
        {"ticker": "EEE", "beat_streak": 4, "eps_surprise_pct": 9.0},
    ])
    trend = pd.DataFrame([
        {"ticker": "AAA", "revision_90d_pct": -8.0},
        {"ticker": "BBB", "revision_90d_pct": 0.5},
        {"ticker": "CCC", "revision_90d_pct": 3.0},
        {"ticker": "EEE", "revision_90d_pct": 12.0},
    ])
    return hist, trend


def test_earnings_scorer_rankuje_wg_trzech_komponentow():
    hist, trend = _earnings_frames()
    scorer = tp.make_earnings_scorer(
        history_fn=lambda tickers: hist,
        trend_fn=lambda tickers: trend,
    )
    scores = scorer.fn(["AAA", "BBB", "CCC", "EEE"], pd.DataFrame(), pd.Timestamp("2026-08-01"))

    assert list(scores.sort_values(ascending=False).index) == ["EEE", "CCC", "BBB", "AAA"]
    assert scores.max() <= 1.0 and scores.min() >= 0.0, "score poza skala 0-1"


def test_earnings_scorer_jest_forward_only():
    scorer = tp.make_earnings_scorer(
        history_fn=lambda tickers: pd.DataFrame(),
        trend_fn=lambda tickers: pd.DataFrame(),
    )
    assert scorer.supports_asof is False


def test_earnings_scorer_renormalizuje_przy_braku_rewizji():
    """Spolka bez rewizji nie moze wypasc z rankingu — wagi sie renormalizuja."""
    hist, trend = _earnings_frames()
    trend = trend[trend["ticker"] != "EEE"]     # EEE traci komponent rewizji

    scorer = tp.make_earnings_scorer(
        history_fn=lambda tickers: hist,
        trend_fn=lambda tickers: trend,
    )
    scores = scorer.fn(["AAA", "BBB", "CCC", "EEE"], pd.DataFrame(), pd.Timestamp("2026-08-01"))

    assert "EEE" in scores.index, "spolka bez rewizji wypadla z rankingu"
    assert pd.notna(scores["EEE"])
    assert scores["EEE"] == pytest.approx(1.0), \
        "EEE jest najlepsza w obu dostepnych komponentach, wiec po renormalizacji 1.0"


def test_earnings_scorer_bez_zadnych_danych_zwraca_pusta_serie():
    scorer = tp.make_earnings_scorer(
        history_fn=lambda tickers: pd.DataFrame(),
        trend_fn=lambda tickers: pd.DataFrame(),
    )
    scores = scorer.fn(["AAA", "BBB"], pd.DataFrame(), pd.Timestamp("2026-08-01"))
    assert scores.dropna().empty


def test_earnings_scorer_ignoruje_tickery_spoza_eligible():
    hist, trend = _earnings_frames()
    scorer = tp.make_earnings_scorer(
        history_fn=lambda tickers: hist,
        trend_fn=lambda tickers: trend,
    )
    scores = scorer.fn(["AAA", "BBB"], pd.DataFrame(), pd.Timestamp("2026-08-01"))
    assert set(scores.index) == {"AAA", "BBB"}
```

- [ ] **Step 2: Uruchom testy — muszą paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k earnings_scorer`
Expected: FAIL — `AttributeError: module 'data.top_picks' has no attribute 'make_earnings_scorer'`

- [ ] **Step 3: Zaimplementuj wspólny helper percentylowy i scorer**

W `data/top_picks.py`, zaraz po `MOMENTUM_SCORER`, wstaw:

```python
# ====== Scorery fundamentalne (forward-only) ======
#
# Import data.financials siedzi WEWNATRZ funkcji, nie na gorze modulu:
# financials importuje streamlita, a ten modul ma zostac importowalny bez
# niego (testy F18 i GitHub Action).

EARNINGS_WEIGHTS = {"beat_streak": 0.40, "surprise": 0.35, "revision": 0.25}
QUALITY_WEIGHTS = {"roe": 0.30, "margin": 0.25, "growth": 0.25, "debt": 0.20}


def _weighted_percentiles(components: dict[str, pd.Series],
                          weights: dict[str, float],
                          index: list[str]) -> pd.Series:
    """Wazona srednia percentyli, z renormalizacja wag do dostepnych komponentow.

    Kazdy komponent jest osobno przeliczany na percentyl (0-1, wyzej = lepiej),
    zeby jednostki (procenty, krotnosci, licznik kwartalow) byly porownywalne.
    Spolka z czescia komponentow dostaje srednia z tego, co ma — wzorzec
    _flexible_score() z momentum.py. Spolka bez zadnego komponentu = NaN.
    """
    ranks: dict[str, pd.Series] = {}
    for key, series in components.items():
        clean = pd.to_numeric(series, errors="coerce").reindex(index).dropna()
        if clean.empty:
            continue
        ranks[key] = clean.rank(pct=True)

    if not ranks:
        return pd.Series(float("nan"), index=index)

    total = pd.Series(0.0, index=index)
    used = pd.Series(0.0, index=index)
    for key, rank in ranks.items():
        weight = weights[key]
        aligned = rank.reindex(index)
        contribution = (aligned * weight).fillna(0.0)
        total += contribution
        used += aligned.notna().astype(float) * weight

    out = total / used.replace(0.0, float("nan"))
    return out


def make_earnings_scorer(history_fn=None, trend_fn=None) -> Scorer:
    """Scorer 'Earnings Momentum' — beat streak + zaskoczenie EPS + rewizje.

    Args:
        history_fn: (tuple[str]) -> DataFrame z ticker/beat_streak/eps_surprise_pct.
            None = bulk_fetch_earnings_history z data.financials.
        trend_fn: (tuple[str]) -> DataFrame z ticker/revision_90d_pct.
            None = bulk_fetch_earnings_trend z data.financials.

    supports_asof=False — yfinance oddaje stan na dzis, nie na zadana date.
    """
    def _fn(eligible: list[str], px: pd.DataFrame, asof: pd.Timestamp) -> pd.Series:
        if history_fn is None or trend_fn is None:
            from data.financials import (
                bulk_fetch_earnings_history,
                bulk_fetch_earnings_trend,
            )
            hist_source = history_fn or bulk_fetch_earnings_history
            trend_source = trend_fn or bulk_fetch_earnings_trend
        else:
            hist_source, trend_source = history_fn, trend_fn

        tickers = tuple(eligible)
        hist = hist_source(tickers)
        trend = trend_source(tickers)

        components: dict[str, pd.Series] = {}
        if hist is not None and not hist.empty and "ticker" in hist.columns:
            indexed = hist.set_index("ticker")
            if "beat_streak" in indexed.columns:
                components["beat_streak"] = indexed["beat_streak"]
            if "eps_surprise_pct" in indexed.columns:
                components["surprise"] = indexed["eps_surprise_pct"]
        if trend is not None and not trend.empty and "ticker" in trend.columns:
            indexed = trend.set_index("ticker")
            if "revision_90d_pct" in indexed.columns:
                components["revision"] = indexed["revision_90d_pct"]

        if not components:
            return pd.Series(float("nan"), index=eligible)
        return _weighted_percentiles(components, EARNINGS_WEIGHTS, eligible)

    return Scorer(name="earnings", supports_asof=False, fn=_fn)


EARNINGS_SCORER = make_earnings_scorer()
```

- [ ] **Step 4: Uruchom pełen pakiet**

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — 80 passed

- [ ] **Step 5: Sprawdź, że moduł nadal nie ciąga Streamlita**

Run: `venv/Scripts/python.exe -c "import sys; import data.top_picks; print('streamlit' in sys.modules)"`
Expected: `False` — import wewnątrz funkcji działa

- [ ] **Step 6: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Add EARNINGS_SCORER (beat streak + surprise + revisions)

Wagi 40/35/25, kazdy komponent osobno na percentyle, renormalizacja
przy brakach. Import financials wewnatrz funkcji — modul zostaje
importowalny bez streamlita."
```

---

## Task 5: QUALITY_SCORER z obsługą banków GPW

**Files:**
- Modify: `data/top_picks.py` (po `EARNINGS_SCORER`)
- Test: `tests/test_top_picks.py`

**Kontekst:** `bulk_fetch_universe(tuple)` zwraca `dict[ticker, dict]` (NIE DataFrame) z kluczami m.in. `roe`, `profit_margin`, `revenue_growth`, `debt_to_equity`. Banki mają nieporównywalne debt/equity — komponent `debt` jest dla nich pomijany, a `_weighted_percentiles` renormalizuje wagi automatycznie.

- [ ] **Step 1: Napisz failing testy**

Dopisz na końcu `tests/test_top_picks.py`:

```python
# ====== QUALITY_SCORER (2026-08-07) ======

def _quality_bulk():
    return {
        "AAA": {"roe": 0.05, "profit_margin": 0.02, "revenue_growth": 0.01,
                "debt_to_equity": 200.0},
        "BBB": {"roe": 0.15, "profit_margin": 0.10, "revenue_growth": 0.08,
                "debt_to_equity": 90.0},
        "CCC": {"roe": 0.30, "profit_margin": 0.22, "revenue_growth": 0.20,
                "debt_to_equity": 20.0},
    }


def test_quality_scorer_rankuje_wg_czterech_komponentow():
    scorer = tp.make_quality_scorer(bulk_fn=lambda tickers: _quality_bulk())
    scores = scorer.fn(["AAA", "BBB", "CCC"], pd.DataFrame(), pd.Timestamp("2026-08-01"))

    assert list(scores.sort_values(ascending=False).index) == ["CCC", "BBB", "AAA"]
    assert scores.max() <= 1.0 and scores.min() >= 0.0


def test_quality_scorer_niski_dlug_jest_lepszy():
    """debt_to_equity musi wchodzic ODWROTNIE — mniej dlugu = wyzszy percentyl."""
    bulk = {
        "LOW":  {"roe": 0.10, "profit_margin": 0.10, "revenue_growth": 0.10,
                 "debt_to_equity": 10.0},
        "HIGH": {"roe": 0.10, "profit_margin": 0.10, "revenue_growth": 0.10,
                 "debt_to_equity": 300.0},
    }
    scorer = tp.make_quality_scorer(bulk_fn=lambda tickers: bulk)
    scores = scorer.fn(["LOW", "HIGH"], pd.DataFrame(), pd.Timestamp("2026-08-01"))
    assert scores["LOW"] > scores["HIGH"]


def test_quality_scorer_pomija_debt_dla_bankow():
    """Bank ma nieporownywalne debt/equity — komponent odpada, wagi sie renormalizuja."""
    bulk = {
        "PKO.WA": {"roe": 0.20, "profit_margin": 0.30, "revenue_growth": 0.10,
                   "debt_to_equity": 900.0},
        "CDR.WA": {"roe": 0.10, "profit_margin": 0.15, "revenue_growth": 0.05,
                   "debt_to_equity": 15.0},
    }
    scorer = tp.make_quality_scorer(bulk_fn=lambda tickers: bulk,
                                    banks={"PKO.WA"})
    scores = scorer.fn(["PKO.WA", "CDR.WA"], pd.DataFrame(), pd.Timestamp("2026-08-01"))

    # PKO wygrywa w ROE, marzy i wzroscie; jego gigantyczny dlug nie moze go ukarac
    assert scores["PKO.WA"] > scores["CDR.WA"]
    assert pd.notna(scores["PKO.WA"])


def test_quality_scorer_jest_forward_only():
    scorer = tp.make_quality_scorer(bulk_fn=lambda tickers: {})
    assert scorer.supports_asof is False


def test_quality_scorer_bez_danych_zwraca_nan():
    scorer = tp.make_quality_scorer(bulk_fn=lambda tickers: {})
    scores = scorer.fn(["AAA", "BBB"], pd.DataFrame(), pd.Timestamp("2026-08-01"))
    assert scores.dropna().empty
```

- [ ] **Step 2: Uruchom testy — muszą paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k quality_scorer`
Expected: FAIL — `AttributeError: module 'data.top_picks' has no attribute 'make_quality_scorer'`

- [ ] **Step 3: Zaimplementuj**

W `data/top_picks.py`, zaraz po `EARNINGS_SCORER`, wstaw:

```python
def make_quality_scorer(bulk_fn=None, banks: set[str] | None = None) -> Scorer:
    """Scorer 'Jakosc biznesu' — ROE + marza + wzrost przychodow + niski dlug.

    Args:
        bulk_fn: (tuple[str]) -> dict[ticker, dict] z kluczami roe,
            profit_margin, revenue_growth, debt_to_equity.
            None = bulk_fetch_universe z data.financials.
        banks: tickery, dla ktorych komponent debt/equity jest pomijany
            (banki maja nieporownywalna strukture bilansu). None = GPW_BANKS.

    supports_asof=False — yfinance oddaje stan na dzis, nie na zadana date.
    """
    def _fn(eligible: list[str], px: pd.DataFrame, asof: pd.Timestamp) -> pd.Series:
        if bulk_fn is None:
            from data.financials import bulk_fetch_universe
            source = bulk_fetch_universe
        else:
            source = bulk_fn

        if banks is None:
            from data.gpw_universe import GPW_BANKS
            bank_set = set(GPW_BANKS)
        else:
            bank_set = set(banks)

        bulk = source(tuple(eligible)) or {}
        if not bulk:
            return pd.Series(float("nan"), index=eligible)

        roe, margin, growth, debt = {}, {}, {}, {}
        for ticker in eligible:
            info = bulk.get(ticker) or {}
            roe[ticker] = info.get("roe")
            margin[ticker] = info.get("profit_margin")
            growth[ticker] = info.get("revenue_growth")
            # Odwrotnie: mniej dlugu = lepiej. Minus przed wartoscia sprawia,
            # ze percentyl liczy sie w dobra strone bez osobnej galezi.
            value = info.get("debt_to_equity")
            if ticker in bank_set or value is None:
                debt[ticker] = None
            else:
                debt[ticker] = -float(value)

        components = {
            "roe": pd.Series(roe, dtype="float64"),
            "margin": pd.Series(margin, dtype="float64"),
            "growth": pd.Series(growth, dtype="float64"),
            "debt": pd.Series(debt, dtype="float64"),
        }
        return _weighted_percentiles(components, QUALITY_WEIGHTS, eligible)

    return Scorer(name="quality", supports_asof=False, fn=_fn)


QUALITY_SCORER = make_quality_scorer()
```

- [ ] **Step 4: Uruchom pełen pakiet**

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — 85 passed

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Add QUALITY_SCORER (ROE, margin, growth, low debt)

Dlug wchodzi ze znakiem minus, wiec percentyl premiuje niskie zadluzenie
bez osobnej galezi. Banki GPW maja komponent dlugu pominiety —
_weighted_percentiles renormalizuje wagi do 1.0."
```

---

## Task 6: RULE_VERSION per strategia + ścieżki logów

**Files:**
- Modify: `data/top_picks.py:16-30` (stałe)
- Test: `tests/test_top_picks.py`

**Uwaga na wsteczną zgodność:** `scripts/update_top_picks.py:164` i `:168` czytają `tp.RULE_VERSION` jako liczbę. Zmiana na dict zepsułaby je — dlatego `RULE_VERSION` zostaje intem dla momentum, a dochodzi osobny słownik `RULE_VERSIONS`. Skrypt migruje w Tasku 7.

- [ ] **Step 1: Napisz failing test**

Dopisz na końcu `tests/test_top_picks.py`:

```python
def test_kazda_strategia_ma_wersje_i_sciezke_loga():
    assert set(tp.RULE_VERSIONS) == {"momentum", "earnings", "quality"}
    assert set(tp.HISTORY_PATHS) == {"momentum", "earnings", "quality"}
    for name, path in tp.HISTORY_PATHS.items():
        assert path.name.endswith(".json"), f"{name}: sciezka nie jest jsonem"
    # Momentum musi wskazywac na istniejacy log — to jedyny prawdziwy track record
    assert tp.HISTORY_PATHS["momentum"] == tp.HISTORY_PATH
    # Trzy rozne pliki, zeby strategie sie nie nadpisywaly
    assert len({p.name for p in tp.HISTORY_PATHS.values()}) == 3


def test_rule_version_pozostaje_intem_dla_wstecznej_zgodnosci():
    assert isinstance(tp.RULE_VERSION, int)
    assert tp.RULE_VERSION == tp.RULE_VERSIONS["momentum"]


def test_strategie_znaja_swoje_rynki():
    """Earnings jest SP500-only — yfinance nie ma historii EPS dla ~80% GPW."""
    assert tp.STRATEGY_MARKETS["momentum"] == ("sp500", "gpw")
    assert tp.STRATEGY_MARKETS["earnings"] == ("sp500",)
    assert tp.STRATEGY_MARKETS["quality"] == ("sp500", "gpw")
```

- [ ] **Step 2: Uruchom testy — muszą paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k "wersje_i_sciezke or wstecznej_zgodnosci or znaja_swoje_rynki"`
Expected: FAIL — `AttributeError: module 'data.top_picks' has no attribute 'RULE_VERSIONS'`

- [ ] **Step 3: Dodaj stałe**

W `data/top_picks.py` zamień blok stałych (linie 16–30, od komentarza `# Wersja reguly` do `SIM_PATH`) na:

```python
# Wersja reguly PER STRATEGIA — podbij przy KAZDEJ zmianie parametrow danej
# reguly. Snapshoty z roznymi wersjami tej samej strategii nie sa porownywalne.
RULE_VERSIONS = {
    "momentum": 1,
    "earnings": 1,
    "quality": 1,
}

# Wsteczna zgodnosc: kod sprzed 2026-08-07 czyta RULE_VERSION jako int.
RULE_VERSION = RULE_VERSIONS["momentum"]

# Ktore rynki obsluguje ktora strategia. Earnings jest SP500-only: yfinance
# nie ma historii EPS dla ~80% GPW (pomiar 2026-08-07, probka 30 spolek).
STRATEGY_MARKETS = {
    "momentum": ("sp500", "gpw"),
    "earnings": ("sp500",),
    "quality": ("sp500", "gpw"),
}

DEFAULT_WEIGHTS = {"12M": 0.40, "6M": 0.30, "3M": 0.20, "1M": 0.10}
MIN_HISTORY = 273        # okno momentum 12-1 (13 miesiecy)
TURNOVER_WINDOW = 60     # sesji do mediany obrotu
MIN_TURNOVER = {
    "sp500": 50_000_000.0,   # USD
    "gpw": 5_000_000.0,      # PLN
}

_DATA_DIR = Path(__file__).parent
HISTORY_PATH = _DATA_DIR / "top_picks_history.json"
SIM_PATH = _DATA_DIR / "top_picks_sim.json"

# Osobny plik na strategie. Log momentum zostaje nietkniety — to jedyny
# prawdziwy track record w aplikacji i nie przepisujemy go pod nowy schemat.
HISTORY_PATHS = {
    "momentum": HISTORY_PATH,
    "earnings": _DATA_DIR / "top_picks_earnings_history.json",
    "quality": _DATA_DIR / "top_picks_quality_history.json",
}
```

- [ ] **Step 4: Uruchom pełen pakiet**

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — 88 passed

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Add per-strategy rule versions, log paths and market maps

RULE_VERSION zostaje intem (czyta go scripts/update_top_picks.py),
dochodzi RULE_VERSIONS. Kazda strategia ma osobny plik loga — istniejacy
track record momentum nie jest migrowany."
```

---

## Task 7: CLI liczy trzy strategie z guardem per strategia

**Files:**
- Modify: `scripts/update_top_picks.py` (cały przepływ `main()` + `validate()`)
- Test: `tests/test_top_picks.py`

**Kluczowa zmiana zachowania:** dziś `validate()` woła `sys.exit(1)` przy każdym błędzie, zabijając cały run. Po zmianie zwraca powód odrzucenia (lub `None`), a wywołujący decyduje: dla momentum nadal `sys.exit`, dla nowych strategii pominięcie zapisu z ostrzeżeniem. Momentum nie może paść przez to, że yfinance nie oddał earningsów.

- [ ] **Step 1: Napisz failing test walidatora**

Dopisz na końcu `tests/test_top_picks.py`:

```python
# ====== Walidator snapshotu (2026-08-07) ======

def test_validate_snapshot_wykrywa_niepelna_piatke():
    from scripts.update_top_picks import validate_snapshot

    prices = _frame(400, ("AAA", "BBB"))
    picks = [{"ticker": "AAA", "group": "S1"}]
    powod = validate_snapshot("sp500", ["AAA", "BBB"], prices, picks,
                              asof=prices.index[-1], top_n=5)
    assert powod is not None
    assert "3" in powod or "pozycji" in powod


def test_validate_snapshot_wykrywa_grupe_znak_zapytania():
    from scripts.update_top_picks import validate_snapshot

    prices = _frame(400, ("AAA", "BBB"))
    picks = [{"ticker": "AAA", "group": "?"}, {"ticker": "BBB", "group": "S1"}]
    powod = validate_snapshot("sp500", ["AAA", "BBB"], prices, picks,
                              asof=prices.index[-1], top_n=2)
    assert powod is not None
    assert "grupy" in powod.lower()


def test_validate_snapshot_przepuszcza_poprawny_snapshot():
    from scripts.update_top_picks import validate_snapshot

    prices = _frame(400, ("AAA", "BBB"))
    picks = [{"ticker": "AAA", "group": "S1"}, {"ticker": "BBB", "group": "S2"}]
    powod = validate_snapshot("sp500", ["AAA", "BBB"], prices, picks,
                              asof=prices.index[-1], top_n=2)
    assert powod is None


def test_validate_snapshot_wykrywa_niskie_pokrycie():
    from scripts.update_top_picks import validate_snapshot

    prices = _frame(400, ("AAA",))
    picks = [{"ticker": "AAA", "group": "S1"}]
    # 1 ticker z danymi na 10 w universe = 10% pokrycia
    powod = validate_snapshot("sp500", [f"T{i}" for i in range(10)], prices, picks,
                              asof=prices.index[-1], top_n=1)
    assert powod is not None
    assert "pokrycie" in powod.lower()
```

- [ ] **Step 2: Uruchom testy — muszą paść**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k validate_snapshot`
Expected: FAIL — `ImportError: cannot import name 'validate_snapshot'`

- [ ] **Step 3: Zamień validate() na validate_snapshot()**

W `scripts/update_top_picks.py` zamień całą funkcję `validate()` (linie 123–146) na:

```python
def validate_snapshot(market: str, tickers: list[str], prices: pd.DataFrame,
                      picks: list[dict], asof: pd.Timestamp,
                      top_n: int) -> str | None:
    """Waliduje snapshot. Zwraca powod odrzucenia albo None gdy OK.

    Pusty lub czesciowy snapshot klamie w sekcji "Wyniki live" na zawsze —
    brak wpisu jest mniej szkodliwy niz wpis nieprawdziwy. Wywolujacy decyduje,
    czy odrzucenie ma zabic caly run (momentum), czy tylko pominac te
    strategie (earnings, quality).
    """
    coverage = len(prices.columns) / max(len(tickers), 1)
    if coverage < MIN_COVERAGE:
        return f"[{market}] pokrycie danych {coverage:.0%} < {MIN_COVERAGE:.0%}"

    staleness = (asof - prices.index[-1]).days
    if staleness > MAX_STALENESS_DAYS:
        return (f"[{market}] ostatnia sesja {prices.index[-1].date()} "
                f"starsza o {staleness} dni od asof {asof.date()}")

    if len(picks) != top_n:
        return f"[{market}] regula zwrocila {len(picks)} pozycji zamiast {top_n}"

    unknown = [p["ticker"] for p in picks if p["group"] == "?"]
    if unknown:
        # Brakujacy wpis w mapie grup wrzuca spolki do wspolnego kubelka "?",
        # co po cichu psuje limit koncentracji.
        return f"[{market}] brak grupy dla {unknown} — uzupelnij mape sektorow"

    return None
```

Dodaj `tests/__init__.py`-owy import path — sprawdź, czy `scripts/` jest importowalne z testów:

Run: `venv/Scripts/python.exe -c "from scripts.update_top_picks import validate_snapshot; print('OK')"`
Expected: `OK`. Jeśli `ModuleNotFoundError: No module named 'scripts'` — utwórz pusty plik `scripts/__init__.py`.

- [ ] **Step 4: Uruchom testy walidatora**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k validate_snapshot`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit walidatora**

```bash
git add scripts/update_top_picks.py tests/test_top_picks.py
git commit -m "Extract validate_snapshot returning reason instead of sys.exit

Pozwala odrzucic snapshot jednej strategii bez zabijania calego runu."
```

- [ ] **Step 6: Przepisz main() na trzy strategie**

W `scripts/update_top_picks.py` zamień ciało `main()` (linie 149–253) na:

```python
STRATEGIES = {
    "momentum": {"scorer": None, "simulate": True, "critical": True},
    "earnings": {"scorer": "earnings", "simulate": False, "critical": False},
    "quality": {"scorer": "quality", "simulate": False, "critical": False},
}


def _scorer_for(name: str):
    """Leniwe pobranie scorera — importy financials tylko gdy potrzebne."""
    if name == "earnings":
        return tp.EARNINGS_SCORER
    if name == "quality":
        return tp.QUALITY_SCORER
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Aktualizacja Top Picks (F18)")
    parser.add_argument("--asof", help="data w formacie YYYY-MM-DD (domyslnie: dzis)")
    parser.add_argument("--dry-run", action="store_true", help="policz i wypisz, nie zapisuj")
    parser.add_argument("--skip-sim", action="store_true", help="pomin przeliczanie symulacji")
    parser.add_argument("--only", choices=sorted(STRATEGIES),
                        help="policz tylko jedna strategie")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--max-per-group", type=int, default=2)
    args = parser.parse_args()

    today = pd.Timestamp(args.asof) if args.asof else pd.Timestamp.today().normalize()
    month_key = today.replace(day=1).strftime("%Y-%m-%d")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    wanted = [args.only] if args.only else list(STRATEGIES)

    # Ceny pobieramy RAZ na rynek i wspoldzielimy miedzy strategiami —
    # bez tego trzy strategie = trzy pelne pobrania yfinance.
    market_data: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]] = {}
    for market, cfg in MARKETS.items():
        print(f"\n=== pobieranie cen: {market} ===", flush=True)
        prices, volumes = download(cfg["tickers"])
        if prices.empty:
            sys.exit(f"[{market}] BLAD: brak jakichkolwiek danych cenowych")
        asof = prices.loc[:today].index[-1]
        print(f"  {len(prices.columns)}/{len(cfg['tickers'])} tickerow, "
              f"ostatnia sesja {prices.index[-1].date()}", flush=True)
        market_data[market] = (prices, volumes, asof)

    sim = {
        "generated_at": generated_at,
        "rule_version": tp.RULE_VERSIONS["momentum"],
        "params": {
            "top_n": args.top_n,
            "max_per_group": args.max_per_group,
            "transaction_cost": 0.001,
            "tax_belka": 0.19,
        },
    }
    failures: list[str] = []

    for strategy in wanted:
        spec = STRATEGIES[strategy]
        scorer = _scorer_for(spec["scorer"])
        markets = tp.STRATEGY_MARKETS[strategy]
        print(f"\n########## strategia: {strategy} ##########", flush=True)

        snapshot = {
            "generated_at": generated_at,
            "asof": None,
            "rule_version": tp.RULE_VERSIONS[strategy],
        }
        rejected = False

        for market in markets:
            cfg = MARKETS[market]
            prices, volumes, asof = market_data[market]
            picks = tp.select_picks(prices, volumes, cfg["groups"], asof,
                                    top_n=args.top_n,
                                    max_per_group=args.max_per_group,
                                    min_turnover=tp.MIN_TURNOVER[market],
                                    scorer=scorer)
            reason = validate_snapshot(market, cfg["tickers"], prices, picks,
                                       today, args.top_n)
            if reason:
                if spec["critical"]:
                    sys.exit(f"BLAD: {reason}")
                print(f"  ODRZUCONO ({strategy}/{market}): {reason}", flush=True)
                failures.append(f"{strategy}/{market}: {reason}")
                rejected = True
                break

            for pick in picks:
                pick["name"] = cfg["names"].get(pick["ticker"], "")
            previous = snapshot.get("asof")
            snapshot["asof"] = max(previous, asof.strftime("%Y-%m-%d")) \
                if previous else asof.strftime("%Y-%m-%d")
            snapshot[market] = picks
            print("  " + " · ".join(f"{p['ticker']} ({p['group']}, {p['score']:.3f})"
                                    for p in picks), flush=True)

        if rejected:
            continue

        if args.dry_run:
            print(f"--dry-run ({strategy}): nic nie zapisano")
            print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        else:
            added = tp.append_snapshot(month_key, snapshot,
                                       path=tp.HISTORY_PATHS[strategy])
            print(f"  snapshot {month_key} [{strategy}]: "
                  f"{'dopisany' if added else 'juz istnial — pomijam'}", flush=True)

        if not spec["simulate"] or args.skip_sim:
            continue

        for market in markets:
            cfg = MARKETS[market]
            prices, volumes, _ = market_data[market]
            start = prices.index[0] + pd.Timedelta(days=400)
            equity = tp.simulate_rule(prices, volumes, cfg["groups"], start=start,
                                      min_turnover=tp.MIN_TURNOVER[market],
                                      top_n=args.top_n,
                                      max_per_group=args.max_per_group,
                                      scorer=scorer)
            if equity.empty:
                print(f"  symulacja pominieta ({market}): pusta krzywa", flush=True)
                continue

            bench = fetch_benchmark(cfg, equity.index)
            stats = calc_stats(equity, trading_days=12)   # seria miesieczna
            if bench is None:
                print(f"  UWAGA ({market}): brak benchmarku {cfg['benchmark']}, "
                      f"symulacja bez porownania", flush=True)
                hits, bench_values = 0.0, []
            else:
                hits = float((equity.pct_change() > bench.pct_change()).mean())
                bench_values = [round(float(v), 2) for v in bench.values]

            sim[market] = {
                "dates": [d.strftime("%Y-%m-%d") for d in equity.index],
                "equity": [round(float(v), 2) for v in equity.values],
                "benchmark": bench_values,
                "benchmark_name": cfg["benchmark"] if bench is not None else None,
                "stats": {
                    # UWAGA: calc_stats zwraca klucz "Max Drawdown", nie "Max DD"
                    "cagr": round(float(stats.get("CAGR", 0)), 4),
                    "max_dd": round(float(stats.get("Max Drawdown", 0)), 4),
                    "sharpe": round(float(stats.get("Sharpe", 0)), 3),
                    "hit_rate": round(hits, 3),
                },
            }
            print(f"  symulacja: {len(equity)} miesiecy, "
                  f"CAGR {stats.get('CAGR', 0):.1%}", flush=True)

    if not args.dry_run and not args.skip_sim and "momentum" in wanted:
        tp.SIM_PATH.write_text(json.dumps(sim, indent=2, ensure_ascii=False),
                               encoding="utf-8")
        print(f"\nsymulacja zapisana: {tp.SIM_PATH.name}")

    if failures:
        print("\nStrategie pominiete w tym runie:")
        for item in failures:
            print(f"  - {item}")
```

- [ ] **Step 7: Uruchom dry-run dla jednej strategii**

Run: `GEM_CA_BUNDLE=/c/ProgramData/Norton/Antivirus/wscert.pem venv/Scripts/python.exe scripts/update_top_picks.py --only quality --skip-sim --dry-run`
Expected: pobiera ceny obu rynków, wypisuje piątkę SP500 i piątkę GPW ze score'ami 0–1, kończy się `--dry-run (quality): nic nie zapisano`. Bez zapisu do plików.

- [ ] **Step 8: Uruchom pełen pakiet**

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — 92 passed

- [ ] **Step 9: Commit**

```bash
git add scripts/update_top_picks.py
git commit -m "Compute three strategies in one CI run

Ceny pobierane raz na rynek i wspoldzielone. Odrzucenie snapshotu
strategii niekrytycznej loguje ostrzezenie zamiast zabijac run —
momentum nie moze paskudnie paść przez brak earningsow w yfinance.
Nowa flaga --only do odpalania pojedynczej strategii."
```

Uwaga dla implementującego: w treści commita usuń polskie znaki — ma być `nie moze padac`.

---

## Task 8: UI — trzy zakładki

**Files:**
- Modify: `pages/9_top_picks.py` (całość)
- Modify: `components/auth.py` (`PAGE_INFO[9]`)

**Kontekst:** dzisiejszy plik renderuje jedną strategię liniowo. Zamieniamy sekcje „skład" i „wyniki live" w funkcje przyjmujące strategię, wołane raz na zakładkę. Komponenty `top_pick_cards`, `section_band`, `kpi_card`, `picks_return_bar`, `category_pie`, `equity_chart` nie wymagają zmian.

- [ ] **Step 1: Wydziel funkcję renderującą skład**

W `pages/9_top_picks.py` zamień pętlę „Sekcja 1" (od `for market, label in MARKET_LABELS.items():` do `st.info(...)` włącznie) na wywołanie funkcji zdefiniowanej **przed** tą pętlą:

```python
EXTRA_COLUMNS = {
    "momentum": {"P/E": "pe", "Fwd P/E": "fwd_pe", "ROE": "roe",
                 "Dyw. %": "dividend_yield"},
    "earnings": {"P/E": "pe", "Fwd P/E": "fwd_pe", "ROE": "roe",
                 "Marza %": "profit_margin"},
    "quality": {"ROE": "roe", "Marza %": "profit_margin",
                "Wzrost przych. %": "revenue_growth", "Debt/Eq": "debt_to_equity"},
}


def render_sklad(latest: dict, markets: tuple[str, ...], strategy: str) -> None:
    """Sekcja 'sklad na <miesiac>' dla jednej strategii."""
    for market in markets:
        label = MARKET_LABELS[market]
        picks = latest.get(market) or []
        if not picks:
            continue

        # Data z entry_date pickow, NIE z pola asof — rynki koncza sesje w roznych
        # momentach (GPW zamyka sie wczesniej niz USA), a asof w snapshocie trzyma
        # tylko jedna, wspolna wartosc.
        sesje = sorted({p.get("entry_date", "") for p in picks if p.get("entry_date")})
        dzien = sesje[-1] if sesje else latest.get("asof", "—")
        icon, market_name = label.split(" ", 1)
        section_band(icon, market_name, f"policzone na zamkniecie {dzien}")

        tickers = [p["ticker"] for p in picks]
        prices = download_prices(tickers, period="1y")
        funda = bulk_fetch_universe(tuple(tickers))

        cards, rows = [], []
        for pick in picks:
            ticker = pick["ticker"]
            series = pd.Series(dtype=float)
            if ticker in prices.columns:
                series = prices[ticker].dropna()
            now = float(series.iloc[-1]) if not series.empty else None
            entry = pick["entry_price"]
            ret = (now / entry - 1) if (now is not None and entry) else None
            sector = pick.get("group", "") or "—"
            info = funda.get(ticker, {}) or {}

            cards.append({
                "ticker": ticker,
                "name": pick.get("name", ""),
                "sector": sector,
                "score": pick["score"],
                "entry": entry,
                "now": now,
                "ret": ret,
                "spark": series.tail(SPARK_SESSIONS) if not series.empty else None,
            })
            row = {
                "Ticker": ticker,
                "Nazwa": pick.get("name", ""),
                "Sektor": sector,
                "Score": round(pick["score"], 3),
                f"Wejscie ({CURRENCY[market]})": round(entry, 2),
                "Teraz": round(now, 2) if now is not None else None,
                "Zwrot": ret,
            }
            for column, key in EXTRA_COLUMNS[strategy].items():
                row[column] = info.get(key)
            rows.append(row)

        top_pick_cards(cards, CURRENCY[market])

        chart_col, pie_col = st.columns([3, 2])
        with chart_col:
            st.plotly_chart(
                picks_return_bar([c["ticker"] for c in cards],
                                 [c["ret"] for c in cards],
                                 title="Zwrot od rebalansu"),
                width="stretch",
                key=f"bar_{strategy}_{market}",
            )
        with pie_col:
            sector_counts = Counter(c["sector"] for c in cards)
            st.plotly_chart(
                category_pie(dict(sector_counts), title="Sektory w piatce (limit 2)"),
                width="stretch",
                key=f"pie_{strategy}_{market}",
            )

        with st.expander(f"📋 Szczegoly — {market_name}"):
            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                width="stretch",
                key=f"tabela_{strategy}_{market}",
                column_config={
                    "Zwrot": st.column_config.NumberColumn("Zwrot od rebalansu",
                                                           format="percent"),
                    "ROE": st.column_config.NumberColumn("ROE", format="%.2f"),
                },
            )
```

**Uwaga krytyczna:** `key=` w `st.plotly_chart`, `st.dataframe` i `st.expander` jest **wymagany** — trzy zakładki renderują te same komponenty i bez unikalnych kluczy Streamlit rzuci `DuplicateWidgetID`.

- [ ] **Step 2: Wydziel funkcję renderującą wyniki live**

Zamień sekcję „Sekcja 2: wyniki live" na funkcję (definiowaną obok `render_sklad`):

```python
def render_wyniki_live(history: dict, markets: tuple[str, ...], strategy: str) -> None:
    """Sekcja 'Wyniki live' — krzywa kapitalu z loga vs benchmark."""
    st.markdown("---")
    st.markdown("## Wyniki live")

    if len(history) < 2:
        st.info(
            f"Track record narasta od pierwszego snapshotu ({sorted(history)[0]}). "
            "Krzywa kapitalu pojawi sie po pierwszym rebalansie — wroc za miesiac."
        )
        return

    for market in markets:
        label = MARKET_LABELS[market]
        all_tickers = sorted({p["ticker"] for snap in history.values()
                              for p in (snap.get(market) or [])})
        if not all_tickers:
            continue
        cfg = BENCHMARKS[market]
        bench = cfg["ticker"]
        if cfg["source"] == "stooq":
            prices = download_prices(all_tickers, period="5y")
            bench_raw = download_stooq(bench, period="5y")
        else:
            prices = download_prices(all_tickers + [bench], period="5y")
            bench_raw = prices[bench] if bench in prices.columns else None

        equity = portfolio_equity(history, prices, market)
        if equity.empty:
            continue

        curves = {f"Top Picks {label}": equity}
        bench_total = None
        if bench_raw is not None and not bench_raw.empty:
            aligned = bench_raw.reindex(equity.index, method="ffill").dropna()
            if not aligned.empty and float(aligned.iloc[0]) != 0:
                bench_curve = (bench_raw.reindex(equity.index, method="ffill")
                               / float(aligned.iloc[0]) * 10000.0)
                curves[bench] = bench_curve
                bench_clean = bench_curve.dropna()
                if not bench_clean.empty:
                    bench_total = float(bench_clean.iloc[-1] / bench_clean.iloc[0] - 1)

        icon, market_name = label.split(" ", 1)
        section_band(icon, market_name, f"benchmark: {bench}")

        total = float(equity.iloc[-1] / equity.iloc[0] - 1)
        cols = st.columns(4)
        kpi_card(cols[0], "Zwrot od startu", fmt_pct(total),
                 f"kapital 10 000 {CURRENCY[market]}",
                 GREEN if total > 0 else RED if total < 0 else "#E5E7EB")
        if bench_total is None:
            kpi_card(cols[1], f"vs {bench}", "—", "brak danych benchmarku")
        else:
            diff = (total - bench_total) * 100
            kpi_card(cols[1], f"vs {bench}",
                     f"{diff:+.1f} p.p.".replace(".", ","),
                     f"{bench}: {fmt_pct(bench_total)}",
                     GREEN if diff > 0 else RED if diff < 0 else "#E5E7EB")
        kpi_card(cols[2], "Rebalansow", str(len(history)), "snapshotow w logu")
        kpi_card(cols[3], "Wartosc portfela",
                 f"{fmt_number(float(equity.iloc[-1]), 0)} {CURRENCY[market]}",
                 f"start 10 000 {CURRENCY[market]}")

        st.plotly_chart(equity_chart(curves, title=f"Top Picks {label} vs {bench}"),
                        width="stretch", key=f"equity_{strategy}_{market}")
```

- [ ] **Step 3: Wydziel funkcję nagłówka i całą zakładkę**

Dodaj funkcje składające zakładkę:

```python
STRATEGY_INFO = {
    "momentum": (
        "Momentum",
        "Ranking po momentum cenowym (12M/6M/3M/1M z anti-1M), "
        "maks. 2 spolki na sektor, prog plynnosci.",
    ),
    "earnings": (
        "Earnings Momentum",
        "Ranking po jakosci wynikow: seria pobic konsensusu (0-4 kwartaly), "
        "wielkosc zaskoczenia EPS i rewizje prognoz analitykow w oknie 90 dni.",
    ),
    "quality": (
        "Jakosc biznesu",
        "Ranking po ROE, marzy netto, wzroscie przychodow i niskim zadluzeniu. "
        "Dla bankow komponent zadluzenia jest pomijany, a wagi renormalizowane.",
    ),
}


def render_naglowek(latest_key: str, latest: dict, markets: tuple[str, ...]) -> None:
    """Karta z data skladu i odliczaniem do rebalansu."""
    today = date.today()
    nxt = _next_rebalance(today)
    days_left = (nxt - today).days
    n_picks = sum(len(latest.get(m) or []) for m in markets)
    rynki = "rynki" if len(markets) > 1 else "rynek"

    st.html(
        f'<div style="background:#141929;border:1px solid rgba(201,168,76,0.2);'
        f'border-radius:14px;padding:16px 20px;margin:8px 0 4px;display:flex;'
        f'flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:center">'
        f'<div>'
        f'<div style="font-size:0.68rem;color:{MUTED};text-transform:uppercase;'
        f'letter-spacing:0.08em">Sklad na</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:#C9A84C;'
        f'line-height:1.2">{latest_key}</div>'
        f'</div>'
        f'<div style="font-size:0.75rem;color:{MUTED};line-height:1.7;text-align:right">'
        f'{n_picks} spolek &middot; {len(markets)} {rynki} &middot; '
        f'regula v{latest.get("rule_version", "?")}<br>'
        f'nastepny rebalans <span style="color:#E5E7EB;font-weight:600">'
        f'{nxt.strftime("%d.%m.%Y")}</span> (za {days_left} dni)'
        f'</div>'
        f'</div>'
    )


def render_strategia(strategy: str) -> None:
    """Cala zakladka jednej strategii."""
    title, opis = STRATEGY_INFO[strategy]
    markets = STRATEGY_MARKETS[strategy]

    st.markdown(f"### {title}")
    st.caption(opis)

    history = load_history(HISTORY_PATHS[strategy])
    if not history:
        st.warning(
            f"Brak pliku `{HISTORY_PATHS[strategy].name}`. Uruchom "
            f"`python scripts/update_top_picks.py --only {strategy}`, "
            "zeby wygenerowac pierwszy snapshot."
        )
        return

    latest_key = sorted(history)[-1]
    latest = history[latest_key]

    versions = {snap.get("rule_version", 0) for snap in history.values()}
    if len(versions) > 1:
        st.warning(
            f"⚠️ Log zawiera snapshoty z roznych wersji reguly ({sorted(versions)}). "
            f"Wyniki sprzed zmiany nie sa porownywalne z obecnymi "
            f"(aktualna: v{RULE_VERSIONS[strategy]})."
        )

    render_naglowek(latest_key, latest, markets)
    render_sklad(latest, markets, strategy)

    if strategy == "earnings":
        st.info(
            "**Tylko S&P 500.** yfinance nie ma historii wynikow kwartalnych dla "
            "ok. 80% spolek z GPW (pomiar na probce 30 spolek, 2026-08-07), wiec "
            "reguła nie mialaby z czego wybierac. To samo ograniczenie dotyczy "
            "strony Insider Screener."
        )
    elif strategy == "quality":
        st.info(
            "Dla bankow z GPW komponent zadluzenia jest pomijany — struktura "
            "bilansu banku nie jest porownywalna ze spolka przemyslowa. Wagi "
            "pozostalych trzech skladnikow sa wtedy renormalizowane do 100%."
        )

    render_wyniki_live(history, markets, strategy)

    if strategy == "momentum":
        render_symulacja()
    else:
        st.markdown("---")
        st.info(
            "**Bez symulacji wstecz.** Ta strategia opiera sie na danych "
            "fundamentalnych, ktore yfinance udostepnia wylacznie w wersji "
            "„na dzis" — nie da sie odtworzyc, jak wygladaly rok temu. "
            "Symulacja liczylaby historyczne miesiace dzisiejszymi danymi "
            "(lookahead bias), wiec swiadomie jej nie ma. Track record narasta "
            "od pierwszego snapshotu."
        )
```

Sekcję 3 (symulacja) opakuj w `def render_symulacja() -> None:` — przenieś do niej istniejący blok `with st.expander("🔬 Symulacja reguly wstecz...")` bez zmian w treści.

- [ ] **Step 4: Podmień importy i wywołanie na zakładki**

Zamień blok importów w `pages/9_top_picks.py` na:

```python
from data.top_picks import (
    HISTORY_PATHS,
    RULE_VERSIONS,
    SIM_PATH,
    STRATEGY_MARKETS,
    load_history,
    portfolio_equity,
)
```

Na końcu pliku, zamiast liniowego renderowania, wstaw przed `render_footer()`:

```python
tab_mom, tab_earn, tab_qual = st.tabs([
    "📈 Momentum", "📊 Earnings Momentum", "🏛️ Jakosc biznesu",
])
with tab_mom:
    render_strategia("momentum")
with tab_earn:
    render_strategia("earnings")
with tab_qual:
    render_strategia("quality")
```

**Pułapka z CLAUDE.md:** wszystkie funkcje `render_*` muszą być zdefiniowane na poziomie modułu **PRZED** blokiem `with tab:`. Ta sama regresja co przy F12 (commit `d7c3407`, `NameError`).

- [ ] **Step 5: Sprawdź kompilację i brak zduplikowanych kluczy**

Run: `venv/Scripts/python.exe -c "import py_compile; py_compile.compile('pages/9_top_picks.py', doraise=True); print('OK')"`
Expected: `OK`

Run: `grep -c 'key=f"' pages/9_top_picks.py`
Expected: `4` — `bar_`, `pie_`, `tabela_` w `render_sklad` i `equity_` w `render_wyniki_live`

- [ ] **Step 6: Zaktualizuj PAGE_INFO**

W `components/auth.py` zamień wpis `9:` na:

```python
    9: ("🎯", "Top Picks", "Trzy miesieczne piatki spolek: momentum cenowe, jakosc wynikow kwartalnych i jakosc biznesu"),
```

- [ ] **Step 7: Odpal aplikację i sprawdź wszystkie trzy zakładki**

Run: `GEM_CA_BUNDLE=/c/ProgramData/Norton/Antivirus/wscert.pem venv/Scripts/python.exe -m streamlit run app.py --server.port 8501 --server.headless true`

Sprawdź w przeglądarce na `http://localhost:8501/top_picks`:
- Zakładka Momentum: identyczna z dzisiejszą, z sekcją symulacji
- Zakładka Earnings Momentum: ostrzeżenie o braku pliku loga (dopóki nie odpalisz skryptu), info box o SP500-only
- Zakładka Jakosc biznesu: jak wyżej + nota o bankach
- Brak `DuplicateWidgetID` w konsoli

Ubij serwer po sprawdzeniu.

- [ ] **Step 8: Commit**

```bash
git add pages/9_top_picks.py components/auth.py
git commit -m "Add three strategy tabs to Top Picks page

Sekcje sklad i wyniki live wydzielone do funkcji wolanych raz na zakladke.
Kazdy komponent ma unikalny key — trzy zakladki renderuja te same widgety.
Zakladki fundamentalne zamiast symulacji maja komunikat o forward-only."
```

---

## Task 9: Wygeneruj pierwsze snapshoty i zamknij dokumentację

**Files:**
- Create: `data/top_picks_earnings_history.json`, `data/top_picks_quality_history.json`
- Modify: `CLAUDE.md`, `.github/workflows/top-picks.yml`

- [ ] **Step 1: Wygeneruj pierwsze snapshoty**

Run:
```bash
GEM_CA_BUNDLE=/c/ProgramData/Norton/Antivirus/wscert.pem \
  venv/Scripts/python.exe scripts/update_top_picks.py --skip-sim
```
Expected: trzy bloki `########## strategia: ... ##########`. Momentum pomija istniejący snapshot sierpniowy (`juz istnial — pomijam`), earnings i quality zapisują nowe pliki. Jeśli któraś strategia zostanie odrzucona, powód pojawi się w sekcji „Strategie pominiete w tym runie".

- [ ] **Step 2: Sprawdź zawartość nowych logów**

Run: `venv/Scripts/python.exe -c "import json,pathlib; [print(p.name, list(json.loads(p.read_text(encoding='utf-8')))) for p in pathlib.Path('data').glob('top_picks_*history.json')]"`
Expected: trzy pliki, każdy z kluczem `2026-08-01`

- [ ] **Step 3: Zaktualizuj workflow**

W `.github/workflows/top-picks.yml` znajdź krok uruchamiający skrypt i upewnij się, że nie ma `--only`. Podnieś `timeout-minutes` do 30 (bulk earnings + ratios dla ~600 spółek przy zimnym cache):

```yaml
    timeout-minutes: 30
```

Jeśli klucz `timeout-minutes` nie istnieje, dodaj go na poziomie `jobs.<nazwa>`.

- [ ] **Step 4: Zaktualizuj CLAUDE.md**

W sekcji `- **Top Picks (F18):**` dopisz na końcu, po akapicie o UI z 2026-08-07:

```markdown
  - **Trzy strategie (2026-08-07):** strona ma `st.tabs` z trzema regulami, kazda z osobnym append-only logiem i wlasnym `RULE_VERSIONS[...]`. **Momentum** (`MOMENTUM_SCORER`, `top_picks_history.json`, SP500+GPW) — bez zmian, jedyna z symulacja wstecz. **Earnings Momentum** (`EARNINGS_SCORER`, `top_picks_earnings_history.json`, **SP500-only**) — beat streak 0-4 `.40` + EPS surprise `.35` + rewizja konsensusu 90d `.25`. **Jakosc biznesu** (`QUALITY_SCORER`, `top_picks_quality_history.json`, SP500+GPW) — ROE `.30` + marza `.25` + wzrost przychodow `.25` + odwrocony dlug `.20`, banki GPW bez komponentu dlugu. `select_picks(..., scorer=)` przyjmuje `Scorer` (dataclass: `name`, `supports_asof`, `fn`); wspolne pozostaja filtr plynnosci, limit sektorowy i rowne wagi. **`simulate_rule()` podnosi `ValueError` dla scorera z `supports_asof=False`** — yfinance oddaje fundamenty tylko „na dzis", wiec symulacja liczylaby historie dzisiejszymi danymi. **Pomiar pokrycia 2026-08-07 (probka 25 SP500 + 30 GPW):** GPW ma 80% brakow w historii EPS (stad SP500-only dla earnings), yfinance oddaje 4 kwartaly zamiast 8 (stad brak symulacji dla obu nowych regul), ROE 92%/100%, P/E 100%/77%. Import `data.financials` siedzi **wewnatrz** funkcji scorera — `data/top_picks.py` zostaje importowalny bez streamlita. CI: `--only <strategia>` do pojedynczego runu; odrzucenie snapshotu strategii niekrytycznej loguje ostrzezenie zamiast zabijac run. Spec: `docs/superpowers/specs/2026-08-07-top-picks-strategie-design.md`. Plan: `docs/superpowers/plans/2026-08-07-top-picks-strategie.md`.
```

W bloku drzewa katalogów zaktualizuj opis strony 9:

```
  9_top_picks.py        # Top Picks — 3 zakladki (momentum / earnings / jakosc), miesieczne piatki SP500+GPW
```

- [ ] **Step 5: Uruchom pełną weryfikację**

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — 92 passed

Run: `for f in app.py components/*.py pages/*.py data/*.py scripts/*.py; do venv/Scripts/python.exe -c "import py_compile,sys; py_compile.compile(sys.argv[1], doraise=True)" "$f" || echo "FAIL $f"; done; echo done`
Expected: brak linii `FAIL`

Run: `venv/Scripts/python.exe -c "import sys; import data.top_picks; print('streamlit w sys.modules:', 'streamlit' in sys.modules)"`
Expected: `streamlit w sys.modules: False`

- [ ] **Step 6: Commit**

```bash
git add data/top_picks_earnings_history.json data/top_picks_quality_history.json \
        CLAUDE.md .github/workflows/top-picks.yml
git commit -m "Add first snapshots for earnings and quality strategies

Plus dokumentacja trzech regul w CLAUDE.md i timeout 30 min w workflow
(bulk earnings + ratios dla ~600 spolek przy zimnym cache)."
```

---

## Weryfikacja końcowa

Po Tasku 9 sprawdź całość:

- [ ] `venv/Scripts/python.exe -m pytest tests/ -q` → 92 passed (66 wyjściowych + 26 nowych)
- [ ] Istniejące 13 testów F18 **nie zostało zmodyfikowanych** — `git diff daa4321 -- tests/test_top_picks.py` pokazuje wyłącznie dopisane bloki, żadnych zmian w liniach 1–218
- [ ] `data/top_picks_history.json` **nie został ruszony** — `git diff daa4321 -- data/top_picks_history.json` jest pusty
- [ ] Wszystkie trzy zakładki renderują się bez `DuplicateWidgetID`
- [ ] Zakładka Momentum wygląda identycznie jak przed zmianą
- [ ] `data/top_picks.py` importuje się bez streamlita
