from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserPreferences(BaseModel):
    """Personal interface settings.

    No key is declared yet: inventing preferences before the screen that needs
    them would be guessing. The mechanism is what matters — when one is needed,
    it is a single typed field added here, with a default, and no migration.

    `extra="allow"` keeps keys this version does not know about. That way a
    newer frontend can store something before the backend is redeployed, and a
    rollback does not silently drop what the user had set.

    ⚠️ Anything about the money rather than the person — the monthly saving
    target, the default account — belongs on Household, not here.
    """

    model_config = ConfigDict(extra="allow")


class UserProfile(BaseModel):
    """The signed-in user as the app shows them."""

    id: int
    email: str
    display_name: str | None
    # Pre-computed so the frontend never repeats the "name or else email" rule.
    label: str
    preferences: dict[str, Any]
    household_id: int
    household_name: str


class UpdateProfile(BaseModel):
    """A partial update: omitted fields are left alone.

    `display_name` accepts null explicitly, which means "go back to showing my
    email" — distinct from omitting the field, which means "do not touch it".
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=120)
    preferences: UserPreferences | None = None

    @field_validator("display_name")
    @classmethod
    def blank_becomes_null(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        # An empty box means "remove my name", not "my name is a space".
        return trimmed or None
