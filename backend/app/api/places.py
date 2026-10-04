from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query, Response
from app.core.config import Settings, get_settings
from app.schemas.places import NearbyQuery, NearbyResponse, Place
from app.services.places_service import get_places_provider, nearby

router = APIRouter(prefix="/api/places", tags=["places"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]

@router.get("/config")
def config(settings: SettingsDependency, response: Response):
    response.headers["Cache-Control"] = "no-store"
    # This is deliberately a PUBLIC, referrer-restricted Maps JavaScript key.
    return {"maps_api_key": settings.maps_api_key, "maps_map_id": settings.maps_map_id}

@router.get("/nearby", response_model=NearbyResponse)
async def nearby_places(query: Annotated[NearbyQuery, Query()], settings: SettingsDependency, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return await nearby(query, get_places_provider(settings))

@router.get("/{place_id}", response_model=Place)
async def place_detail(place_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,255}$")], settings: SettingsDependency, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return await get_places_provider(settings).detail(place_id)
