"""Testy components/version.py — wskaznik wdrozonej wersji w stopce."""
import os
import subprocess

import pytest

from components.version import (
    _read_date_from_git_log,
    _read_sha_from_git_dir,
    get_version,
    version_label,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_sha_zgadza_sie_z_gitem():
    """SHA czytany z .git musi byc tym samym, co zwraca `git rev-parse`."""
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                         capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("brak gita w srodowisku")
    assert _read_sha_from_git_dir(__import__("pathlib").Path(REPO)) == out.stdout.strip()


def test_get_version_zwraca_krotki_sha_i_date():
    v = get_version()
    assert set(v) == {"sha", "date"}
    if v["sha"] is not None:
        assert len(v["sha"]) == 7
        assert all(c in "0123456789abcdef" for c in v["sha"])
    if v["date"] is not None:
        assert len(v["date"]) == 10 and v["date"][4] == "-" and v["date"][7] == "-"


def test_brak_repozytorium_nie_wywala_tylko_zwraca_none(tmp_path):
    """Na hostingu bez .git aplikacja ma dzialac, po prostu bez wersji."""
    from pathlib import Path
    assert _read_sha_from_git_dir(tmp_path) is None
    assert _read_date_from_git_log(tmp_path) is None
    assert isinstance(Path(tmp_path), Path)


def test_packed_refs_jest_obslugiwane(tmp_path):
    """Swiezy klon trzyma refy w packed-refs, nie w .git/refs/heads/."""
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    sha = "a" * 40
    (git / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted\n"
        f"{sha} refs/heads/main\n", encoding="utf-8")
    assert _read_sha_from_git_dir(tmp_path) == sha


def test_detached_head(tmp_path):
    """HEAD moze zawierac goly SHA zamiast ref:."""
    git = tmp_path / ".git"
    git.mkdir()
    sha = "b" * 40
    (git / "HEAD").write_text(sha + "\n", encoding="utf-8")
    assert _read_sha_from_git_dir(tmp_path) == sha


def test_gitdir_pointer_file(tmp_path):
    """.git moze byc plikiem wskazujacym katalog (worktree)."""
    real = tmp_path / "realgit"
    real.mkdir()
    sha = "c" * 40
    (real / "HEAD").write_text(sha + "\n", encoding="utf-8")
    (tmp_path / ".git").write_text("gitdir: %s\n" % real, encoding="utf-8")
    assert _read_sha_from_git_dir(tmp_path) == sha


def test_version_label_pusty_gdy_brak_sha(monkeypatch):
    """Pusty label => stopka nie renderuje wiersza z wersja."""
    monkeypatch.setattr("components.version.get_version",
                        lambda *a, **k: {"sha": None, "date": None})
    assert version_label() == ""


def test_version_label_format(monkeypatch):
    monkeypatch.setattr("components.version.get_version",
                        lambda *a, **k: {"sha": "5ed5739", "date": "2026-10-08"})
    assert version_label() == "wersja 5ed5739 · 2026-10-08"


def test_version_label_bez_daty(monkeypatch):
    monkeypatch.setattr("components.version.get_version",
                        lambda *a, **k: {"sha": "5ed5739", "date": None})
    assert version_label() == "wersja 5ed5739"
