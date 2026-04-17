"""Obliczenia momentum, sygnaly GEM, backtest."""

import pandas as pd
import numpy as np


def calc_realized_vol(prices: pd.Series, window: int = 20,
                      trading_days: int = 252) -> pd.Series:
    """Zrealizowana zmiennosc roczna z rolling okna dziennych zwrotow.

    Zwraca sigma * sqrt(252). Do uzycia jako input do vol targetingu —
    pozycja = target_vol / realized_vol.
    """
    daily = prices.pct_change()
    return daily.rolling(window).std(ddof=0) * np.sqrt(trading_days)


def vol_target_position(realized_vol: float, target_vol: float,
                         max_leverage: float = 1.0,
                         min_leverage: float = 0.0) -> float:
    """Oblicz wage pozycji dla celu zmiennosci.

    pos = clamp(target_vol / realized_vol, min_leverage, max_leverage).
    NaN / zero → zwraca max_leverage (neutralny fallback).
    """
    if pd.isna(realized_vol) or realized_vol <= 0:
        return max_leverage
    raw = target_vol / realized_vol
    return max(min_leverage, min(max_leverage, raw))


def calc_returns(prices: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Oblicza stopy zwrotu dla roznych okresow. Zwraca dict z kluczami '1M','3M','6M','12M'.

    12M uzywa momentum 12-1 (skip-month): zwrot od 13 mies. wstecz do 1 mies. wstecz,
    pomijajac ostatni miesiac (unikanie efektu short-term reversal).
    """
    periods = {"1M": 21, "3M": 63, "6M": 126}
    result = {}
    for label, days in periods.items():
        if len(prices) > days:
            result[label] = prices.pct_change(periods=days)
        else:
            result[label] = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)

    # 12M momentum: skip-month (12-1)
    # price(t-21) / price(t-273) - 1 = zwrot od 13 mies. wstecz do 1 mies. wstecz
    skip = 21       # 1 miesiac (pomijamy)
    total = 273     # 13 miesiecy wstecz (12M + 1M skip)
    if len(prices) > total:
        result["12M"] = prices.shift(skip) / prices.shift(total) - 1
    else:
        result["12M"] = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    return result


def latest_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Zwraca ostatnie stopy zwrotu dla kazdego tickera. Kolumny: 1M, 3M, 6M, 12M.

    Zoptymalizowana wersja — oblicza tylko ostatni wiersz zamiast pelnych DataFrames.
    Forward-fill eliminuje trailing NaN gdy zrodla danych konczą sie na roznych datach.
    """
    prices = prices.ffill()
    n = len(prices)
    result = {}
    # (min_rows, ideal_lookback) — min obnizone ~8% bo yfinance zwraca mniej niz kalendarz
    periods = {"1M": (19, 21), "3M": (58, 63), "6M": (115, 126)}

    for label, (min_rows, ideal) in periods.items():
        if n >= min_rows:
            lookback = min(ideal, n - 1)
            ret = prices.iloc[-1] / prices.iloc[-lookback] - 1
        else:
            ret = pd.Series(np.nan, index=prices.columns)
        result[label] = ret.replace([np.inf, -np.inf], np.nan)

    # 12M momentum: skip-month (12-1) when enough data, else simple 12M
    # iloc[-1] = today (t), iloc[-1-skip] = t-21, iloc[-1-total] = t-273
    skip = 21
    total = 273
    if n >= total + 1:
        ret_12m = prices.iloc[-1 - skip] / prices.iloc[-1 - total] - 1
    elif n >= 230:
        ret_12m = prices.iloc[-1] / prices.iloc[0] - 1
    else:
        ret_12m = pd.Series(np.nan, index=prices.columns)
    result["12M"] = ret_12m.replace([np.inf, -np.inf], np.nan)

    return pd.DataFrame(result)


def composite_score(ret_row: pd.Series) -> float:
    """Wynik kompozytowy: 12M*50% + 6M*25% + 3M*15% + 1M*10%.

    Legacy — suma wazonych surowych zwrotow. Wrazliwy na skew miedzy aktywami
    (np. krypto 1M -30% dominuje). Preferuj rank_based_score() dla rotacji.
    """
    weights = {"12M": 0.50, "6M": 0.25, "3M": 0.15, "1M": 0.10}
    score = 0.0
    for period, w in weights.items():
        val = ret_row.get(period, np.nan)
        if pd.notna(val):
            score += val * w
        else:
            return np.nan
    return score


def rank_based_score(rets: pd.DataFrame,
                     weights: dict | None = None,
                     anti_1m: bool = True) -> pd.Series:
    """Ranking percentylowy per okres + wazona suma rankow.

    Dla kazdej kolumny (1M/3M/6M/12M) oblicza rank percentylowy (0-1, wyzej=lepiej)
    wzgledem innych tickerow. 1M jest flipowany jesli anti_1m=True (short-term reversal
    effect — Jegadeesh 1990): w 1M nizszy zwrot → wyzszy score.

    Args:
        rets: DataFrame z kolumnami 1M/3M/6M/12M (index = ticker)
        weights: wagi dla okresow (default: 12M=0.40, 6M=0.30, 3M=0.20, 1M=0.10)
        anti_1m: czy odwracac rank 1M (default True)

    Returns:
        Series z jedna wartoscia score per ticker (0-1). NaN jesli brak wszystkich.
    """
    if weights is None:
        weights = {"12M": 0.40, "6M": 0.30, "3M": 0.20, "1M": 0.10}

    available = [p for p in weights if p in rets.columns]
    if not available:
        return pd.Series(np.nan, index=rets.index)

    # Rank percentylowy per kolumna (0-1, z NaN zachowanym)
    ranks = rets[available].rank(axis=0, pct=True, na_option="keep")
    if anti_1m and "1M" in ranks.columns:
        ranks["1M"] = 1.0 - ranks["1M"]

    # Renormalizacja wag po dostepnych okresach
    total_w = sum(weights[p] for p in available)
    norm_w = {p: weights[p] / total_w for p in available}

    score = pd.Series(0.0, index=rets.index)
    mask_any = pd.Series(False, index=rets.index)
    for period in available:
        col = ranks[period]
        mask_any = mask_any | col.notna()
        score = score + col.fillna(0.5) * norm_w[period]  # NaN → neutralny 0.5
    score[~mask_any] = np.nan
    return score


def build_ranking(prices: pd.DataFrame, risk_free_annual: float) -> pd.DataFrame:
    """Buduje ranking ETF-ow z wynikiem kompozytowym i sygnalem momentum absolutnego.

    Args:
        prices: DataFrame z cenami (kolumny = tickery)
        risk_free_annual: roczna stopa wolna od ryzyka w % (np. 4.5)

    Returns:
        DataFrame z kolumnami: 1M, 3M, 6M, 12M, Wynik, Momentum_abs
    """
    rets = latest_returns(prices)
    rf_decimal = risk_free_annual / 100.0

    rets["Wynik"] = rets.apply(composite_score, axis=1)
    rets["Momentum_abs"] = rets["12M"].apply(
        lambda x: "TAK" if pd.notna(x) and x > rf_decimal else "NIE"
    )
    rets = rets.sort_values("Wynik", ascending=False)
    return rets


def gem_classic_signal(prices: pd.DataFrame, risk_free_annual: float) -> dict:
    """Klasyczny sygnał GEM (QQQ vs VEA vs EEM vs ACWI vs AGG).

    Returns dict z kluczami:
        signal: 'QQQ' | 'VEA' | 'EEM' | 'ACWI' | 'AGG'
        signal_label: opis po polsku
        qqq_12m, vea_12m, eem_12m, acwi_12m, agg_12m: stopy zwrotu 12M
        risk_free: stopa wolna
    """
    rets = latest_returns(prices)
    rf_decimal = risk_free_annual / 100.0

    qqq_ret = rets.loc["QQQ", "12M"] if "QQQ" in rets.index else np.nan
    vea_ret = rets.loc["VEA", "12M"] if "VEA" in rets.index else np.nan
    eem_ret = rets.loc["EEM", "12M"] if "EEM" in rets.index else np.nan
    acwi_ret = rets.loc["ACWI", "12M"] if "ACWI" in rets.index else np.nan
    agg_ret = rets.loc["AGG", "12M"] if "AGG" in rets.index else np.nan

    if pd.isna(qqq_ret):
        signal = "BRAK_DANYCH"
        label = "Brak danych do obliczenia sygnalu"
    elif qqq_ret < rf_decimal:
        signal = "AGG"
        label = "OBLIGACJE (AGG) — momentum absolutny ujemny"
    else:
        # Momentum relatywny: porownaj QQQ vs VEA vs EEM vs ACWI
        candidates = {"QQQ": qqq_ret}
        if pd.notna(vea_ret):
            candidates["VEA"] = vea_ret
        if pd.notna(eem_ret):
            candidates["EEM"] = eem_ret
        if pd.notna(acwi_ret):
            candidates["ACWI"] = acwi_ret
        best = max(candidates, key=candidates.get)
        if best == "QQQ":
            signal = "QQQ"
            label = "AKCJE USA (QQQ) — momentum relatywny na korzysc USA"
        elif best == "VEA":
            signal = "VEA"
            label = "AKCJE MIEDZYNARODOWE (VEA) — momentum relatywny na korzysc rynkow rozwi."
        elif best == "EEM":
            signal = "EEM"
            label = "RYNKI WSCHODZACE (EEM) — momentum relatywny na korzysc EM"
        else:
            signal = "ACWI"
            label = "AKCJE GLOBALNE (ACWI) — momentum relatywny na korzysc rynku globalnego"

    return {
        "signal": signal,
        "signal_label": label,
        "qqq_12m": qqq_ret,
        "vea_12m": vea_ret,
        "eem_12m": eem_ret,
        "acwi_12m": acwi_ret,
        "agg_12m": agg_ret,
        "risk_free": risk_free_annual,
    }


def backtest_gem(prices: pd.DataFrame, risk_free_annual: float,
                 start_capital: float = 10000, lookback: int = 273,
                 trend_filter: bool = False,
                 sma_window: int = 200,
                 vol_target: float | None = None,
                 max_leverage: float = 1.0,
                 vol_window: int = 20) -> dict:
    """Backtest klasycznego GEM vs Buy&Hold QQQ vs ACWI vs AGG.

    Args:
        prices: DataFrame z cenami (wymagane: QQQ, VEA, EEM, ACWI, AGG)
        risk_free_annual: roczna stopa wolna w % (np. 4.5)
        start_capital: kapital poczatkowy
        lookback: okno momentum w dniach (default 273 = 12M + 1M skip)
        trend_filter: jesli True, dodatkowo wymaga cena > SMA(sma_window) dla
            wybranego aktywa akcyjnego; inaczej → AGG. Redukuje whipsawy w
            rynku bocznym przez AND z filtrem trendu (Faber-style).
        sma_window: okno SMA dla filtra trendu (default 200 dni)
        vol_target: jesli ustawione (np. 0.15 = 15% rocznie), skaluj pozycje
            tak, aby oczekiwana zmiennosc = target. pos = target/realized, clamped
            do [0, max_leverage]. None = wylaczone (defaultowy full-position).
            Scalowanie tylko gdy sygnal = akcje; AGG zawsze full.
        max_leverage: maks. dzwignia przy vol_target (1.0 = bez dzwigni, 2.0 = 2x)
        vol_window: okno realizowanej zmiennosci (dni, default 20)

    Returns dict z:
        equity_gem, equity_qqq, equity_acwi, equity_agg: pd.Series equity curves
        stats: dict ze statystykami per strategia (CAGR, DD, Sharpe, Sortino,
               Calmar; dla "GEM" dodatkowo Win Rate, Profit Factor, Trades)
        signals: lista (date, signal) zmian sygnalu
    """
    required = ["QQQ", "VEA", "EEM", "ACWI", "AGG"]
    for t in required:
        if t not in prices.columns:
            return None

    prices_clean = prices[required].dropna()
    if len(prices_clean) < lookback + 10:
        return None

    dates = prices_clean.index[lookback:]
    daily_returns = prices_clean.pct_change()
    rf_decimal = risk_free_annual / 100.0
    skip = 21

    equity_assets = ["QQQ", "VEA", "EEM", "ACWI"]
    sma = (prices_clean[equity_assets].rolling(sma_window, min_periods=max(50, sma_window // 4)).mean()
           if trend_filter else None)

    def _resolve_signal(idx: int) -> str:
        if idx < lookback or idx < skip:
            return "AGG"
        qqq_r = prices_clean["QQQ"].iloc[idx - skip] / prices_clean["QQQ"].iloc[idx - lookback] - 1
        if qqq_r < rf_decimal:
            return "AGG"
        candidates = {
            a: prices_clean[a].iloc[idx - skip] / prices_clean[a].iloc[idx - lookback] - 1
            for a in equity_assets
        }
        best = max(candidates, key=candidates.get)
        if trend_filter and sma is not None:
            price_now = prices_clean[best].iloc[idx]
            sma_now = sma[best].iloc[idx]
            if pd.notna(sma_now) and price_now < sma_now:
                return "AGG"
        return best

    idx0 = prices_clean.index.get_loc(dates[0])
    current_signal = _resolve_signal(idx0)
    signals_log = [(dates[0], current_signal)]

    # Vol targeting: precompute realized vol per equity asset (none for AGG)
    vols = None
    if vol_target is not None:
        vols = {a: calc_realized_vol(prices_clean[a], vol_window) for a in equity_assets}

    rf_daily = rf_decimal / 252

    gem_equity = [start_capital]
    for i in range(1, len(dates)):
        date = dates[i]
        idx = prices_clean.index.get_loc(date)

        if i % 21 == 0:
            new_signal = _resolve_signal(idx)
            if new_signal != current_signal:
                signals_log.append((date, new_signal))
                current_signal = new_signal

        day_ret = daily_returns.loc[date, current_signal]
        if pd.isna(day_ret):
            gem_equity.append(gem_equity[-1])
            continue

        if vol_target is not None and current_signal in equity_assets:
            # uzyj wczorajszej realized vol (brak lookahead)
            rv_series = vols[current_signal]
            rv = rv_series.iloc[idx - 1] if idx >= 1 else np.nan
            pos = vol_target_position(rv, vol_target, max_leverage=max_leverage)
            port_ret = pos * day_ret + (1 - pos) * rf_daily
        else:
            port_ret = day_ret

        gem_equity.append(gem_equity[-1] * (1 + port_ret))

    qqq_prices = prices_clean["QQQ"].loc[dates]
    acwi_prices = prices_clean["ACWI"].loc[dates]
    agg_prices = prices_clean["AGG"].loc[dates]

    eq_gem = pd.Series(gem_equity, index=dates, name="GEM")
    eq_qqq = pd.Series((start_capital * qqq_prices / qqq_prices.iloc[0]).values, index=dates, name="QQQ Buy&Hold")
    eq_acwi = pd.Series((start_capital * acwi_prices / acwi_prices.iloc[0]).values, index=dates, name="ACWI Buy&Hold")
    eq_agg = pd.Series((start_capital * agg_prices / agg_prices.iloc[0]).values, index=dates, name="AGG Buy&Hold")

    stats = {
        "GEM": calc_stats(eq_gem, 252, rf_decimal),
        "QQQ B&H": calc_stats(eq_qqq, 252, rf_decimal),
        "ACWI B&H": calc_stats(eq_acwi, 252, rf_decimal),
        "AGG B&H": calc_stats(eq_agg, 252, rf_decimal),
    }
    stats["GEM"].update(trade_stats(signals_log, eq_gem))

    return {
        "equity_gem": eq_gem,
        "equity_qqq": eq_qqq,
        "equity_acwi": eq_acwi,
        "equity_agg": eq_agg,
        "stats": stats,
        "signals": signals_log,
    }


def backtest_sma200(prices: pd.DataFrame, risk_free_annual: float,
                    start_capital: float = 10000, sma_window: int = 200,
                    buffer_pct: float = 0.0,
                    monthly_check: bool = False,
                    vol_target: float | None = None,
                    max_leverage: float = 1.0,
                    vol_window: int = 20) -> dict | None:
    """Backtest QQQ + SMA 200: QQQ gdy cena > SMA(200), AGG gdy ponizej.

    Args:
        prices: DataFrame z cenami (wymagane: QQQ, AGG)
        risk_free_annual: roczna stopa wolna w %
        start_capital: kapital poczatkowy
        sma_window: okno SMA (default 200)
        buffer_pct: histereza (0.01 = 1%). Switch do AGG tylko gdy cena <
            SMA * (1 - buffer); switch do QQQ tylko gdy cena > SMA * (1 + buffer).
            Redukuje whipsawy w rynku bocznym — Faber rekomenduje 2%.
        monthly_check: jesli True, sprawdzaj sygnal tylko co ~21 dni (rebalans
            miesieczny zamiast dziennego). Dalej redukuje whipsawy kosztem
            opoznionej reakcji.
        vol_target: cel rocznej zmiennosci (np. 0.15 = 15%). Pozycja =
            target/realized, clamped do [0, max_leverage]. None = wylaczone.
            Scalowanie dziala tylko gdy sygnal = QQQ; AGG zawsze full.
        max_leverage: maks. dzwignia dla vol_target (1.0 = bez dzwigni)
        vol_window: okno realizowanej zmiennosci (dni, default 20)

    Returns dict z equity curves, stats (z Sortino/Calmar/Win Rate), signals.
    """
    required = ["QQQ", "AGG"]
    for t in required:
        if t not in prices.columns:
            return None

    prices_clean = prices[required].dropna()
    if len(prices_clean) < sma_window + 10:
        return None

    qqq = prices_clean["QQQ"]
    sma = qqq.rolling(window=sma_window).mean()

    start_idx = prices_clean.index[sma_window]
    dates = prices_clean.index[prices_clean.index >= start_idx]
    daily_returns = prices_clean.pct_change()
    rf_decimal = risk_free_annual / 100.0
    upper_mult = 1.0 + buffer_pct
    lower_mult = 1.0 - buffer_pct

    # Poczatkowy sygnal bez histerezy (pierwsza decyzja)
    current_signal = "QQQ" if qqq.loc[dates[0]] > sma.loc[dates[0]] else "AGG"
    signals_log = [(dates[0], current_signal)]

    # Vol targeting: precompute realized vol na QQQ (AGG niescalowany)
    qqq_vol = calc_realized_vol(qqq, vol_window) if vol_target is not None else None
    rf_daily = rf_decimal / 252

    equity = [start_capital]
    for i in range(1, len(dates)):
        date = dates[i]
        date_prev = dates[i - 1]

        # Sprawdzamy sygnal codziennie lub co miesiac
        check_today = (not monthly_check) or (i % 21 == 0)
        if check_today:
            p = qqq.loc[date_prev]
            s = sma.loc[date_prev]
            if pd.notna(p) and pd.notna(s):
                if current_signal == "QQQ" and p < s * lower_mult:
                    current_signal = "AGG"
                    signals_log.append((date, "AGG"))
                elif current_signal == "AGG" and p > s * upper_mult:
                    current_signal = "QQQ"
                    signals_log.append((date, "QQQ"))

        day_ret = daily_returns.loc[date, current_signal]
        if pd.isna(day_ret):
            equity.append(equity[-1])
            continue

        if vol_target is not None and current_signal == "QQQ":
            rv = qqq_vol.loc[date_prev]
            pos = vol_target_position(rv, vol_target, max_leverage=max_leverage)
            port_ret = pos * day_ret + (1 - pos) * rf_daily
        else:
            port_ret = day_ret

        equity.append(equity[-1] * (1 + port_ret))

    eq_sma = pd.Series(equity, index=dates, name="QQQ+SMA200")
    qqq_prices = qqq.loc[dates]
    eq_qqq = pd.Series((start_capital * qqq_prices / qqq_prices.iloc[0]).values,
                        index=dates, name="QQQ Buy&Hold")
    agg_prices = prices_clean["AGG"].loc[dates]
    eq_agg = pd.Series((start_capital * agg_prices / agg_prices.iloc[0]).values,
                        index=dates, name="AGG Buy&Hold")

    stats = {
        "QQQ+SMA200": calc_stats(eq_sma, 252, rf_decimal),
        "QQQ B&H": calc_stats(eq_qqq, 252, rf_decimal),
        "AGG B&H": calc_stats(eq_agg, 252, rf_decimal),
    }
    stats["QQQ+SMA200"].update(trade_stats(signals_log, eq_sma))

    return {
        "equity_sma": eq_sma,
        "equity_qqq": eq_qqq,
        "equity_agg": eq_agg,
        "stats": stats,
        "signals": signals_log,
    }


def backtest_tqqq_mom(prices: pd.DataFrame, risk_free_annual: float,
                      start_capital: float = 10000, lookback: int = 273) -> dict | None:
    """Backtest TQQQ + Momentum: syntetyczny TQQQ (3x QQQ), timing 12-1 momentum.

    TQQQ syntetyzowany z QQQ (daily_return * 3) — pozwala siegnac dalej niz 2010.
    Rebalans co 21 dni: jesli QQQ 12M skip-month > rf → TQQQ, w przeciwnym razie → AGG.
    Returns dict z equity curves, stats, signals.
    """
    required = ["QQQ", "AGG"]
    for t in required:
        if t not in prices.columns:
            return None

    prices_clean = prices[required].dropna()
    if len(prices_clean) < lookback + 10:
        return None

    dates = prices_clean.index[lookback:]
    qqq_daily = prices_clean["QQQ"].pct_change()
    agg_daily = prices_clean["AGG"].pct_change()
    tqqq_daily = qqq_daily * 3  # syntetyczny 3x leverage

    rf_decimal = risk_free_annual / 100.0
    skip = 21

    # Poczatkowy sygnal
    idx0 = prices_clean.index.get_loc(dates[0])
    if idx0 >= lookback and idx0 >= skip:
        qqq_r0 = prices_clean["QQQ"].iloc[idx0 - skip] / prices_clean["QQQ"].iloc[idx0 - lookback] - 1
    else:
        qqq_r0 = 0

    current_signal = "TQQQ" if qqq_r0 > rf_decimal else "AGG"
    signals_log = [(dates[0], current_signal)]

    # TQQQ+Momentum equity
    mom_equity = [start_capital]
    # TQQQ Buy&Hold equity
    tqqq_bh_equity = [start_capital]

    for i in range(1, len(dates)):
        date = dates[i]
        idx = prices_clean.index.get_loc(date)

        # Rebalans co 21 dni (miesieczny)
        if i % 21 == 0:
            if idx >= lookback and idx >= skip:
                qqq_ret = prices_clean["QQQ"].iloc[idx - skip] / prices_clean["QQQ"].iloc[idx - lookback] - 1
            else:
                qqq_ret = 0

            new_signal = "TQQQ" if qqq_ret > rf_decimal else "AGG"
            if new_signal != current_signal:
                signals_log.append((date, new_signal))
                current_signal = new_signal

        # Dzienny zwrot strategii
        if current_signal == "TQQQ":
            day_ret = tqqq_daily.loc[date]
        else:
            day_ret = agg_daily.loc[date]

        if pd.notna(day_ret):
            mom_equity.append(mom_equity[-1] * (1 + day_ret))
        else:
            mom_equity.append(mom_equity[-1])

        # TQQQ B&H
        tqqq_ret = tqqq_daily.loc[date]
        if pd.notna(tqqq_ret):
            tqqq_bh_equity.append(tqqq_bh_equity[-1] * (1 + tqqq_ret))
        else:
            tqqq_bh_equity.append(tqqq_bh_equity[-1])

    # Equity curves
    eq_mom = pd.Series(mom_equity, index=dates, name="TQQQ+Momentum")
    eq_tqqq_bh = pd.Series(tqqq_bh_equity, index=dates, name="TQQQ Buy&Hold")
    qqq_prices = prices_clean["QQQ"].loc[dates]
    eq_qqq = pd.Series((start_capital * qqq_prices / qqq_prices.iloc[0]).values,
                        index=dates, name="QQQ Buy&Hold")
    agg_prices = prices_clean["AGG"].loc[dates]
    eq_agg = pd.Series((start_capital * agg_prices / agg_prices.iloc[0]).values,
                        index=dates, name="AGG Buy&Hold")

    stats = {
        "TQQQ+Mom": calc_stats(eq_mom, 252, rf_decimal),
        "TQQQ B&H": calc_stats(eq_tqqq_bh, 252, rf_decimal),
        "QQQ B&H": calc_stats(eq_qqq, 252, rf_decimal),
        "AGG B&H": calc_stats(eq_agg, 252, rf_decimal),
    }
    stats["TQQQ+Mom"].update(trade_stats(signals_log, eq_mom))

    return {
        "equity_tqqq_mom": eq_mom,
        "equity_tqqq_bh": eq_tqqq_bh,
        "equity_qqq": eq_qqq,
        "equity_agg": eq_agg,
        "stats": stats,
        "signals": signals_log,
    }


def rolling_momentum(prices: pd.Series, window: int = 252) -> pd.Series:
    """Rolling momentum (stopa zwrotu) dla jednego tickera."""
    return prices.pct_change(periods=window)


def drawdown_series(prices: pd.Series) -> pd.Series:
    """Seria drawdown (spadek od szczytu) dla jednego tickera."""
    running_max = prices.cummax()
    return (prices - running_max) / running_max


def monthly_returns_matrix(prices: pd.Series) -> pd.DataFrame:
    """Pivot rok × miesiac z miesięcznymi zwrotami.

    Returns DataFrame: index=rok, kolumny=1..12, wartosci = zwrot procentowy.
    """
    monthly = prices.resample("ME").last().pct_change().dropna()
    df = pd.DataFrame({"year": monthly.index.year, "month": monthly.index.month, "ret": monthly.values})
    pivot = df.pivot_table(index="year", columns="month", values="ret", aggfunc="first")
    pivot.columns = list(range(1, 13))[:len(pivot.columns)]
    return pivot


def top_drawdowns(prices: pd.Series, n: int = 10) -> pd.DataFrame:
    """Top N drawdownow z detalami: peak, trough, recovery, depth, duration.

    Returns DataFrame z kolumnami:
        peak_date, trough_date, recovery_date, depth_pct, days_down, days_recovery
    """
    running_max = prices.cummax()
    dd = (prices - running_max) / running_max

    records = []
    in_dd = False
    peak_date = trough_date = None
    peak_val = trough_val = 0.0

    for date, val in dd.items():
        price = prices.loc[date]
        if val < 0 and not in_dd:
            in_dd = True
            # find peak date
            peak_val = running_max.loc[date]
            mask = prices.loc[:date]
            peak_date = mask[mask == peak_val].index[-1]
            trough_date = date
            trough_val = price
        elif val < 0 and in_dd:
            if price < trough_val:
                trough_date = date
                trough_val = price
        elif val >= 0 and in_dd:
            in_dd = False
            depth = (trough_val / peak_val - 1)
            days_down = (trough_date - peak_date).days
            days_recovery = (date - trough_date).days
            records.append({
                "peak_date": peak_date,
                "trough_date": trough_date,
                "recovery_date": date,
                "depth_pct": depth,
                "days_down": days_down,
                "days_recovery": days_recovery,
            })

    # Handle ongoing drawdown
    if in_dd:
        depth = (trough_val / peak_val - 1)
        days_down = (trough_date - peak_date).days
        records.append({
            "peak_date": peak_date,
            "trough_date": trough_date,
            "recovery_date": None,
            "depth_pct": depth,
            "days_down": days_down,
            "days_recovery": None,
        })

    if not records:
        return pd.DataFrame()

    result = pd.DataFrame(records).sort_values("depth_pct").head(n).reset_index(drop=True)
    result.index = result.index + 1  # 1-based
    return result


def monte_carlo_simulation(equity: pd.Series, years: int = 10,
                           n_sims: int = 1000,
                           trading_days: int = 252) -> pd.DataFrame:
    """Bootstrap Monte Carlo simulation przyszlych sciezek.

    Returns DataFrame: index=dzien (0..years*trading_days), kolumny=symulacja 0..n_sims-1.
    """
    daily_rets = equity.pct_change().dropna().values
    n_days = years * trading_days
    start_val = equity.iloc[-1]

    rng = np.random.default_rng(42)
    sims = np.empty((n_days + 1, n_sims))
    sims[0] = start_val

    for t in range(1, n_days + 1):
        sampled = rng.choice(daily_rets, size=n_sims)
        sims[t] = sims[t - 1] * (1 + sampled)

    return pd.DataFrame(sims, columns=range(n_sims))


def calc_ema(prices: pd.Series, spans=(20, 50, 200)) -> pd.DataFrame:
    """EMA dla zadanych okien. Zwraca DataFrame z kolumnami EMA_20, EMA_50, itd."""
    result = pd.DataFrame(index=prices.index)
    for s in spans:
        result[f"EMA_{s}"] = prices.ewm(span=s, adjust=False).mean()
    return result


def calc_macd(prices: pd.Series, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """MACD: linia MACD, linia Signal, Histogram."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({"MACD": macd_line, "Signal": signal_line, "Histogram": histogram})


def calc_rsi(prices: pd.Series, period=14) -> pd.Series:
    """Klasyczny RSI Wildera (ewm z com=period-1). Wartosci 0-100."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_bollinger(prices: pd.Series, period=20, std_dev=2) -> pd.DataFrame:
    """Bollinger Bands: Middle (SMA), Upper, Lower."""
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return pd.DataFrame({"Middle": middle, "Upper": upper, "Lower": lower})


def relative_strength(asset: pd.Series, benchmark: pd.Series,
                      sma_windows: tuple = (50, 200)) -> pd.DataFrame:
    """Oblicza Relative Strength (asset/benchmark) + SMA linii RS.

    Returns DataFrame z kolumnami: RS, RS_SMA_50, RS_SMA_200 (znormalizowane do 100).
    """
    common = asset.dropna().index.intersection(benchmark.dropna().index)
    if len(common) < 20:
        return pd.DataFrame()

    a = asset.loc[common]
    b = benchmark.loc[common]
    rs = (a / b)
    rs = rs / rs.iloc[0] * 100  # normalizacja do bazy 100

    result = pd.DataFrame({"RS": rs}, index=common)
    for w in sma_windows:
        if len(rs) > w:
            result[f"RS_SMA_{w}"] = rs.rolling(window=w, min_periods=1).mean()
    return result


def correlation_matrix(prices: pd.DataFrame, period: int = 252) -> pd.DataFrame:
    """Macierz korelacji zwrotow dziennych za ostatnie `period` dni."""
    recent = prices.tail(period)
    returns = recent.pct_change().dropna()
    return returns.corr()


def calc_stats(equity: pd.Series, trading_days: int = 252,
               rf_decimal: float = 0.0) -> dict:
    """Oblicza statystyki backtestu: CAGR, calkowity zwrot, max DD, Sharpe, Sortino, Calmar.

    Args:
        equity: Series z wartoscia portfela
        trading_days: dni handlowe/rok (252 akcje, 365 krypto)
        rf_decimal: roczna stopa wolna od ryzyka jako ulamek (np. 0.045)
    """
    years = len(equity) / trading_days
    total_ret = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else 0
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    max_dd = dd.min()
    dr = equity.pct_change().dropna()
    excess = dr - rf_decimal / trading_days
    std = excess.std(ddof=0)
    sharpe = excess.mean() / std * np.sqrt(trading_days) if std > 0 else 0
    downside = excess[excess < 0]
    dstd = downside.std(ddof=0) if len(downside) > 1 else 0
    sortino = excess.mean() / dstd * np.sqrt(trading_days) if dstd > 0 else 0
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    return {
        "CAGR": cagr,
        "Calkowity zwrot": total_ret,
        "Max Drawdown": max_dd,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Calmar": calmar,
    }


def trade_stats(signals_log: list, equity: pd.Series) -> dict:
    """Statystyki per transakcja (segment miedzy zmianami sygnalu).

    Liczy zwrot kazdego segmentu od daty wejscia do daty zmiany na nastepny
    sygnal (ostatni segment konczy sie na ostatniej dacie equity). Pozwala na
    sensowny "win rate" per sygnal — zwyklym Sharpe dla dni nie daje sie
    wyliczyc czy strategia generuje dobre czy zle decyzje.

    Args:
        signals_log: lista (date, signal) z zmianami sygnalu (date wejscia)
        equity: Series equity curve

    Returns:
        dict: Win Rate (0-1), Profit Factor, Avg Trade (ulamek), Trades (int)
    """
    if not signals_log or len(equity) < 2:
        return {"Win Rate": 0.0, "Profit Factor": 0.0, "Avg Trade": 0.0, "Trades": 0}

    change_dates = [s[0] for s in signals_log]
    change_dates.append(equity.index[-1])
    returns = []
    for i in range(len(change_dates) - 1):
        start = change_dates[i]
        end = change_dates[i + 1]
        eq_slice = equity.loc[start:end]
        if len(eq_slice) < 2:
            continue
        start_val = eq_slice.iloc[0]
        end_val = eq_slice.iloc[-1]
        if start_val > 0:
            returns.append(end_val / start_val - 1)

    if not returns:
        return {"Win Rate": 0.0, "Profit Factor": 0.0, "Avg Trade": 0.0, "Trades": 0}

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    win_rate = len(wins) / len(returns)
    sum_wins = sum(wins) if wins else 0.0
    sum_losses = abs(sum(losses)) if losses else 0.0
    if sum_losses > 0:
        profit_factor = sum_wins / sum_losses
    else:
        profit_factor = float("inf") if sum_wins > 0 else 0.0
    avg_trade = sum(returns) / len(returns)
    return {
        "Win Rate": win_rate,
        "Profit Factor": profit_factor,
        "Avg Trade": avg_trade,
        "Trades": len(returns),
    }


def backtest_rotation(prices: pd.DataFrame, top_n: int = 3,
                       lookback: int = 273, rebalance_freq: int = 21,
                       start_capital: float = 10000,
                       trading_days: int = 252,
                       benchmarks: dict[str, str | list[str]] | None = None,
                       score_func=None,
                       rank_based: bool = False,
                       rank_weights: dict | None = None,
                       anti_1m: bool = True) -> dict | None:
    """Backtest rotacji momentum — wspolna logika dla S&P 500, GPW, krypto.

    Args:
        prices: DataFrame z cenami (kolumny = tickery)
        top_n: ile spolek trzymac w portfelu
        lookback: okno lookback w dniach
        rebalance_freq: czestotliwosc rebalansu (dni)
        start_capital: kapital poczatkowy
        trading_days: dni handlowe/rok
        benchmarks: dict z benchmarkami, np. {"SPY B&H": "SPY", "EW B&H": list_of_tickers}
        score_func: funkcja do obliczania wyniku (default: composite_score).
            Ignorowana gdy rank_based=True.
        rank_based: jesli True, uzyj rank_based_score() (percentyle per okres + 1M
            flip jako anti-signal). Bardziej odporny na outliery i skew — preferowany
            dla rotacji w heterogenicznym universe (akcje GPW, krypto)
        rank_weights: wagi dla rank scoringu (default: 12M=0.40, 6M=0.30, 3M=0.20, 1M=0.10)
        anti_1m: czy odwracac rank 1M (default True, uzywane gdy rank_based=True)

    Returns:
        dict z equity curves (dict[str, pd.Series]) i stats (dict)
    """
    if score_func is None:
        score_func = composite_score

    available_cols = [c for c in prices.columns if prices[c].dropna().shape[0] > lookback]
    if len(available_cols) < top_n:
        return None

    bt_clean = prices[available_cols].dropna(how="all")
    if len(bt_clean) < lookback + 10:
        return None

    daily_rets = bt_clean.pct_change()
    dates = bt_clean.index[lookback:]
    mom_equity = [start_capital]
    current_holdings = []

    for i, date in enumerate(dates):
        if i % rebalance_freq == 0:
            idx = bt_clean.index.get_loc(date)
            if idx >= lookback:
                window_prices = bt_clean.iloc[idx - lookback:idx + 1]
                rets_now = latest_returns(window_prices)
                if rank_based:
                    rets_now["score"] = rank_based_score(rets_now, rank_weights, anti_1m)
                else:
                    rets_now["score"] = rets_now.apply(score_func, axis=1)
                rets_now = rets_now.dropna(subset=["score"])
                if len(rets_now) >= top_n:
                    current_holdings = rets_now.nlargest(top_n, "score").index.tolist()

        if current_holdings and date in daily_rets.index:
            port_ret = daily_rets.loc[date, current_holdings].mean()
            if pd.notna(port_ret):
                mom_equity.append(mom_equity[-1] * (1 + port_ret))
            else:
                mom_equity.append(mom_equity[-1])
        else:
            mom_equity.append(mom_equity[-1])

    mom_equity = mom_equity[1:]
    eq_mom = pd.Series(mom_equity, index=dates, name=f"Momentum Top {top_n}")

    # Benchmarki
    equity_curves = {f"Momentum Top {top_n}": eq_mom}

    if benchmarks:
        for bm_name, bm_spec in benchmarks.items():
            bm_eq = [start_capital]
            if isinstance(bm_spec, str):
                # Pojedynczy ticker benchmark
                if bm_spec in prices.columns:
                    bm_rets = prices[bm_spec].pct_change()
                    for date in dates:
                        if date in bm_rets.index and pd.notna(bm_rets.loc[date]):
                            bm_eq.append(bm_eq[-1] * (1 + bm_rets.loc[date]))
                        else:
                            bm_eq.append(bm_eq[-1])
                else:
                    bm_eq.extend([start_capital] * len(dates))
            elif isinstance(bm_spec, list):
                # Equal-weight basket benchmark
                bm_cols = [c for c in bm_spec if c in daily_rets.columns]
                for date in dates:
                    if date in daily_rets.index and bm_cols:
                        bm_ret = daily_rets.loc[date, bm_cols].mean()
                        if pd.notna(bm_ret):
                            bm_eq.append(bm_eq[-1] * (1 + bm_ret))
                        else:
                            bm_eq.append(bm_eq[-1])
                    else:
                        bm_eq.append(bm_eq[-1])

            bm_eq = bm_eq[1:]
            equity_curves[bm_name] = pd.Series(bm_eq, index=dates, name=bm_name)

    # Stats
    rf_decimal = 0.0  # domyslnie bez rf, strona podaje rf osobno
    stats = {}
    for name, eq in equity_curves.items():
        stats[name] = calc_stats(eq, trading_days, rf_decimal)

    return {"equity_curves": equity_curves, "stats": stats}


def strategy_correlations(prices: pd.DataFrame, rf: float,
                          window: int = 63) -> pd.DataFrame | None:
    """Rolling korelacja miedzy equity curves 3 strategii: GEM, SMA200, TQQQ+Mom.

    Args:
        prices: DataFrame z cenami (musi zawierac QQQ, VEA, EEM, ACWI, AGG)
        rf: roczna stopa wolna od ryzyka w %
        window: okno rolling korelacji w dniach

    Returns:
        DataFrame z kolumnami: "GEM vs SMA200", "GEM vs TQQQ+Mom", "SMA200 vs TQQQ+Mom"
        lub None jesli brak danych.
    """
    bt_gem = backtest_gem(prices, rf)
    bt_sma = backtest_sma200(prices, rf)
    bt_tqqq = backtest_tqqq_mom(prices, rf)

    if bt_gem is None or bt_sma is None or bt_tqqq is None:
        return None

    eq_gem = bt_gem["equity_gem"]
    eq_sma = bt_sma["equity_sma"]
    eq_tqqq = bt_tqqq["equity_tqqq_mom"]

    # Wspolny indeks
    common_idx = eq_gem.index.intersection(eq_sma.index).intersection(eq_tqqq.index)
    if len(common_idx) < window + 10:
        return None

    rets = pd.DataFrame({
        "GEM": eq_gem.loc[common_idx].pct_change(),
        "SMA200": eq_sma.loc[common_idx].pct_change(),
        "TQQQ+Mom": eq_tqqq.loc[common_idx].pct_change(),
    }).dropna()

    if len(rets) < window + 1:
        return None

    corr_df = pd.DataFrame(index=rets.index)
    corr_df["GEM vs SMA200"] = rets["GEM"].rolling(window).corr(rets["SMA200"])
    corr_df["GEM vs TQQQ+Mom"] = rets["GEM"].rolling(window).corr(rets["TQQQ+Mom"])
    corr_df["SMA200 vs TQQQ+Mom"] = rets["SMA200"].rolling(window).corr(rets["TQQQ+Mom"])

    return corr_df.dropna()
