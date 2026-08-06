"""CLI: liczy miesieczny snapshot Top Picks i przelicza symulacje.

Odpalane przez .github/workflows/top-picks.yml pierwszego dnia miesiaca.
Lokalnie:  venv/Scripts/python.exe scripts/update_top_picks.py --dry-run
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Norton (i inne AV robiace TLS interception) lamia weryfikacje certyfikatu
# lokalnie — na CI ten blok jest no-opem.
_CA = os.environ.get("GEM_CA_BUNDLE")
if _CA and Path(_CA).exists():
    for _var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        os.environ[_var] = _CA

import yfinance as yf  # noqa: E402

from data import top_picks as tp  # noqa: E402
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES, GPW_SECTOR_MAP  # noqa: E402
from data.momentum import calc_stats  # noqa: E402
from data.sp500_universe import (  # noqa: E402
    SP500_NAMES,
    SP500_SECTOR_MAP,
    SP500_TOP100,
)

MARKETS = {
    "sp500": {
        "tickers": list(SP500_TOP100),
        "groups": SP500_SECTOR_MAP,
        "names": SP500_NAMES,
        "benchmark": "SPY",
    },
    "gpw": {
        "tickers": list(ALL_GPW_TICKERS),
        # Sektor, NIE indeks: WIG20/mWIG40 nie chroni przed piecioma bankami,
        # a filtr plynnosci zbija sWIG80 do zera (zostaja 2 grupy = sufit 4 pozycji).
        "groups": GPW_SECTOR_MAP,
        "names": GPW_NAMES,
        # yfinance nie ma historii indeksow GPW (zwraca 1 wiersz) — benchmark
        # leci przez stooq.com z fallbackiem na data/cache/wig20.csv.
        "benchmark": "WIG20",
        "benchmark_source": "stooq",
    },
}

CHUNK = 40
RETRIES = 3
MIN_COVERAGE = 0.80      # min. frakcja tickerow z danymi
MAX_STALENESS_DAYS = 5   # ostatnia sesja nie starsza niz tyle od asof


def download(tickers: list[str], period: str = "12y") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pobiera Close i Volume w porcjach, z retry. Zwraca (close, volume)."""
    closes, volumes = {}, {}
    for i in range(0, len(tickers), CHUNK):
        chunk = tickers[i:i + CHUNK]
        for attempt in range(RETRIES):
            try:
                data = yf.download(" ".join(chunk), period=period, auto_adjust=True,
                                   progress=False, group_by="column")
                if data is None or data.empty:
                    raise RuntimeError("pusta odpowiedz")
                if isinstance(data.columns, pd.MultiIndex):
                    close, volume = data["Close"], data["Volume"]
                else:
                    close = data[["Close"]].rename(columns={"Close": chunk[0]})
                    volume = data[["Volume"]].rename(columns={"Volume": chunk[0]})
                for col in close.columns:
                    if close[col].dropna().shape[0] > 100:
                        closes[col] = close[col]
                        volumes[col] = volume[col]
                break
            except Exception as exc:  # noqa: BLE001
                wait = 2 * (3 ** attempt)
                print(f"  chunk {i // CHUNK + 1} proba {attempt + 1}/{RETRIES}: {exc}",
                      flush=True)
                if attempt == RETRIES - 1:
                    print(f"  chunk {i // CHUNK + 1}: PORAZKA po {RETRIES} probach", flush=True)
                else:
                    print(f"  czekam {wait}s", flush=True)
                    time.sleep(wait)

    close_df = pd.DataFrame(closes)
    volume_df = pd.DataFrame(volumes)
    for frame in (close_df, volume_df):
        if hasattr(frame.index, "tz") and frame.index.tz is not None:
            frame.index = frame.index.tz_localize(None)
    return close_df.dropna(how="all"), volume_df.dropna(how="all")


def fetch_benchmark(cfg: dict, index: pd.DatetimeIndex) -> pd.Series | None:
    """Benchmark rynku, znormalizowany do 10 000 na pierwszej dacie `index`.

    GPW idzie przez stooq (yfinance nie ma historii indeksow WIG) — z fallbackiem
    na data/cache/*.csv, ktory dziala takze gdy stooq zablokuje IP runnera.
    """
    if cfg.get("benchmark_source") == "stooq":
        from data.downloader import download_stooq
        series = download_stooq(cfg["benchmark"], period="15y")
    else:
        frame, _ = download([cfg["benchmark"]], period="12y")
        series = None if frame.empty else frame.iloc[:, 0]

    if series is None or series.empty:
        return None
    aligned = series.reindex(index, method="ffill").dropna()
    if aligned.empty or float(aligned.iloc[0]) == 0:
        return None
    return aligned.reindex(index, method="ffill") / float(aligned.iloc[0]) * 10000.0


def validate(market: str, tickers: list[str], prices: pd.DataFrame,
             picks: list[dict], asof: pd.Timestamp, top_n: int) -> None:
    """Twarda walidacja. Kazdy blad = sys.exit(1) BEZ zapisu.

    Pusty lub czesciowy snapshot klamie w sekcji "Wyniki live" na zawsze —
    brak wpisu jest mniej szkodliwy niz wpis nieprawdziwy.
    """
    coverage = len(prices.columns) / max(len(tickers), 1)
    if coverage < MIN_COVERAGE:
        sys.exit(f"[{market}] BLAD: pokrycie danych {coverage:.0%} < {MIN_COVERAGE:.0%}")

    staleness = (asof - prices.index[-1]).days
    if staleness > MAX_STALENESS_DAYS:
        sys.exit(f"[{market}] BLAD: ostatnia sesja {prices.index[-1].date()} "
                 f"starsza o {staleness} dni od asof {asof.date()}")

    if len(picks) != top_n:
        sys.exit(f"[{market}] BLAD: regula zwrocila {len(picks)} pozycji zamiast {top_n}")

    unknown = [p["ticker"] for p in picks if p["group"] == "?"]
    if unknown:
        # Brakujacy wpis w mapie grup wrzuca spolki do wspolnego kubelka "?",
        # co po cichu psuje limit koncentracji. Lepiej zatrzymac sie glosno.
        sys.exit(f"[{market}] BLAD: brak grupy dla {unknown} — uzupelnij mape sektorow")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aktualizacja Top Picks (F18)")
    parser.add_argument("--asof", help="data w formacie YYYY-MM-DD (domyslnie: dzis)")
    parser.add_argument("--dry-run", action="store_true", help="policz i wypisz, nie zapisuj")
    parser.add_argument("--skip-sim", action="store_true", help="pomin przeliczanie symulacji")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--max-per-group", type=int, default=2)
    args = parser.parse_args()

    today = pd.Timestamp(args.asof) if args.asof else pd.Timestamp.today().normalize()
    month_key = today.replace(day=1).strftime("%Y-%m-%d")

    snapshot = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "asof": None,
        "rule_version": tp.RULE_VERSION,
    }
    sim = {
        "generated_at": snapshot["generated_at"],
        "rule_version": tp.RULE_VERSION,
        "params": {
            "top_n": args.top_n,
            "max_per_group": args.max_per_group,
            "transaction_cost": 0.001,
            "tax_belka": 0.19,
        },
    }

    for market, cfg in MARKETS.items():
        print(f"\n=== {market} ===", flush=True)
        prices, volumes = download(cfg["tickers"])
        if prices.empty:
            sys.exit(f"[{market}] BLAD: brak jakichkolwiek danych cenowych")
        print(f"  pobrano {len(prices.columns)}/{len(cfg['tickers'])} tickerow, "
              f"ostatnia sesja {prices.index[-1].date()}", flush=True)

        asof = prices.loc[:today].index[-1]
        picks = tp.select_picks(prices, volumes, cfg["groups"], asof,
                                top_n=args.top_n, max_per_group=args.max_per_group,
                                min_turnover=tp.MIN_TURNOVER[market])
        validate(market, cfg["tickers"], prices, picks, today, args.top_n)

        for pick in picks:
            pick["name"] = cfg["names"].get(pick["ticker"], "")
        snapshot["asof"] = asof.strftime("%Y-%m-%d")
        snapshot[market] = picks
        print("  " + " · ".join(f"{p['ticker']} ({p['group']}, {p['score']:.3f})"
                                for p in picks), flush=True)

        if args.skip_sim:
            continue

        start = prices.index[0] + pd.Timedelta(days=400)
        equity = tp.simulate_rule(prices, volumes, cfg["groups"], start=start,
                                  min_turnover=tp.MIN_TURNOVER[market],
                                  top_n=args.top_n, max_per_group=args.max_per_group)
        if equity.empty:
            print(f"  symulacja pominieta ({market}): pusta krzywa", flush=True)
            continue

        bench = fetch_benchmark(cfg, equity.index)
        stats = calc_stats(equity, trading_days=12)   # seria miesieczna
        if bench is None:
            # Brak benchmarku nie moze kasowac calej symulacji — sekcja 3 jest
            # wartosciowa takze sama krzywa reguly.
            print(f"  UWAGA ({market}): brak benchmarku {cfg['benchmark']}, "
                  f"symulacja bez porownania", flush=True)
            hits = 0.0
            bench_values = []
        else:
            hits = float((equity.pct_change() > bench.pct_change()).mean())
            bench_values = [round(float(v), 2) for v in bench.values]

        sim[market] = {
            "dates": [d.strftime("%Y-%m-%d") for d in equity.index],
            "equity": [round(float(v), 2) for v in equity.values],
            "benchmark": bench_values,
            "benchmark_name": cfg["benchmark"] if bench is not None else None,
            "stats": {
                # UWAGA: calc_stats zwraca klucz "Max Drawdown", nie "Max DD"
                "cagr": round(float(stats.get("CAGR", 0)), 4),
                "max_dd": round(float(stats.get("Max Drawdown", 0)), 4),
                "sharpe": round(float(stats.get("Sharpe", 0)), 3),
                "hit_rate": round(hits, 3),
            },
        }
        print(f"  symulacja: {len(equity)} miesiecy, CAGR {stats.get('CAGR', 0):.1%}", flush=True)

    if args.dry_run:
        print("\n--dry-run: nic nie zapisano")
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return

    added = tp.append_snapshot(month_key, snapshot)
    print(f"\nsnapshot {month_key}: {'dopisany' if added else 'juz istnial — pomijam'}")
    if not args.skip_sim:
        tp.SIM_PATH.write_text(json.dumps(sim, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"symulacja zapisana: {tp.SIM_PATH.name}")


if __name__ == "__main__":
    main()
