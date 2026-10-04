"""Transient place discovery. Provider responses are never persisted or logged."""
from abc import ABC, abstractmethod
import asyncio
import logging
import httpx
from pydantic import ValidationError
from app.core.config import Settings
from app.core.errors import ServiceError
from app.schemas.places import Attribution, NearbyQuery, NearbyResponse, Place

logger = logging.getLogger(__name__)
FIELDS = "id,displayName,formattedAddress,location,primaryType,types,rating,priceLevel,attributions"
PRICES = {"PRICE_LEVEL_FREE": 0, "PRICE_LEVEL_INEXPENSIVE": 1, "PRICE_LEVEL_MODERATE": 2, "PRICE_LEVEL_EXPENSIVE": 3, "PRICE_LEVEL_VERY_EXPENSIVE": 4}

class PlacesProvider(ABC):
    @abstractmethod
    async def nearby(self, query: NearbyQuery) -> list[Place]: ...
    @abstractmethod
    async def detail(self, place_id: str) -> Place: ...


def normalize(raw: dict) -> Place:
    primary = raw.get("primaryType", "")
    types = raw.get("types", [])
    category = next((kind for kind in ("cafe", "bar", "restaurant") if primary == kind or primary.endswith("_" + kind)), None)
    category = category or next((kind for kind in ("restaurant", "cafe", "bar") if kind in types), None)
    if category is None:
        raise ServiceError(404, "This place is not a restaurant, cafe, or bar.")
    return Place(id=raw["id"], name=raw["displayName"]["text"], address=raw.get("formattedAddress", ""),
                 latitude=raw["location"]["latitude"], longitude=raw["location"]["longitude"], category=category,
                 rating=raw.get("rating"), price_level=PRICES.get(raw.get("priceLevel")),
                 attributions=[Attribution(name=a["provider"], url=a.get("providerUri") or None) for a in raw.get("attributions", [])])

class GooglePlacesProvider(PlacesProvider):
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def _request(self, method: str, path: str, mask: str, body=None) -> dict:
        key = self.settings.places_api_key.get_secret_value()
        if not key:
            raise ServiceError(503, "Nearby places are not configured yet. Please try again later.")
        try:
            async with asyncio.timeout(self.settings.places_timeout_seconds):
                async with httpx.AsyncClient(timeout=self.settings.places_timeout_seconds, transport=self.transport) as client:
                    async with client.stream(method, "https://places.googleapis.com/v1/" + path,
                                             headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": mask}, json=body) as response:
                        if response.status_code == 404:
                            raise ServiceError(404, "This place could not be found.")
                        if response.status_code == 429:
                            raise ServiceError(503, "Nearby places are busy. Please try again shortly.")
                        if response.status_code >= 400:
                            raise ServiceError(502, "Nearby places are unavailable. Please try again later.")
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > 1048576:
                                raise ValueError("oversized response")
                        import json
                        data = json.loads(content)
                        if not isinstance(data, dict):
                            raise ValueError("invalid response")
                        return data
        except (TimeoutError, httpx.TimeoutException):
            raise ServiceError(504, "Finding nearby places took too long. Please try again.") from None
        except (httpx.HTTPError, ValueError):
            raise ServiceError(502, "Nearby places are unavailable. Please try again later.") from None

    async def nearby(self, query: NearbyQuery) -> list[Place]:
        raw = await self._request("POST", "places:searchNearby", ",".join("places." + f for f in FIELDS.split(",")), {
            "includedTypes": [query.place_type], "maxResultCount": 20, "rankPreference": "DISTANCE",
            "locationRestriction": {"circle": {"center": {"latitude": query.latitude, "longitude": query.longitude}, "radius": query.radius}},
        })
        try:
            rows = raw.get("places", [])
            if not isinstance(rows, list) or len(rows) > 20:
                raise ValueError("invalid places")
            return list({p.id: p for p in (normalize(row) for row in rows)}.values())
        except (KeyError, TypeError, AttributeError, ValueError, ValidationError, ServiceError):
            raise ServiceError(502, "We couldn't read nearby places. Please try again.") from None

    async def detail(self, place_id: str) -> Place:
        raw = await self._request("GET", "places/" + place_id, FIELDS)
        try:
            place = normalize(raw)
            if place.id != place_id:
                raise ValueError("mismatched place")
            return place
        except (KeyError, TypeError, AttributeError, ValueError, ValidationError):
            raise ServiceError(502, "We couldn't read this place. Please try again.") from None


def get_places_provider(settings: Settings) -> PlacesProvider:
    return GooglePlacesProvider(settings)

async def nearby(query: NearbyQuery, provider: PlacesProvider) -> NearbyResponse:
    logger.info("places_search_started")
    try:
        places = await provider.nearby(query)
    except ServiceError:
        logger.warning("places_search_failed")
        raise
    logger.info("places_search_completed", extra={"result_count": len(places)})
    return NearbyResponse(places=places)
