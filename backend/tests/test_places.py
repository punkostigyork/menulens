import asyncio
import json
from unittest.mock import patch
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from app.main import app
from app.core.config import Settings
from app.core.errors import ServiceError
from app.schemas.places import NearbyQuery
from app.services.places_service import GooglePlacesProvider

RAW = {"id":"ChIJ_test", "displayName":{"text":"Test café"}, "formattedAddress":"Budapest", "location":{"latitude":47.5,"longitude":19.04}, "primaryType":"cafe", "types":["cafe","restaurant"], "rating":4.7,"priceLevel":"PRICE_LEVEL_MODERATE", "attributions":[{"provider":"Example","providerUri":"https://example.com"}]}

def provider(handler):
    return GooglePlacesProvider(Settings(places_api_key=SecretStr("test-private-key")), transport=httpx.MockTransport(handler))

def test_nearby_route_normalizes_and_keeps_keys_private(database):
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json={"places":[RAW]})
    with TestClient(app) as client, patch("app.api.places.get_places_provider",return_value=provider(handler)):
        response=client.get("/api/places/nearby",params={"latitude":47.5,"longitude":19.04,"place_type":"cafe","radius":500})
    assert response.status_code==200
    assert response.headers["cache-control"]=="no-store"
    place=response.json()["places"][0]
    assert place=={"id":"ChIJ_test","name":"Test café","address":"Budapest","latitude":47.5,"longitude":19.04,"category":"cafe","rating":4.7,"price_level":2,"provider":"google","attributions":[{"name":"Example","url":"https://example.com/"}]}
    assert "test-private-key" not in response.text
    request=requests[0]
    assert str(request.url)=="https://places.googleapis.com/v1/places:searchNearby"
    assert request.headers["X-Goog-Api-Key"]=="test-private-key"
    assert "*" not in request.headers["X-Goog-FieldMask"]
    body=json.loads(request.content)
    assert body["includedTypes"]==["cafe"]
    assert body["rankPreference"]=="DISTANCE"
    assert body["locationRestriction"]["circle"]["radius"]==500

@pytest.mark.parametrize("changes",[{"latitude":91},{"latitude":"nan"},{"longitude":181},{"longitude":"inf"},{"radius":99},{"radius":50001},{"radius":1.5},{"place_type":"hotel"},{"unexpected":1}])
def test_query_validation_precedes_provider(database,changes):
    with TestClient(app) as client, patch("app.api.places.get_places_provider") as factory:
        response=client.get("/api/places/nearby",params={"latitude":47.5,"longitude":19.04,**changes})
    assert response.status_code==422
    factory.assert_not_called()

def test_config_only_exposes_public_maps_settings(database):
    settings=database[1]
    settings.places_api_key=SecretStr("private-places")
    settings.openai_api_key=SecretStr("private-ai")
    settings.maps_api_key="public-browser"
    with TestClient(app) as client:
        response=client.get("/api/places/config")
    assert response.json()=={"maps_api_key":"public-browser","maps_map_id":"DEMO_MAP_ID"}
    assert "private" not in response.text

def test_missing_config_is_safe(database):
    with TestClient(app) as client:
        response=client.get("/api/places/nearby?latitude=0&longitude=0")
    assert response.status_code==503
    assert "not configured" in response.json()["detail"]

def test_detail_and_bad_ids(database):
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json=RAW)
    with TestClient(app) as client, patch("app.api.places.get_places_provider",return_value=provider(handler)):
        response=client.get("/api/places/ChIJ_test")
        assert response.status_code==200
        assert response.json()["category"]=="cafe"
        assert client.get("/api/places/bad%20id").status_code==422
        assert client.get("/api/places/"+"a"*256).status_code==422
    assert len(requests)==1
    assert requests[0].method=="GET"
    assert requests[0].url.path=="/v1/places/ChIJ_test"
    assert requests[0].headers["X-Goog-FieldMask"].startswith("id,")

@pytest.mark.parametrize("status,expected",[(401,502),(403,502),(429,503),(500,502),(404,404)])
def test_provider_failures_do_not_expose_body(status,expected):
    instance=provider(lambda r:httpx.Response(status,text="secret credential and provider internals"))
    with pytest.raises(ServiceError) as error:
        asyncio.run(instance.nearby(NearbyQuery(latitude=0,longitude=0)))
    assert error.value.status_code==expected
    assert "secret" not in error.value.message

@pytest.mark.parametrize("data",[{"places":None},{"places":[{}]},{"places":[{**RAW,"rating":6}]},{"places":[{**RAW,"location":{"latitude":999,"longitude":0}}]},{"places":[{**RAW,"attributions":[{"provider":"x","providerUri":"javascript:alert(1)"}]}]},[RAW],{"places":[RAW]*21}])
def test_bad_payload(data):
    instance=provider(lambda r:httpx.Response(200,json=data))
    with pytest.raises(ServiceError) as error:
        asyncio.run(instance.nearby(NearbyQuery(latitude=0,longitude=0)))
    assert error.value.status_code==502

def test_empty_optional_fields_and_duplicates():
    raw={k:v for k,v in RAW.items() if k not in {"rating","priceLevel","attributions","formattedAddress"}}
    instance=provider(lambda r:httpx.Response(200,json={"places":[raw,raw]}))
    rows=asyncio.run(instance.nearby(NearbyQuery(latitude=0,longitude=0)))
    assert len(rows)==1 and rows[0].rating is None and rows[0].price_level is None
    empty=provider(lambda r:httpx.Response(200,json={}))
    assert asyncio.run(empty.nearby(NearbyQuery(latitude=0,longitude=0)))==[]

def test_timeout_network_and_size():
    def timeout(r): raise httpx.ReadTimeout("secret timeout")
    def network(r): raise httpx.ConnectError("secret network")
    for handler,status in [(timeout,504),(network,502),(lambda r:httpx.Response(200,content=b"x"*1048577),502)]:
        with pytest.raises(ServiceError) as error:
            asyncio.run(provider(handler).nearby(NearbyQuery(latitude=0,longitude=0)))
        assert error.value.status_code==status
        assert "secret" not in error.value.message

def test_detail_wrong_place_and_non_food():
    for raw,status in [({**RAW,"id":"other"},502),({**RAW,"primaryType":"hotel","types":["hotel"]},404)]:
        with pytest.raises(ServiceError) as error:
            asyncio.run(provider(lambda r:httpx.Response(200,json=raw)).detail("ChIJ_test"))
        assert error.value.status_code==status


def test_access_logs_omit_coordinates():
    import logging
    from app.core.logging import RedactQueryFilter
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %s', ("127.0.0.1", "GET", "/api/places/nearby?latitude=47.5&longitude=19.04", "1.1", 200), None)
    assert RedactQueryFilter().filter(record)
    assert "/api/places/nearby" in record.getMessage()
    assert "latitude" not in record.getMessage() and "47.5" not in record.getMessage()
