"""Modul autoryzacji Premium — freemium model GEM ETF Dashboard."""

import hashlib
import streamlit as st

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
    st.html(f'''
    <div style="
        max-width:520px;
        margin:60px auto;
        text-align:center;
        padding:48px 32px;
        background:#141929;
        border:2px solid rgba(201,168,76,0.3);
        border-radius:20px;
    ">
        <div style="font-size:56px;margin-bottom:12px;">🔒</div>
        <div style="font-size:24px;font-weight:700;color:#E5E7EB;margin-bottom:4px;">
            {icon} {title}
        </div>
        <div style="color:#9CA3AF;font-size:14px;margin-bottom:28px;line-height:1.6;">
            {desc}
        </div>

        <div style="
            background:rgba(201,168,76,0.08);
            border:1px solid rgba(201,168,76,0.2);
            border-radius:12px;
            padding:20px;
            margin-bottom:24px;
        ">
            <div style="color:#C9A84C;font-weight:700;font-size:16px;margin-bottom:6px;">
                Odblokuj wszystkie strony Premium
            </div>
            <div style="color:#9CA3AF;font-size:13px;">
                Jednorazowy dostep &middot; 49 zl &middot; Lifetime
            </div>
        </div>

        <a href="{NAFFY_URL}" target="_blank" rel="noopener" style="
            display:inline-block;
            background:linear-gradient(135deg,#C9A84C,#E8C96A);
            color:#0B0E1A;
            font-weight:700;
            font-size:15px;
            padding:14px 40px;
            border-radius:10px;
            text-decoration:none;
            margin-bottom:20px;
            letter-spacing:0.02em;
        ">Kup dostep Premium</a>

        <div style="color:#6B7280;font-size:12px;line-height:1.6;">
            Po zakupie otrzymasz kod aktywacyjny w pliku PDF.<br>
            Wpisz go w panelu bocznym (sidebar), aby odblokowac dostep.
        </div>
    </div>
    ''')


def premium_teaser(title: str, desc: str) -> None:
    """Zaslepka karty/zakladki Premium (Pulpit, Sygnal GEM, pozniej Karta spolki)."""
    st.html(f'''
    <div style="background:#141929;border:1px dashed rgba(201,168,76,0.35);
                border-radius:14px;padding:20px;text-align:center;">
        <div style="font-size:22px;margin-bottom:6px;">🔒</div>
        <div style="color:#E5E7EB;font-weight:700;font-size:15px;margin-bottom:4px;">{title}</div>
        <div style="color:#9CA3AF;font-size:13px;line-height:1.5;margin-bottom:12px;">{desc}</div>
    </div>
    ''')
    st.link_button("Odblokuj Premium", NAFFY_URL, width="stretch")
