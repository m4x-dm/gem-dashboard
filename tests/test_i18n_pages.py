"""Offline: darmowe strony po angielsku (?lang=en) — bez wyjatkow i bez polskich napisow.

Wykrywacz pominietych tekstow: szukamy polskich znakow diakrytycznych i typowych polskich
slow w calym wyrenderowanym drzewie (markdown, html, przyciski, zakladki, widgety, sidebar).
"""
import json
import re

import pytest
from streamlit.testing.v1 import AppTest

from tests.test_pulpit_offline import APP, _offline  # noqa: F401  (autouse fixture: dane syntetyczne)

PAGES = {
    "pulpit": "views/start/pulpit.py",
    "sygnal": "views/strategia/sygnal.py",
    "ranking": "views/etf/ranking.py",
    "o-strategii": "views/strategia/o_strategii.py",
}

# Polskie znaki + czeste polskie slowa pisane bez ogonkow (stare napisy w kodzie)
POLISH = re.compile(
    r"[ąęśłżźćńóĄĘŚŁŻŹĆŃÓ]|\b(?:brak|dane|danych|spolk\w*|zwrot|wynik\w*|sygnal\w*|"
    r"obligacje|akcje|rynki|wolna|stopa|dodaj|wyczysc|ulubione|kategoria|wszystkie|teraz)\b",
    re.I,
)
# Nazwy wlasne, ktore wolno zostawic (marka portalu w linku)
ALLOWED = ("inwestowanie.edu.pl",)
PROPER_NAME_COLS = {"Name", "Nazwa", "Company", "Holder", "Spółka", "Spolka"}
TICKER_OPTION = re.compile(r"^(?:\[[A-Z]+\] )?[A-Z0-9.^=-]+ — ")

TEXT_TYPES = ("markdown", "caption", "html", "button", "expander", "tab", "selectbox", "checkbox",
              "text_input", "number_input", "info", "warning", "error", "success", "subheader",
              "title", "header", "metric", "segmented_control", "radio", "download_button",
              "link_button", "page_link", "toast", "multiselect")


CHART_KEYS = {"text", "title", "name", "hovertemplate", "texttemplate", "labels", "x", "y", "ticktext"}


def _collect_chart_text(node, out, key=None):
    if isinstance(node, dict):
        for k, v in node.items():
            _collect_chart_text(v, out, k)
    elif isinstance(node, list):
        for v in node:
            _collect_chart_text(v, out, key)
    elif isinstance(node, str) and key in CHART_KEYS:
        out.append(node)


def _texts(at) -> list[str]:
    out = []
    for kind in TEXT_TYPES:
        try:
            elems = at.get(kind)
        except Exception:
            continue
        for e in elems:
            p = e.proto
            for field in ("body", "label", "placeholder", "help"):
                v = getattr(p, field, None)
                if isinstance(v, str) and v:
                    out.append(v)
            for opt in getattr(p, "options", []) or []:
                opt = opt if isinstance(opt, str) else getattr(opt, "label", "")
                if not TICKER_OPTION.match(opt):  # "JSW.WA — Jastrzebska Spolka..." = nazwa wlasna
                    out.append(opt)
    # Wykresy Plotly: spec to JSON (polskie znaki jako \uXXXX) -> parsujemy i zbieramy
    # napisy spod kluczy z trescia (tytuly, osie, etykiety, hover), bez kolorow/typow.
    for e in at.get("plotly_chart"):
        _collect_chart_text(json.loads(e.proto.spec), out)
    # Tabele: naglowki, nazwa indeksu i komorki tekstowe (bez kolumn z nazwami wlasnymi)
    for e in at.dataframe:
        try:
            df = e.value
        except Exception:
            continue
        out.extend(str(c) for c in df.columns)
        if df.index.name:
            out.append(str(df.index.name))
        for c in df.columns:
            if str(c) in PROPER_NAME_COLS or df[c].dtype != object:
                continue
            out.extend(v for v in df[c].dropna().unique()[:50] if isinstance(v, str))
    return out


def _polish_leftovers(at) -> list[str]:
    bad = []
    for txt in _texts(at):
        clean = txt
        for a in ALLOWED:
            clean = clean.replace(a, "")
        clean = re.sub(r"<[^>]+>", " ", clean)  # tagi HTML (style, atrybuty)
        if POLISH.search(clean):
            bad.append(re.sub(r"\s+", " ", clean).strip()[:120])
    return bad


def _run(page: str, premium: bool):
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["_auth_retries"] = 3
    at.session_state["lang"] = "en"
    if premium:
        at.session_state["premium"] = True
    at.switch_page(PAGES[page]).run()
    return at


@pytest.mark.parametrize("premium", [False, True], ids=["free", "premium"])
@pytest.mark.parametrize("page", list(PAGES))
def test_free_pages_render_in_english(page, premium):
    at = _run(page, premium)
    assert not at.exception, at.exception
    leftovers = _polish_leftovers(at)
    assert not leftovers, "Polskie teksty w wersji EN:\n" + "\n".join(sorted(set(leftovers)))


def test_english_pulpit_shows_english_ui():
    at = _run("pulpit", premium=False)
    md = " ".join(m.value for m in at.markdown)
    assert "Market indicators" in md
    assert "Top 5 ETFs by momentum" in md
    assert any("Global Equity Momentum — ETF analysis" in c.value for c in at.sidebar.caption)


def test_polish_is_default():
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["_auth_retries"] = 3
    at.switch_page(PAGES["pulpit"]).run()
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "Wskaźniki rynku" in md
