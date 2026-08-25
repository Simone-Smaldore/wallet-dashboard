"""The household: the settings that belong to the money, not to the person.

Today that is one field, the monthly savings target. It has its own router
rather than riding along on `/api/auth/me` because the distinction matters: the
day this app is shared, someone else's preference must not be able to move the
numbers you look at. This is also where a default account and a currency will
land when they exist.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, DbDep
from app.domain.vocabulary import CategoryKind
from app.models import Category, Household
from app.schemas.household import HouseholdOut, HouseholdUpdate

router = APIRouter(prefix="/api/household", tags=["household"])


@router.get("", response_model=HouseholdOut)
def read_household(user: CurrentUserDep, db: DbDep) -> Household:
    return _get(db, user.household_id)


@router.patch("", response_model=HouseholdOut)
def update_household(
    payload: HouseholdUpdate, user: CurrentUserDep, db: DbDep
) -> Household:
    """⚠️ Sending an explicit null clears the target; leaving the field out does
    nothing at all. "I no longer want a target" is an instruction, and it has to
    be distinguishable from "I am not talking about the target"."""
    household = _get(db, user.household_id)

    if "monthly_savings_target_cents" in payload.model_fields_set:
        household.monthly_savings_target_cents = payload.monthly_savings_target_cents

    if "salary_category_id" in payload.model_fields_set:
        _check_salary_category(db, user.household_id, payload.salary_category_id)
        household.salary_category_id = payload.salary_category_id

    db.commit()
    db.refresh(household)
    return household


def _check_salary_category(db, household_id: int, category_id: int | None) -> None:
    """It has to be an income category, and it has to be yours.

    ⚠️ A spending category here would make every cycle start on a grocery run.
    The rule is refused at the door rather than left to produce nonsense
    downstream, where it would look like a bug in the arithmetic.
    """
    if category_id is None:
        return

    category = db.get(Category, category_id)
    if category is None or category.household_id != household_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria non trovata"
        )
    if category.kind != CategoryKind.INCOME.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Lo stipendio è un'entrata: scegli una categoria di entrata",
        )


def _get(db, household_id: int) -> Household:
    household = db.get(Household, household_id)
    if household is None:
        # Only reachable if the row a live session points at has been deleted.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Household non trovato"
        )
    return household
