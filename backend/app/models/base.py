from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for every model.

    Empty at M0: the first tables arrive with the login flow in M1. It exists
    already because Alembic's env.py needs some metadata to compare against,
    and an empty comparison is a valid one.
    """
