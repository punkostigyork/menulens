import re
import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

ExplanationLanguage = Literal["en", "hu"]
Tag = Literal["Hungarian", "Italian", "meat", "poultry", "seafood", "pasta", "soup", "dessert", "coffee", "cocktail", "sweet", "savory", "spicy", "breakfast", "brunch"]


class ExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: ExplanationLanguage = "en"


class DishSource(BaseModel):
    name: str
    original_description: str | None
    ingredients: list[str]


class GeneratedExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    language: ExplanationLanguage
    description: str = Field(min_length=1, max_length=400)
    tags: list[Tag] = Field(max_length=5)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        if len(value.split()) > 70 or len(re.findall(r"[.!?](?:\s|$)", value)) > 2:
            raise ValueError("Use at most two short sentences")
        normalized = "".join(c for c in unicodedata.normalize("NFKD", value).casefold() if c.isalpha())
        # Defense in depth for common EN/HU safety claims; semantic guarantees still need evaluation.
        forbidden = ("glutenfree", "nutfree", "peanutfree", "dairyfree", "lactosefree", "allergenfree", "allergyfree", "allergysafe", "safeforallerg", "glutenmentes", "diomentes", "mogyoromentes", "tejmentes", "laktozmentes", "allergenmentes", "allergiabiztos")
        if any(claim in normalized for claim in forbidden):
            raise ValueError("Do not make dietary or allergy safety claims")
        return value

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, value):
        return list(dict.fromkeys(value))


def explanation_schema() -> dict:
    schema = GeneratedExplanation.model_json_schema()
    def simplify(value):
        if isinstance(value, list): return [simplify(item) for item in value]
        if not isinstance(value, dict): return value
        result = {k: simplify(v) for k, v in value.items() if k not in {"minLength", "maxLength", "maxItems", "title"}}
        if result.get("type") == "object": result["additionalProperties"] = False
        return result
    return simplify(schema)


class ExplanationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item_id: UUID
    language: ExplanationLanguage
    status: Literal["processing", "ready", "failed"]
    description: str | None
    tags: list[str]
    error_message: str | None
    created_at: datetime
