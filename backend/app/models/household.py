from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Household(Base, TimestampMixin):
    """The space everything hangs off.

    There is exactly one row, and today exactly one user in it. It exists as a
    table anyway for two reasons: every account, category and transaction will
    carry household_id, and inventing that key later would touch every model —
    and the day the app is shared with someone else, nothing has to move.

    Settings that are about the money rather than about the person live here
    (the monthly saving target arrives with M4), because `user.preferences` is
    personal and must not change the numbers someone else sees.
    """

    __tablename__ = "household"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="household")  # noqa: F821
