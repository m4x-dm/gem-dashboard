"""Wersja wdrozenia — krotki SHA commita i jego data.

Po co: na Streamlit Cloud nie widac z zewnatrz, ktory commit jest aktualnie
wdrozony. Bez tego weryfikacja deployu sprowadza sie do zgadywania po liczbach
w UI, co zawodzi, gdy zmiana nic nie zmienia wizualnie (np. fix lookaheadu).

Jak czytamy SHA (kolejno, pierwszy ktory zadziala):
  1. katalog .git czytany bezposrednio — bez binarki `git`, bez subprocess
  2. `git rev-parse` przez subprocess — gdyby uklad .git byl nietypowy
  3. zmienne srodowiskowe CI (gdyby kiedys doszedl inny hosting)
Jesli zadne nie zadziala, zwracamy None i stopka po prostu nie pokazuje wersji.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _read_sha_from_git_dir(root: Path) -> str | None:
    """Czyta SHA z .git bez uruchamiania gita. Obsluguje tez packed-refs."""
    git_dir = root / ".git"
    if git_dir.is_file():  # worktree/submodule: "gitdir: <sciezka>"
        try:
            pointer = git_dir.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not pointer.startswith("gitdir:"):
            return None
        git_dir = Path(pointer.split(":", 1)[1].strip())
        if not git_dir.is_absolute():
            git_dir = (root / git_dir).resolve()
    if not git_dir.is_dir():
        return None

    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None

    if not head.startswith("ref:"):
        return head or None  # detached HEAD — HEAD zawiera goly SHA

    ref = head.split(":", 1)[1].strip()
    ref_file = git_dir / ref
    try:
        return ref_file.read_text(encoding="utf-8").strip() or None
    except OSError:
        pass

    # ref moze byc spakowany w packed-refs (czesty przypadek po swiezym klonie)
    try:
        for line in (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[1].strip() == ref:
                return parts[0].strip()
    except OSError:
        pass
    return None


def _read_date_from_git_log(root: Path) -> str | None:
    """Data ostatniego commita z .git/logs/HEAD (ostatnie pole to unix ts)."""
    try:
        lines = (root / ".git" / "logs" / "HEAD").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        parts = line.split()
        for token in reversed(parts):
            if token.isdigit() and len(token) >= 9:
                try:
                    ts = datetime.fromtimestamp(int(token), tz=timezone.utc)
                    return ts.strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    return None
    return None


def _from_subprocess(root: Path) -> tuple[str | None, str | None]:
    def run(args: list[str]) -> str | None:
        try:
            out = subprocess.run(args, cwd=str(root), capture_output=True,
                                 text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip() or None if out.returncode == 0 else None

    return (run(["git", "rev-parse", "HEAD"]),
            run(["git", "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d"]))


@lru_cache(maxsize=1)
def get_version(root: str | None = None) -> dict[str, str | None]:
    """Zwraca {"sha": "5ed5739"|None, "date": "2026-10-08"|None}.

    Wynik jest stabilny w obrebie procesu (lru_cache) — commit nie zmienia sie
    bez restartu aplikacji.
    """
    base = Path(root) if root else _ROOT

    sha = _read_sha_from_git_dir(base)
    date = _read_date_from_git_log(base)

    if sha is None or date is None:
        sub_sha, sub_date = _from_subprocess(base)
        sha = sha or sub_sha
        date = date or sub_date

    if sha is None:
        for key in ("STREAMLIT_COMMIT_SHA", "GIT_COMMIT", "GITHUB_SHA", "SOURCE_VERSION"):
            if os.environ.get(key):
                sha = os.environ[key]
                break

    return {"sha": sha[:7] if sha else None, "date": date}


def version_label() -> str:
    """Krotki tekst do stopki, np. "wersja 5ed5739 - 2026-10-08". Pusty gdy brak."""
    v = get_version()
    if not v["sha"]:
        return ""
    return "wersja %s%s" % (v["sha"], " · %s" % v["date"] if v["date"] else "")
