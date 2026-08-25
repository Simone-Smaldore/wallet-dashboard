from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.vocabulary import CategoryKind, is_known_color, is_known_icon


class CategoryBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", check_fields=False)
    @classmethod
    def trim(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("color", check_fields=False)
    @classmethod
    def known_color(cls, value: str | None) -> str | None:
        """A colour outside the palette is a colour no chart knows how to draw.

        The value is a token name (`chart-3`), not a hex: the design owns the
        actual colour, and this only records which of its six series was chosen.
        """
        if value is not None and not is_known_color(value):
            raise ValueError("Colore fuori dalla palette del design system")
        return value

    @field_validator("icon", check_fields=False)
    @classmethod
    def known_icon(cls, value: str | None) -> str | None:
        """Only from the curated list: the frontend imports those icons by name,
        so one outside it would render as nothing at all."""
        if value is not None and not is_known_icon(value):
            raise ValueError("Icona fuori dall'elenco previsto")
        return value


class CategoryCreate(CategoryBase):
    name: str = Field(min_length=1, max_length=120)
    kind: CategoryKind
    color: str = Field(max_length=20)
    icon: str = Field(max_length=40)


class CategoryUpdate(CategoryBase):
    """Partial. ⚠️ `kind` is missing on purpose: a spending category cannot
    become an income one. Movements already point at it, and flipping the sign
    would move past amounts from one side of every chart to the other."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = Field(default=None, max_length=20)
    icon: str | None = Field(default=None, max_length=40)
    position: int | None = Field(default=None, ge=0)
    is_archived: bool | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    kind: CategoryKind
    color: str
    icon: str
    position: int
    is_archived: bool
