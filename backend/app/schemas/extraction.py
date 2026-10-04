from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Name = Annotated[str, Field(min_length=1, max_length=255)]
Ingredient = Annotated[str, Field(min_length=1, max_length=120)]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class ExtractionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ExtractedItem(ExtractionModel):
    name: Name
    price: Decimal | None = Field(default=None, ge=0, le=Decimal("9999999999.99"), max_digits=12, decimal_places=2)
    currency: Currency | None = None
    original_description: str | None = Field(default=None, max_length=4000)
    ingredients: list[Ingredient] = Field(default_factory=list, max_length=50)

    @field_validator("price", mode="before")
    @classmethod
    def reject_boolean_price(cls, value):
        if isinstance(value, bool):
            raise ValueError("price must be a number, not a boolean")
        return value


class ExtractedSection(ExtractionModel):
    name: Name
    items: list[ExtractedItem] = Field(min_length=1, max_length=500)


class ExtractedMenu(ExtractionModel):
    restaurant_name: Name | None = None
    currency: Currency | None = None
    language: str | None = Field(default=None, min_length=2, max_length=20)
    sections: list[ExtractedSection] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def limit_total_items(self):
        if sum(len(section.items) for section in self.sections) > 1000:
            raise ValueError("too many menu items")
        return self


def provider_schema() -> dict:
    # Shared supported subset; full constraints remain enforced locally.
    unsupported = {"default", "title", "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems", "pattern"}
    def simplify(value):
        if isinstance(value, list): return [simplify(item) for item in value]
        if not isinstance(value, dict): return value
        result = {key: simplify(item) for key, item in value.items() if key not in unsupported}
        if result.get("type") == "object":
            result["additionalProperties"] = False
            result["required"] = list(result.get("properties", {}))
        return result
    schema = simplify(ExtractedMenu.model_json_schema())
    schema["$defs"]["ExtractedItem"]["properties"]["price"] = {"anyOf": [{"type": "number"}, {"type": "null"}]}
    return schema
