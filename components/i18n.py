"""Tlumaczenia interfejsu (PL = jezyk zrodlowy, EN = pierwszy dodatkowy).

Wzorzec jak gettext: w kodzie zostaje polski tekst opakowany w tr("..."),
a katalog locales/<jezyk>.py mapuje polski tekst na tlumaczenie.
Brak wpisu w katalogu = polski tekst (strona sie nie psuje, najwyzej jest po polsku).
tests/test_i18n.py pilnuje, zeby kazde tr("literal") mialo tlumaczenie.

Zasady:
- Wartosci uzywane w logice (opcje selectboxow, kolumny DataFrame, sygnaly TAK/NIE)
  zostaja po polsku — tlumaczymy tylko przy wyswietlaniu (format_func=tr, rename kolumn).
- Zmienne w tekscie: tr("Dodano {ticker}", ticker=x) — klucz katalogu bez podstawionych wartosci.
- Dlugie bloki markdown: tr_doc("id", polski_tekst) — tlumaczenie w DOCS pod tym id.

Jezyk: ?lang=en w adresie (link z portalu / reklamy) -> session_state["lang"].
Router (app.py) wola init_lang() przed st.navigation, bo tytuly stron sa tlumaczone.
"""
from __future__ import annotations

import streamlit as st

DEFAULT_LANG = "pl"
LANGS: dict[str, str] = {"pl": "Polski", "en": "English"}


def _catalog(lang: str) -> dict[str, str]:
    if lang == "en":
        from components.locales.en import EN
        return EN
    return {}


def _docs(lang: str) -> dict[str, str]:
    if lang == "en":
        from components.locales.en import DOCS
        return DOCS
    return {}


def init_lang() -> str:
    """Ustala jezyk z adresu (?lang=) lub sesji i synchronizuje adres.

    Adres jest zrodlem prawdy przy wejsciu z linku; potem jezyk trzyma sesja,
    a parametr dopisujemy z powrotem (przejscie w gornym menu czysci query params),
    zeby odswiezenie strony i skopiowany link zachowaly jezyk.
    """
    qp = st.query_params.get("lang")
    if qp in LANGS:
        st.session_state["lang"] = qp
    lang = st.session_state.get("lang", DEFAULT_LANG)
    if lang not in LANGS:
        lang = DEFAULT_LANG
    st.session_state["lang"] = lang
    _sync_url(lang)
    return lang


def _sync_url(lang: str) -> None:
    try:
        if lang == DEFAULT_LANG:
            if "lang" in st.query_params:
                del st.query_params["lang"]
        elif st.query_params.get("lang") != lang:
            st.query_params["lang"] = lang
    except Exception:
        pass


def set_lang(lang: str) -> None:
    if lang in LANGS:
        st.session_state["lang"] = lang
        _sync_url(lang)


def get_lang() -> str:
    lang = st.session_state.get("lang", DEFAULT_LANG)
    return lang if lang in LANGS else DEFAULT_LANG


def is_pl() -> bool:
    return get_lang() == "pl"


def tr(text: str, **kwargs) -> str:
    """Tlumaczy polski tekst na biezacy jezyk; kwargs podstawia przez str.format."""
    lang = get_lang()
    if lang != DEFAULT_LANG:
        text = _catalog(lang).get(text, text)
    return text.format(**kwargs) if kwargs else text


def tr_doc(doc_id: str, pl_text: str) -> str:
    """Dlugi blok tekstu (markdown) — tlumaczenie po identyfikatorze."""
    lang = get_lang()
    if lang == DEFAULT_LANG:
        return pl_text
    return _docs(lang).get(doc_id, pl_text)


def render_lang_switch() -> None:
    """Przelacznik jezyka (sidebar). Zmiana od razu przeladowuje strone."""
    codes = list(LANGS)
    current = get_lang()

    def _on_change():
        set_lang(st.session_state["_lang_switch"])

    # Ustawiane PRZED utworzeniem widgetu (po utworzeniu Streamlit rzuca wyjatek).
    # Klik w aktywny przycisk odznacza go (None) — wtedy set_lang nic nie robi,
    # a w nastepnym przebiegu wracamy do biezacego jezyka.
    st.session_state["_lang_switch"] = current
    st.segmented_control(
        "Language / Język", codes, key="_lang_switch",
        format_func=lambda c: LANGS[c], on_change=_on_change,
        label_visibility="collapsed",
    )
