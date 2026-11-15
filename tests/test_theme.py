"""Tokeny szaty B — jedno zrodlo prawdy, bez zlotych ramek."""
import tomllib
from pathlib import Path

import pytest

from components import constants as c

ROOT = Path(__file__).resolve().parents[1]


def test_tokens():
    assert c.BG == "#0E1117"
    assert c.BG_CARD == "#151922"
    assert c.GOLD == "#D4B062"
    assert c.BORDER == "#232937"
    assert len(c.CHART_COLORS) == 8 and c.CHART_COLORS[0] == c.GOLD


def test_streamlit_theme_matches_tokens():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    th = cfg["theme"]
    assert th["backgroundColor"] == c.BG
    assert th["secondaryBackgroundColor"] == c.BG_CARD
    assert th["primaryColor"] == c.GOLD
    assert th["textColor"] == c.TEXT


@pytest.mark.xfail(strict=True, reason="Task 3")
def test_no_hardcoded_old_gold_in_ui_code():
    offenders = []
    for p in list((ROOT / "pages").rglob("*.py")) + list((ROOT / "components").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        if "#C9A84C" in src or "201,168,76" in src or "#141929" in src:
            offenders.append(p.relative_to(ROOT).as_posix())
    assert offenders == []
