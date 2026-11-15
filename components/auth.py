"""Modul autoryzacji Premium — freemium model GEM ETF Dashboard."""

import hashlib
import streamlit as st

from components.constants import BG_CARD, GOLD, GOLD_SOFT, MUTED, SHADOW, TEXT

# Klucz localStorage
STORAGE_KEY = "gem_premium_hash"

# Link do zakupu na Naffy (do uzupelnienia po stworzeniu produktu)
NAFFY_URL = "https://naffy.io/damian-majewski/gem-etf-dashboard-premium"


def _get_valid_hashes() -> set:
    """Wczytaj zestaw prawidlowych hashy z secrets.toml."""
    try:
        return set(st.secrets.get("activation_codes", []))
    except Exception:
        return set()


def _hash_code(code: str) -> str:
    """Normalizuje i hashuje kod (upper, bez myslnikow/spacji) -> SHA-256 hex."""
    normalized = code.upper().replace("-", "").replace(" ", "")
    return hashlib.sha256(normalized.encode()).hexdigest()


def init_auth():
    """Inicjalizuje premium status z localStorage. Wywolaj raz w setup_sidebar()."""
    # Fast path — juz aktywowany w tej sesji
    if st.session_state.get("premium") is True:
        return

    # Limit prob odczytu localStorage (component moze nie zaladowac od razu)
    retries = st.session_state.get("_auth_retries", 0)
    if retries >= 3:
        st.session_state.setdefault("premium", False)
        return

    try:
        from streamlit_local_storage import LocalStorage
        ls = LocalStorage()
        stored_hash = ls.getItem(STORAGE_KEY)

        if stored_hash and stored_hash in _get_valid_hashes():
            st.session_state["premium"] = True
            st.session_state["_auth_retries"] = 3  # Koniec prob
            return
    except Exception:
        pass

    st.session_state["_auth_retries"] = retries + 1
    st.session_state.setdefault("premium", False)


def is_premium() -> bool:
    """Sprawdza czy uzytkownik ma aktywny dostep Premium."""
    return st.session_state.get("premium", False)


def activate_code(code: str) -> bool:
    """Waliduje kod i aktywuje Premium. Zwraca True jesli kod prawidlowy."""
    code_hash = _hash_code(code)
    if code_hash in _get_valid_hashes():
        st.session_state["premium"] = True
        st.session_state["_auth_retries"] = 3
        # Zapisz hash w localStorage (persistence miedzy sesjami)
        try:
            from streamlit_local_storage import LocalStorage
            ls = LocalStorage()
            ls.setItem(STORAGE_KEY, code_hash)
        except Exception:
            pass  # Dziala w sesji, nie przetrwa zamkniecia przegladarki
        return True
    return False


def deactivate():
    """Wyloguj Premium — czysc sesje i localStorage."""
    st.session_state["premium"] = False
    st.session_state["_auth_retries"] = 0
    try:
        from streamlit_local_storage import LocalStorage
        ls = LocalStorage()
        ls.setItem(STORAGE_KEY, "")
    except Exception:
        pass


def render_lock_screen(icon: str, title: str, desc: str) -> None:
    """Renderuje ekran blokady z CTA zakupu."""
    st.html(f"""
    <div style="max-width:520px;margin:60px auto;text-align:center;padding:44px 32px;
                background:{BG_CARD};border-radius:14px;box-shadow:{SHADOW};">
        <div style="font-size:18px;margin-bottom:10px;">🔒</div>
        <div style="font-size:24px;font-weight:650;color:{TEXT};margin-bottom:6px;">{title}</div>
        <div style="color:{MUTED};font-size:14px;margin-bottom:28px;line-height:1.6;">{desc}</div>
        <div style="background:{GOLD_SOFT};border-radius:12px;padding:18px;margin-bottom:24px;">
            <div style="color:{GOLD};font-weight:650;font-size:16px;margin-bottom:6px;">
                Odblokuj wszystkie strony Premium
            </div>
            <div style="color:{MUTED};font-size:13px;">
                Jednorazowy dostęp &middot; 49 zł &middot; Lifetime
            </div>
        </div>
        <a href="{NAFFY_URL}" target="_blank" rel="noopener" style="display:inline-block;
            background:{GOLD};color:#1A1405;font-weight:650;font-size:15px;padding:13px 36px;
            border-radius:10px;text-decoration:none;margin-bottom:20px;">Kup dostep Premium</a>
        <div style="color:{MUTED};font-size:12px;line-height:1.6;">
            Po zakupie otrzymasz kod aktywacyjny w pliku PDF.<br>
            Wpisz go w panelu bocznym (sidebar), aby odblokować dostęp.
        </div>
    </div>
    """)


def premium_teaser(title: str, desc: str) -> None:
    """Zaslepka karty/zakladki Premium (Pulpit, Sygnal GEM, pozniej Karta spolki)."""
    st.html(f"""
    <div style="background:{BG_CARD};border-radius:14px;box-shadow:{SHADOW};
                padding:18px 20px;text-align:center;">
        <div style="font-size:16px;margin-bottom:6px;">🔒</div>
        <div style="color:{TEXT};font-weight:650;font-size:15px;margin-bottom:4px;">{title}</div>
        <div style="color:{MUTED};font-size:13px;line-height:1.5;margin-bottom:4px;">{desc}</div>
    </div>
    """)
    st.link_button("Odblokuj Premium", NAFFY_URL, width="stretch")
