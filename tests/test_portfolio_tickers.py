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
