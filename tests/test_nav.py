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
