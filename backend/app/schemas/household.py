from pydantic import BaseModel, ConfigDict, Field


class HouseholdOut(BaseModel):
    """The settings that are about the money rather than about the person.

    ⚠️ Separate from `/api/auth/me` on purpose. Preferences are personal — a
    remembered account, a collapsed panel — and the day this app is shared, a
    personal preference must not be able to change the numbers the other person
    sees. A savings target changes numbers, so it lives here.
    """

    id: int
    name: str
    #: Null means "not set", which is not the same as zero: a target of zero
    #: would show a bar that is full for the wrong reason.
    monthly_savings_target_cents: int | None
    #: Which income category counts as the salary. Null: not chosen yet.
    salary_category_id: int | None


class HouseholdUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: Explicitly nullable: sending null is how you say "forget the target",
    #: which is a real instruction and not the same as leaving the field out.
    monthly_savings_target_cents: int | None = Field(default=None, ge=0)
    salary_category_id: int | None = None
