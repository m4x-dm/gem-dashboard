"""Wspolna konfiguracja sidebar i CSS dla wszystkich stron."""

import streamlit as st
from components.constants import BG2, BG_CARD, BG_HOVER, BORDER, TEXT, MUTED, SHADOW, GOLD, GOLD_SOFT
from components.auth import init_auth, is_premium, activate_code, deactivate, NAFFY_URL
from components.i18n import tr, render_lang_switch

PORTAL_URL = "https://inwestowanie.edu.pl/"


def inject_css():
    """Globalny CSS — ukrycie menu, stylowanie sidebar i kart."""
    css = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stDecoration"] {display: none;}
        /* Ukryj deploy button ale zachowaj sidebar toggle */
        [data-testid="stToolbar"] button[kind="header"] {display: none;}

        html, body, [class*="st-"] { font-variant-numeric: tabular-nums; }

        /* --- Sidebar --- */
        [data-testid="stSidebar"] { background-color: __BG2__; }
        [data-testid="stSidebar"] > div:first-child {
            scrollbar-width: none;
            -ms-overflow-style: none;
        }
        [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar { display: none; }

        /* Nav links (sidebar, mobile) */
        a[data-testid="stSidebarNavLink"] {
            border-radius: 8px;
            padding: 6px 12px;
            margin: 2px 0;
            color: __MUTED__;
            transition: background-color 0.2s;
        }
        a[data-testid="stSidebarNavLink"]:hover { background-color: __BG_HOVER__; }
        a[data-testid="stSidebarNavLink"][aria-current="page"] {
            background-color: __BG_HOVER__;
            color: #fff;
            font-weight: 600;
        }

        /* --- Gorne menu nawigacji --- */
        a[data-testid="stTopNavLink"] {
            color: __MUTED__;
            font-size: 13px;
            border-radius: 8px;
            padding: 7px 12px;
            transition: background-color 0.2s, color 0.2s;
        }
        a[data-testid="stTopNavLink"]:hover { background-color: __BG_HOVER__; color: __TEXT__; }
        a[data-testid="stTopNavLink"][aria-current="page"],
        a[data-testid="stTopNavLink"][aria-selected="true"] {
            background-color: __BG_HOVER__;
            color: #fff;
        }
        [data-testid="stTopNavDropdownLink"] { border-radius: 8px; }

        /* --- Metrics --- */
        .stMetric {
            background-color: __BG_CARD__;
            padding: 14px 16px;
            border-radius: 14px;
            border: none;
            box-shadow: __SHADOW__;
        }
        .stMetric [data-testid="stMetricLabel"] {
            color: __MUTED__;
            font-size: 12px;
            text-transform: none;
        }
        .stMetric [data-testid="stMetricValue"] { font-weight: 650; }

        /* --- Tabs (segmentowane pigulki) --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background: transparent;
            padding: 0;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 7px 12px;
            color: __MUTED__;
            transition: background-color 0.2s;
        }
        .stTabs [data-baseweb="tab"]:hover { background-color: __BG_HOVER__; }
        .stTabs [aria-selected="true"] {
            background-color: __BG_HOVER__ !important;
            color: __TEXT__ !important;
        }
        .stTabs [data-baseweb="tab-highlight"],
        .stTabs [data-baseweb="tab-border"] { display: none; }

        /* --- Naglowki --- */
        h1 {
            font-weight: 650;
            font-size: clamp(1.5rem, 3vw, 1.9rem);
            letter-spacing: -0.01em;
        }
        h3 { font-weight: 600; font-size: 1.1rem; }

        /* --- Expandery i kontenery z ramka --- */
        [data-testid="stExpander"] details,
        [data-testid="stExpander"],
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: __BORDER__;
            border-radius: 14px;
        }

        /* --- DataFrames --- */
        .stDataFrame { border-radius: 8px; }
        .stDataFrame [data-testid="stDataFrameResizable"] th {
            font-size: 11px;
            color: __MUTED__;
            text-transform: none;
        }

        /* --- Plotly charts container --- */
        .stPlotlyChart { border-radius: 8px; overflow: hidden; }

        /* --- Responsive mobile --- */
        @media (max-width: 768px) {
            .stTabs [data-baseweb="tab-list"] { flex-wrap: wrap; gap: 2px; }
            .stTabs [data-baseweb="tab"] { padding: 6px 10px; font-size: 0.8rem; }
            .stMetric { padding: 10px 12px; }
            .stDataFrame [data-testid="stDataFrameResizable"] th { font-size: 9px; }
        }
        /* --- Pulpit: kafelki rynku --- */
        .gem-tiles { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
        @media (max-width: 760px) { .gem-tiles { grid-template-columns:repeat(2,1fr); } }
    </style>
    """
    for key, val in {
        "__BG2__": BG2, "__BG_CARD__": BG_CARD, "__BG_HOVER__": BG_HOVER,
        "__BORDER__": BORDER, "__TEXT__": TEXT, "__MUTED__": MUTED, "__SHADOW__": SHADOW,
    }.items():
        css = css.replace(key, val)
    st.markdown(css, unsafe_allow_html=True)


def setup_sidebar():
    """Sidebar z ustawieniami — wywolaj na kazdej stronie."""
    inject_css()

    with st.sidebar:
        st.markdown("## GEM Dashboard")
        render_lang_switch()
        st.caption(tr("Global Equity Momentum — analiza ETF-ow"))
        st.markdown(
            f'<a href="{PORTAL_URL}?utm_source=gem-dashboard&utm_medium=app&utm_campaign=sidebar" '
            f'target="_blank" rel="noopener" style="color:{GOLD};font-size:13px;text-decoration:none;">'
            + tr('Poradniki o inwestowaniu: inwestowanie.edu.pl ↗') + '</a>',
            unsafe_allow_html=True,
        )
        st.divider()

        # === PREMIUM ===
        init_auth()
        if is_premium():
            st.markdown(
                f'<div style="background:{GOLD_SOFT};'
                'border-radius:10px;padding:8px 12px;text-align:center;margin-bottom:8px;">'
                f'<span style="color:{GOLD};font-weight:650;font-size:13px;">'
                + tr('Premium aktywny') + '</span></div>',
                unsafe_allow_html=True,
            )
            if st.button(tr("Wyloguj Premium"), width="stretch"):
                deactivate()
                st.rerun()
        else:
            with st.expander(tr("Aktywuj Premium"), icon=":material/key:"):
                code_input = st.text_input(
                    tr("Kod aktywacyjny"),
                    placeholder="GEM4-XXXX-XXXX-XXXX",
                    key="activation_code_input",
                )
                if st.button(tr("Aktywuj"), width="stretch"):
                    if code_input:
                        if activate_code(code_input):
                            st.success(tr("Premium aktywowany!"))
                            st.rerun()
                        else:
                            st.error(tr("Nieprawidlowy kod."))
                    else:
                        st.warning(tr("Wpisz kod aktywacyjny."))
                st.markdown(
                    f'<a href="{NAFFY_URL}" target="_blank" style="color:{GOLD};font-size:12px;">'
                    + tr('Kup dostep Premium (49 zl)') + '</a>',
                    unsafe_allow_html=True,
                )
        st.divider()

        # === ULUBIONE TICKERY ===
        st.markdown("### " + tr("Ulubione"))
        if "favorites" not in st.session_state:
            st.session_state["favorites"] = set()

        fav_input = st.text_input("Ticker", max_chars=12, key="fav_input",
                                  placeholder=tr("np. AAPL, BTC-USD"))
        if st.button(tr("Dodaj do ulubionych"), key="fav_add_btn") and fav_input:
            t = fav_input.upper().strip()
            if len(st.session_state["favorites"]) >= 8:
                st.warning(tr("Maks. 8 ulubionych."))
            else:
                st.session_state["favorites"].add(t)
                st.rerun()

        if st.session_state["favorites"]:
            st.caption(tr("Ulubione") + ": " + ", ".join(sorted(st.session_state["favorites"])))
            if st.button(tr("Wyczysc ulubione"), key="fav_clear"):
                st.session_state["favorites"] = set()
                st.rerun()

        st.divider()

        # === ALERTY CENOWE ===
        st.markdown("### " + tr("Alerty"))
        if "alerts" not in st.session_state:
            st.session_state["alerts"] = []

        with st.expander(tr("Dodaj alert")):
            alert_ticker = st.text_input("Ticker", max_chars=12,
                                         key="alert_ticker_input",
                                         placeholder=tr("np. QQQ"))
            alert_cond = st.selectbox(tr("Warunek"), ["spadek", "wzrost"],
                                      key="alert_cond", format_func=tr)
            alert_thresh = st.number_input(tr("Prog (%)"), min_value=0.1,
                                           max_value=99.0, value=5.0,
                                           step=0.5, key="alert_thresh")
            alert_period = st.selectbox(tr("Okres"), ["1D", "1W", "1M"],
                                        key="alert_period")
            if st.button(tr("Dodaj alert"), key="alert_add_btn") and alert_ticker:
                if len(st.session_state["alerts"]) >= 5:
                    st.warning(tr("Maks. 5 alertow."))
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
                st.caption(f"{a['ticker']} {tr(a['condition'])} >{a['threshold']:.1f}% ({a['period']})")
            if st.button(tr("Wyczysc alerty"), key="alert_clear"):
                st.session_state["alerts"] = []
                st.rerun()

        st.divider()

        # Ustawienia
        st.markdown("### " + tr("Ustawienia"))

        manual_rf = st.checkbox(tr("Reczna stopa wolna od ryzyka"),
                                value="risk_free_manual" in st.session_state)
        if manual_rf:
            rf_value = st.number_input(
                tr("Stopa wolna (%)"), min_value=0.0, max_value=15.0, value=4.5, step=0.1
            )
            st.session_state["risk_free_manual"] = rf_value
        else:
            st.session_state.pop("risk_free_manual", None)

        st.divider()

        # Dodaj wlasny ticker
        st.markdown("### " + tr("Dodaj ticker"))
        custom_ticker = st.text_input(tr("Ticker (np. ARKK)"), max_chars=10)
        if st.button(tr("Dodaj")) and custom_ticker:
            import re
            custom_ticker = custom_ticker.upper().strip()
            if not re.match(r'^[A-Z0-9.\-=^]+$', custom_ticker):
                st.error(tr("Nieprawidlowy format tickera."))
            elif "custom_tickers" not in st.session_state:
                st.session_state["custom_tickers"] = [custom_ticker]
                st.success(tr("Dodano {ticker}", ticker=custom_ticker))
                st.rerun()
            elif len(st.session_state["custom_tickers"]) >= 10:
                st.warning(tr("Mozesz dodac maksymalnie 10 wlasnych tickerow."))
            elif custom_ticker not in st.session_state["custom_tickers"]:
                st.session_state["custom_tickers"].append(custom_ticker)
                st.success(tr("Dodano {ticker}", ticker=custom_ticker))
                st.rerun()
            else:
                st.info(tr("{ticker} juz jest na liscie", ticker=custom_ticker))

        if st.session_state.get("custom_tickers"):
            st.caption(tr("Dodane") + ": " + ", ".join(st.session_state["custom_tickers"]))
            if st.button(tr("Wyczysc dodane")):
                st.session_state["custom_tickers"] = []
                st.rerun()

        st.divider()

        # Odswiezenie danych
        if st.button(tr("Odswiez dane"), icon=":material/refresh:", width="stretch"):
            st.cache_data.clear()
            st.toast(tr("Cache wyczyszczony — dane zostana pobrane od nowa."))
            st.rerun()

        st.divider()
        st.caption(tr("Dane: Yahoo Finance (yfinance)"))
        st.caption(tr("Strategia: Gary Antonacci — GEM"))



def render_footer():
    """Stopka na dole strony."""
    from components.version import version_label

    label = version_label()
    version_html = (
        '<p style="margin:6px 0 0;color:#374151;font-size:10px;letter-spacing:0.04em">%s</p>'
        % label
    ) if label else ""

    st.html(
        '<div style="text-align:center;color:#4B5563;font-size:11px;'
        f'padding:32px 16px 16px;border-top:1px solid {BORDER};'
        'margin-top:48px;letter-spacing:0.02em;line-height:1.6;max-width:700px;margin-left:auto;margin-right:auto">'
        '<p style="margin:0 0 8px;color:#6B7280;font-style:italic">'
        + tr('Dashboard ma charakter edukacyjny i informacyjny. Nie stanowi porady inwestycyjnej, '
            'finansowej ani prawnej. Wyniki historyczne i symulacje nie gwarantują przyszłych zwrotów. '
            'Przed podjęciem decyzji inwestycyjnych skonsultuj się z licencjonowanym doradcą finansowym.')
        + '</p>'
        '<p style="margin:0">&copy; 2026 M4X &middot; ' + tr('Wszelkie prawa zastrzeżone') + '</p>'
        + version_html +
        '</div>'
    )
    # Link poza st.html(): st.html renderuje w sandboxowanym iframe, z ktorego linki nie zawsze sie otwieraja
    st.markdown(
        f'<p style="text-align:center;font-size:12px;margin:0 0 16px;">'
        f'<a href="{PORTAL_URL}strategia-gem/?utm_source=gem-dashboard&utm_medium=app&utm_campaign=footer" '
        f'target="_blank" rel="noopener" style="color:{GOLD};text-decoration:none;">'
        + tr('Jak działa strategia GEM i jak inwestować w ETF-y: inwestowanie.edu.pl ↗') + '</a></p>',
        unsafe_allow_html=True,
    )


def get_risk_free() -> float:
    """Pobierz stope wolna (z session_state lub yfinance)."""
    if "risk_free_manual" in st.session_state:
        return st.session_state["risk_free_manual"]
    from data.downloader import get_risk_free_rate
    rf = get_risk_free_rate()
    if rf is None:
        st.warning(tr("Nie udalo sie pobrac stopy wolnej. Uzywam domyslnej: 4,5%"))
        return 4.5
    return rf
