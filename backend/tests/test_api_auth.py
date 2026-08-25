"""The magic-link flow end to end, against SQLite."""

from datetime import timedelta

from sqlalchemy import select

from app.api.deps import SESSION_COOKIE
from app.domain import auth as domain
from app.models import LoginToken, Session, User
from tests.conftest import ALLOWED, STRANGER


def _link_for(sent_emails: list[dict]) -> str:
    return sent_emails[-1]["link"]


def _token_from(link: str) -> str:
    return link.split("token=", 1)[1]


def test_request_link_answers_the_same_to_everyone(client, sent_emails):
    """⚠️ The rule that must never break.

    An allowed address, a stranger and a rate-limited caller all get the same
    status and the same body. Anything else turns this endpoint into a way to
    find out who has access to someone's finances.
    """
    allowed = client.post("/api/auth/request-link", json={"email": ALLOWED})
    stranger = client.post("/api/auth/request-link", json={"email": STRANGER})

    assert allowed.status_code == stranger.status_code == 200
    assert allowed.json() == stranger.json()

    # And only the allowed address actually caused an email.
    assert [mail["to"] for mail in sent_emails] == [ALLOWED]


def test_rate_limited_requests_look_identical_too(client, sent_emails, settings):
    for _ in range(settings.login_requests_per_hour):
        client.post("/api/auth/request-link", json={"email": ALLOWED})
    before = len(sent_emails)

    limited = client.post("/api/auth/request-link", json={"email": ALLOWED})

    assert limited.status_code == 200
    assert limited.json() == {
        "message": "Se l'indirizzo è abilitato riceverai un link fra pochi istanti."
    }
    # The answer is the same, but nothing was sent.
    assert len(sent_emails) == before


def test_full_sign_in_flow(client, sent_emails, db):
    client.post("/api/auth/request-link", json={"email": ALLOWED})
    token = _token_from(_link_for(sent_emails))

    verified = client.post("/api/auth/verify", json={"token": token})
    assert verified.status_code == 200
    body = verified.json()
    assert body["email"] == ALLOWED
    # Until a name is set, the label falls back to the address — a rule the
    # frontend must never have to repeat.
    assert body["label"] == ALLOWED

    assert client.cookies.get(SESSION_COOKIE)

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]

    # The clear token is nowhere in the database.
    stored = db.scalars(select(LoginToken)).all()
    assert all(token not in row.token_hash for row in stored)


def test_a_link_works_only_once(client, sent_emails):
    client.post("/api/auth/request-link", json={"email": ALLOWED})
    token = _token_from(_link_for(sent_emails))

    assert client.post("/api/auth/verify", json={"token": token}).status_code == 200

    replayed = client.post("/api/auth/verify", json={"token": token})
    assert replayed.status_code == 400


def test_an_expired_link_is_refused(client, sent_emails, db):
    client.post("/api/auth/request-link", json={"email": ALLOWED})
    token = _token_from(_link_for(sent_emails))

    record = db.scalar(
        select(LoginToken).where(LoginToken.token_hash == domain.hash_token(token))
    )
    record.expires_at = domain.utcnow() - timedelta(seconds=1)
    db.commit()

    assert client.post("/api/auth/verify", json={"token": token}).status_code == 400


def test_an_invented_token_is_refused(client):
    response = client.post("/api/auth/verify", json={"token": "x" * 40})
    assert response.status_code == 400


def test_me_requires_a_session(client):
    assert client.get("/api/auth/me").status_code == 401


def test_profile_update_is_partial(client, sent_emails):
    client.post("/api/auth/request-link", json={"email": ALLOWED})
    client.post("/api/auth/verify", json={"token": _token_from(_link_for(sent_emails))})

    named = client.patch("/api/auth/me", json={"display_name": "  Simone  "})
    assert named.json()["display_name"] == "Simone"
    assert named.json()["label"] == "Simone"

    # Saving a preference must not touch the name.
    with_pref = client.patch("/api/auth/me", json={"preferences": {"tema": "scuro"}})
    assert with_pref.json()["display_name"] == "Simone"
    assert with_pref.json()["preferences"] == {"tema": "scuro"}

    # A second screen saving its own setting must not wipe the first one.
    merged = client.patch("/api/auth/me", json={"preferences": {"altro": 1}})
    assert merged.json()["preferences"] == {"tema": "scuro", "altro": 1}

    # Explicit null means "drop my name", which is not the same as omitting it.
    cleared = client.patch("/api/auth/me", json={"display_name": None})
    assert cleared.json()["display_name"] is None
    assert cleared.json()["label"] == ALLOWED


def test_unknown_profile_fields_are_refused(client, sent_emails):
    client.post("/api/auth/request-link", json={"email": ALLOWED})
    client.post("/api/auth/verify", json={"token": _token_from(_link_for(sent_emails))})

    # extra="forbid": a misspelled field fails loudly instead of vanishing.
    response = client.patch("/api/auth/me", json={"displayName": "Simone"})
    assert response.status_code == 422


def test_logout_revokes_only_this_browser(client, sent_emails, db):
    client.post("/api/auth/request-link", json={"email": ALLOWED})
    client.post("/api/auth/verify", json={"token": _token_from(_link_for(sent_emails))})

    # A second session, as if from another device.
    user = db.scalar(select(User).where(User.email == ALLOWED))
    other = Session(
        user_id=user.id,
        token_hash=domain.hash_token("altro-dispositivo"),
        expires_at=domain.expiry_from(domain.utcnow(), days=30),
    )
    db.add(other)
    db.commit()

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    db.refresh(other)
    assert other.revoked_at is None


def test_logout_all_revokes_every_session(client, sent_emails, db):
    client.post("/api/auth/request-link", json={"email": ALLOWED})
    client.post("/api/auth/verify", json={"token": _token_from(_link_for(sent_emails))})

    user = db.scalar(select(User).where(User.email == ALLOWED))
    other = Session(
        user_id=user.id,
        token_hash=domain.hash_token("telefono-perso"),
        expires_at=domain.expiry_from(domain.utcnow(), days=30),
    )
    db.add(other)
    db.commit()

    assert client.post("/api/auth/logout-all").status_code == 204

    db.refresh(other)
    assert other.revoked_at is not None
