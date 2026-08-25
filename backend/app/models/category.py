from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    """What a movement was for.

    ⚠️ Two separate lists, one per sign (`kind`). "Stipendio" must not turn up
    among the spending categories, and no chart may put the two in the same pie.
    The unique index is on (household, kind, lower(name)): without the lower(),
    "Bar" and "bar" coexist and become two slices of the same thing.

    ⚠️ Categories are archived, never deleted: past movements point at them, and
    the month-on-month comparison reads them. Archived means it can no longer be
    chosen and still appears in the charts of the past.

    `color` holds a **token name** (`chart-1` … `chart-6`), not a hex. If the
    design retunes a series every category follows without a data migration, and
    the promise that no colour is written outside tokens.css survives.

    `icon` holds a Lucide name from the curated list in domain/vocabulary.py.
    """

    __tablename__ = "category"
    __table_args__ = (
        # Unique per household *and per sign*: "Regalo" is a legitimate name on
        # both lists — one is a present you bought, the other money you were
        # given. Case-insensitive, or "Bar" and "bar" become two slices of the
        # same pie.
        Index(
            "uq_category_household_kind_name",
            "household_id",
            "kind",
            text("lower(name)"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
    icon: Mapped[str] = mapped_column(String(40), nullable=False)

    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
