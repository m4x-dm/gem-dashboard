"""Testy helperow universe SP500 + GPW."""
from data.sp500_universe import get_sp500_universe, SP500_SECTORS
from data.gpw_universe import get_gpw_universe, GPW_CATEGORIES


def test_get_sp500_universe_returns_flat_list():
    universe = get_sp500_universe()
    assert isinstance(universe, list)
    assert all(isinstance(t, str) for t in universe)
    # SP500_SECTORS ma 456 spolek (komentarz w pliku mowi ~503 ale realnie 456)
    assert 440 < len(universe) < 470
    # Brak duplikatow
    assert len(universe) == len(set(universe))


def test_get_sp500_universe_contains_blue_chips():
    universe = get_sp500_universe()
    for ticker in ["AAPL", "MSFT", "NVDA", "GOOGL", "JPM"]:
        assert ticker in universe, f"{ticker} brakuje w SP500_UNIVERSE"


def test_get_gpw_universe_returns_flat_list():
    universe = get_gpw_universe()
    assert isinstance(universe, list)
    assert all(isinstance(t, str) for t in universe)
    # GPW_CATEGORIES ma 121 spolek (komentarz w pliku mowi 140 ale realnie 121)
    assert 110 < len(universe) < 130
    assert len(universe) == len(set(universe))


def test_get_gpw_universe_tickers_have_wa_suffix():
    universe = get_gpw_universe()
    # Wszystkie GPW tickery musza miec .WA suffix
    assert all(t.endswith(".WA") for t in universe), \
        "Wszystkie GPW tickery musza koncyc sie .WA"


def test_get_gpw_universe_contains_wig20():
    universe = get_gpw_universe()
    for ticker in ["PKO.WA", "PEO.WA", "KGH.WA", "CDR.WA", "ALE.WA"]:
        assert ticker in universe
