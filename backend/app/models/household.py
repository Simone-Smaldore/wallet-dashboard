from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Household(Base, TimestampMixin):
    """The space everything hangs off.

    There is exactly one row, and today exactly one user in it. It exists as a
    table anyway for two reasons: every account, category and transaction will
    carry household_id, and inventing that key later would touch every model —
    and the day the app is shared with someone else, nothing has to move.

    Settings that are about the money rather than about the person live here,
    because `user.preferences` is personal and must not change the numbers
    someone else sees.
    """

    __tablename__ = "household"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    #: How much you mean to put aside in a month.
    #:
    #: ⚠️ Nullable, and null means "I have not set one" — which is a different
    #: statement from a target of zero, and the screen says so instead of
    #: showing a bar that is full for the wrong reason.
    #:
    #: A column and not a table: there is one value, and past months are judged
    #: against the current one. A deliberate simplification — the day the history
    #: of the target matters this becomes a table with `valid_from`, and past
    #: months stop changing their verdict every time you raise the bar.
    monthly_savings_target_cents: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    #: Which income category is the salary.
    #:
    #: ⚠️ The savings goal is judged salary to salary, not month to month —
    #: money arrives on a day that is not the first, and what matters is whether
    #: November's salary was still partly there when December's landed. So the
    #: app has to know which movement *is* a salary, and it is told rather than
    #: guessing: "any income" would let a 10 € refund open a cycle, and "the
    #: biggest income of the month" would move the boundaries the month you sell
    #: something expensive, without saying so.
    #:
    #: Null means not chosen yet, and the screen asks instead of assuming.
    #: ⚠️ `use_alter`: category points at household and this points back, so
    #: the two tables cannot be created — or dropped — in any single order. The
    #: constraint is added on its own afterwards, which is exactly what the
    #: migration does too.
    salary_category_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "category.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_household_salary_category",
        ),
        nullable=True,
    )

    users: Mapped[list["User"]] = relationship(back_populates="household")  # noqa: F821
