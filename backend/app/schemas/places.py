from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, HttpUrl

PlaceType = Literal["restaurant", "cafe", "bar"]
PlaceId = str

class NearbyQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    place_type: PlaceType = "restaurant"
    radius: int = Field(default=1500, ge=100, le=50000)

class Attribution(BaseModel):
    name: str
    url: HttpUrl | None = None

class Place(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,255}$")
    name: str = Field(min_length=1, max_length=1000)
    address: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category: PlaceType
    rating: float | None = Field(default=None, ge=0, le=5)
    price_level: int | None = Field(default=None, ge=0, le=4)
    provider: Literal["google"] = "google"
    attributions: list[Attribution] = Field(default_factory=list)

class NearbyResponse(BaseModel):
    places: list[Place]
    limit: int = 20
