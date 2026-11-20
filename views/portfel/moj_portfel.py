"""Moj portfel — import eksportu XTB (XLSX), pozycje, struktura, panel 'Co sie dzieje'.

Spec: docs/superpowers/specs/2026-11-19-moj-portfel-import-design.md
Dane portfela zyja w localStorage przegladarki (components/portfolio_storage.py);
w sesji trzymamy je w st.session_state["portfolio_accounts"], bo LocalStorage.getItem
czyta stan z chwili zamontowania komponentu (po setItem bylby nieaktualny).
"""
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import nav
from components.auth import is_premium, premium_teaser
from components.cards import kpi_card
from components.charts import _base_layout, benchmark_whatif_chart, portfolio_value_chart
from components.constants import BORDER, CHART_COLORS, GOLD, MUTED, TEXT
from components.formatting import GREEN, RED, fmt_number, fmt_pct
from components.i18n import is_pl, tr
from components.portfolio_storage import clear_portfolio, load_portfolio, save_portfolio
from components.sidebar import render_footer
from data import fundamentals_snapshot
from data.gpw_universe import GPW_NAMES
from data.portfolio import alerts, history, valuation
from data.portfolio.tickers import currency_for, fx_ticker, xtb_to_yahoo
from data.portfolio.xtb_parser import XtbFormatError, parse_xtb_xlsx
from data.sp500_universe import SP500_NAMES

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
                      typ=tr(ACCOUNT_LABELS[acc.account_type]), n=acc.lots["xtb_ticker"].nunique()))
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


@st.cache_data(ttl=900, show_spinner=False)
def _quotes(tickers: tuple[str, ...]) -> pd.DataFrame:
    return valuation.fetch_live_prices(tickers)


@st.cache_data(ttl=15 * 60, show_spinner=False)
def _alerts(tickers: tuple[str, ...], day: str) -> tuple[list, dict]:
    """Alerty fundamentalne (moduł 2) + status źródeł per spółka.

    Cache tylko 15 min: Yahoo bywa blokowany z IP Streamlit Cloud, a udane pobrania i tak
    siedzą w cache funkcji z financials.py (24 h, bez zapamiętywania porażek).
    `day` w kluczu, żeby okno 30 dni przesuwało się z datą.
    """
    from data import financials as fin
    status: dict = {}
    items = alerts.collect(tickers, pd.Timestamp(day), fin.fetch_earnings_dates,
                           fin.fetch_upgrades_downgrades, fin.fetch_insider_transactions,
                           fin.fetch_last_report_date, status=status)
    return items, status


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _history_prices(tickers: tuple[str, ...], start: str) -> pd.DataFrame:
    return history.fetch_history(tickers, start)


def _history(accounts: dict, account_type: str | None) -> None:
    """Wykresy w czasie: wartosc vs wplaty (free) i 'co gdyby' indeksy (Premium)."""
    accs = list(accounts.values())
    start = history.history_start(accs)
    if start is None:
        return
    st.markdown(tr("#### Wartość i wpłaty"))
    first = (pd.Timestamp(start) - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    with st.spinner(tr("Pobieram historię kursów…")):
        try:
            prices = _history_prices(tuple(sorted(history.history_tickers(accs))), first)
        except Exception:
            prices = pd.DataFrame()
    if prices.empty:
        st.info(tr("Nie udało się pobrać historii kursów — spróbuj ponownie za chwilę."))
        return
    df, checks = history.reconstruct(accs, prices, account_type)
    if df.empty:
        st.caption(tr("Brak operacji na wybranym koncie."))
        return
    if checks["volume_mismatch"] or checks["unparsed"]:
        st.warning(tr("Eksport nie obejmuje całej historii konta — w XTB wybierz zakres dat od początku "
                      "konta. Wykres może być niedokładny."))
    st.plotly_chart(portfolio_value_chart(df), width="stretch", key="pf_hist_value",
                    config={"displayModeBar": False})

    st.markdown(tr("#### Porównanie z indeksami"))
    if not is_premium():
        premium_teaser(tr("Twój portfel vs WIG20, mWIG40, S&P 500 i Nasdaq 100"),
                       tr("Ile byś miał, gdyby każda Twoja wpłata trafiła tego samego dnia do indeksu."))
        return
    bench = history.benchmark_prices_pln(prices)
    flows = df["flow"][df["flow"] != 0]
    comp = pd.DataFrame({"Twój portfel": df["value"]}, index=df.index)
    for name in bench.columns:
        comp[name] = history.whatif(flows, bench[name], df.index)
    comp["Wpłaty netto"] = df["deposits"]
    st.plotly_chart(benchmark_whatif_chart(comp), width="stretch", key="pf_hist_bench",
                    config={"displayModeBar": False})
    st.caption(tr("Co gdyby: każda wpłata (i wypłata) tego samego dnia kupuje fundusz indeksowy z "
                  "reinwestycją dywidend — WIG20: ETFBW20TR, mWIG40: ETFBM40TR, S&P 500: SPY, "
                  "Nasdaq 100: QQQ (w zł)."))
    mine = float(df["value"].iloc[-1])
    rows = []
    for name in bench.columns:
        v = comp[name].dropna()
        if v.empty:
            continue
        diff = mine - float(v.iloc[-1])
        color = GREEN if diff >= 0 else RED
        rows.append(f'<div style="display:flex;justify-content:space-between;gap:10px;padding:8px 0;'
                    f'border-bottom:1px solid {BORDER};font-variant-numeric:tabular-nums">'
                    f'<span style="color:{TEXT}">{escape(name)}</span><span style="color:{MUTED}">'
                    f'{_pln(float(v.iloc[-1]))} · <span style="color:{color}">'
                    f'{tr("Twój portfel")} {"+" if diff >= 0 else "−"}{_pln(abs(diff))}</span></span></div>')
    if rows:
        st.html("".join(rows))


def _pln(v: float) -> str:
    """Kwota w zlotych: '4 346 zł' (EN: '4,346 PLN')."""
    return f"{fmt_number(v)} {'zł' if is_pl() else 'PLN'}"


def _has_card(yahoo) -> bool:
    """Karta spolki istnieje tylko dla S&P 500 i GPW."""
    return isinstance(yahoo, str) and (yahoo in SP500_NAMES or yahoo in GPW_NAMES)


def _kpis(s: dict) -> None:
    c = st.columns(5)
    pcolor = GREEN if s["profit"] >= 0 else RED
    dcolor = GREEN if s["day"] >= 0 else RED
    kpi_card(c[0], "Wartość", _pln(s['value']))
    kpi_card(c[1], "Zysk / strata", _pln(s['profit']), fmt_pct(s["profit_pct"]), pcolor)
    kpi_card(c[2], "Dziś", _pln(s['day']), fmt_pct(s["day_pct"]), dcolor)
    kpi_card(c[3], "Wpłaty netto", _pln(s['deposits']))
    kpi_card(c[4], "Dywidendy", _pln(s['dividends']), "po podatku u źródła")


# Klikalne wiersze jak na Pulpicie: st.container(key="pfrow_*") z HTML-em wiersza
# i przezroczystym st.buttonem rozciagnietym na caly wiersz (nawigacja st.switch_page).
# CSS przez st.markdown — st.html wycina <style> (CLAUDE.md; ten sam wzorzec co pulpit.py).
_CLICK_CSS = f"""<style>
[class*="st-key-pfrow_"] {{ position:relative; gap:0; }}
[class*="st-key-pfrow_"] .stElementContainer:has(.stButton) {{ position:absolute; inset:0; z-index:2; }}
[class*="st-key-pfrow_"] .stButton, [class*="st-key-pfrow_"] .stButton button {{
  width:100%; height:100%; min-height:0; }}
[class*="st-key-pfrow_"] .stButton button {{ background:transparent; border:none; color:transparent;
  border-radius:8px; padding:0; box-shadow:none; }}
[class*="st-key-pfrow_"] .stButton button:hover {{ background:rgba(255,255,255,.04); }}
[class*="st-key-pfrow_"] .stButton button:focus-visible {{ outline:1px solid {GOLD}; }}
[class*="st-key-pfrow_"] .stButton button p {{ color:transparent; }}
</style>"""


def _qty(v: float) -> str:
    """Ilosc bez zbednych zer po przecinku: 3, 0,5, 1,2345."""
    s = fmt_number(v, 4)
    return s.rstrip("0").rstrip(",.") if s[-5:-4] in (",", ".") else s


def _row_html(r) -> str:
    pp = r["profit_pct"]
    pc = GREEN if (pp == pp and pp >= 0) else RED
    warn = "" if r["live"] else f' <span title="{tr("kurs z dnia raportu")}">⚠</span>'
    badge = (f'<span style="font-size:11px;padding:1px 6px;border-radius:4px;background:{BORDER};'
             f'color:{MUTED};margin-left:6px">{tr(ACCOUNT_LABELS[r["account"]])}</span>')
    avg = f' · {tr("śr.")} {fmt_number(r["avg_price"], 2)}' if r["avg_price"] == r["avg_price"] else ""
    return (
        f'<div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid {BORDER};">'
        f'<div style="flex:1;min-width:0;overflow-wrap:anywhere">'
        f'<span style="color:{GOLD};font-weight:650">{escape(str(r["xtb_ticker"]))}</span>{badge}'
        f'<div style="color:{MUTED};font-size:12px">{escape(str(r["name"]))} · {_qty(r["volume"])}'
        f' × {fmt_number(r["price"], 2)} {r["currency"]}{warn}{avg}</div></div>'
        f'<div style="text-align:right;font-variant-numeric:tabular-nums;flex-shrink:0">'
        f'<div style="color:{TEXT};font-weight:600">{_pln(r["value_pln"])}</div>'
        f'<div style="font-size:12px"><span style="color:{pc}">{fmt_pct(pp, 1)}</span>'
        f' <span style="color:{MUTED}">· {fmt_pct(r["share"], 0).lstrip("+")}</span></div></div></div>'
    )


def _positions(pos: pd.DataFrame) -> None:
    st.markdown(tr("#### Pozycje"))
    st.markdown(_CLICK_CSS, unsafe_allow_html=True)
    for i, r in pos.iterrows():
        with st.container(key=f"pfrow_{i}"):
            st.html(_row_html(r))
            if _has_card(r["yahoo"]) and st.button(tr("Otwórz kartę {ticker}", ticker=r["yahoo"]),
                                                   key=f"pfbtn_{i}_{r['yahoo']}",
                                                   help=tr("Karta spółki {ticker}", ticker=r["yahoo"])):
                nav.go_company(r["yahoo"])


def _allocation(pos: pd.DataFrame) -> None:
    st.markdown(tr("#### Struktura"))
    by = st.segmented_control(tr("Według"), ["Spółki", "Konta", "Waluty"], default="Spółki",
                              format_func=tr, key="pf_alloc_by") or "Spółki"
    col = {"Spółki": "xtb_ticker", "Konta": "account", "Waluty": "currency"}[by]
    g = pos.groupby(col)["value_pln"].sum().sort_values(ascending=False)
    labels = [tr(ACCOUNT_LABELS.get(k, k)) if col == "account" else str(k) for k in g.index]
    fig = go.Figure(go.Pie(labels=labels, values=g.values, hole=0.6, sort=False,
                           marker=dict(colors=[CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(g))]),
                           textinfo="percent"))
    fig.update_layout(**_base_layout(height=300))
    fig.update_layout(showlegend=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _when(days: int) -> str:
    if days == 0:
        return tr("dziś")
    if days == 1:
        return tr("jutro")
    if days == -1:
        return tr("wczoraj")
    return tr("za {n} dni", n=days) if days > 0 else tr("{n} dni temu", n=-days)


_ICONS = {"earnings": "📊", "upcoming": "📅", "targets": "🎯", "insider_buy": "🟢", "insider_sell": "🔴",
          "insider_sells": "🔴", "no_data": "ℹ", "fetch_failed": "⚠"}


def _usd(v: float) -> str:
    if v != v:
        return ""
    big = v >= 1e6
    num = fmt_number(v / 1e6, 1) if big else fmt_number(v / 1e3, 0)
    if is_pl():
        return f"{num} {'mln' if big else 'tys.'} USD"
    return f"${num}{'M' if big else 'k'}"


def _alert_text(a) -> str:
    p = dict(a.params)
    if a.kind == "earnings":
        p["s"] = fmt_pct(p["s"] / 100, 1)
    if a.kind == "upcoming":
        p["d"] = f"{a.date:%d.%m}"
        p["when"] = _when(p.pop("days"))
    if a.kind == "rating" and not p.get("frm"):
        p["frm"] = "—"
    txt = tr(a.text, **{k: v for k, v in p.items() if k != "usd"})
    if "usd" in p and _usd(p["usd"]):
        txt += f" · {_usd(p['usd'])}"
    return txt


def _alert_row(a) -> str:
    color = {"pos": GREEN, "neg": RED}.get(a.tone, MUTED)
    icon = _ICONS.get(a.kind) or ("⬆" if a.tone == "pos" else "⬇" if a.tone == "neg" else "✚")
    date = f'<span style="color:{MUTED};white-space:nowrap">{a.date:%d.%m}</span>'         if a.date is not None and a.kind != "upcoming" else ""
    ticker = "" if a.kind in ("no_data", "fetch_failed") else f'<b style="color:{GOLD}">{escape(a.ticker)}</b> '
    return (f'<div style="display:flex;gap:8px;align-items:baseline;padding:8px 0;'
            f'border-bottom:1px solid {BORDER};font-size:13px">'
            f'<span>{icon}</span><span style="flex:1;min-width:0;overflow-wrap:anywhere">{ticker}'
            f'<span style="color:{color if a.kind not in ("no_data", "fetch_failed") else MUTED}">{escape(_alert_text(a))}</span>'
            f'</span>{date}</div>')


_MARK = {"ok": "✅", "empty": "❌", "error": "❌", "skip": "—"}


def _sources(status: dict) -> None:
    """Diagnostyka: które źródło Yahoo odpowiedziało dla której spółki (blokady na Streamlit Cloud)."""
    if not status:
        return
    with st.expander(tr("Źródła danych")):
        head = (f'<tr style="color:{MUTED}"><th style="text-align:left;font-weight:500">{tr("Spółka")}</th>'
                + "".join(f'<th style="font-weight:500">{tr(h)}</th>' for h in ("Wyniki", "Analitycy", "Insiderzy"))
                + "</tr>")
        rows = "".join(
            f'<tr><td style="color:{GOLD}">{escape(t)}</td>'
            + "".join(f'<td style="text-align:center">{_MARK.get(s.get(k), "—")}</td>'
                      for k in ("earnings", "ratings", "insiders")) + "</tr>"
            for t, s in sorted(status.items()))
        st.html(f'<table style="width:100%;font-size:13px;border-collapse:collapse">{head}{rows}</table>')
        st.caption(tr("✅ dane pobrane · ❌ Yahoo nie zwrócił danych (bywa chwilowo blokowany — przy kolejnym "
                      "otwarciu strona spróbuje ponownie) · — źródło niedostępne dla GPW."))


def _panel(pos: pd.DataFrame) -> None:
    st.markdown(tr("#### Co się dzieje"))
    if not is_premium():
        premium_teaser(tr("Alerty dla Twojego portfela"),
                       tr("Wyniki lepsze/gorsze od oczekiwań, zmiany rekomendacji analityków, transakcje "
                          "insiderów i najbliższe raporty — a wkrótce przełamania poziomów technicznych i newsy."))
        return
    stocks = pos[(pos["category"] == "STOCK") & pos["yahoo"].notna()] if "category" in pos else pos
    tickers = tuple(sorted(set(stocks["yahoo"])))
    if not tickers:
        st.caption(tr("Brak spółek w portfelu — alerty dotyczą akcji, nie ETF-ów."))
        return
    with st.spinner(tr("Sprawdzam wyniki, analityków i insiderów…")):
        try:
            items, status = _alerts(tickers, f"{pd.Timestamp.now():%Y-%m-%d}")
        except Exception:
            items, status = [], {}
    if not items:
        st.caption(tr("Brak zdarzeń dla spółek z portfela w ostatnich 30 dniach."))
        return
    st.html("".join(_alert_row(a) for a in items))
    snap_at = fundamentals_snapshot.generated_at()
    if snap_at is not None:
        st.caption(tr("Dane fundamentalne z dziennego zrzutu z {d} UTC.", d=f"{snap_at:%d.%m %H:%M}"))
    _sources(status)
    st.caption(tr("Ostatnie 30 dni · wyniki: beat/miss przy niespodziance EPS ≥ 2% · insiderzy: zakupy i "
                  "sprzedaże ≥ 1 mln USD osobno · dane Yahoo Finance, dla GPW zwykle niedostępne."))


def _delete(ls) -> None:
    with st.popover(tr("Usuń portfel")):
        st.caption(tr("Usuwa wczytane konta z tej przeglądarki. Tej operacji nie można cofnąć."))
        if st.button(tr("Tak, usuń"), key="pf_delete_confirm", type="primary"):
            clear_portfolio(ls)
            st.session_state["portfolio_accounts"] = {}
            st.session_state["pf_done_files"] = set()
            st.session_state["pf_upload_nonce"] = st.session_state.get("pf_upload_nonce", 0) + 1
            st.rerun()


def _render_portfolio(ls, accounts: dict) -> None:
    present = sorted({a.account_type for a in accounts.values()}, key=["IKE", "IKZE", "ZWYKLE"].index)
    options = ["Wszystkie"] + present
    choice = st.segmented_control(tr("Konto"), options, default="Wszystkie", key="pf_account",
                                  format_func=lambda o: tr(ACCOUNT_LABELS.get(o, o))) or "Wszystkie"
    account_type = None if choice == "Wszystkie" else choice

    tickers = set()
    for a in accounts.values():
        for xt in a.lots["xtb_ticker"]:
            y = xtb_to_yahoo(xt)
            if y:
                tickers.add(y)
            fx = fx_ticker(currency_for(xt))
            if fx:
                tickers.add(fx)
    try:
        quotes = _quotes(tuple(sorted(tickers)))
    except Exception:
        quotes = pd.DataFrame(columns=["last", "prev"])
    pos, s = valuation.value_portfolio(list(accounts.values()), quotes, account_type)

    if s["report_time"] is not None:
        st.caption(tr("Stan pozycji z raportu XTB z {d}; kursy z Yahoo Finance (opóźnione do 15 min).",
                      d=f"{s['report_time']:%d.%m.%Y}"))
    _kpis(s)
    left, right = st.columns([2, 1])
    with left:
        if pos.empty:
            st.info(tr("Brak otwartych pozycji na wybranym koncie."))
        else:
            _positions(pos)
        _history(accounts, account_type)
        if not pos.empty:
            _allocation(pos)
    with right:
        with st.container(key="pf_panel"):
            _panel(pos)
    _delete(ls)


st.markdown(tr("# Mój portfel"))
st.caption(tr("Wczytaj eksport z XTB — zobaczysz pozycje, zysk, strukturę i nadchodzące raporty spółek"))

ls = _storage()
accounts = _accounts(ls)

with st.expander(tr("Wczytaj eksport z XTB"), expanded=not accounts):
    _handle_uploads(ls, accounts)
    if not accounts:
        _howto()

if accounts:
    _render_portfolio(ls, accounts)
_privacy()

render_footer()
