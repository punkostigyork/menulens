from typing import Annotated, Literal
from pydantic import BaseModel, Field, computed_field


class TextPage(BaseModel):
    page_number: int = Field(ge=1)
    kind: Literal["text"] = "text"
    text: str = Field(min_length=1)


class ImagePage(BaseModel):
    page_number: int = Field(ge=1)
    kind: Literal["image"] = "image"
    media_type: Literal["image/png"] = "image/png"
    data_base64: str = Field(min_length=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    extracted_text: str = ""


class PreparedDocument(BaseModel):
    """Provider-neutral input; ordered pages retain their original page numbers."""
    page_count: int = Field(ge=1)
    pages: list[Annotated[TextPage | ImagePage, Field(discriminator="kind")]] = Field(min_length=1)
    skipped_blank_pages: list[int] = Field(default_factory=list)

    @computed_field
    @property
    def mode(self) -> Literal["text", "images", "mixed"]:
        kinds = {page.kind for page in self.pages}
        return "mixed" if len(kinds) > 1 else "text" if "text" in kinds else "images"
