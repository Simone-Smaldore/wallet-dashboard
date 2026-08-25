"""Outgoing email.

Brevo's transactional endpoint is a single JSON POST, so it goes through
urllib rather than pulling an HTTP client into the runtime dependencies —
the smaller requirements.txt stays, the fewer compiled wheels have to line up
with whatever Python version Vercel is on this month.

Everything funnels through send_magic_link(), so swapping provider later means
editing one function.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.config import Settings
from app.mail import templates

logger = logging.getLogger(__name__)

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"
TIMEOUT_SECONDS = 10

# Brevo sits behind Cloudflare, which rejects urllib's default
# "Python-urllib/3.x" signature with a 403 "browser_signature_banned" on most
# endpoints. Any honest identifier gets through; leaving the default does not.
# There is a regression test on this header, because it is invisible and easy
# to lose in a rewrite.
USER_AGENT = "wallet/0.1 (+https://github.com/Simone-Smaldore/wallet-dashboard)"


class EmailNotSent(RuntimeError):
    """The provider refused the message."""


def send_magic_link(settings: Settings, *, to: str, link: str) -> None:
    minutes = settings.login_token_ttl_minutes

    if not settings.brevo_api_key or not settings.mail_from:
        _print_to_console(to=to, link=link, minutes=minutes)
        return

    payload = {
        "sender": {"email": settings.mail_from, "name": settings.mail_from_name},
        "to": [{"email": to}],
        "subject": templates.SUBJECT,
        "textContent": templates.magic_link_text(link, minutes),
        "htmlContent": templates.magic_link_html(link, minutes),
    }

    request = urllib.request.Request(
        BREVO_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": settings.brevo_api_key,
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            if response.status >= 300:
                raise EmailNotSent(f"Brevo ha risposto {response.status}")
    except urllib.error.HTTPError as exc:
        # Read the body: Brevo explains refusals (unverified sender, bad key)
        # there, and without it the failure is impossible to diagnose remotely.
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise EmailNotSent(
            f"Brevo ha risposto {exc.code}: {detail}{_hint(exc.code, detail, settings)}"
        ) from exc
    except urllib.error.URLError as exc:
        raise EmailNotSent(f"Brevo irraggiungibile: {exc.reason}") from exc


def _hint(code: int, body: str, settings: Settings) -> str:
    """Turn Brevo's refusal into the thing to actually go and fix.

    These three account for essentially every failure, and each one otherwise
    reads as an opaque status code in a log nobody is watching.
    """
    if "browser_signature_banned" in body:
        return (
            "\n  -> Cloudflare ha bloccato la richiesta: manca uno user-agent "
            "esplicito nella chiamata."
        )
    if code == 401:
        return (
            "\n  -> Chiave rifiutata. Serve una chiave API v3 (prefisso 'xkeysib-'); "
            "quelle SMTP ('xsmtpsib-') non valgono per questo endpoint."
        )
    if code == 400 and "sender" in body.lower():
        return (
            f"\n  -> MAIL_FROM ({settings.mail_from}) non risulta verificato su Brevo. "
            "Aggiungilo in Senders e conferma il link che ti arriva."
        )
    return ""


def _print_to_console(*, to: str, link: str, minutes: int) -> None:
    """Development fallback: no key configured, so show the link on the terminal.

    This is the whole reason local development does not need a Brevo account.
    """
    logger.warning(
        "\n"
        "  ---------------------------------------------------------------\n"
        "  Nessuna BREVO_API_KEY: email non inviata.\n"
        "  Destinatario: %s\n"
        "  Link di accesso (valido %d minuti):\n"
        "\n"
        "    %s\n"
        "  ---------------------------------------------------------------\n",
        to,
        minutes,
        link,
    )
