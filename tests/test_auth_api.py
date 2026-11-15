"""components.auth po migracji: bez numerow stron, z publicznym API blokady."""
import components.auth as auth


def test_legacy_numbered_api_removed():
    assert not hasattr(auth, "FREE_PAGES")
    assert not hasattr(auth, "PAGE_INFO")
    assert not hasattr(auth, "require_premium")


def test_public_api_present():
    assert callable(auth.render_lock_screen)
    assert callable(auth.premium_teaser)
    assert callable(auth.is_premium)
