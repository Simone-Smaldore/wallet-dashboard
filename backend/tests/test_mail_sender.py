"""Regression tests on the Brevo call.

The header assertion below looks trivial and is not: without an explicit
user-agent Cloudflare answers 403 browser_signature_banned to urllib's default
signature, and every magic link fails silently. It is invisible in the payload
and easy to drop while tidying up, which is exactly why it is pinned here.
"""

import json

import pytest

from app.config import Settings
from app.mail import sender


@pytest.fixture
def configured() -> Settings:
    return Settings(
        brevo_api_key="xkeysib-finta",
        mail_from="io@example.com",
        mail_from_name="Wallet",
        login_token_ttl_minutes=15,
    )


class _Response:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_the_request_carries_an_explicit_user_agent(monkeypatch, configured):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["headers"] = {k.lower(): v for k, v in request.headers.items()}
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr(sender.urllib.request, "urlopen", fake_urlopen)

    sender.send_magic_link(configured, to="tu@example.com", link="https://x/y?token=t")

    assert captured["headers"]["user-agent"] == sender.USER_AGENT
    assert "python-urllib" not in captured["headers"]["user-agent"].lower()
    assert captured["headers"]["api-key"] == "xkeysib-finta"


def test_the_email_carries_the_link_and_nothing_about_money(monkeypatch, configured):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr(sender.urllib.request, "urlopen", fake_urlopen)

    sender.send_magic_link(configured, to="tu@example.com", link="https://x/y?token=t")

    body = captured["body"]
    assert body["to"] == [{"email": "tu@example.com"}]
    assert "https://x/y?token=t" in body["textContent"]
    # The euro sign would mean an amount slipped into the least protected
    # channel this system has.
    assert "€" not in body["textContent"]
    assert "€" not in body["htmlContent"]


def test_without_a_key_the_link_goes_to_the_terminal(monkeypatch, caplog):
    """This fallback is the whole reason local development needs no Brevo account."""
    unconfigured = Settings(brevo_api_key="", mail_from="")

    def explode(*args, **kwargs):
        raise AssertionError("non deve chiamare Brevo senza chiave")

    monkeypatch.setattr(sender.urllib.request, "urlopen", explode)

    with caplog.at_level("WARNING"):
        sender.send_magic_link(unconfigured, to="tu@example.com", link="https://x/y?t=1")

    assert "https://x/y?t=1" in caplog.text


def test_a_refusal_explains_what_to_go_and_fix(configured):
    """Brevo answers with status codes; the log has to say what to do about them."""
    assert "user-agent" in sender._hint(403, "browser_signature_banned", configured)
    assert "xkeysib-" in sender._hint(401, "", configured)
    assert "Senders" in sender._hint(400, "invalid sender", configured)
