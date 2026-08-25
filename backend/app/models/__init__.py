"""SQLAlchemy models.

Every model is imported here so that Alembic's autogenerate sees the complete
metadata from a single import. At M0 there is only the base: the first tables
(household, app_user, login_token, session) arrive with M1.
"""

from app.models.base import Base

__all__ = ["Base"]
