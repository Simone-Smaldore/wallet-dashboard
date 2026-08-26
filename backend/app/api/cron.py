"""The daily job, as an endpoint, because that is how Vercel schedules things.

⚠️ **Outside the session, and therefore behind a secret.** A cron has no cookie
and no user; Vercel calls the URL with `Authorization: Bearer $CRON_SECRET`. If
the variable is not set the route refuses everything — an open endpoint that
writes to the database is not something to leave to a default.

⚠️ It answers with counts and never with amounts. A cron log is the least
protected place this system writes to, and "quanto vale il tuo patrimonio" is
not something to put in one.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbDep, SettingsDep
from app.models import Household
from app.prices.refresh import refresh

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.get("/prices")
def daily_prices(
    db: DbDep,
    settings: SettingsDep,
    authorization: str | None = Header(default=None),
) -> dict[str, int]:
    """Refresh every automatically-priced asset. Runs once a day."""
    _authorise(settings.cron_secret, authorization)

    updated = 0
    failed = 0
    for household in db.scalars(select(Household)):
        for outcome in refresh(db, household.id):
            if outcome.ok:
                updated += 1
            else:
                failed += 1
    db.commit()

    # ⚠️ Failures are reported, not swallowed. A run that says only what worked
    # cannot be told apart from a run that did nothing.
    return {"updated": updated, "failed": failed}


def _authorise(secret: str, header: str | None) -> None:
    if not secret:
        # No secret configured means no scheduled writes. Refusing is the safe
        # default; the alternative is a public endpoint that touches the data.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET non configurato",
        )

    expected = f"Bearer {secret}"
    # Constant time: the comparison is against a secret, and a timing difference
    # is a slow way of reading it.
    if header is None or not hmac.compare_digest(header, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non autorizzato")
