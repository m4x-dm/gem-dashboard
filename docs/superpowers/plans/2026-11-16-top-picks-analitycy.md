# Top Picks — strategie analityczne: plan wdrożenia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dodać do Top Picks dwie strategie oparte na konsensusie analityków — „Polecane przez analityków” i „Potencjał do ceny docelowej” — na S&P 500 i GPW, z comiesięcznym logiem jak obecne strategie.

**Architecture:** Dwa nowe forward-only scorery w `data/top_picks.py` (wzorzec `make_quality_scorer`), dane z istniejącego `bulk_fetch_universe` (+ pole `recommendation_mean`). CI (`scripts/update_top_picks.py` + workflow) liczy i zapisuje snapshoty do dwóch nowych logów, wzbogacając pozycje o kontekst analityków. Strona `views/spolki/top_picks.py` dostaje dwie nowe zakładki.

**Tech Stack:** Python 3.11 (venv), pandas, yfinance, Streamlit 1.55, pytest + `streamlit.testing.v1.AppTest`.

**Spec:** `docs/superpowers/specs/2026-11-16-top-picks-analitycy-design.md`

**Konwencje repo (przeczytaj przed startem):**
- Testy: `venv/Scripts/python.exe -m pytest tests -q -m "not network"` (z katalogu repo). Pełny pakiet ~1,5 min, obecnie 376 passed / 44 skipped.
- `data/top_picks.py` MUSI być importowalny bez streamlita — `data.financials` importuj wewnątrz funkcji.
- Teksty UI w `views/spolki/top_picks.py` i `components/cards.py` są bez polskich znaków (ASCII) — trzymaj się tego.
- Commity: krótki imperative tytuł po angielsku, stopka `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Bez pusha do czasu zgody użytkownika.

---

## Mapa plików

| Plik | Zmiana |
|---|---|
| `data/financials.py` | `bulk_fetch_universe`: + pole `recommendation_mean` |
| `data/top_picks.py` | stabilne sortowanie w `select_picks`; stałe `MIN_ANALYSTS_SP500/GPW`, `UPSIDE_MAX_RECOMMENDATION`; `min_analysts_for`, `consensus_label`; `make_analyst_scorer`, `make_upside_scorer`, `ANALYST_SCORER`, `UPSIDE_SCORER`; `enrich_analyst_context`; wpisy w `RULE_VERSIONS`, `STRATEGY_MARKETS`, `HISTORY_PATHS` |
| `scripts/update_top_picks.py` | `STRATEGIES` + `_scorer_for` dla nowych strategii; `validate_snapshot(min_picks=...)`; wzbogacenie pozycji |
| `.github/workflows/top-picks.yml` | `git add` dwóch nowych logów |
| `components/cards.py` | `top_pick_cards`: opcjonalne `score_text` i `note` |
| `views/spolki/top_picks.py` | 2 nowe zakładki, `STRATEGY_INFO`, kolumny tabeli z pozycji, notki |
| `data/top_picks_analyst_history.json`, `data/top_picks_upside_history.json` | pierwsze snapshoty (Task 10) |
| `tests/test_top_picks.py` | nowe testy + aktualizacja testów rejestru |
| `tests/test_top_picks_page.py` (nowy) | AppTest strony z 5 zakładkami |

---

### Task 1: `recommendation_mean` w `bulk_fetch_universe`

**Files:**
- Modify: `data/financials.py` (słownik w `bulk_fetch_universe`, ok. linia 413–417)
- Test: `tests/test_top_picks.py` (dopisz na końcu)

- [ ] **Step 1: Write the failing test**

```python
# ====== Strategie analityczne (2026-11-16) ======

def test_bulk_fetch_universe_zwraca_recommendation_mean(monkeypatch):
    import data.financials as fin
    info = {"currentPrice": 100.0, "trailingEps": 5.0,
            "recommendationMean": 1.8, "numberOfAnalystOpinions": 12,
            "targetMeanPrice": 130.0}
    monkeypatch.setattr(fin, "_fetch_info", lambda t: info)
    out = fin.bulk_fetch_universe(("ZZTEST_RM1",))
    assert out["ZZTEST_RM1"]["recommendation_mean"] == 1.8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py::test_bulk_fetch_universe_zwraca_recommendation_mean -q`
Expected: FAIL z `KeyError: 'recommendation_mean'`

- [ ] **Step 3: Write minimal implementation**

W `data/financials.py`, w słowniku budowanym w `bulk_fetch_universe`, pod linią `"recommendation_key": info.get("recommendationKey"),` dodaj:

```python
            "recommendation_mean": info.get("recommendationMean"),
```

- [ ] **Step 4: Run test to verify it passes**

Run: jak w Step 2. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/financials.py tests/test_top_picks.py
git commit -m "Financials: expose recommendation_mean in bulk_fetch_universe"
```

---

### Task 2: stabilne sortowanie w `select_picks`

**Files:**
- Modify: `data/top_picks.py` (`select_picks`, linia `scores = scores.dropna().sort_values(ascending=False)`)
- Test: `tests/test_top_picks.py`

- [ ] **Step 1: Write the failing test**

```python
def test_select_picks_remis_rozstrzyga_ticker_alfabetycznie():
    prices = _frame(400, ("CCC", "AAA", "BBB"))
    volumes = _volumes(prices)
    groups = {"AAA": "S1", "BBB": "S2", "CCC": "S3"}
    tie = tp.Scorer(name="tie", supports_asof=True,
                    fn=lambda eligible, px, asof: pd.Series(1.0, index=["CCC", "BBB", "AAA"]))
    picks = tp.select_picks(prices, volumes, groups, prices.index[-1],
                            top_n=3, scorer=tie)
    assert [p["ticker"] for p in picks] == ["AAA", "BBB", "CCC"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py::test_select_picks_remis_rozstrzyga_ticker_alfabetycznie -q`
Expected: FAIL (kolejność inna niż alfabetyczna)

- [ ] **Step 3: Write minimal implementation**

W `select_picks` zamień:

```python
    scores = scores.dropna().sort_values(ascending=False)
```

na:

```python
    # Stabilne sortowanie po posortowanym indeksie: pelne remisy rozstrzyga
    # ticker alfabetycznie (determinizm logu). Domyslny quicksort nie jest stabilny.
    scores = scores.dropna().sort_index().sort_values(ascending=False, kind="mergesort")
```

- [ ] **Step 4: Run tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q`
Expected: wszystkie PASS (stare testy select_picks też)

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Top picks: deterministic tie-break in select_picks"
```

---

### Task 3: scorer „Polecane przez analityków”

**Files:**
- Modify: `data/top_picks.py` (po `QUALITY_SCORER = make_quality_scorer()`)
- Test: `tests/test_top_picks.py`

- [ ] **Step 1: Write the failing tests**

```python
def _analyst_bulk():
    return {
        "AAA": {"recommendation_mean": 2.4, "num_analysts": 20,
                "target_mean": 150.0, "current_price": 100.0},
        "BBB": {"recommendation_mean": 1.5, "num_analysts": 10,
                "target_mean": 110.0, "current_price": 100.0},
        "CCC": {"recommendation_mean": 1.5, "num_analysts": 30,
                "target_mean": 105.0, "current_price": 100.0},
        "DDD": {"recommendation_mean": 1.1, "num_analysts": 4,     # ponizej progu SP500
                "target_mean": 200.0, "current_price": 100.0},
        "EEE": {"recommendation_mean": None, "num_analysts": 25,
                "target_mean": 120.0, "current_price": 100.0},
    }


def test_min_analysts_zalezy_od_rynku():
    assert tp.min_analysts_for("AAPL") == 5
    assert tp.min_analysts_for("PKO.WA") == 3


def test_consensus_label():
    assert tp.consensus_label(1.3) == "Strong Buy"
    assert tp.consensus_label(2.0) == "Buy"
    assert tp.consensus_label(3.0) == "Hold"
    assert tp.consensus_label(4.0) == "Sell"
    assert tp.consensus_label(4.8) == "Strong Sell"
    assert tp.consensus_label(None) == "—"


def test_analyst_scorer_rankuje_po_konsensusie_z_tiebreakiem():
    scorer = tp.make_analyst_scorer(bulk_fn=lambda tickers: _analyst_bulk())
    scores = scorer.fn(["AAA", "BBB", "CCC", "DDD", "EEE"], pd.DataFrame(),
                       pd.Timestamp("2026-11-16"))
    ranked = list(scores.dropna().sort_values(ascending=False).index)
    # CCC i BBB maja 1,5 — CCC ma wiecej analitykow; DDD ponizej progu; EEE bez rm
    assert ranked == ["CCC", "BBB", "AAA"]


def test_analyst_scorer_gpw_ma_nizszy_prog():
    bulk = {"PKO.WA": {"recommendation_mean": 1.8, "num_analysts": 3}}
    scorer = tp.make_analyst_scorer(bulk_fn=lambda tickers: bulk)
    scores = scorer.fn(["PKO.WA"], pd.DataFrame(), pd.Timestamp("2026-11-16"))
    assert pd.notna(scores["PKO.WA"])


def test_analyst_scorer_jest_forward_only_i_bez_danych_nan():
    scorer = tp.make_analyst_scorer(bulk_fn=lambda tickers: {})
    assert scorer.supports_asof is False
    scores = scorer.fn(["AAA"], pd.DataFrame(), pd.Timestamp("2026-11-16"))
    assert scores.dropna().empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k "analyst or consensus or min_analysts"`
Expected: FAIL z `AttributeError: module 'data.top_picks' has no attribute ...`

- [ ] **Step 3: Write minimal implementation**

W `data/top_picks.py` po `QUALITY_SCORER = make_quality_scorer()` dodaj:

```python
# ====== Scorery analityczne (2026-11-16, forward-only) ======
#
# Pomiar pokrycia yfinance 2026-11-16: SP500 ma konsensus prawie wszedzie
# (mediana 18 analitykow), GPW tylko ok. 1/3 spolek (mediana 3) — stad
# nizszy prog dla GPW. Ranking oparty na 1-2 opiniach to opinia jednego biura.

MIN_ANALYSTS_SP500 = 5
MIN_ANALYSTS_GPW = 3
UPSIDE_MAX_RECOMMENDATION = 2.5   # co najmniej "Buy" w skali Yahoo 1-5


def min_analysts_for(ticker: str) -> int:
    """Prog liczby analitykow zalezny od rynku (GPW = sufiks .WA)."""
    return MIN_ANALYSTS_GPW if ticker.endswith(".WA") else MIN_ANALYSTS_SP500


def consensus_label(rm) -> str:
    """Etykieta sredniej rekomendacji Yahoo (1 = Strong Buy ... 5 = Strong Sell)."""
    if rm is None or pd.isna(rm):
        return "—"
    rm = float(rm)
    if rm <= 1.5:
        return "Strong Buy"
    if rm <= 2.5:
        return "Buy"
    if rm <= 3.5:
        return "Hold"
    if rm <= 4.5:
        return "Sell"
    return "Strong Sell"


def _analyst_fields(info: dict) -> tuple[float | None, int]:
    """(recommendation_mean, num_analysts) z rekordu bulk, z bezpieczna konwersja."""
    rm = info.get("recommendation_mean")
    try:
        rm = float(rm) if rm is not None else None
    except (TypeError, ValueError):
        rm = None
    try:
        n = int(info.get("num_analysts") or 0)
    except (TypeError, ValueError):
        n = 0
    return rm, n


def _bulk_source(bulk_fn):
    if bulk_fn is not None:
        return bulk_fn
    from data.financials import bulk_fetch_universe
    return bulk_fetch_universe


def make_analyst_scorer(bulk_fn=None) -> Scorer:
    """Scorer 'Polecane przez analitykow' — najnizsza srednia rekomendacja.

    score = -recommendation_mean + min(num_analysts, 99) * 1e-5
    (rm ma krok 0,01, wiec skladnik <= 0,001 rozstrzyga tylko remisy:
    wiecej analitykow = wyzej). Spolki ponizej progu analitykow lub bez
    rm dostaja NaN i odpadaja w select_picks.

    supports_asof=False — yfinance zna tylko dzisiejszy konsensus.
    """
    def _fn(eligible: list[str], px: pd.DataFrame, asof: pd.Timestamp) -> pd.Series:
        bulk = _bulk_source(bulk_fn)(tuple(eligible)) or {}
        out = {}
        for ticker in eligible:
            rm, n = _analyst_fields(bulk.get(ticker) or {})
            if rm is None or n < min_analysts_for(ticker):
                out[ticker] = float("nan")
            else:
                out[ticker] = -rm + min(n, 99) * 1e-5
        return pd.Series(out, index=eligible, dtype="float64")

    return Scorer(name="analyst", supports_asof=False, fn=_fn)


ANALYST_SCORER = make_analyst_scorer()
```

- [ ] **Step 4: Run tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k "analyst or consensus or min_analysts"`
Expected: PASS

Sprawdź też import bez streamlita:
Run: `venv/Scripts/python.exe -c "import sys; import data.top_picks; print('streamlit' in sys.modules)"`
Expected: `False`

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Top picks: analyst consensus scorer"
```

---

### Task 4: scorer „Potencjał do ceny docelowej”

**Files:**
- Modify: `data/top_picks.py` (po `ANALYST_SCORER = make_analyst_scorer()`)
- Test: `tests/test_top_picks.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_upside_scorer_wymaga_konsensusu_i_rankuje_po_potencjale():
    bulk = _analyst_bulk()
    bulk["FFF"] = {"recommendation_mean": 3.2, "num_analysts": 15,   # Hold -> odpada
                   "target_mean": 300.0, "current_price": 100.0}
    scorer = tp.make_upside_scorer(bulk_fn=lambda tickers: bulk)
    scores = scorer.fn(list(bulk), pd.DataFrame(), pd.Timestamp("2026-11-16"))
    ranked = list(scores.dropna().sort_values(ascending=False).index)
    # AAA +50%, BBB +10%, CCC +5%; DDD ponizej progu, EEE bez rm, FFF Hold
    assert ranked == ["AAA", "BBB", "CCC"]
    assert scores["AAA"] == pytest.approx(0.50, abs=1e-4)


def test_upside_scorer_odrzuca_brak_ceny_i_celu():
    bulk = {
        "AAA": {"recommendation_mean": 1.5, "num_analysts": 10,
                "target_mean": None, "current_price": 100.0},
        "BBB": {"recommendation_mean": 1.5, "num_analysts": 10,
                "target_mean": 120.0, "current_price": 0.0},
        "CCC": {"recommendation_mean": 1.5, "num_analysts": 10,
                "target_mean": 120.0, "current_price": None},
    }
    scorer = tp.make_upside_scorer(bulk_fn=lambda tickers: bulk)
    scores = scorer.fn(list(bulk), pd.DataFrame(), pd.Timestamp("2026-11-16"))
    assert scores.dropna().empty


def test_upside_scorer_jest_forward_only():
    assert tp.make_upside_scorer(bulk_fn=lambda t: {}).supports_asof is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k upside`
Expected: FAIL z `AttributeError: ... make_upside_scorer`

- [ ] **Step 3: Write minimal implementation**

```python
def _upside(info: dict) -> float | None:
    """target_mean / current_price - 1; None gdy brak lub cena <= 0."""
    try:
        target = float(info.get("target_mean"))
        price = float(info.get("current_price"))
    except (TypeError, ValueError):
        return None
    if price <= 0 or pd.isna(target) or pd.isna(price):
        return None
    return target / price - 1


def make_upside_scorer(bulk_fn=None) -> Scorer:
    """Scorer 'Potencjal do ceny docelowej' — tylko spolki z konsensusem >= Buy.

    Warunek rm <= UPSIDE_MAX_RECOMMENDATION odcina pulapke: kurs mocno spadl,
    analitycy nie zdazyli obnizyc celow, a sami mowia Hold/Sell.
    score = upside + min(num_analysts, 99) * 1e-7 (tie-break).

    supports_asof=False — yfinance zna tylko dzisiejsze ceny docelowe.
    """
    def _fn(eligible: list[str], px: pd.DataFrame, asof: pd.Timestamp) -> pd.Series:
        bulk = _bulk_source(bulk_fn)(tuple(eligible)) or {}
        out = {}
        for ticker in eligible:
            info = bulk.get(ticker) or {}
            rm, n = _analyst_fields(info)
            up = _upside(info)
            if (rm is None or rm > UPSIDE_MAX_RECOMMENDATION
                    or n < min_analysts_for(ticker) or up is None):
                out[ticker] = float("nan")
            else:
                out[ticker] = up + min(n, 99) * 1e-7
        return pd.Series(out, index=eligible, dtype="float64")

    return Scorer(name="upside", supports_asof=False, fn=_fn)


UPSIDE_SCORER = make_upside_scorer()
```

- [ ] **Step 4: Run tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k "upside or analyst"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Top picks: target upside scorer with consensus filter"
```

---

### Task 5: rejestr strategii (wersje, rynki, logi)

**Files:**
- Modify: `data/top_picks.py` (`RULE_VERSIONS`, `STRATEGY_MARKETS`, `HISTORY_PATHS`)
- Modify: `tests/test_top_picks.py` (`test_kazda_strategia_ma_wersje_i_sciezke_loga`, `test_strategie_znaja_swoje_rynki`)

- [ ] **Step 1: Update the tests (fail first)**

W `test_kazda_strategia_ma_wersje_i_sciezke_loga` zamień zbiory i licznik:

```python
    names = {"momentum", "earnings", "quality", "analyst", "upside"}
    assert set(tp.RULE_VERSIONS) == names
    assert set(tp.HISTORY_PATHS) == names
    for name, path in tp.HISTORY_PATHS.items():
        assert path.name.endswith(".json"), f"{name}: sciezka nie jest jsonem"
    assert tp.HISTORY_PATHS["momentum"] == tp.HISTORY_PATH
    # Rozne pliki, zeby strategie sie nie nadpisywaly
    assert len({p.name for p in tp.HISTORY_PATHS.values()}) == len(names)
```

W `test_strategie_znaja_swoje_rynki` dopisz:

```python
    assert tp.STRATEGY_MARKETS["analyst"] == ("sp500", "gpw")
    assert tp.STRATEGY_MARKETS["upside"] == ("sp500", "gpw")
```

- [ ] **Step 2: Run to verify failure**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k "wersje or rynki"`
Expected: FAIL

- [ ] **Step 3: Implement**

```python
RULE_VERSIONS = {
    "momentum": 1,
    "earnings": 1,
    "quality": 1,
    "analyst": 1,
    "upside": 1,
}
```

```python
STRATEGY_MARKETS = {
    "momentum": ("sp500", "gpw"),
    "earnings": ("sp500",),
    "quality": ("sp500", "gpw"),
    "analyst": ("sp500", "gpw"),
    "upside": ("sp500", "gpw"),
}
```

```python
HISTORY_PATHS = {
    "momentum": HISTORY_PATH,
    "earnings": _DATA_DIR / "top_picks_earnings_history.json",
    "quality": _DATA_DIR / "top_picks_quality_history.json",
    "analyst": _DATA_DIR / "top_picks_analyst_history.json",
    "upside": _DATA_DIR / "top_picks_upside_history.json",
}
```

- [ ] **Step 4: Run tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Top picks: register analyst and upside strategies"
```

---

### Task 6: kontekst analityków w pozycjach (`enrich_analyst_context`)

**Files:**
- Modify: `data/top_picks.py` (po `UPSIDE_SCORER`)
- Test: `tests/test_top_picks.py`

- [ ] **Step 1: Write the failing test**

```python
def test_enrich_analyst_context_dopisuje_pola():
    picks = [{"ticker": "AAA"}, {"ticker": "ZZZ"}]
    tp.enrich_analyst_context(picks, _analyst_bulk())
    assert picks[0]["recommendation_mean"] == 2.4
    assert picks[0]["num_analysts"] == 20
    assert picks[0]["target_mean"] == 150.0
    assert picks[0]["upside"] == pytest.approx(0.5, abs=1e-4)
    # brak rekordu -> pola sa, ale puste (UI pokazuje "—")
    assert picks[1]["recommendation_mean"] is None
    assert picks[1]["upside"] is None
```

- [ ] **Step 2: Run to verify failure**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py::test_enrich_analyst_context_dopisuje_pola -q`
Expected: FAIL (`AttributeError`)

- [ ] **Step 3: Implement**

```python
def enrich_analyst_context(picks: list[dict], bulk: dict) -> list[dict]:
    """Dopisuje do pozycji kontekst analitykow z dnia wyboru (in place).

    Zapisywany w logu, zeby karta pokazywala oczekiwania z dnia zakupu,
    a nie dzisiejsze.
    """
    for pick in picks:
        info = bulk.get(pick["ticker"]) or {}
        rm, n = _analyst_fields(info)
        up = _upside(info)
        target = info.get("target_mean")
        pick["recommendation_mean"] = round(rm, 2) if rm is not None else None
        pick["num_analysts"] = n
        pick["target_mean"] = round(float(target), 2) if target is not None else None
        pick["upside"] = round(up, 4) if up is not None else None
    return picks
```

- [ ] **Step 4: Run tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks.py
git commit -m "Top picks: store analyst context with each pick"
```

---

### Task 7: CI script — nowe strategie, krótszy skład, wzbogacenie

**Files:**
- Modify: `scripts/update_top_picks.py` (`validate_snapshot`, `STRATEGIES`, `_scorer_for`, pętla strategii)
- Test: `tests/test_top_picks.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_validate_snapshot_akceptuje_krotszy_sklad_gdy_min_picks():
    from scripts.update_top_picks import validate_snapshot

    prices = _frame(400, ("AAA", "BBB"))
    picks = [{"ticker": "AAA", "group": "S1"}]
    assert validate_snapshot("gpw", ["AAA", "BBB"], prices, picks,
                             asof=prices.index[-1], top_n=5, min_picks=1) is None
    powod = validate_snapshot("gpw", ["AAA", "BBB"], prices, [],
                              asof=prices.index[-1], top_n=5, min_picks=1)
    assert powod is not None and "pozycji" in powod


def test_strategie_ci_obejmuja_analitykow():
    from scripts.update_top_picks import STRATEGIES, _scorer_for

    assert set(STRATEGIES) == set(tp.RULE_VERSIONS)
    for name in ("analyst", "upside"):
        assert STRATEGIES[name]["simulate"] is False
        assert STRATEGIES[name]["critical"] is False
        assert STRATEGIES[name]["min_picks"] == 1
        assert _scorer_for(STRATEGIES[name]["scorer"]).name == name
```

- [ ] **Step 2: Run to verify failure**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q -k "min_picks or ci_obejmuja"`
Expected: FAIL (`TypeError: unexpected keyword 'min_picks'` / `KeyError`)

- [ ] **Step 3: Implement**

`validate_snapshot` — nowa sygnatura i warunek długości:

```python
def validate_snapshot(market: str, tickers: list[str], prices: pd.DataFrame,
                      picks: list[dict], asof: pd.Timestamp,
                      top_n: int, min_picks: int | None = None) -> str | None:
```

zamień blok:

```python
    if len(picks) != top_n:
        return f"[{market}] regula zwrocila {len(picks)} pozycji zamiast {top_n}"
```

na:

```python
    # min_picks=None -> wymagamy pelnej piatki (momentum/earnings/quality).
    # Strategie analityczne dopuszczaja krotszy sklad (cienkie pokrycie GPW),
    # ale nigdy pusty — pusty wpis klamalby w "Wyniki live".
    if min_picks is None:
        if len(picks) != top_n:
            return f"[{market}] regula zwrocila {len(picks)} pozycji zamiast {top_n}"
    elif not (min_picks <= len(picks) <= top_n):
        return (f"[{market}] regula zwrocila {len(picks)} pozycji "
                f"(dozwolone {min_picks}-{top_n})")
```

`STRATEGIES` i `_scorer_for`:

```python
STRATEGIES = {
    "momentum": {"scorer": None, "simulate": True, "critical": True, "min_picks": None},
    "earnings": {"scorer": "earnings", "simulate": False, "critical": False, "min_picks": None},
    "quality": {"scorer": "quality", "simulate": False, "critical": False, "min_picks": None},
    "analyst": {"scorer": "analyst", "simulate": False, "critical": False, "min_picks": 1},
    "upside": {"scorer": "upside", "simulate": False, "critical": False, "min_picks": 1},
}


def _scorer_for(name: str):
    """Leniwe pobranie scorera — importy financials tylko gdy potrzebne."""
    return {
        "earnings": tp.EARNINGS_SCORER,
        "quality": tp.QUALITY_SCORER,
        "analyst": tp.ANALYST_SCORER,
        "upside": tp.UPSIDE_SCORER,
    }.get(name)
```

W pętli rynków w `main()`, zaraz po `picks = tp.select_picks(...)`, dodaj obsługę pustego rynku (spec: pusty rynek nie zapisuje się jako wynik, ale nie blokuje drugiego rynku):

```python
            if spec["min_picks"] is not None and not picks:
                # Strategie analityczne: brak kandydatow na jednym rynku (cienkie
                # pokrycie GPW) pomija tylko ten rynek, nie cala strategie.
                print(f"  ({strategy}/{market}) brak spolek spelniajacych warunki — "
                      f"rynek pominiety w snapshocie", flush=True)
                continue
```

i zamień wywołanie walidacji:

```python
            reason = validate_snapshot(market, cfg["tickers"], prices, picks,
                                       today, args.top_n,
                                       min_picks=spec["min_picks"])
```

Po pętli rynków (przed `if rejected: continue`) dodaj warunek, że snapshot bez żadnego rynku nie jest zapisywany:

```python
        if not rejected and not any(snapshot.get(m) for m in markets):
            print(f"  ODRZUCONO ({strategy}): zaden rynek nie dal skladu", flush=True)
            failures.append(f"{strategy}: pusty snapshot")
            rejected = True
```

i pod pętlą `for pick in picks: pick["name"] = ...` dodaj:

```python
            if strategy in ("analyst", "upside"):
                from data.financials import bulk_fetch_universe
                tp.enrich_analyst_context(
                    picks, bulk_fetch_universe(tuple(p["ticker"] for p in picks)))
```

- [ ] **Step 4: Run tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py -q`
Expected: PASS (w tym stare testy `validate_snapshot`)

- [ ] **Step 5: Commit**

```bash
git add scripts/update_top_picks.py tests/test_top_picks.py
git commit -m "Top picks CI: analyst and upside strategies, allow short GPW lists"
```

---

### Task 8: workflow commituje wszystkie logi

**Files:**
- Modify: `.github/workflows/top-picks.yml` (krok „Commit and push”)
- Test: `tests/test_top_picks.py`

- [ ] **Step 1: Write the failing test**

```python
def test_workflow_commituje_wszystkie_logi():
    """Lekcja 2026-08-07: bez git add CI liczy snapshot i wyrzuca go do kosza."""
    from pathlib import Path
    wf = (Path(__file__).resolve().parents[1] / ".github/workflows/top-picks.yml").read_text(
        encoding="utf-8")
    for path in tp.HISTORY_PATHS.values():
        assert f"data/{path.name}" in wf, f"workflow nie commituje {path.name}"
```

- [ ] **Step 2: Run to verify failure**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks.py::test_workflow_commituje_wszystkie_logi -q`
Expected: FAIL (`workflow nie commituje top_picks_analyst_history.json`)

- [ ] **Step 3: Implement**

```yaml
          git add data/top_picks_history.json \
                  data/top_picks_earnings_history.json \
                  data/top_picks_quality_history.json \
                  data/top_picks_analyst_history.json \
                  data/top_picks_upside_history.json \
                  data/top_picks_sim.json
```

Sprawdź też `timeout-minutes` w workflow: dwie nowe strategie korzystają z cache `bulk_fetch_universe` po quality, więc czas runu nie powinien istotnie wzrosnąć. Zostaw bez zmian.

- [ ] **Step 4: Run test** — Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/top-picks.yml tests/test_top_picks.py
git commit -m "Top picks workflow: commit analyst and upside logs"
```

---

### Task 9: UI — karty i dwie nowe zakładki

**Files:**
- Modify: `components/cards.py` (`top_pick_cards`)
- Modify: `views/spolki/top_picks.py` (`EXTRA_COLUMNS`, `STRATEGY_INFO`, `render_sklad`, `render_strategia`, tabs)
- Create: `tests/test_top_picks_page.py`

- [ ] **Step 1: Write the failing AppTest**

```python
"""AppTest strony Top Picks: 5 zakladek, nowe strategie renderuja sie z logu."""
import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGE = "views/spolki/top_picks.py"


def _snapshot():
    pick = {"ticker": "AAPL", "group": "Tech", "score": -1.4, "entry_price": 100.0,
            "entry_date": "2026-11-14", "weight": 0.5, "name": "Apple",
            "recommendation_mean": 1.4, "num_analysts": 40, "target_mean": 130.0,
            "upside": 0.3}
    return {"2026-11-01": {"generated_at": "x", "asof": "2026-11-14",
                           "rule_version": 1, "sp500": [pick], "gpw": []}}


def test_top_picks_ma_piec_zakladek_i_renderuje_analitykow(tmp_path, monkeypatch):
    import data.top_picks as tp
    import data.downloader as dl
    import data.financials as fin

    paths = dict(tp.HISTORY_PATHS)
    for name in ("analyst", "upside"):
        p = tmp_path / f"{name}.json"
        p.write_text(json.dumps(_snapshot()), encoding="utf-8")
        paths[name] = p
    monkeypatch.setattr(tp, "HISTORY_PATHS", paths)
    idx = pd.bdate_range(end="2026-11-14", periods=260)
    monkeypatch.setattr(dl, "download_prices",
                        lambda tickers, period="1y": pd.DataFrame(
                            {t: range(100, 100 + len(idx)) for t in tickers}, index=idx))
    monkeypatch.setattr(dl, "download_stooq", lambda *a, **k: None)
    monkeypatch.setattr(fin, "bulk_fetch_universe", lambda tickers: {})

    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["_auth_retries"] = 3
    at.session_state["premium"] = True
    at.switch_page(PAGE).run()

    assert not at.exception, at.exception
    labels = [t.label for t in at.tabs]
    assert any("analitykow" in l for l in labels)
    assert any("docelowej" in l for l in labels)
    html = " ".join(str(e.proto.body) for e in at.get("html"))
    assert "Strong Buy" in html
    assert "40 analitykow" in html
```

Uwaga dla wykonawcy: jeżeli `app.py` przy starcie woła `LocalStorage()` i test wisi, skopiuj stub `_FakeLocalStorage` + monkeypatch z `tests/test_pulpit_offline.py` (fixture `_offline`). Jeżeli `views/spolki/top_picks.py` importuje `download_prices`/`bulk_fetch_universe` przez `from ... import`, monkeypatch na module `dl`/`fin` zadziała tylko, jeśli AppTest importuje stronę po patchu — tak jest (strona wykonuje się w `run()`).

- [ ] **Step 2: Run to verify failure**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks_page.py -q`
Expected: FAIL (brak zakładek analitycznych)

- [ ] **Step 3: Implement `top_pick_cards` — opcjonalne `score_text` i `note`**

W `components/cards.py`, w `top_pick_cards` zamień:

```python
        score = pick.get("score")
        score_str = f"{score:.3f}".replace(".", ",") if score is not None else "—"
```

na:

```python
        score = pick.get("score")
        score_str = pick.get("score_text") or (
            "score " + (f"{score:.3f}".replace(".", ",") if score is not None else "—"))
        note = pick.get("note") or ""
        note_html = (f'<div style="font-size:0.6rem;color:{MUTED};margin:-4px 0 8px;'
                     f'line-height:1.4">{note}</div>') if note else ""
```

W f-stringu karty zamień `f'<span style="font-size:0.6rem;color:{MUTED}">score {score_str}</span>'` na `f'<span style="font-size:0.6rem;color:{MUTED}">{score_str}</span>'`, a za blokiem sektora (`...letter-spacing:0.03em">{sector}</div>'`) dodaj linię `f'{note_html}'`. Zaktualizuj docstring: klucze opcjonalne `score_text`, `note`.

- [ ] **Step 4: Implement widok**

W `views/spolki/top_picks.py`:

Import (do istniejącego `from data.top_picks import (...)`): `consensus_label`.

`EXTRA_COLUMNS` — dodaj (klucze z prefiksem `pick:` czytane z pozycji, nie z `funda`):

```python
    "analyst": {"Konsensus": "pick:recommendation_mean", "Analitycy": "pick:num_analysts",
                "Cena docelowa": "pick:target_mean", "Potencjal %": "pick:upside"},
    "upside": {"Potencjal %": "pick:upside", "Konsensus": "pick:recommendation_mean",
               "Analitycy": "pick:num_analysts", "Cena docelowa": "pick:target_mean"},
```

W `render_sklad` zamień pętlę kolumn:

```python
            for column, key in EXTRA_COLUMNS[strategy].items():
                if key.startswith("pick:"):
                    row[column] = pick.get(key[5:])
                else:
                    row[column] = info.get(key)
```

i w słowniku `cards.append({...})` dopisz:

```python
                **_analyst_card_fields(pick, strategy, CURRENCY[market]),
```

z nowym helperem nad `render_sklad`:

```python
def _analyst_card_fields(pick: dict, strategy: str, currency: str) -> dict:
    """score_text + note dla kart strategii analitycznych (z danych z dnia wyboru)."""
    if strategy not in ("analyst", "upside"):
        return {}
    rm, n = pick.get("recommendation_mean"), pick.get("num_analysts") or 0
    target, up = pick.get("target_mean"), pick.get("upside")
    rm_str = f"{rm:.2f}".replace(".", ",") if rm is not None else "—"
    up_str = f"{up * 100:+.0f}%" if up is not None else "—"
    tgt_str = f"{fmt_number(target, 2)} {currency}" if target is not None else "—"
    score_text = (f"konsensus {rm_str}" if strategy == "analyst"
                  else f"potencjal {up_str}")
    note = (f"{consensus_label(rm)} &middot; {n} analitykow<br>"
            f"cel {tgt_str} ({up_str})")
    return {"score_text": score_text, "note": note}
```

Po pętli rynków w `render_sklad`, dla strategii analitycznych z krótszym składem — na początku pętli `for market in markets:` po `picks = latest.get(market) or []` dodaj:

```python
        if strategy in ("analyst", "upside") and 0 < len(picks) < 5:
            st.caption(
                f"{MARKET_LABELS[market]}: tylko {len(picks)} spolek spelnia warunki "
                "(min. liczba analitykow"
                + (", konsensus co najmniej Buy" if strategy == "upside" else "")
                + ") — piatka nie jest dobierana na sile."
            )
```

`STRATEGY_INFO` — dodaj:

```python
    "analyst": (
        "Polecane przez analitykow",
        "5 spolek z najlepsza srednia rekomendacja analitykow (skala Yahoo: "
        "1 = Strong Buy, 5 = Sell). Min. 5 analitykow dla S&P 500 i 3 dla GPW, "
        "przy remisie wygrywa spolka z wieksza liczba analitykow; maks. 2 na sektor.",
    ),
    "upside": (
        "Potencjal do ceny docelowej",
        "5 spolek z najwiekszym potencjalem do sredniej ceny docelowej analitykow — "
        "tylko sposrod tych, ktore analitycy polecaja kupic (konsensus co najmniej "
        "Buy). Progi analitykow jak w strategii Polecane; maks. 2 na sektor.",
    ),
```

W `render_strategia`, w łańcuchu `if strategy == "earnings": ... elif strategy == "quality": ...` dodaj:

```python
    elif strategy in ("analyst", "upside"):
        st.info(
            "**Zrodlo: konsensus analitykow z Yahoo Finance** (srednia rekomendacja, "
            "liczba analitykow, srednia cena docelowa) — stan z dnia wyboru. Na GPW "
            "konsensus ma ok. 1/3 spolek (pomiar 2026-11-16), stad nizszy prog i "
            "mozliwy krotszy sklad. Pierwszy sklad wybrany 16.11.2026, czyli w polowie "
            "miesiaca. To nie jest rekomendacja inwestycyjna."
        )
```

Tabs na dole pliku:

```python
st.caption(
    "Piec niezaleznych regul wybiera po piatce spolek pierwszego dnia miesiaca. "
    "Kazda patrzy na co innego: cenowe momentum, jakosc wynikow kwartalnych, "
    "jakosc biznesu albo konsensus analitykow. Sklad nie jest recznie korygowany."
)

tab_mom, tab_earn, tab_qual, tab_an, tab_up = st.tabs([
    "📈 Momentum", "📊 Earnings Momentum", "🏛️ Jakosc biznesu",
    "🎯 Polecane przez analitykow", "💹 Potencjal do ceny docelowej",
])
with tab_mom:
    render_strategia("momentum")
with tab_earn:
    render_strategia("earnings")
with tab_qual:
    render_strategia("quality")
with tab_an:
    render_strategia("analyst")
with tab_up:
    render_strategia("upside")
```

(Zastępuje dotychczasowy `st.caption("Trzy niezalezne reguly ...")` i trzy zakładki.)

- [ ] **Step 5: Run tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_top_picks_page.py tests/test_top_picks.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add components/cards.py views/spolki/top_picks.py tests/test_top_picks_page.py
git commit -m "Top picks page: analyst and upside tabs"
```

---

### Task 10: pierwsze snapshoty (start logu 16.11)

**Files:**
- Create: `data/top_picks_analyst_history.json`, `data/top_picks_upside_history.json` (generowane)

- [ ] **Step 1: Dry run obu strategii**

Run (lokalnie, z certyfikatem Nortona jeśli jest):
```bash
GEM_CA_BUNDLE="C:/ProgramData/Norton/Antivirus/wscert.pem" venv/Scripts/python.exe scripts/update_top_picks.py --only analyst --dry-run --skip-sim
GEM_CA_BUNDLE="C:/ProgramData/Norton/Antivirus/wscert.pem" venv/Scripts/python.exe scripts/update_top_picks.py --only upside --dry-run --skip-sim
```
Expected: dla każdej strategii lista SP500 (5 pozycji) i GPW (1–5 pozycji), w JSON pola `recommendation_mean`, `num_analysts`, `target_mean`, `upside`. Brak „ODRZUCONO”.

Sprawdź sensowność: SP500 analyst — konsensusy ≤ ~1,6; upside — wszystkie `recommendation_mean` ≤ 2,5, `upside` dodatnie i malejące; maks. 2 spółki z jednego sektora. Jeśli coś odstaje (np. upside > 150%), zatrzymaj się i zgłoś użytkownikowi przed zapisem.

- [ ] **Step 2: Zapis**

```bash
GEM_CA_BUNDLE="C:/ProgramData/Norton/Antivirus/wscert.pem" venv/Scripts/python.exe scripts/update_top_picks.py --only analyst --skip-sim
GEM_CA_BUNDLE="C:/ProgramData/Norton/Antivirus/wscert.pem" venv/Scripts/python.exe scripts/update_top_picks.py --only upside --skip-sim
```
Expected: `snapshot 2026-11-01 [analyst]: dopisany`, `snapshot 2026-11-01 [upside]: dopisany`. Pliki logów momentum/earnings/quality bez zmian (`git status` pokazuje tylko 2 nowe pliki).

- [ ] **Step 3: Commit**

```bash
git add data/top_picks_analyst_history.json data/top_picks_upside_history.json
git commit -m "Top picks: first analyst and upside snapshots (2026-11-16)"
```

---

### Task 11: weryfikacja końcowa

- [ ] **Step 1: Pełny pakiet offline**

Run: `venv/Scripts/python.exe -m pytest tests -q -m "not network"`
Expected: wszystkie PASS (≥ 376 + nowe), 0 failed.

- [ ] **Step 2: Wizualnie**

Uruchom lokalnie z Premium (tymczasowy `_shot_app.py` w repo: `st.session_state["premium"] = True` + `exec(app.py)`), zrób zrzut `scripts/screenshot.py http://localhost:8599/top_picks ...` obu nowych zakładek (domyślnie pokazuje się pierwsza zakładka — do zrzutu nowych zakładek możesz tymczasowo zamienić kolejność w `_shot_app`-ie albo obejrzeć ręcznie). Sprawdź: karty z „konsensus 1,40” / „potencjal +34%”, linia „Strong Buy · N analitykow · cel …”, tabela z kolumnami analityków, notka o źródle. Usuń `_shot_app.py` i zatrzymaj serwer.

- [ ] **Step 3: Raport dla użytkownika i zgoda na push**

Pokaż składy obu strategii (SP500 i GPW) i zapytaj o push na `main` (deploy Streamlit Cloud). Nie pushuj bez zgody.
