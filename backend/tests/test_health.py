"""M0 smoke tests: no database required, they only pin the contract of /api/health."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.db import normalize_database_url, redact_dsn
from app.main import app


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health_reports_missing_database_without_crashing(monkeypatch):
    monkeypatch.setattr(
        "app.config.Settings",
        lambda: Settings(database_url="", environment="test"),
    )

    response = TestClient(app).get("/api/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "not_configured"
    assert body["environment"] == "test"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgres://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
        (
            "postgresql://u:p@host/db?sslmode=require",
            "postgresql+psycopg://u:p@host/db?sslmode=require",
        ),
        (
            "postgresql+psycopg://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
    ],
)
def test_normalize_database_url_targets_psycopg3(given, expected):
    assert normalize_database_url(given) == expected


@pytest.mark.parametrize(
    "message",
    [
        'could not connect to postgresql+psycopg://wallet:hunter2@ep-x-pooler.neon.tech/neondb',
        "OperationalError: postgres://wallet:hunter2@host:5432/neondb?sslmode=require timed out",
    ],
)
def test_health_detail_never_carries_a_connection_string(message):
    """/api/health is public, and the driver quotes the URL it failed on.

    The password is the part that must never reach the page. This is the only
    reason redact_dsn exists, so it is the thing worth pinning.
    """
    redacted = redact_dsn(message)

    assert "hunter2" not in redacted
    assert "wallet:" not in redacted
    assert "[rimosso]" in redacted
