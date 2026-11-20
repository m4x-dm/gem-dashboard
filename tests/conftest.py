"""Wspolne fixture'y testow."""
import pytest


@pytest.fixture(autouse=True)
def _no_fundamentals_snapshot(monkeypatch):
    """Testy nie siegaja po dzienny zrzut z GitHuba (data/fundamentals_snapshot.py).

    Test, ktory sprawdza zrzut, podstawia go sam (fs.set_for_tests) albo usuwa te zmienna.
    """
    monkeypatch.setenv("GEM_FUNDAMENTALS_SNAPSHOT", "0")
    from data import fundamentals_snapshot as fs
    fs.reset()
    yield
    fs.reset()
