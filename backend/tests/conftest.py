"""Test harness for the API.

Runs against SQLite in memory rather than Neon: the auth logic is plain SQL and
the suite has to be runnable offline, in a second, without touching the real
database. It also exercises a useful edge — SQLite hands back naive datetimes,
so anything assuming tz-aware values from Postgres fails here first.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.config import Settings, get_settings
from app.main import app
from app.models import Base, Household

ALLOWED = "simone@example.com"
STRANGER = "estraneo@example.com"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite://",
        environment="test",
        app_base_url="http://testserver",
        allowed_emails=[ALLOWED],
        brevo_api_key="",
        mail_from="",
        login_token_ttl_minutes=15,
        session_ttl_days=30,
        login_requests_per_hour=5,
    )


@pytest.fixture
def db_factory() -> Iterator[sessionmaker[DbSession]]:
    # StaticPool keeps one connection alive, which is what makes ":memory:"
    # survive across the several sessions a single request opens.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with factory() as seed:
        seed.add(Household(name="Wallet"))
        seed.commit()

    yield factory
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(db_factory) -> Iterator[DbSession]:
    """A session for assertions, separate from the one the app uses."""
    with db_factory() as session:
        yield session


@pytest.fixture
def sent_emails(monkeypatch) -> list[dict]:
    """Capture outgoing mail instead of sending it."""
    captured: list[dict] = []

    def fake_send(settings, *, to: str, link: str) -> None:
        captured.append({"to": to, "link": link})

    monkeypatch.setattr("app.api.auth.send_magic_link", fake_send)
    return captured


@pytest.fixture
def client(db_factory, settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_factory()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def signed_in(client, sent_emails) -> TestClient:
    """A client that has already been through the magic-link flow.

    Everything from M2 on sits behind a session, and repeating the four calls in
    every test would bury what each one is actually about.
    """
    client.post("/api/auth/request-link", json={"email": ALLOWED})
    link = sent_emails[-1]["link"]
    client.post("/api/auth/verify", json={"token": link.split("token=", 1)[1]})
    return client
