"""The auth rules, tested where they are pure: no database, no HTTP."""

from datetime import timedelta

import pytest

from app.domain import auth


def test_email_comparison_ignores_case_and_spaces():
    assert auth.normalize_email("  Mario@Example.COM ") == "mario@example.com"
    assert auth.is_allowed("MARIO@example.com", ["mario@example.com"])
    assert not auth.is_allowed("altro@example.com", ["mario@example.com"])


def test_tokens_are_stored_hashed_and_compared_in_constant_time():
    token = auth.generate_token()
    digest = auth.hash_token(token)

    # The clear token must not be recoverable from what we persist.
    assert token not in digest
    assert len(digest) == 64

    assert auth.tokens_match(token, digest)
    assert not auth.tokens_match(auth.generate_token(), digest)


def test_a_fresh_link_opens_and_a_spent_one_does_not():
    now = auth.utcnow()
    fresh = auth.LoginTokenState(expires_at=now + timedelta(minutes=15), used_at=None)
    fresh.check(now)  # does not raise

    spent = auth.LoginTokenState(expires_at=now + timedelta(minutes=15), used_at=now)
    with pytest.raises(auth.InvalidToken):
        spent.check(now)


def test_an_expired_link_does_not_open():
    now = auth.utcnow()
    expired = auth.LoginTokenState(expires_at=now - timedelta(seconds=1), used_at=None)

    with pytest.raises(auth.InvalidToken):
        expired.check(now)


def test_naive_datetimes_from_the_database_are_read_as_utc():
    """SQLite gives back naive datetimes; treating them as local would shift the
    expiry by whatever the machine's offset happens to be."""
    now = auth.utcnow()
    naive_future = (now + timedelta(minutes=10)).replace(tzinfo=None)

    assert not auth.is_expired(naive_future, now)


def test_a_revoked_session_is_never_active():
    now = auth.utcnow()
    live = auth.SessionState(expires_at=now + timedelta(days=30), revoked_at=None)
    revoked = auth.SessionState(expires_at=now + timedelta(days=30), revoked_at=now)

    assert live.is_active(now)
    assert not revoked.is_active(now)


def test_rate_limit_trips_at_the_ceiling_not_after_it():
    assert not auth.rate_limit_exceeded(4, 5)
    assert auth.rate_limit_exceeded(5, 5)


def test_magic_link_points_at_the_confirm_page():
    link = auth.build_magic_link("https://wallet.example.app/", "abc123")
    assert link == "https://wallet.example.app/accedi/conferma?token=abc123"
