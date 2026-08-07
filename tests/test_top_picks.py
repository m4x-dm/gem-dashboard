"""Testy silnika Top Picks (F18) — syntetyczne ramki, bez sieci."""
import json

import numpy as np
import pandas as pd
import pytest

from data import top_picks as tp


def _frame(n_days: int = 400, tickers=("AAA", "BBB", "CCC"), start="2024-01-01"):
    """Ramka cen rosnacych liniowo, kazdy ticker o inny wspolczynnik."""
    idx = pd.bdate_range(start, periods=n_days)
    data = {}
    for i, t in enumerate(tickers):
        data[t] = np.linspace(100.0, 100.0 + 10 * (i + 1), n_days)
    return pd.DataFrame(data, index=idx)


def _volumes(prices: pd.DataFrame, shares: float = 1_000_000.0):
    return pd.DataFrame(shares, index=prices.index, columns=prices.columns)


def test_eligible_odrzuca_ticker_z_krotka_historia():
    prices = _frame(400, ("AAA", "BBB"))
    prices.loc[prices.index[:250], "BBB"] = np.nan  # BBB ma tylko 150 sesji
    vols = _volumes(prices)
    out = tp._eligible(prices, vols, prices.index[-1], min_turnover=0.0)
    assert "AAA" in out
    assert "BBB" not in out


def test_eligible_odrzuca_ticker_ponizej_progu_plynnosci():
    prices = _frame(400, ("AAA", "BBB"))
    vols = _volumes(prices)
    vols["BBB"] = 10.0  # ~1000 obrotu dziennie
    out = tp._eligible(prices, vols, prices.index[-1], min_turnover=1_000_000.0)
    assert "AAA" in out
    assert "BBB" not in out


def test_select_picks_zwraca_dokladnie_top_n():
    tickers = tuple(f"T{i}" for i in range(10))
    prices = _frame(400, tickers)
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}  # kazdy inny sektor
    picks = tp.select_picks(prices, vols, groups, prices.index[-1], top_n=5)
    assert len(picks) == 5
    scores = [p["score"] for p in picks]
    assert scores == sorted(scores, reverse=True), "wynik nie jest posortowany malejaco"
    assert len({p["ticker"] for p in picks}) == 5, "duplikaty w skladzie"


def test_select_picks_egzekwuje_limit_sektorowy():
    # 5 najmocniejszych tickerow w jednym sektorze, 3 slabsze w innych
    tickers = ("A1", "A2", "A3", "A4", "A5", "B1", "C1", "D1")
    idx = pd.bdate_range("2024-01-01", periods=400)
    data = {}
    for i, t in enumerate(tickers[:5]):
        data[t] = np.linspace(100.0, 400.0 - i, 400)      # mocne
    for i, t in enumerate(tickers[5:]):
        data[t] = np.linspace(100.0, 120.0 - i, 400)      # slabe
    prices = pd.DataFrame(data, index=idx)
    vols = _volumes(prices)
    groups = {t: ("SEKTOR_A" if t.startswith("A") else t[0]) for t in tickers}

    picks = tp.select_picks(prices, vols, groups, idx[-1], top_n=5, max_per_group=2)

    assert len(picks) == 5
    a_count = sum(1 for p in picks if p["group"] == "SEKTOR_A")
    assert a_count == 2, f"limit sektorowy zlamany: {a_count} spolek z SEKTOR_A"


def test_select_picks_nie_widzi_przyszlosci():
    """asof=T musi dac ten sam wynik z ramka pelna i z ramka przycieta do T."""
    tickers = tuple(f"T{i}" for i in range(8))
    prices = _frame(500, tickers)
    # Po dacie T odwracamy trendy — gdyby regula podgladala przyszlosc,
    # wynik na pelnej ramce bylby inny.
    asof = prices.index[400]
    prices.loc[prices.index[401]:] = prices.loc[prices.index[401]:].iloc[::-1].values
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}

    full = tp.select_picks(prices, vols, groups, asof, top_n=5)
    trimmed = tp.select_picks(prices.loc[:asof], vols.loc[:asof], groups, asof, top_n=5)

    assert [p["ticker"] for p in full] == [p["ticker"] for p in trimmed]
    assert [p["entry_price"] for p in full] == [p["entry_price"] for p in trimmed]


def test_select_picks_wagi_sumuja_sie_do_jeden():
    tickers = tuple(f"T{i}" for i in range(6))
    prices = _frame(400, tickers)
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}
    picks = tp.select_picks(prices, vols, groups, prices.index[-1], top_n=5)
    assert sum(p["weight"] for p in picks) == pytest.approx(1.0, abs=1e-6)


def test_append_snapshot_tworzy_plik_gdy_nie_istnieje(tmp_path):
    path = tmp_path / "hist.json"
    payload = {"asof": "2026-07-31", "rule_version": 1, "sp500": [], "gpw": []}
    added = tp.append_snapshot("2026-08-01", payload, path=path)
    assert added is True
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "2026-08-01" in saved
    assert saved["2026-08-01"]["asof"] == "2026-07-31"


def test_append_snapshot_nie_nadpisuje_istniejacego_miesiaca(tmp_path):
    path = tmp_path / "hist.json"
    first = {"asof": "2026-07-31", "rule_version": 1, "sp500": [{"ticker": "MU"}], "gpw": []}
    second = {"asof": "2026-07-31", "rule_version": 1, "sp500": [{"ticker": "XXX"}], "gpw": []}
    tp.append_snapshot("2026-08-01", first, path=path)
    added = tp.append_snapshot("2026-08-01", second, path=path)
    assert added is False
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["2026-08-01"]["sp500"][0]["ticker"] == "MU", "log zostal nadpisany"


def test_portfolio_equity_liczy_zwrot_recznie_sprawdzalny():
    idx = pd.bdate_range("2026-01-01", periods=45)
    prices = pd.DataFrame({
        "AAA": np.linspace(100.0, 110.0, 45),   # +10%
        "BBB": np.linspace(50.0, 60.0, 45),     # +20%
    }, index=idx)
    history = {
        "2026-01-01": {
            "asof": idx[0].strftime("%Y-%m-%d"),
            "sp500": [
                {"ticker": "AAA", "weight": 0.5, "entry_price": 100.0},
                {"ticker": "BBB", "weight": 0.5, "entry_price": 50.0},
            ],
        }
    }
    equity = tp.portfolio_equity(history, prices, "sp500", start_capital=10000.0)
    # 50% * 1.10 + 50% * 1.20 = 1.15
    assert float(equity.iloc[-1]) == pytest.approx(11500.0, rel=1e-6)
    assert float(equity.iloc[0]) == pytest.approx(10000.0, rel=1e-9)


def test_portfolio_equity_lancuchuje_dwa_snapshoty():
    """Sciezka wielosegmentowa (>=2 snapshoty) uruchomi sie dopiero przy pierwszym
    rebalansie we wrzesniu 2026 — test pokrywa ja z wyprzedzeniem."""
    idx = pd.bdate_range("2026-01-01", periods=61)
    prices = pd.DataFrame({
        "AAA": np.linspace(100.0, 120.0, 61),   # +20% na calej dlugosci
        "BBB": np.linspace(200.0, 200.0, 61),   # plasko
    }, index=idx)
    mid = idx[30]
    history = {
        "2026-01-01": {
            "asof": idx[0].strftime("%Y-%m-%d"),
            "sp500": [{"ticker": "AAA", "weight": 1.0, "entry_price": 100.0}],
        },
        "2026-02-01": {
            "asof": mid.strftime("%Y-%m-%d"),
            "sp500": [{"ticker": "BBB", "weight": 1.0, "entry_price": 200.0}],
        },
    }
    equity = tp.portfolio_equity(history, prices, "sp500", start_capital=10000.0)

    # Segment 1: AAA od idx[0] do idx[30]; segment 2: BBB (plaskie) do konca.
    kapital_po_pierwszym = 10000.0 * (prices["AAA"].iloc[30] / prices["AAA"].iloc[0])
    assert float(equity.iloc[-1]) == pytest.approx(kapital_po_pierwszym, rel=1e-6)
    assert equity.index.is_monotonic_increasing
    assert not equity.index.has_duplicates, "data styku segmentow policzona dwa razy"


def test_portfolio_equity_z_pustym_logiem_zwraca_pusta_serie():
    prices = _frame(50, ("AAA",))
    equity = tp.portfolio_equity({}, prices, "sp500")
    assert isinstance(equity, pd.Series)
    assert equity.empty


def test_mapy_grup_pokrywaja_cale_universe():
    """Brakujacy wpis wrzuca spolki do wspolnego kubelka "?" i psuje limit
    koncentracji w obie strony — blokuje je razem, a jednoczesnie pozwala
    obejsc limit ich prawdziwego sektora. Regresja z 2026-08-06."""
    from data.gpw_universe import ALL_GPW_TICKERS, GPW_SECTOR_MAP
    from data.sp500_universe import SP500_SECTOR_MAP, SP500_TOP100

    brak_sp = [t for t in SP500_TOP100 if t not in SP500_SECTOR_MAP]
    assert brak_sp == [], f"SP500_TOP100 bez sektora: {brak_sp}"

    brak_gpw = [t for t in ALL_GPW_TICKERS if t not in GPW_SECTOR_MAP]
    assert brak_gpw == [], f"GPW bez sektora: {brak_gpw}"


def test_gpw_sektory_rozdzielaja_banki_od_reszty_finansow():
    """Banki musza byc osobna grupa — inaczej limit 2 na "Finanse" przepuszcza
    dwa banki plus XTB i GPW jako te same ryzyko."""
    from data.gpw_universe import GPW_BANKS, GPW_SECTOR_MAP

    for ticker in GPW_BANKS:
        assert GPW_SECTOR_MAP.get(ticker) == "Banki", f"{ticker} nie jest w grupie Banki"
    assert GPW_SECTOR_MAP.get("XTB.WA") == "Finanse"


def test_simulate_rule_zwraca_miesieczna_serie_i_reaguje_na_koszty():
    tickers = tuple(f"T{i}" for i in range(8))
    prices = _frame(700, tickers, start="2023-01-02")
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}

    bez_kosztow = tp.simulate_rule(prices, vols, groups, start=prices.index[300],
                                   min_turnover=0.0, transaction_cost=0.0, tax_belka=0.0)
    z_kosztami = tp.simulate_rule(prices, vols, groups, start=prices.index[300],
                                  min_turnover=0.0, transaction_cost=0.01, tax_belka=0.0)

    assert isinstance(bez_kosztow, pd.Series)
    assert len(bez_kosztow) >= 6, "za malo punktow miesiecznych"
    assert isinstance(bez_kosztow.index, pd.DatetimeIndex)
    assert float(z_kosztami.iloc[-1]) < float(bez_kosztow.iloc[-1]), \
        "koszty transakcyjne nie obnizyly wyniku"


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


def test_simulate_rule_odmawia_scorera_bez_wsparcia_asof():
    """Scorer fundamentalny w symulacji = lookahead bias. Ma padac glosno,
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
