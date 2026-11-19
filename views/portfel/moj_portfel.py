"""Moj portfel — import eksportu XTB (XLSX), pozycje, struktura, panel 'Co sie dzieje'.

Spec: docs/superpowers/specs/2026-11-19-moj-portfel-import-design.md
Dane portfela zyja w localStorage przegladarki (components/portfolio_storage.py);
w sesji trzymamy je w st.session_state["portfolio_accounts"], bo LocalStorage.getItem
czyta stan z chwili zamontowania komponentu (po setItem bylby nieaktualny).
"""
import streamlit as st

from components.i18n import tr
from components.portfolio_storage import clear_portfolio, load_portfolio, save_portfolio  # noqa: F401
from components.sidebar import render_footer
from data.portfolio.xtb_parser import XtbFormatError, parse_xtb_xlsx

ACCOUNT_LABELS = {"Wszystkie": "Wszystkie", "IKE": "IKE", "IKZE": "IKZE", "ZWYKLE": "Zwykłe"}


def _storage():
    from streamlit_local_storage import LocalStorage
    return LocalStorage()


def _accounts(ls) -> dict:
    """Konta z sesji, a gdy ich tam nie ma — z localStorage.

    Pusty odczyt NIE trafia do sesji: przy pierwszym zamontowaniu komponent localStorage
    zwraca {} i dopiero po chwili (rerun) oddaje dane przegladarki. Gdybysmy zapamietali
    pusty wynik, zapisany portfel nie pokazalby sie do konca sesji. Do sesji trafia
    tylko: udany odczyt, uszkodzony JSON (jako {}), wczytanie plikow i usuniecie portfela.
    """
    if "portfolio_accounts" in st.session_state:
        return st.session_state["portfolio_accounts"]
    accounts, corrupt = load_portfolio(ls)
    if corrupt:
        st.warning(tr("Zapisany portfel był uszkodzony — wczytaj eksport z XTB ponownie."))
        st.session_state["portfolio_accounts"] = accounts
    elif accounts:
        st.session_state["portfolio_accounts"] = accounts
    return accounts


def _handle_uploads(ls, accounts: dict) -> None:
    # Klucz z licznikiem: po "Usun portfel" uploader startuje pusty (inaczej pliki,
    # ktore w nim zostaly, wczytalyby sie od razu ponownie).
    nonce = st.session_state.get("pf_upload_nonce", 0)
    files = st.file_uploader(tr("Pliki .xlsx z XTB (możesz wybrać kilka: zwykłe, IKE, IKZE)"),
                             type=["xlsx", "zip"], accept_multiple_files=True, key=f"pf_upload_{nonce}")
    done = st.session_state.setdefault("pf_done_files", set())
    changed = False
    for f in files or []:
        if f.file_id in done:
            continue
        done.add(f.file_id)
        try:
            acc = parse_xtb_xlsx(f.getvalue(), f.name)
        except XtbFormatError as exc:
            st.error(f"{f.name}: {exc}")
            continue
        accounts[acc.account_id] = acc
        changed = True
        st.success(tr("Wczytano konto {typ} ({n} pozycji).",
                      typ=tr(ACCOUNT_LABELS[acc.account_type]), n=len(acc.lots)))
        if acc.skipped_cfd:
            st.info(tr("Pominięto {n} pozycji CFD — portfel pokazuje akcje i ETF-y.", n=acc.skipped_cfd))
    if changed:
        st.session_state["portfolio_accounts"] = accounts
        if save_portfolio(ls, accounts):
            st.warning(tr("Historia operacji była bardzo długa — zapisano ostatnie 5 lat."))


def _howto() -> None:
    st.markdown(tr("#### Jak pobrać eksport z XTB"))
    st.markdown(tr("1. W xStation otwórz **Historia konta** i wybierz zakres dat od początku konta.\n"
                   "2. Kliknij **Eksport** i wybierz format **XLSX**.\n"
                   "3. XTB pobiera archiwum ZIP — rozpakuj je i wczytaj pliki `.xlsx` (osobny plik dla "
                   "każdego konta: zwykłe, IKE, IKZE)."))


def _privacy() -> None:
    with st.expander(tr("Prywatność danych")):
        st.markdown(tr("Plik jest przetwarzany tylko w pamięci i nie jest zapisywany na serwerze. "
                       "Wczytane pozycje zostają w tej przeglądarce (localStorage) — na innym urządzeniu "
                       "trzeba wczytać plik ponownie. Przycisk „Usuń portfel” kasuje je całkowicie."))


st.markdown(tr("# Mój portfel"))
st.caption(tr("Wczytaj eksport z XTB — zobaczysz pozycje, zysk, strukturę i nadchodzące raporty spółek"))

ls = _storage()
accounts = _accounts(ls)

with st.expander(tr("Wczytaj eksport z XTB"), expanded=not accounts):
    _handle_uploads(ls, accounts)
    if not accounts:
        _howto()

if accounts:
    st.caption(tr("Portfel wczytany — szczegóły w kolejnym kroku."))
else:
    _privacy()

render_footer()
