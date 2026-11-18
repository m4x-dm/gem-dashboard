"""Tlumaczenia: kazde tr("literal") w kodzie ma wpis w katalogu EN, placeholdery sie zgadzaja,
tytuly stron po przetlumaczeniu pozostaja jednoznaczne dla routera (bramka Premium)."""
import ast
import string
from pathlib import Path

import pytest

from components import i18n, nav
from components.locales.en import DOCS, EN

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ["components", "views", "data"]


def _source_files():
    for d in SCAN_DIRS:
        for p in (ROOT / d).rglob("*.py"):
            if "locales" not in p.parts:
                yield p
    yield ROOT / "app.py"


def _literal(node):
    """Tekst stalego argumentu (takze sklejanych 'a' 'b'); None dla wyrazen dynamicznych."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _calls(func_name):
    found = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == func_name and node.args):
                found.append((path.relative_to(ROOT), node.lineno, node.args))
    return found


def _fields(s: str) -> set:
    return {f for _, f, _, _ in string.Formatter().parse(s) if f}


def test_every_t_literal_has_english_translation():
    missing = []
    for path, line, args in _calls("tr"):
        text = _literal(args[0])
        if text is not None and text not in EN:
            missing.append(f"{path}:{line}: {text[:70]!r}")
    assert not missing, "Brak tlumaczen EN:\n" + "\n".join(missing)


def test_every_t_doc_has_english_document():
    missing = []
    for path, line, args in _calls("tr_doc"):
        doc_id = _literal(args[0])
        if doc_id is not None and doc_id not in DOCS:
            missing.append(f"{path}:{line}: {doc_id}")
    assert not missing, "Brak dokumentow EN:\n" + "\n".join(missing)


@pytest.mark.parametrize("pl,en", list(EN.items()))
def test_placeholders_match(pl, en):
    assert _fields(pl) == _fields(en), (pl, en)
    assert en.strip(), pl


def test_page_titles_and_descriptions_translated():
    for p in nav.PAGES:
        assert p.title in EN, p.title
        assert p.description in EN, p.description
    for section in nav.SECTION_ORDER:
        if section:
            assert section in EN, section


def test_translated_titles_resolve_to_same_page():
    # Router identyfikuje strone po tytule; tytul EN nie moze wskazac innej strony
    # (np. platna strona z tytulem identycznym jak darmowa = obejscie bramki).
    pl_titles = {p.title: p for p in nav.PAGES}
    en_titles = {}
    for p in nav.PAGES:
        en = EN[p.title]
        assert en not in en_titles, f"Zduplikowany tytul EN: {en}"
        en_titles[en] = p
        assert pl_titles.get(en, p) is p, f"Tytul EN {en!r} koliduje z innym tytulem PL"
        assert nav.by_title(en) is p


def test_t_falls_back_to_polish_and_formats(monkeypatch):
    monkeypatch.setattr(i18n, "get_lang", lambda: "en")
    assert i18n.tr("Tego tekstu nie ma w katalogu") == "Tego tekstu nie ma w katalogu"
    assert i18n.tr("Dodano {ticker}", ticker="AAPL") == EN["Dodano {ticker}"].format(ticker="AAPL")
    monkeypatch.setattr(i18n, "get_lang", lambda: "pl")
    assert i18n.tr("Dodano {ticker}", ticker="AAPL") == "Dodano AAPL"


def test_number_formatting_per_language(monkeypatch):
    from components import formatting
    monkeypatch.setattr(formatting, "is_pl", lambda: True)
    assert formatting.fmt_pct(0.123456) == "+12,35%"
    assert formatting.fmt_number(1234.5, 2) == "1 234,50"
    monkeypatch.setattr(formatting, "is_pl", lambda: False)
    assert formatting.fmt_pct(0.123456) == "+12.35%"
    assert formatting.fmt_number(1234.5, 2) == "1,234.50"
    assert formatting.fmt_number(10000) == "10,000"
