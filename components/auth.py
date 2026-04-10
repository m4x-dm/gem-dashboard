"""Modul autoryzacji Premium — freemium model GEM ETF Dashboard."""

import hashlib
import streamlit as st

# Strony dostepne za darmo (indeksy stron)
FREE_PAGES = {0, 1, 2, 6}

# Klucz localStorage
STORAGE_KEY = "gem_premium_hash"

# Opisy stron premium (do lock screena)
PAGE_INFO = {
    3: ("\U0001f4c8", "Wykresy", "Interaktywne wykresy cen, momentum i drawdown dla wybranych ETF-ow"),
    4: ("\u2696\ufe0f", "Porownanie", "Head-to-head 2\u20134 ETF-ow z macierza korelacji i statystykami"),
    5: ("\U0001f52c", "Backtest", "GEM vs Buy&Hold \u2014 krzywa kapitalu, Sharpe, MDD i wiecej"),
    7: ("\U0001f1fa\U0001f1f8", "S&P 500", "Ranking, wykresy i backtest ~456 spolek z indeksu S&P 500"),
    8: ("\U0001f1f5\U0001f1f1", "Polskie Akcje GPW", "120 spolek z WIG20, mWIG40 i sWIG80 \u2014 momentum i backtest"),
    9: ("\U0001fa99", "Kryptowaluty", "Top 200 kryptowalut \u2014 ranking, alt/BTC ratio, analiza techniczna"),
    10: ("\U0001f3d7\ufe0f", "Portfolio Builder", "Zbuduj portfel, ustaw wagi, backtest i analiza korelacji"),
    11: ("\U0001f50e", "Screener", "Cross-asset ranking momentum ze wszystkich klas aktywow"),
    12: ("\U0001f30d", "Makro Dashboard", "VIX, yield curve, DXY, S&P+200MA, zloto, ropa"),
    13: ("\U0001f4c5", "Sezonowosc", "Heatmapa miesiecznych zwrotow i wzorce sezonowe"),
    14: ("\U0001f4b1", "Waluta PLN/USD", "Wplyw kursu USD/PLN na zwroty ETF-ow w zlotowkach"),
    15: ("\U0001f4c9", "Drawdowny", "Analiza spadkow od szczytu \u2014 glebokosc, czas trwania, odbudowa"),
    16: ("\U0001f6a6", "Historia Sygnalow", "Pelna historia zmian sygnalu GEM w czasie"),
    17: ("\U0001f3b2", "Monte Carlo", "Symulacja przyszlych zwrotow \u2014 ile mozesz miec za N lat?"),
    18: ("\U0001f504", "Rotacja Sektorowa", "Ktory sektor GICS prowadzi? Heatmapa momentum sektorow"),
    19: ("\U0001f517", "Intermarket", "Relacje miedzy klasami aktywow: akcje, obligacje, zloto, dolar"),
    20: ("\U0001f500", "Side-by-Side", "Porownaj dwa aktywa obok siebie — cena, drawdown, RS"),
}

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


def require_premium(page_num: int) -> bool:
    """Gate premium — renderuje lock screen jesli brak dostepu.

    Uzycie na stronie premium:
        from components.auth import require_premium
        if not require_premium(7): st.stop()

    Zwraca True jesli dostep OK, False jesli zablokowany.
    """
    if page_num in FREE_PAGES or is_premium():
        return True

    _render_lock_screen(page_num)
    return False


def _render_lock_screen(page_num: int):
    """Renderuje ekran blokady z CTA zakupu."""
    info = PAGE_INFO.get(page_num, ("🔒", "Premium", "Ta strona wymaga dostepu Premium."))
    icon, title, desc = info

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
                Odblokuj wszystkie 16 stron
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
