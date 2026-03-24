"""Wspolna konfiguracja sidebar i CSS dla wszystkich stron."""

import streamlit as st
from components.auth import init_auth, is_premium, activate_code, deactivate, NAFFY_URL


def inject_css():
    """Globalny CSS — ukrycie menu, stylowanie sidebar i kart."""
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stDecoration"] {display: none;}
        /* Ukryj deploy button ale zachowaj sidebar toggle */
        [data-testid="stToolbar"] button[kind="header"] {display: none;}

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {
            background-color: #111827;
        }

        /* Ukryj scrollbar w sidebar zachowujac scroll */
        [data-testid="stSidebar"] > div:first-child {
            scrollbar-width: none;           /* Firefox */
            -ms-overflow-style: none;        /* IE/Edge */
        }
        [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar {
            display: none;                   /* Chrome/Safari */
        }

        /* Nav links */
        a[data-testid="stSidebarNavLink"] {
            border-radius: 8px;
            padding: 6px 12px;
            margin: 2px 0;
            transition: background-color 0.2s, border-left 0.2s;
            border-left: 3px solid transparent;
        }
        a[data-testid="stSidebarNavLink"]:hover {
            background-color: rgba(201,168,76,0.08);
            border-left: 3px solid #C9A84C;
        }
        a[data-testid="stSidebarNavLink"][aria-current="page"] {
            background-color: rgba(201,168,76,0.12);
            border-left: 3px solid #C9A84C;
            font-weight: 600;
        }

        /* Separator between ETF section (pages 0-6) and market sections (7-9)
           UWAGA: nth-child(8) = 8. link w sidebar (strona 7_sp500).
           Jesli dodasz/usuniesz strone, zaktualizuj te indeksy! */
        a[data-testid="stSidebarNavLink"]:nth-child(8) {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(201,168,76,0.15);
        }

        /* Separator between market sections (7-9) and tools (10-12) */
        a[data-testid="stSidebarNavLink"]:nth-child(11) {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(201,168,76,0.15);
        }

        /* Separator between tools (10-12) and analytics (13-19) */
        a[data-testid="stSidebarNavLink"]:nth-child(14) {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(201,168,76,0.15);
        }

        /* --- Metrics --- */
        .stMetric {
            background-color: #141929;
            padding: 12px;
            border-radius: 12px;
            border: 1px solid rgba(201,168,76,0.2);
            transition: border-color 0.2s;
        }
        .stMetric:hover {
            border-color: rgba(201,168,76,0.45);
        }

        /* --- Tabs --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background-color: rgba(20,25,41,0.5);
            border-radius: 10px;
            padding: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            transition: background-color 0.2s;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: rgba(201,168,76,0.08);
        }
        .stTabs [aria-selected="true"] {
            background-color: rgba(201,168,76,0.15) !important;
        }

        /* --- DataFrames --- */
        .stDataFrame {
            border-radius: 8px;
        }
        .stDataFrame [data-testid="stDataFrameResizable"] th {
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.05em;
            color: #C9A84C;
        }

        /* --- Plotly charts container --- */
        .stPlotlyChart {
            border-radius: 8px;
            overflow: hidden;
        }

        /* --- Responsive mobile --- */
        @media (max-width: 768px) {
            .stTabs [data-baseweb="tab-list"] {
                flex-wrap: wrap;
                gap: 2px;
            }
            .stTabs [data-baseweb="tab"] {
                padding: 6px 10px;
                font-size: 0.8rem;
            }
            .stMetric { padding: 8px; }
            .stDataFrame [data-testid="stDataFrameResizable"] th { font-size: 9px; }
        }

    </style>
    """, unsafe_allow_html=True)


def setup_sidebar():
    """Sidebar z ustawieniami — wywolaj na kazdej stronie."""
    inject_css()

    with st.sidebar:
        st.markdown("## 📈 GEM Dashboard")
        st.caption("Global Equity Momentum — analiza ETF-ow")
        st.divider()

        # === PREMIUM ===
        init_auth()
        if is_premium():
            st.markdown(
                '<div style="background:rgba(201,168,76,0.12);border:1px solid rgba(201,168,76,0.3);'
                'border-radius:8px;padding:8px 12px;text-align:center;margin-bottom:8px;">'
                '<span style="color:#C9A84C;font-weight:700;font-size:13px;">'
                '⭐ Premium aktywny</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("Wyloguj Premium", use_container_width=True):
                deactivate()
                st.rerun()
        else:
            with st.expander("🔑 Aktywuj Premium"):
                code_input = st.text_input(
                    "Kod aktywacyjny",
                    placeholder="GEM4-XXXX-XXXX-XXXX",
                    key="activation_code_input",
                )
                if st.button("Aktywuj", use_container_width=True):
                    if code_input:
                        if activate_code(code_input):
                            st.success("Premium aktywowany!")
                            st.rerun()
                        else:
                            st.error("Nieprawidlowy kod.")
                    else:
                        st.warning("Wpisz kod aktywacyjny.")
                st.markdown(
                    f'<a href="{NAFFY_URL}" target="_blank" style="color:#C9A84C;font-size:12px;">'
                    'Kup dostep Premium (49 zl)</a>',
                    unsafe_allow_html=True,
                )
        st.divider()

        # === ULUBIONE TICKERY ===
        st.markdown("### ⭐ Ulubione")
        if "favorites" not in st.session_state:
            st.session_state["favorites"] = set()

        fav_input = st.text_input("Ticker", max_chars=12, key="fav_input",
                                  placeholder="np. AAPL, BTC-USD")
        if st.button("Dodaj do ulubionych", key="fav_add_btn") and fav_input:
            t = fav_input.upper().strip()
            if len(st.session_state["favorites"]) >= 8:
                st.warning("Maks. 8 ulubionych.")
            else:
                st.session_state["favorites"].add(t)
                st.rerun()

        if st.session_state["favorites"]:
            st.caption("Ulubione: " + ", ".join(sorted(st.session_state["favorites"])))
            if st.button("Wyczysc ulubione", key="fav_clear"):
                st.session_state["favorites"] = set()
                st.rerun()

        st.divider()

        # === ALERTY CENOWE ===
        st.markdown("### 🔔 Alerty")
        if "alerts" not in st.session_state:
            st.session_state["alerts"] = []

        with st.expander("Dodaj alert"):
            alert_ticker = st.text_input("Ticker", max_chars=12,
                                         key="alert_ticker_input",
                                         placeholder="np. QQQ")
            alert_cond = st.selectbox("Warunek", ["spadek", "wzrost"],
                                      key="alert_cond")
            alert_thresh = st.number_input("Prog (%)", min_value=0.1,
                                           max_value=99.0, value=5.0,
                                           step=0.5, key="alert_thresh")
            alert_period = st.selectbox("Okres", ["1D", "1W", "1M"],
                                        key="alert_period")
            if st.button("Dodaj alert", key="alert_add_btn") and alert_ticker:
                if len(st.session_state["alerts"]) >= 5:
                    st.warning("Maks. 5 alertow.")
                else:
                    st.session_state["alerts"].append({
                        "ticker": alert_ticker.upper().strip(),
                        "condition": alert_cond,
                        "threshold": alert_thresh,
                        "period": alert_period,
                    })
                    st.rerun()

        if st.session_state["alerts"]:
            for i, a in enumerate(st.session_state["alerts"]):
                st.caption(f"{a['ticker']} {a['condition']} >{a['threshold']:.1f}% ({a['period']})")
            if st.button("Wyczysc alerty", key="alert_clear"):
                st.session_state["alerts"] = []
                st.rerun()

        st.divider()

        # Ustawienia
        st.markdown("### ⚙️ Ustawienia")

        manual_rf = st.checkbox("Reczna stopa wolna od ryzyka",
                                value="risk_free_manual" in st.session_state)
        if manual_rf:
            rf_value = st.number_input(
                "Stopa wolna (%)", min_value=0.0, max_value=15.0, value=4.5, step=0.1
            )
            st.session_state["risk_free_manual"] = rf_value
        else:
            st.session_state.pop("risk_free_manual", None)

        st.divider()

        # Dodaj wlasny ticker
        st.markdown("### ➕ Dodaj ticker")
        custom_ticker = st.text_input("Ticker (np. ARKK)", max_chars=10)
        if st.button("Dodaj") and custom_ticker:
            import re
            custom_ticker = custom_ticker.upper().strip()
            if not re.match(r'^[A-Z0-9.\-=^]+$', custom_ticker):
                st.error("Nieprawidlowy format tickera.")
            elif "custom_tickers" not in st.session_state:
                st.session_state["custom_tickers"] = [custom_ticker]
                st.success(f"Dodano {custom_ticker}")
                st.rerun()
            elif len(st.session_state["custom_tickers"]) >= 10:
                st.warning("Mozesz dodac maksymalnie 10 wlasnych tickerow.")
            elif custom_ticker not in st.session_state["custom_tickers"]:
                st.session_state["custom_tickers"].append(custom_ticker)
                st.success(f"Dodano {custom_ticker}")
                st.rerun()
            else:
                st.info(f"{custom_ticker} juz jest na liscie")

        if st.session_state.get("custom_tickers"):
            st.caption("Dodane: " + ", ".join(st.session_state["custom_tickers"]))
            if st.button("Wyczysc dodane"):
                st.session_state["custom_tickers"] = []
                st.rerun()

        st.divider()

        # Odswiezenie danych
        if st.button("🔄 Odswiez dane", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cache wyczyszczony — dane zostana pobrane od nowa.")
            st.rerun()

        st.divider()
        st.caption("Dane: Yahoo Finance (yfinance)")
        st.caption("Strategia: Gary Antonacci — GEM")



def render_footer():
    """Stopka na dole strony."""
    st.html(
        '<div style="text-align:center;color:#4B5563;font-size:11px;'
        'padding:32px 16px 16px;border-top:1px solid rgba(201,168,76,0.1);'
        'margin-top:48px;letter-spacing:0.02em;line-height:1.6;max-width:700px;margin-left:auto;margin-right:auto">'
        '<p style="margin:0 0 8px;color:#6B7280;font-style:italic">'
        'Dashboard ma charakter edukacyjny i informacyjny. Nie stanowi porady inwestycyjnej, '
        'finansowej ani prawnej. Wyniki historyczne i symulacje nie gwarantują przyszłych zwrotów. '
        'Przed podjęciem decyzji inwestycyjnych skonsultuj się z licencjonowanym doradcą finansowym.</p>'
        '<p style="margin:0">&copy; 2026 M4X &middot; Wszelkie prawa zastrzeżone</p>'
        '</div>'
    )


def get_risk_free() -> float:
    """Pobierz stope wolna (z session_state lub yfinance)."""
    if "risk_free_manual" in st.session_state:
        return st.session_state["risk_free_manual"]
    from data.downloader import get_risk_free_rate
    rf = get_risk_free_rate()
    if rf is None:
        st.warning("Nie udalo sie pobrac stopy wolnej. Uzywam domyslnej: 4,5%")
        return 4.5
    return rf
