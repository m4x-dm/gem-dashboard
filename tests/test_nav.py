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
    assert {p.key for p in nav.PAGES if p.free} == {"pulpit", "sygnal", "ranking-etf", "o-strategii", "karta"}


def test_page_count():
    assert len(nav.PAGES) == 25


def test_sections_known_and_non_empty():
    used = {p.section for p in nav.PAGES}
    assert used <= set(nav.SECTION_ORDER)
    for section in ("Strategia GEM", "ETF", "Spółki", "Portfel", "Rynek", "Krypto"):
        assert any(p.section == section for p in nav.PAGES), section


def test_get_and_by_path():
    p = nav.get("sp500")
    assert p.path == "views/spolki/sp500.py"
    assert nav.by_path("views/spolki/sp500.py") is p
    assert nav.by_title("S&P 500") is p
    with pytest.raises(KeyError):
        nav.get("nie-ma-takiej")


def test_descriptions_present():
    for p in nav.PAGES:
        assert p.description.strip(), p.key


MIGRATED = list(nav.PAGES)


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


def test_no_top_level_numbered_pages_left():
    assert not list((ROOT / "views").glob("*.py"))


def test_every_page_file_is_registered():
    on_disk = {p.relative_to(ROOT).as_posix() for p in (ROOT / "views").glob("*/*.py")}
    assert on_disk == {p.path for p in nav.PAGES}


def test_krypto_is_last_section():
    nav_sections = list(nav.build_navigation().keys())
    assert nav_sections[-1] == "Krypto"
    assert nav.PAGES[-1].key == "krypto"


def test_access_info_unknown_page_fails_closed():
    free, icon, title, desc = nav.access_info("Nieistniejaca strona")
    assert free is False
    assert icon == ":material/lock:" and title == "Nieistniejaca strona"
    assert "Premium" in desc


def test_access_info_matches_registry():
    for p in nav.PAGES:
        assert nav.access_info(p.title) == (p.free, p.icon, p.title, p.description)


def test_no_pages_directory():
    # Katalog "pages/" obok st.navigation wlacza stary tryb MPA Streamlita:
    # bezposrednie linki (np. /ranking) pokazuja wtedy "Page not found".
    assert not (ROOT / "pages").exists()


def test_navigation_built_before_sidebar():
    # Kolejnosc w routerze: st.navigation przed setup_sidebar (deep linki).
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert src.index("st.navigation(") < src.index("\nsetup_sidebar()")


def test_icons_are_material():
    for p in nav.PAGES:
        assert p.icon.startswith(":material/"), p.key


def test_page_titles_have_no_emoji():
    import re
    for f in (ROOT / "views").rglob("*.py"):
        m = re.search(r'st\.markdown\(f?"# ([^"]*)"', f.read_text(encoding="utf-8"))
        assert m, f
        assert not any(ord(ch) > 0x2FFF for ch in m.group(1)), f


def test_karta_first_in_spolki_and_free():
    spolki = [p for p in nav.PAGES if p.section == "Spółki"]
    assert spolki[0].key == "karta"
    assert nav.get("karta").free is True
    assert nav.get("karta").path == "views/spolki/karta.py"


def test_company_nav_helpers_exist():
    assert callable(nav.go_company) and callable(nav.company_link)


@pytest.mark.parametrize("needle", ["deep_dive_ticker", "pending_view", "_finanse_ticker", "_finanse_default"])
def test_no_legacy_deep_dive_state(needle):
    # Wszystkie drill-downy spolek ida na Karte spolki (nav.go_company) —
    # stary mechanizm session_state + switch_page na strone rynku jest usuniety.
    files = list((ROOT / "views").rglob("*.py")) + list((ROOT / "components").rglob("*.py"))
    hits = [p.relative_to(ROOT).as_posix() for p in files if needle in p.read_text(encoding="utf-8")]
    assert hits == []


@pytest.mark.parametrize("path", ["views/spolki/sp500.py", "views/spolki/gpw.py"])
def test_market_pages_have_no_per_company_finanse_tab(path):
    src = (ROOT / path).read_text(encoding="utf-8")
    assert '"💰 Finanse"' not in src
    assert "render_sprawozdania_deep_dive" not in src
    assert "nav.go_company(" in src
