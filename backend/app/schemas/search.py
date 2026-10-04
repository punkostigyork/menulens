from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from app.schemas.explanation import Tag
from app.schemas.menu_item import MenuItemRead

Term = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Money = Annotated[Decimal, Field(ge=0, le=Decimal("9999999999.99"), max_digits=12, decimal_places=2, allow_inf_nan=False)]
Unsupported = Literal["allergy_safety", "exclusions", "location", "nutrition", "alternatives", "other"]


class SearchIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ingredients: list[Term] = Field(default_factory=list, max_length=8)
    tags: list[Tag] = Field(default_factory=list, max_length=5)
    name: Term | None = None
    min_price: Money | None = None
    max_price: Money | None = None
    min_price_inclusive: bool = Field(default=True, strict=True)
    max_price_inclusive: bool = Field(default=True, strict=True)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    unsupported: list[Unsupported] = Field(default_factory=list, max_length=6)

    @field_validator("min_price", "max_price", mode="before")
    @classmethod
    def numeric_price(cls, value):
        if isinstance(value, bool): raise ValueError("Price must be numeric")
        return value

    @field_validator("ingredients", "tags", "unsupported")
    @classmethod
    def unique_terms(cls, value):
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def valid_range(self):
        if any(not any(char.isalnum() for char in term) for term in [*self.ingredients, *([self.name] if self.name else [])]):
            raise ValueError("Search terms must contain letters or numbers")
        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price or (self.min_price == self.max_price and not (self.min_price_inclusive and self.max_price_inclusive)):
                raise ValueError("Price range is empty")
        return self


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str | None = Field(default=None, min_length=1, max_length=500)
    filters: SearchIntent | None = None
    menu_id: UUID | None = None
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=2147483647)

    @model_validator(mode="after")
    def one_input(self):
        if (self.query is None) == (self.filters is None):
            raise ValueError("Provide either a query or filters")
        return self


class SearchMatch(BaseModel):
    item: MenuItemRead
    menu_id: UUID
    menu_title: str
    section_name: str
    matched_inferred_tags: list[str]


class SearchResponse(BaseModel):
    intent: SearchIntent
    results: list[SearchMatch]
    total: int
    limit: int
    offset: int
    has_more: bool
    clarification: str | None = None


def search_intent_schema() -> dict:
    def simplify(value):
        if isinstance(value, list): return [simplify(item) for item in value]
        if not isinstance(value, dict): return value
        result = {key: simplify(item) for key, item in value.items() if key not in {"default", "title", "minLength", "maxLength", "maxItems", "pattern", "minimum", "maximum"}}
        if result.get("type") == "object":
            result["additionalProperties"] = False
            result["required"] = list(result["properties"])
        return result
    schema = simplify(SearchIntent.model_json_schema())
    for name in ("min_price", "max_price"):
        schema["properties"][name] = {"anyOf": [{"type": "number"}, {"type": "null"}]}
    return schema
