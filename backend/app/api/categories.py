"""The categories.

Two lists that never mix: one for what goes out, one for what comes in.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import CurrentUserDep, DbDep
from app.domain.vocabulary import CATEGORY_COLORS, DEFAULT_CATEGORY_ICON
from app.models import Category
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(user: CurrentUserDep, db: DbDep) -> list[Category]:
    return list(
        db.scalars(
            select(Category)
            .where(Category.household_id == user.household_id)
            # Expenses first, then income; archived last within each group. The
            # screen shows them as two blocks and never interleaves the signs.
            .order_by(
                Category.kind,
                Category.is_archived,
                Category.position,
                func.lower(Category.name),
            )
        ).all()
    )


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, user: CurrentUserDep, db: DbDep) -> Category:
    _refuse_duplicate(db, user.household_id, payload.kind.value, payload.name)

    highest = db.scalar(
        select(func.max(Category.position)).where(
            Category.household_id == user.household_id,
            Category.kind == payload.kind.value,
        )
    )

    category = Category(
        household_id=user.household_id,
        name=payload.name,
        kind=payload.kind.value,
        color=payload.color or _next_color(db, user.household_id),
        icon=payload.icon or DEFAULT_CATEGORY_ICON,
        position=(highest or 0) + 1,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, payload: CategoryUpdate, user: CurrentUserDep, db: DbDep
) -> Category:
    category = get_owned(db, user.household_id, category_id)
    provided = payload.model_fields_set

    if "name" in provided and payload.name is not None:
        _refuse_duplicate(
            db, user.household_id, category.kind, payload.name, excluding=category.id
        )
        # Renaming propagates everywhere by itself: movements point at the row,
        # they do not carry a copy of the name.
        category.name = payload.name

    if "color" in provided and payload.color is not None:
        category.color = payload.color
    if "icon" in provided and payload.icon is not None:
        category.icon = payload.icon
    if "position" in provided and payload.position is not None:
        category.position = payload.position
    if "is_archived" in provided and payload.is_archived is not None:
        category.is_archived = payload.is_archived

    db.commit()
    db.refresh(category)
    return category


def _next_color(db: DbSession, household_id: int) -> str:
    """The least used colour of the palette, ties broken by palette order.

    Six colours and more categories than that means repeats are inevitable; what
    is avoidable is two categories created one after the other coming out
    identical, which is exactly when you would be looking at them together.
    """
    used = list(
        db.scalars(select(Category.color).where(Category.household_id == household_id)).all()
    )
    return min(CATEGORY_COLORS, key=lambda color: (used.count(color), CATEGORY_COLORS.index(color)))


def get_owned(db: DbSession, household_id: int, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None or category.household_id != household_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria non trovata"
        )
    return category


def _refuse_duplicate(
    db: DbSession,
    household_id: int,
    kind: str,
    name: str,
    *,
    excluding: int | None = None,
) -> None:
    """Unique per household *and per sign*, case-insensitively.

    Per sign, because "Regalo" is a legitimate name on both lists: one is a
    present you bought, the other is money someone gave you. Case-insensitively,
    because "Bar" and "bar" would become two slices of the same pie.
    """
    clash = db.scalar(
        select(Category).where(
            Category.household_id == household_id,
            Category.kind == kind,
            func.lower(Category.name) == name.strip().lower(),
        )
    )
    if clash is not None and clash.id != excluding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Esiste già una categoria chiamata {clash.name}",
        )
