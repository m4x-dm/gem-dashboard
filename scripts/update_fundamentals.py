"""CLI: dzienny zrzut danych fundamentalnych (wyniki, data raportu, analitycy, insiderzy).

Odpalane przez .github/workflows/fundamentals.yml codziennie o 05:30 UTC. Yahoo odrzuca
zapytania quoteSummary z IP Streamlit Cloud, a z GitHub Actions je obsluguje — aplikacja czyta
ten plik (data/fundamentals_snapshot.py) zamiast pytac Yahoo.
Lokalnie:  venv/Scripts/python.exe scripts/update_fundamentals.py --out fundamentals.json.gz --limit 20
"""
import argparse
import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["GEM_FUNDAMENTALS_SNAPSHOT"] = "0"   # zbieramy z Yahoo, nie z poprzedniego zrzutu

_CA = os.environ.get("GEM_CA_BUNDLE")
if _CA and Path(_CA).exists():
    for _var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        os.environ[_var] = _CA

from data import fundamentals_snapshot as fs  # noqa: E402
from data.fundamentals_extra import EXTRA_TICKERS  # noqa: E402
from data.gpw_universe import get_gpw_universe  # noqa: E402
from data.sp500_universe import get_sp500_universe  # noqa: E402

UD_DAYS = 90
MIN_SP500_EARNINGS = 0.5   # ponizej = Yahoo blokuje tez GitHuba -> nie nadpisujemy zrzutu


def _ts(v):
    try:
        return pd.Timestamp(int(v), unit="s").normalize() if v else None
    except (TypeError, ValueError):
        return None


def fetch_one(ticker: str, fin, today: pd.Timestamp) -> dict:
    """Dane jednej spolki z Yahoo (te same funkcje co aplikacja). Bledy -> None w danym polu."""
    rec = {"eh": None, "rd": None, "nd": None, "ud": None, "ins": None}
    try:
        rec["eh"] = fin.get_earnings_history(ticker, n_quarters=8)
    except Exception:
        pass
    try:
        info = fin._fetch_info(ticker)
        rec["rd"] = _ts(info.get("earningsTimestamp"))
        nd = _ts(info.get("earningsTimestampStart"))
        rec["nd"] = nd if nd is not None and nd > today else None
        if rec["rd"] is not None and rec["rd"] > today:      # Yahoo podaje tu czasem przyszly termin
            rec["nd"] = rec["nd"] or rec["rd"]
            rec["rd"] = None
    except Exception:
        pass
    if not ticker.upper().endswith(".WA"):
        try:
            ud = fin.fetch_upgrades_downgrades(ticker)
            if ud is not None:
                ud = ud[ud.index >= today - pd.Timedelta(days=UD_DAYS)]
            rec["ud"] = ud if ud is not None and not ud.empty else None
        except Exception:
            pass
        try:
            rec["ins"] = fin.fetch_insider_transactions(ticker)
        except Exception:
            pass
    return rec


# Pierwszy run w CI (2026-11-20): po ~450 spolkach Yahoo zaczal odrzucac zapytania (401 Invalid
# Crumb) — GPW i lista extra wyszly w 0%. Stad mniej watkow i dwie powtorki dla brakow.
RETRIES = ((60, 2), (120, 1))   # (pauza s, watki)


def missing(ticker: str, rec: dict) -> list[str]:
    """Pola, ktore warto pobrac ponownie (GPW: tylko wyniki — reszty Yahoo dla GPW nie ma)."""
    need = ("eh",) if ticker.upper().endswith(".WA") else ("eh", "ud", "ins")
    return [k for k in need if rec.get(k) is None]


def _pass(tickers: list[str], fin, today, workers: int) -> dict[str, dict]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(zip(tickers, ex.map(lambda t: fetch_one(t, fin, today), tickers)))


def collect(tickers: list[str], fin, today: pd.Timestamp, workers: int = 4,
            retries=RETRIES, sleep=None) -> dict[str, dict]:
    sleep = sleep or time.sleep          # rozwiazywane przy wywolaniu (testy podmieniaja time.sleep)
    per = _pass(tickers, fin, today, workers)
    for wait, w in retries:
        todo = [t for t in tickers if missing(t, per[t])]
        if not todo:
            break
        print(f"  powtorka: {len(todo)} spolek z brakami, pauza {wait} s, {w} watki", flush=True)
        sleep(wait)
        again = _pass(todo, fin, today, w)
        for t in todo:
            for k, v in again[t].items():
                if per[t].get(k) is None and v is not None:
                    per[t][k] = v
    return per


def coverage(per_ticker: dict[str, dict], tickers: list[str], kind: str) -> float:
    if not tickers:
        return 0.0
    return sum(1 for t in tickers if per_ticker.get(t, {}).get(kind) is not None) / len(tickers)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="fundamentals.json.gz")
    ap.add_argument("--limit", type=int, default=0, help="tylko N pierwszych spolek z kazdej grupy (test)")
    args = ap.parse_args(argv)

    from data import financials as fin
    sp500, gpw, extra = get_sp500_universe(), get_gpw_universe(), list(EXTRA_TICKERS)
    if args.limit:
        sp500, gpw, extra = sp500[:args.limit], gpw[:args.limit], extra[:args.limit]
    tickers = list(dict.fromkeys(sp500 + gpw + extra))
    today = pd.Timestamp.now().normalize()
    t0 = time.time()
    per = collect(tickers, fin, today)
    print(f"pobrano {len(per)} spolek w {time.time() - t0:.0f} s", flush=True)
    for name, group in (("S&P 500", sp500), ("GPW", gpw), ("extra", extra)):
        print(f"  {name:8} " + " · ".join(f"{k} {coverage(per, group, k):.0%}"
                                          for k in ("eh", "rd", "nd", "ud", "ins")), flush=True)
    cov = coverage(per, sp500, "eh")
    if cov < MIN_SP500_EARNINGS:
        print(f"ODRZUCONO: wyniki tylko dla {cov:.0%} S&P 500 (< {MIN_SP500_EARNINGS:.0%}) — "
              "Yahoo blokuje? Poprzedni zrzut zostaje.", flush=True)
        return 1
    # Do pliku tylko spolki z jakimikolwiek danymi: spolka w zrzucie = "Yahoo nie ma nic wiecej",
    # wiec aplikacja nie pytalaby o nia Yahoo. Pusta -> aplikacja sprobuje sama (lokalnie dziala).
    kept = {t: r for t, r in per.items() if any(v is not None for v in r.values())}
    print(f"  w pliku {len(kept)} z {len(per)} spolek", flush=True)
    payload = fs.build_payload(kept, generated_at=pd.Timestamp.now(tz="UTC"))
    data = gzip.compress(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    Path(args.out).write_bytes(data)
    print(f"zapisano {args.out}: {len(data) / 1024:.0f} KB", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
