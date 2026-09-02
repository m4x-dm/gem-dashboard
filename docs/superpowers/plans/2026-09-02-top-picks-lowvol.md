# Top Picks — czwarta strategia (Niska zmiennosc): plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dodac do `pages/9_top_picks.py` czwarta zakladke „Niska zmiennosc" — piatke defensywna wybierana wylacznie z szeregow cenowych, z symulacja wstecz i wlasnym append-only logiem.

**Architecture:** Nowy `Scorer` w `data/top_picks.py` (`supports_asof=True`, cztery komponenty ryzyka liczone z okna 252 sesji przez istniejace `_weighted_percentiles`). Poniewaz to druga strategia z symulacja, plik `top_picks_sim.json` — dzis kluczowany wylacznie po rynku — dostaje rejestr `SIM_PATHS` odwzorowujacy istniejace `HISTORY_PATHS`, po jednym pliku na strategie. Strona 9 i skrypt CI czytaja/pisza przez ten rejestr.

**Tech Stack:** Python 3.11 (`venv/Scripts/python.exe`), pandas, numpy, pytest, Streamlit, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-02-top-picks-lowvol-design.md`

---

## Uwagi wykonawcze (przeczytaj przed Task 1)

1. **Interpreter:** wszystkie komendy uzywaj `./venv/Scripts/python.exe`, NIE golego `python` (to Python 3.14 bez zaleznosci projektu).
2. **Katalog roboczy:** `C:/Users/m4x/Desktop/AI/gem-dashboard`.
3. **ASCII-only:** caly kod aplikacji jest bez polskich znakow diakrytycznych (`zmiennosc`, nie `zmienność`). Nie „poprawiaj" tego.
4. **`data/top_picks.py` nie moze importowac streamlita** na poziomie modulu — musi byc importowalny w GitHub Action i w testach. Nowy scorer czyta tylko ceny, wiec nie potrzebuje zadnych importow warunkowych (w przeciwienstwie do `earnings`/`quality`, ktore importuja `data.financials` wewnatrz funkcji).
5. **Commituj po kazdym tasku.** Nie pushuj — `main` auto-deployuje na Streamlit Cloud, decyzja o publikacji nalezy do uzytkownika.
6. Pracuj na branchu: `git checkout -b feat/top-picks-lowvol` przed Task 1.

---

## Struktura plikow

| Plik | Odpowiedzialnosc | Akcja |
|---|---|---|
| `data/top_picks.py` | silnik: scorer, rejestry strategii, sciezki artefaktow | modyfikacja |
| `tests/test_top_picks_lowvol.py` | testy komponentow scorera i rejestrow | **nowy** |
| `scripts/update_top_picks.py` | generator snapshotow i symulacji (CI) | modyfikacja |
| `pages/9_top_picks.py` | UI: czwarta zakladka, symulacja per strategia | modyfikacja |
| `.github/workflows/top_picks.yml` | `git add` nowych artefaktow | modyfikacja |
| `CLAUDE.md` | dokumentacja sekcji Top Picks (F18) | modyfikacja |

Testy nowej reguly ida do **osobnego pliku**, a nie do `tests/test_top_picks.py` (juz 300+ linii). Testy rejestrow tez tam, bo dotycza spojnosci wprowadzanej przez ten plan.

---

## Task 1: Rejestr SIM_PATHS

Rozwiazuje kolizje: `scripts/update_top_picks.py` zapisuje `sim[market]`, kluczujac wylacznie po rynku. Druga strategia z symulacja nadpisalaby wyniki momentum. Ten task wprowadza rejestr sciezek, jeszcze bez nowej strategii.

**Files:**
- Modify: `data/top_picks.py` (okolice linii 221-232, przy `HISTORY_PATHS`)
- Test: `tests/test_top_picks_lowvol.py` (nowy)

- [ ] **Step 1: Napisz failujacy test**

Utworz `tests/test_top_picks_lowvol.py`:

```python
"""Testy strategii 'Niska zmiennosc' (lowvol) i rejestrow strategii."""
import numpy as np
import pandas as pd

from data import top_picks as tp


class TestRejestryStrategii:
    """Kazda strategia musi byc opisana we wszystkich rejestrach naraz."""

    def test_sim_paths_istnieje_i_ma_momentum(self):
        assert "momentum" in tp.SIM_PATHS
        assert tp.SIM_PATHS["momentum"] == tp.SIM_PATH

    def test_sim_paths_daje_rozne_pliki_per_strategia(self):
        sciezki = list(tp.SIM_PATHS.values())
        assert len(sciezki) == len(set(sciezki))
```

- [ ] **Step 2: Uruchom test — ma failowac**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py -q`
Expected: FAIL — `AttributeError: module 'data.top_picks' has no attribute 'SIM_PATHS'`

- [ ] **Step 3: Dodaj rejestr**

W `data/top_picks.py`, bezposrednio pod blokiem `HISTORY_PATHS`, dopisz:

```python
# Symulacja per strategia. Wspolny plik nie wystarczy: skrypt zapisuje wynik
# jako sim[market], wiec druga strategia z supports_asof=True nadpisalaby
# krzywa momentum. Rejestr odwzorowuje HISTORY_PATHS.
SIM_PATHS = {
    "momentum": SIM_PATH,
}
```

- [ ] **Step 4: Uruchom test — ma przejsc**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks_lowvol.py
git commit -m "Dodaj rejestr SIM_PATHS — symulacja per strategia"
```

---

## Task 2: Komponent zmiennosci i drawdownu

Pierwsze dwa z czterech komponentow. Kazdy zwraca `pd.Series` indeksowana tickerem, gdzie **wyzej = lepiej** — dlatego miary „im mniej, tym lepiej" wchodza ze znakiem minus (wzorzec `debt_to_equity` z `make_quality_scorer`).

**Files:**
- Modify: `data/top_picks.py`
- Test: `tests/test_top_picks_lowvol.py`

- [ ] **Step 1: Napisz failujace testy**

Dopisz do `tests/test_top_picks_lowvol.py` (nad `class TestRejestryStrategii`):

```python
def _spokojny(n=300, start=100.0, drift=0.0003):
    """Szereg rosnacy gladko, bez szumu."""
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.Series(start * np.exp(np.arange(n) * drift), index=idx)


def _piloksztaltny(n=300, start=100.0, drift=0.0003, amp=0.05):
    """Ten sam trend, ale z duzym szumem dzien po dniu."""
    idx = pd.bdate_range("2024-01-01", periods=n)
    baza = start * np.exp(np.arange(n) * drift)
    szum = amp * np.where(np.arange(n) % 2 == 0, 1.0, -1.0)
    return pd.Series(baza * (1.0 + szum), index=idx)


class TestKomponenty:

    def test_vol_premiuje_szereg_spokojny(self):
        px = pd.DataFrame({"CALM": _spokojny(), "NOISY": _piloksztaltny()})
        out = tp._lowvol_components(["CALM", "NOISY"], px)
        assert out["vol"]["CALM"] > out["vol"]["NOISY"]

    def test_drawdown_premiuje_szereg_bez_dolka(self):
        plaski = _spokojny()
        z_dolkiem = _spokojny().copy()
        # 40-sesyjne zalamanie o 30% w srodku okna
        z_dolkiem.iloc[150:190] = z_dolkiem.iloc[150:190] * 0.7
        px = pd.DataFrame({"FLAT": plaski, "CRASH": z_dolkiem})
        out = tp._lowvol_components(["FLAT", "CRASH"], px)
        assert out["drawdown"]["FLAT"] > out["drawdown"]["CRASH"]

    def test_komponenty_licza_tylko_okno(self):
        """Dane starsze niz LOWVOL_WINDOW nie wplywaja na wynik."""
        dlugi = _spokojny(n=600)
        zaburzony = dlugi.copy()
        zaburzony.iloc[:200] = zaburzony.iloc[:200] * 0.4  # szok poza oknem
        px_a = pd.DataFrame({"AAA": dlugi})
        px_b = pd.DataFrame({"AAA": zaburzony})
        a = tp._lowvol_components(["AAA"], px_a)
        b = tp._lowvol_components(["AAA"], px_b)
        assert a["vol"]["AAA"] == b["vol"]["AAA"]
```

- [ ] **Step 2: Uruchom testy — maja failowac**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py::TestKomponenty -q`
Expected: FAIL — `AttributeError: module 'data.top_picks' has no attribute '_lowvol_components'`

- [ ] **Step 3: Zaimplementuj dwa komponenty**

W `data/top_picks.py`, pod `QUALITY_WEIGHTS`, dodaj stale:

```python
LOWVOL_WEIGHTS = {"vol": 0.35, "drawdown": 0.25,
                  "downside": 0.20, "stability": 0.20}
LOWVOL_WINDOW = 252   # 12M; _eligible wymaga MIN_HISTORY=273, wiec zawsze jest komplet
```

Nad `make_quality_scorer` dodaj funkcje (na razie z dwoma komponentami):

```python
def _lowvol_components(eligible: list[str],
                       px: pd.DataFrame) -> dict[str, pd.Series]:
    """Komponenty ryzyka z okna LOWVOL_WINDOW. Wyzej = lepiej w kazdym.

    Miary "im mniej, tym lepiej" (zmiennosc, downside) wchodza ze znakiem
    minus, zeby percentyl liczyl sie w dobra strone bez osobnej galezi —
    wzorzec z debt_to_equity w make_quality_scorer.
    """
    okno = px.tail(LOWVOL_WINDOW)
    vol, dd = {}, {}

    for ticker in eligible:
        if ticker not in okno.columns:
            vol[ticker] = dd[ticker] = None
            continue
        seria = okno[ticker].dropna()
        if len(seria) < 2:
            vol[ticker] = dd[ticker] = None
            continue

        zwroty = seria.pct_change().dropna()
        vol[ticker] = -float(zwroty.std(ddof=0)) if len(zwroty) else None

        szczyt = seria.cummax()
        dd[ticker] = float(((seria - szczyt) / szczyt).min())

    return {
        "vol": pd.Series(vol, dtype="float64"),
        "drawdown": pd.Series(dd, dtype="float64"),
    }
```

- [ ] **Step 4: Uruchom testy — maja przejsc**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks_lowvol.py
git commit -m "Dodaj komponenty vol i drawdown dla strategii lowvol"
```

---

## Task 3: Komponent downside deviation

Odroznia spolke, ktora spada gwaltownie, od takiej, ktora rosnie skokowo — obie moga miec identyczna zmiennosc calkowita.

**Files:**
- Modify: `data/top_picks.py`
- Test: `tests/test_top_picks_lowvol.py`

- [ ] **Step 1: Napisz failujacy test**

Dopisz do `class TestKomponenty`:

```python
    def test_downside_odroznia_asymetrie(self):
        """Dwa szeregi o podobnej zmiennosci calkowitej, rozny rozklad ogona."""
        idx = pd.bdate_range("2024-01-01", periods=300)
        rng = np.random.default_rng(42)

        # symetryczny: szum normalny
        sym = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 300))), index=idx)

        # asymetryczny: te same odchylenia, ale wieksze w dol
        kroki = rng.normal(0, 0.01, 300)
        kroki[kroki < 0] *= 2.0
        asym = pd.Series(100 * np.exp(np.cumsum(kroki)), index=idx)

        px = pd.DataFrame({"SYM": sym, "ASYM": asym})
        out = tp._lowvol_components(["SYM", "ASYM"], px)
        assert out["downside"]["SYM"] > out["downside"]["ASYM"]
```

- [ ] **Step 2: Uruchom test — ma failowac**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py::TestKomponenty::test_downside_odroznia_asymetrie -q`
Expected: FAIL — `KeyError: 'downside'`

- [ ] **Step 3: Dodaj komponent**

W `_lowvol_components`: dopisz `down = {}` obok `vol, dd = {}, {}` (linia staje sie `vol, dd, down = {}, {}, {}`), w petli po `zwroty` dodaj:

```python
        ujemne = zwroty[zwroty < 0]
        down[ticker] = -float(ujemne.std(ddof=0)) if len(ujemne) > 1 else None
```

oraz w bloku wczesnego `continue` ustaw `down[ticker] = None` (obie galezie). W zwracanym dict dodaj:

```python
        "downside": pd.Series(down, dtype="float64"),
```

- [ ] **Step 4: Uruchom testy — maja przejsc**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks_lowvol.py
git commit -m "Dodaj komponent downside deviation dla lowvol"
```

---

## Task 4: Komponent stabilnosci trendu (R2 ze znakiem nachylenia)

**To jest miejsce z pulapka.** Samo R² nagradza kazdy rowny trend, takze rowny zjazd — spolka osuwajaca sie gladko w dol mialaby swietna „stabilnosc". Dlatego `stability = R² * sign(nachylenia)`.

**Files:**
- Modify: `data/top_picks.py`
- Test: `tests/test_top_picks_lowvol.py`

- [ ] **Step 1: Napisz failujace testy**

Dopisz do `class TestKomponenty`:

```python
    def test_stability_premiuje_rowny_wzrost_nad_pila(self):
        px = pd.DataFrame({"CALM": _spokojny(), "NOISY": _piloksztaltny()})
        out = tp._lowvol_components(["CALM", "NOISY"], px)
        assert out["stability"]["CALM"] > out["stability"]["NOISY"]

    def test_stability_karze_rowny_spadek(self):
        """Pulapka R2: gladki zjazd ma wysokie R2, ale ma dostac UJEMNY wklad."""
        rosnacy = _spokojny(drift=0.0005)
        malejacy = _spokojny(drift=-0.0005)
        px = pd.DataFrame({"UP": rosnacy, "DOWN": malejacy})
        out = tp._lowvol_components(["UP", "DOWN"], px)
        assert out["stability"]["UP"] > 0
        assert out["stability"]["DOWN"] < 0
        assert out["stability"]["UP"] > out["stability"]["DOWN"]
```

- [ ] **Step 2: Uruchom testy — maja failowac**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py::TestKomponenty -q`
Expected: FAIL — `KeyError: 'stability'`

- [ ] **Step 3: Dodaj komponent**

W `_lowvol_components`: rozszerz inicjalizacje na `vol, dd, down, stab = {}, {}, {}, {}`, ustaw `stab[ticker] = None` w obu galeziach wczesnego `continue`, a w glownej petli dopisz:

```python
        # R2 regresji log-ceny wzgledem czasu, PODPISANE znakiem nachylenia.
        # Samo R2 nagradza takze rowny zjazd — gladko umierajaca spolka
        # miala by najwyzsza "stabilnosc", czyli odwrotnosc zamierzonego efektu.
        logi = np.log(seria.to_numpy(dtype="float64"))
        czas = np.arange(len(logi), dtype="float64")
        if len(logi) > 2 and np.isfinite(logi).all() and logi.std() > 0:
            nachylenie, wyraz = np.polyfit(czas, logi, 1)
            dopasowanie = nachylenie * czas + wyraz
            reszty = float(((logi - dopasowanie) ** 2).sum())
            calkowita = float(((logi - logi.mean()) ** 2).sum())
            r2 = 1.0 - reszty / calkowita if calkowita > 0 else 0.0
            stab[ticker] = float(np.sign(nachylenie) * r2)
        else:
            stab[ticker] = None
```

W zwracanym dict dodaj:

```python
        "stability": pd.Series(stab, dtype="float64"),
```

Upewnij sie, ze `import numpy as np` jest na gorze `data/top_picks.py` — jesli nie ma, dodaj go pod `import pandas as pd`.

- [ ] **Step 4: Uruchom testy — maja przejsc**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add data/top_picks.py tests/test_top_picks_lowvol.py
git commit -m "Dodaj komponent stabilnosci trendu (R2 ze znakiem nachylenia)"
```

---

## Task 5: Scorer lowvol i rejestracja strategii

**Files:**
- Modify: `data/top_picks.py`
- Test: `tests/test_top_picks_lowvol.py`

- [ ] **Step 1: Napisz failujace testy**

Dopisz do `tests/test_top_picks_lowvol.py`:

```python
class TestScorer:

    def test_scorer_wspiera_asof(self):
        """Regula czysto cenowa MUSI umiec liczyc historycznie — to jej sens."""
        assert tp.LOWVOL_SCORER.supports_asof is True
        assert tp.LOWVOL_SCORER.name == "lowvol"

    def test_scorer_premiuje_spokojna_spolke(self):
        px = pd.DataFrame({"CALM": _spokojny(), "NOISY": _piloksztaltny()})
        wynik = tp.LOWVOL_SCORER.fn(["CALM", "NOISY"], px, px.index[-1])
        assert wynik["CALM"] > wynik["NOISY"]

    def test_scorer_zwraca_tylko_eligible(self):
        px = pd.DataFrame({"AAA": _spokojny(), "BBB": _spokojny(),
                           "CCC": _piloksztaltny()})
        wynik = tp.LOWVOL_SCORER.fn(["AAA", "BBB"], px, px.index[-1])
        assert set(wynik.index) == {"AAA", "BBB"}

    def test_scorer_renormalizuje_przy_brakach(self):
        """Spolka z czescia komponentow dostaje srednia z dostepnych, nie NaN."""
        krotka = _spokojny(n=300).copy()
        krotka.iloc[:-3] = np.nan   # zostaja 3 sesje: brak downside, jest vol
        px = pd.DataFrame({"PELNA": _spokojny(), "KROTKA": krotka})
        wynik = tp.LOWVOL_SCORER.fn(["PELNA", "KROTKA"], px, px.index[-1])
        assert not pd.isna(wynik["PELNA"])

    def test_scorer_nie_widzi_przyszlosci(self):
        """Ranking na asof nie zmienia sie po dolozeniu danych po asof."""
        px = pd.DataFrame({"AAA": _spokojny(n=400), "BBB": _piloksztaltny(n=400)})
        asof = px.index[300]

        wczesniej = tp.LOWVOL_SCORER.fn(["AAA", "BBB"], px.loc[:asof], asof)

        pozniej = px.copy()
        pozniej.iloc[301:, :] = pozniej.iloc[301:, :] * 3.0   # szok po asof
        potem = tp.LOWVOL_SCORER.fn(["AAA", "BBB"], pozniej.loc[:asof], asof)

        pd.testing.assert_series_equal(wczesniej, potem)


class TestSpojnoscRejestrow:

    def test_lowvol_jest_we_wszystkich_rejestrach(self):
        for rejestr in (tp.RULE_VERSIONS, tp.STRATEGY_MARKETS,
                        tp.HISTORY_PATHS, tp.SIM_PATHS):
            assert "lowvol" in rejestr, f"brak lowvol w {rejestr}"

    def test_lowvol_dziala_na_obu_rynkach(self):
        assert tp.STRATEGY_MARKETS["lowvol"] == ("sp500", "gpw")

    def test_rejestry_podstawowe_maja_te_same_klucze(self):
        assert set(tp.RULE_VERSIONS) == set(tp.STRATEGY_MARKETS)
        assert set(tp.RULE_VERSIONS) == set(tp.HISTORY_PATHS)

    def test_wagi_sumuja_sie_do_jeden(self):
        assert abs(sum(tp.LOWVOL_WEIGHTS.values()) - 1.0) < 1e-9
```

- [ ] **Step 2: Uruchom testy — maja failowac**

Run: `./venv/Scripts/python.exe -m pytest tests/test_top_picks_lowvol.py -q`
Expected: FAIL — `AttributeError: module 'data.top_picks' has no attribute 'LOWVOL_SCORER'`

- [ ] **Step 3: Dodaj scorer i wpisy w rejestrach**

Pod `_lowvol_components` dodaj:

```python
def make_lowvol_scorer() -> Scorer:
    """Scorer 'Niska zmiennosc' — zmiennosc, drawdown, downside i stabilnosc trendu.

    supports_asof=True: komponenty licza sie wylacznie z szeregu cenowego, a
    select_picks() podaje px juz obciete do asof. W odroznieniu od scorerow
    fundamentalnych nie ma tu zadnego wejscia zwracajacego "stan na dzis",
    wiec symulacja wstecz jest uczciwa.

    Trzy pierwsze komponenty sa ze soba skorelowane (mierza warianty tego
    samego ryzyka) — to swiadome: celem jest piatka defensywna, nie
    zbalansowana. stability jest jedynym niezaleznym wymiarem.
    """
    def _fn(eligible: list[str], px: pd.DataFrame,
            asof: pd.Timestamp) -> pd.Series:
        components = _lowvol_components(eligible, px)
        return _weighted_percentiles(components, LOWVOL_WEIGHTS, eligible)

    return Scorer(name="lowvol", supports_asof=True, fn=_fn)


LOWVOL_SCORER = make_lowvol_scorer()
```

W `RULE_VERSIONS` dodaj `"lowvol": 1,`. W `STRATEGY_MARKETS` dodaj `"lowvol": ("sp500", "gpw"),`. W `HISTORY_PATHS` dodaj `"lowvol": _DATA_DIR / "top_picks_lowvol_history.json",`. W `SIM_PATHS` dodaj `"lowvol": _DATA_DIR / "top_picks_lowvol_sim.json",`.

- [ ] **Step 4: Uruchom pelny zestaw testow**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — wszystkie dotychczasowe (117) plus nowe

- [ ] **Step 5: Sprawdz, ze modul nie ciagnie streamlita**

Run: `./venv/Scripts/python.exe -c "import sys; import data.top_picks; print('streamlit' in sys.modules)"`
Expected: `False`

- [ ] **Step 6: Commit**

```bash
git add data/top_picks.py tests/test_top_picks_lowvol.py
git commit -m "Dodaj LOWVOL_SCORER i zarejestruj strategie lowvol"
```

---

## Task 6: Skrypt CI — symulacja per strategia

Skrypt musi (a) znac nowa strategie, (b) zapisywac symulacje do `SIM_PATHS[strategy]` zamiast wspolnego `SIM_PATH`.

**Files:**
- Modify: `scripts/update_top_picks.py`

- [ ] **Step 1: Zarejestruj strategie**

W `STRATEGIES` dodaj wpis (`critical: False` — awaria nowej reguly nie moze wywalic calego runu):

```python
    "lowvol": {"scorer": "lowvol", "simulate": True, "critical": False},
```

W `_scorer_for` dodaj przed `return None`:

```python
    if name == "lowvol":
        return tp.LOWVOL_SCORER
```

- [ ] **Step 2: Przenies akumulator symulacji do petli strategii**

Obecnie `sim = {...}` jest tworzony RAZ przed petla `for strategy in wanted:` i wypelniany jako `sim[market]`. Przenies jego tworzenie **do wnetrza** petli, na poczatek kazdej iteracji, i uzyj wersji reguly danej strategii:

```python
        sim = {
            "generated_at": generated_at,
            "rule_version": tp.RULE_VERSIONS[strategy],
            "params": {
                "top_n": args.top_n,
                "max_per_group": args.max_per_group,
                "transaction_cost": 0.001,
                "tax_belka": 0.19,
            },
        }
```

Usun stary blok `sim = {...}` sprzed petli.

- [ ] **Step 3: Zapisuj do sciezki per strategia**

Zapis siedzi dzis **poza** petla strategii (okolice linii 315-318) i jest zabramkowany na momentum:

```python
    if not args.dry_run and not args.skip_sim and "momentum" in wanted:
        tp.SIM_PATH.write_text(json.dumps(sim, indent=2, ensure_ascii=False),
                               encoding="utf-8")
        print(f"
symulacja zapisana: {tp.SIM_PATH.name}")
```

**Usun ten blok w calosci.** W jego miejsce dodaj zapis na koncu ciala petli `for strategy in wanted:` — czyli bezposrednio po wewnetrznej petli `for market in markets:` liczacej symulacje, z wcieciem 8 spacji:

```python
        if not args.dry_run:
            sciezka = tp.SIM_PATHS[strategy]
            sciezka.write_text(json.dumps(sim, indent=2, ensure_ascii=False),
                               encoding="utf-8")
            print(f"  symulacja zapisana: {sciezka.name}", flush=True)
```

`args.skip_sim` i `spec["simulate"]` sa juz obsluzone wczesniejszym `continue`, wiec nie powtarzaj ich w warunku.

- [ ] **Step 4: Zweryfikuj na sucho, ze momentum dziala jak dotad**

```bash
GEM_CA_BUNDLE=$(./venv/Scripts/python.exe -c "import certifi,os; print(os.path.join(os.path.dirname(certifi.where()),'_gem_bundle.pem'))") \
  ./venv/Scripts/python.exe scripts/update_top_picks.py --only momentum --dry-run --skip-sim
```
Expected: wypisuje piatke dla sp500 i gpw, konczy sie `--dry-run (momentum): nic nie zapisano`, plik `data/top_picks_sim.json` **niezmieniony** (`git diff --stat data/top_picks_sim.json` pusty)

- [ ] **Step 5: Wygeneruj pierwszy snapshot i symulacje lowvol**

```bash
GEM_CA_BUNDLE=$(./venv/Scripts/python.exe -c "import certifi,os; print(os.path.join(os.path.dirname(certifi.where()),'_gem_bundle.pem'))") \
  ./venv/Scripts/python.exe scripts/update_top_picks.py --only lowvol
```
Expected: powstaja `data/top_picks_lowvol_history.json` i `data/top_picks_lowvol_sim.json`; `data/top_picks_sim.json` bez zmian

- [ ] **Step 6: Potwierdz brak kolizji**

Run: `git status --short data/top_picks_sim.json`
Expected: pusto (plik momentum nietkniety)

- [ ] **Step 7: Commit**

```bash
git add scripts/update_top_picks.py data/top_picks_lowvol_history.json data/top_picks_lowvol_sim.json
git commit -m "CI: policz strategie lowvol, zapisuj symulacje per strategia"
```

---

## Task 7: Workflow — git add nowych artefaktow

**Krok krytyczny.** Przy poprzednim rozszerzeniu (2026-08-07) workflow liczyl nowe strategie co miesiac i ich nie commitowal, bo `git add` wymienial tylko stare pliki — logi nigdy by nie naroslyy.

**Files:**
- Modify: `.github/workflows/top_picks.yml` (okolice linii 36-39)

- [ ] **Step 1: Rozszerz git add**

Zamien liste plikow w kroku „Commit and push" na:

```yaml
          git add data/top_picks_history.json \
                  data/top_picks_earnings_history.json \
                  data/top_picks_quality_history.json \
                  data/top_picks_lowvol_history.json \
                  data/top_picks_sim.json \
                  data/top_picks_lowvol_sim.json
```

- [ ] **Step 2: Zweryfikuj, ze YAML sie parsuje**

Run: `./venv/Scripts/python.exe -c "import yaml,io; d=yaml.safe_load(io.open('.github/workflows/top_picks.yml',encoding='utf-8').read()); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 3: Sprawdz, ze wymienione sa wszystkie artefakty**

```bash
./venv/Scripts/python.exe - <<'EOF'
import io
from data import top_picks as tp
wf = io.open(".github/workflows/top_picks.yml", encoding="utf-8").read()
braki = [p.name for p in list(tp.HISTORY_PATHS.values()) + list(tp.SIM_PATHS.values())
         if p.name not in wf]
print("brakujace w git add:", braki or "brak — OK")
assert not braki
EOF
```
Expected: `brakujace w git add: brak — OK`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/top_picks.yml
git commit -m "CI: commituj artefakty strategii lowvol"
```

---

## Task 8: UI — symulacja czytana per strategia

Dzis `render_symulacja()` nie przyjmuje argumentow i czyta globalny `SIM_PATH`, a `render_strategia` wola ja tylko dla `momentum`. Trzeba ja sparametryzowac, zanim dojdzie czwarta zakladka.

**Files:**
- Modify: `pages/9_top_picks.py`

- [ ] **Step 1: Zmien import**

W bloku `from data.top_picks import (...)` zamien `SIM_PATH,` na `SIM_PATHS,`.

- [ ] **Step 2: Sparametryzuj funkcje**

Zmien sygnature `def render_symulacja() -> None:` na `def render_symulacja(strategy: str) -> None:` i na jej poczatku, przed uzyciem, dodaj:

```python
    sim_path = SIM_PATHS[strategy]
```

Nastepnie w ciele funkcji zamien wszystkie trzy wystapienia `SIM_PATH` na `sim_path` (warunek `.exists()`, komunikat `st.info` z `.name`, oraz `.read_text(...)`).

- [ ] **Step 3: Zmien warunek wywolania**

W `render_strategia` zamien:

```python
    if strategy == "momentum":
        render_symulacja()
```

na:

```python
    if strategy in SIM_PATHS:
        render_symulacja(strategy)
```

- [ ] **Step 4: Zweryfikuj, ze strona sie parsuje i renderuje**

```bash
./venv/Scripts/python.exe -c "import ast; ast.parse(open('pages/9_top_picks.py',encoding='utf-8').read()); print('parsuje sie OK')"
```
Expected: `parsuje sie OK`

```bash
GEM_CA_BUNDLE=$(./venv/Scripts/python.exe -c "import certifi,os; print(os.path.join(os.path.dirname(certifi.where()),'_gem_bundle.pem'))") \
./venv/Scripts/python.exe - <<'EOF'
import os, sys
sys.path.insert(0, os.getcwd())
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("pages/9_top_picks.py", default_timeout=300)
at.session_state["premium"] = True
at.run()
print("EXCEPTION:", at.exception[0].message if at.exception else "brak")
EOF
```
Expected: `EXCEPTION: brak`

- [ ] **Step 5: Commit**

```bash
git add pages/9_top_picks.py
git commit -m "UI: czytaj symulacje per strategia zamiast globalnego SIM_PATH"
```

---

## Task 9: UI — czwarta zakladka

**Files:**
- Modify: `pages/9_top_picks.py`

- [ ] **Step 1: Dodaj opis strategii**

W `STRATEGY_INFO` dodaj wpis:

```python
    "lowvol": (
        "Niska zmiennosc",
        "Ranking po ryzyku: zmiennosc 12M, najglebszy drawdown, odchylenie "
        "spadkow i stabilnosc trendu. Wybiera spolki spokojne, nie najszybsze.",
    ),
```

- [ ] **Step 2: Dodaj kolumny fundamentalne**

W `EXTRA_COLUMNS` dodaj wpis (fundamenty sluza tu wylacznie za kontekst, reguly nie dotykaja):

```python
    "lowvol": {"P/E": "pe", "ROE": "roe", "Marza %": "profit_margin",
               "Dyw. %": "dividend_yield"},
```

- [ ] **Step 3: Dodaj info box o zachowaniu w hossie**

W `render_strategia`, w lancuchu `elif strategy == "quality":`, dopisz kolejna galaz:

```python
    elif strategy == "lowvol":
        st.info(
            "**Ta regula z zalozenia zostaje w tyle w silnej hossie.** Szuka "
            "spolek o najnizszym ryzyku, nie o najwyzszym zwrocie — jej sens to "
            "plytszy drawdown, nie wyzszy CAGR. Trzy z czterech komponentow "
            "mierza warianty tego samego ryzyka; to swiadome, bo celem jest "
            "piatka defensywna, a nie zbalansowana."
        )
```

- [ ] **Step 4: Dodaj zakladke**

Zamien blok tworzenia zakladek na koncu pliku na:

```python
tab_mom, tab_earn, tab_qual, tab_lv = st.tabs([
    "📈 Momentum", "📊 Earnings Momentum", "🏛️ Jakosc biznesu", "🛡️ Niska zmiennosc",
])
with tab_mom:
    render_strategia("momentum")
with tab_earn:
    render_strategia("earnings")
with tab_qual:
    render_strategia("quality")
with tab_lv:
    render_strategia("lowvol")
```

- [ ] **Step 5: Zaktualizuj caption strony**

Zamien `st.caption("Trzy niezalezne reguly ...")` na:

```python
st.caption(
    "Cztery niezalezne reguly wybieraja po piatce spolek pierwszego dnia miesiaca. "
    "Kazda patrzy na co innego: cenowe momentum, jakosc wynikow kwartalnych, "
    "jakosc biznesu albo poziom ryzyka. Sklad nie jest recznie korygowany."
)
```

- [ ] **Step 6: Zweryfikuj render**

```bash
GEM_CA_BUNDLE=$(./venv/Scripts/python.exe -c "import certifi,os; print(os.path.join(os.path.dirname(certifi.where()),'_gem_bundle.pem'))") \
./venv/Scripts/python.exe - <<'EOF'
import os, sys
sys.path.insert(0, os.getcwd())
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("pages/9_top_picks.py", default_timeout=300)
at.session_state["premium"] = True
at.run()
print("EXCEPTION:", at.exception[0].message if at.exception else "brak")
print("zakladek:", len(at.tabs))
EOF
```
Expected: `EXCEPTION: brak`, `zakladek: 4`

- [ ] **Step 7: Commit**

```bash
git add pages/9_top_picks.py
git commit -m "UI: czwarta zakladka Top Picks — Niska zmiennosc"
```

---

## Task 10: Dokumentacja i domkniecie

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Zaktualizuj sekcje Top Picks (F18)**

W `CLAUDE.md`, w sekcji **Top Picks (F18)**, dopisz opis czwartej strategii:

```markdown
**Niska zmiennosc (lowvol)** — regula czysto cenowa, SP500 + GPW. Cztery
komponenty z okna 252 sesji: zmiennosc zrealizowana (0,35), najglebszy
drawdown (0,25), downside deviation (0,20), stabilnosc trendu jako R2
podpisane znakiem nachylenia (0,20). `supports_asof=True`, wiec **druga
strategia z symulacja wstecz** obok momentum.

Symulacje trzymane sa per strategia w `SIM_PATHS` — wspolny plik nie
wystarczyl, bo skrypt zapisuje wynik jako `sim[market]` i druga strategia
nadpisywalaby krzywa momentum.

Samo R2 nagradza takze rowny zjazd, dlatego stabilnosc jest mnozona przez
znak nachylenia — bez tego regula zbieralaby najspokojniej umierajace spolki.
```

- [ ] **Step 2: Uruchom pelny zestaw testow**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS, bez failow

- [ ] **Step 3: Sprawdz, ze wszystkie strony sie parsuja**

```bash
./venv/Scripts/python.exe - <<'EOF'
import ast, pathlib
for p in sorted(pathlib.Path("pages").glob("*.py")):
    ast.parse(p.read_text(encoding="utf-8"))
    print("OK", p.name)
EOF
```
Expected: kazda strona `OK`

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "Dokumentacja: czwarta strategia Top Picks (lowvol)"
```

- [ ] **Step 5: Podsumuj dla uzytkownika**

Zaraportuj: sklad pierwszej piatki lowvol dla obu rynkow, CAGR i Max DD z symulacji **wraz z przypomnieniem o survivorship bias**, oraz ile spolek przeszlo filtr. Zapytaj o merge do `main` — **nie mergeuj i nie pushuj samodzielnie**, bo `main` auto-deployuje na Streamlit Cloud.
