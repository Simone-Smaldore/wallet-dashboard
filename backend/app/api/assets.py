"""The assets: what an investment account actually holds.

⚠️ An asset is not a movement and does not pretend to be one. Liquidity is
recorded — you type what happened — while an investment is *valued*: a quantity
you rarely touch and a price that moves on its own. The two live side by side,
and the account's balance (capital paid in) and the asset's valuation (what it
is worth) are both shown, because they are both true and neither is the other.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import CurrentUserDep, DbDep
from app.domain.assets import value_cents
from app.domain.vocabulary import AccountKind, PriceSource, TransactionKind
from app.models import Account, Asset, AssetValuation, Transaction
from app.prices import Quote, borsa_italiana, coingecko
from app.prices.refresh import refresh
from app.schemas.asset import (
    AssetCreate,
    AssetPurchase,
    AssetOut,
    AssetUpdate,
    PriceProbe,
    PriceProbeResult,
    RefreshResult,
)

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetOut])
def list_assets(user: CurrentUserDep, db: DbDep) -> list[AssetOut]:
    assets = db.scalars(
        select(Asset).where(Asset.household_id == user.household_id).order_by(Asset.name)
    ).all()
    return [_to_schema(db, asset) for asset in assets]


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, user: CurrentUserDep, db: DbDep) -> AssetOut:
    _check_account(db, user.household_id, payload.account_id)
    _refuse_duplicate(db, user.household_id, payload.name)

    asset = Asset(
        household_id=user.household_id,
        account_id=payload.account_id,
        name=payload.name,
        kind=payload.kind.value,
        quantity=payload.quantity,
        price_basis=payload.price_basis.value,
        source=payload.source.value,
        source_ref=payload.source_ref,
        opened_at=payload.opened_at,
        notes=payload.notes,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _to_schema(db, asset)


@router.patch("/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: int, payload: AssetUpdate, user: CurrentUserDep, db: DbDep
) -> AssetOut:
    asset = _get_owned(db, user.household_id, asset_id)
    provided = payload.model_fields_set

    if "name" in provided and payload.name is not None:
        _refuse_duplicate(db, user.household_id, payload.name, excluding=asset.id)
        asset.name = payload.name
    if "account_id" in provided and payload.account_id is not None:
        _check_account(db, user.household_id, payload.account_id)
        asset.account_id = payload.account_id
    if "kind" in provided and payload.kind is not None:
        asset.kind = payload.kind.value
    if "quantity" in provided and payload.quantity is not None:
        asset.quantity = payload.quantity
    if "price_basis" in provided and payload.price_basis is not None:
        asset.price_basis = payload.price_basis.value
    if "source" in provided and payload.source is not None:
        asset.source = payload.source.value
    if "source_ref" in provided:
        asset.source_ref = payload.source_ref
    if "closed_at" in provided:
        asset.closed_at = payload.closed_at
    if "notes" in provided:
        asset.notes = payload.notes

    db.commit()
    db.refresh(asset)
    return _to_schema(db, asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: int, user: CurrentUserDep, db: DbDep) -> None:
    """⚠️ Closing is usually what you want, not deleting.

    A sold holding still explains a year of the net-worth curve; deleting it
    rewrites that history. This exists for the one you created by mistake five
    minutes ago.
    """
    db.delete(_get_owned(db, user.household_id, asset_id))
    db.commit()


@router.post("/{asset_id}/buy", response_model=AssetOut)
def buy(
    asset_id: int, payload: AssetPurchase, user: CurrentUserDep, db: DbDep
) -> AssetOut:
    """Record a purchase: the money leaves a bank account, the quantity grows.

    This is the gesture that happens every month — 80 € into the ETF — and it is
    two facts at once.

    ⚠️ **Both, or neither.** Doing them as two calls from the screen would mean
    one of them can land alone: money moved with no shares to show for it, or
    shares from nowhere. Neither would raise anything, both numbers would look
    plausible, and the gain would quietly become fiction. One commit is the only
    honest shape.

    ⚠️ The money side is a **transfer**, not a spend. Buying is not consumption:
    the net worth must not move, and the spending pie must not see it. What it
    does do is leave the current account, so the month's budget loses it — see
    stats.savings_month.
    """
    asset = _get_owned(db, user.household_id, asset_id)

    source = db.get(Account, payload.from_account_id)
    if source is None or source.household_id != user.household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conto non trovato")
    if source.id == asset.account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="I soldi devono uscire da un altro conto",
        )

    db.add(
        Transaction(
            household_id=user.household_id,
            kind=TransactionKind.TRANSFER.value,
            date=payload.date,
            amount_cents=payload.amount_cents,
            account_id=source.id,
            counter_account_id=asset.account_id,
            description=payload.description or f"Acquisto {asset.name}",
            created_by_user_id=user.id,
        )
    )
    # Added, never replaced: you tell the app what you bought, it keeps the
    # total. Making you type the new total is making you do the arithmetic this
    # app exists to do.
    asset.quantity = asset.quantity + payload.quantity

    db.commit()
    db.refresh(asset)
    return _to_schema(db, asset)


@router.post("/probe", response_model=PriceProbeResult)
def probe(payload: PriceProbe, user: CurrentUserDep, db: DbDep) -> PriceProbeResult:
    """Ask a source for a price right now, without saving anything.

    ⚠️ This is the whole reason the asset form has a "prova adesso" button. A
    mistyped ISIN is otherwise invisible: nothing errors, the daily job simply
    finds nothing, and you notice three weeks later because a number never
    moved. Better to find out while you are still looking at the field.
    """
    quote = _probe(payload)
    if quote is None:
        return PriceProbeResult(found=False)

    return PriceProbeResult(
        found=True,
        unit_price_cents=quote.unit_price_cents,
        date=quote.date,
        value_cents=(
            value_cents(payload.quantity, quote.unit_price, payload.price_basis)
            if payload.quantity is not None
            else None
        ),
    )


@router.post("/refresh", response_model=RefreshResult)
def refresh_now(user: CurrentUserDep, db: DbDep) -> RefreshResult:
    """Run the daily update by hand, from the app."""
    outcomes = refresh(db, user.household_id)
    db.commit()
    return RefreshResult(
        lines=[f"{'ok' if o.ok else '—'} {o.asset}: {o.detail}" for o in outcomes]
    )


def _probe(payload: PriceProbe) -> Quote | None:
    if not payload.source_ref:
        return None
    if payload.source is PriceSource.COINGECKO:
        return coingecko.fetch(payload.source_ref)
    if payload.source is PriceSource.BORSA_ITALIANA:
        return borsa_italiana.fetch(payload.source_ref, kind_hint=payload.kind)
    return None


def _get_owned(db: DbSession, household_id: int, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None or asset.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset non trovato")
    return asset


def _check_account(db: DbSession, household_id: int, account_id: int) -> None:
    """⚠️ It has to be an investment account.

    An asset inside a current account would make that account's balance mean two
    things at once — the money in it and the value of something else — which is
    the one thing this model exists to keep apart.
    """
    account = db.get(Account, account_id)
    if account is None or account.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conto non trovato")
    if account.kind != AccountKind.INVESTIMENTO.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Un asset sta in un conto di tipo investimento",
        )


def _refuse_duplicate(
    db: DbSession, household_id: int, name: str, *, excluding: int | None = None
) -> None:
    clash = db.scalar(
        select(Asset).where(Asset.household_id == household_id, Asset.name == name.strip())
    )
    if clash is not None and clash.id != excluding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Esiste già un asset chiamato {clash.name}",
        )


def latest_valuations(db: DbSession, household_id: int) -> dict[int, AssetValuation]:
    """The newest valuation of each asset, keyed by asset id.

    ⚠️ The **latest**, not an average and not the first: the net worth is what
    things are worth now. Loaded in one pass so the summary does not run a query
    per holding.
    """
    rows = db.execute(
        select(AssetValuation)
        .join(Asset, Asset.id == AssetValuation.asset_id)
        .where(Asset.household_id == household_id)
        .order_by(AssetValuation.asset_id, AssetValuation.date)
    ).scalars()

    newest: dict[int, AssetValuation] = {}
    for valuation in rows:
        newest[valuation.asset_id] = valuation
    return newest


def _to_schema(db: DbSession, asset: Asset) -> AssetOut:
    latest = db.scalar(
        select(AssetValuation)
        .where(AssetValuation.asset_id == asset.id)
        .order_by(AssetValuation.date.desc())
        .limit(1)
    )
    return AssetOut(
        id=asset.id,
        account_id=asset.account_id,
        name=asset.name,
        kind=asset.kind,
        quantity=asset.quantity,
        price_basis=asset.price_basis,
        source=asset.source,
        source_ref=asset.source_ref,
        opened_at=asset.opened_at,
        closed_at=asset.closed_at,
        notes=asset.notes,
        value_cents=latest.value_cents if latest else None,
        unit_price_cents=latest.unit_price_cents if latest else None,
        valued_on=latest.date if latest else None,
    )
