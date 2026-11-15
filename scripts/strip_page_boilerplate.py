"""Jednorazowa migracja 2026-11-15: usuwa z plikow stron boilerplate,
ktory przejal router (app.py): set_page_config, setup_sidebar(), require_premium.

Uzycie: python scripts/strip_page_boilerplate.py pages/etf/ranking.py [...]
"""
import re
import sys
from pathlib import Path

PATTERNS = [
    # st.set_page_config(...) jedno- lub wieloliniowe
    (re.compile(r"^st\.set_page_config\(.*?\)\n", re.S | re.M), ""),
    # setup_sidebar() jako osobna linia
    (re.compile(r"^setup_sidebar\(\)\n", re.M), ""),
    # if not require_premium(N): st.stop()   (jedna linia)
    (re.compile(r"^if not require_premium\(\d+\):\s*st\.stop\(\)\n", re.M), ""),
    # if not require_premium(N):\n    st.stop()
    (re.compile(r"^if not require_premium\(\d+\):\n\s+st\.stop\(\)\n", re.M), ""),
    # import require_premium
    (re.compile(r"^from components\.auth import require_premium\n", re.M), ""),
]


def strip_sidebar_import(src: str) -> str:
    """Usun setup_sidebar z listy importu components.sidebar (zachowaj reszte)."""
    def fix(m: re.Match) -> str:
        names = [n.strip() for n in m.group(1).split(",") if n.strip() != "setup_sidebar"]
        return f"from components.sidebar import {', '.join(names)}\n" if names else ""
    return re.sub(r"^from components\.sidebar import (.+)\n", fix, src, flags=re.M)


def main(paths: list[str]) -> None:
    for path in paths:
        p = Path(path)
        src = p.read_text(encoding="utf-8")
        new = src
        for pattern, repl in PATTERNS:
            new = pattern.sub(repl, new)
        new = strip_sidebar_import(new)
        if new != src:
            p.write_text(new, encoding="utf-8")
            print(f"OK   {path}")
        else:
            print(f"SKIP {path} (bez zmian)")


if __name__ == "__main__":
    main(sys.argv[1:])
