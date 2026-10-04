import asyncio
import json
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.main import app
from app.core.config import Settings
from app.models import Menu, MenuSection, MenuItem, ItemExplanation
from app.schemas.search import SearchIntent, SearchRequest, search_intent_schema
from app.services.ai.base import AIProvider, ProviderResult, ProviderError
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.search_interpreter import interpret_search
from app.services.search_service import filter_dishes

class Interpreter(AIProvider):
    name = "test"
    model = "test-model"
    def __init__(self, replies=None):
        self.replies = replies or [SearchIntent(ingredients=["chicken"],tags=["spicy"],max_price=Decimal("5000"),max_price_inclusive=False,currency="HUF").model_dump_json()]
        self.calls = []
    async def extract_menu(self,*args): raise AssertionError("No extraction during search")
    async def interpret_search(self,query,schema,instructions):
        self.calls.append((query,schema,instructions))
        result = self.replies[min(len(self.calls)-1,len(self.replies)-1)]
        if isinstance(result,Exception): raise result
        return ProviderResult(result,12,34)

@pytest.fixture
def catalog(database):
    with TestClient(app) as client, Session(database[0]) as session:
        menu = Menu(original_filename="Test.pdf",stored_filename=str(uuid4())+".pdf",content_type="application/pdf",status="processed")
        section = MenuSection(menu=menu,name="Main",display_order=0)
        session.add(menu)
        rows = [
            ("Csípős csirke",4590,"HUF",["Csirkemell","paprika"],["spicy"]),
            ("Chicken at limit",5000,"HUF",["chicken"],["spicy"]),
            ("Chicken EUR",10,"EUR",["chicken"],["spicy"]),
            ("Chicken unpriced",None,"HUF",["chicken"],["spicy"]),
            ("Chicken unknown currency",1,None,["chicken"],["spicy"]),
            ("Chicken inferred",4200,"HUF",["chicken"],[]),
            ("Chicken failed inference",4100,"HUF",["chicken"],[]),
            ("Champignon",1000,"HUF",["champignon"],[]),
            ("Hortobágyi húsos palacsinta",4590,"HUF",["marhahús","tejföl"],[]),
            ("Free coffee",0,"HUF",["coffee"],["coffee"]),
        ]
        items = []
        for i,(name,price,currency,ingredients,tags) in enumerate(rows):
            item = MenuItem(section=section,display_order=i,name=name,price=price,currency=currency,ingredients=ingredients,tags=tags)
            session.add(item); items.append(item)
        session.flush()
        for index,status in [(5,"ready"),(6,"failed")]:
            session.add(ItemExplanation(item_id=items[index].id,language="en",status=status,description="Spicy chicken.",tags=["spicy"],provider="test",model="test",prompt_version="test"))
        hidden = Menu(original_filename="Hidden.pdf",stored_filename=str(uuid4())+".pdf",content_type="application/pdf",status="failed")
        hidden_section = MenuSection(menu=hidden,name="Hidden",display_order=0)
        session.add(MenuItem(section=hidden_section,display_order=0,name="Hidden chicken",price=100,currency="HUF",ingredients=["chicken"],tags=["spicy"]))
        session.commit()
        yield client,str(menu.id)

def names(response): return [row["item"]["name"] for row in response.json()["results"]]

@pytest.mark.parametrize("value", [
    {"ingredients":[""]},{"ingredients":["%"]},{"ingredients":[1]},{"tags":["gluten-free"]},
    {"max_price":-1},{"max_price":"NaN"},{"max_price":"Infinity"},{"max_price":True},
    {"max_price":"10.001"},{"max_price":"10000000000"},{"currency":"huf"},
    {"min_price":10,"max_price":5},{"min_price":5,"max_price":5,"max_price_inclusive":False},
    {"record_ids":[str(uuid4())]},{"sql":"SELECT * FROM menu_items"},{"max_price_inclusive":"false"},
])
def test_intent_validation(value):
    with pytest.raises(ValidationError): SearchIntent.model_validate(value)

def test_query_and_deterministic_results(catalog):
    client,_ = catalog; provider = Interpreter()
    with patch("app.services.search_service.get_provider",return_value=provider):
        response = client.post("/api/search",json={"query":"I want spicy chicken under 5000 HUF."})
    assert response.status_code == 200,response.text
    assert set(names(response)) == {"Csípős csirke","Chicken inferred"}
    assert response.json()["intent"]["max_price"] == "5000"
    assert len(provider.calls) == 1 and provider.calls[0][0] == "I want spicy chicken under 5000 HUF."
    inferred = next(row for row in response.json()["results"] if row["item"]["name"] == "Chicken inferred")
    assert inferred["matched_inferred_tags"] == ["spicy"]
    source = next(row for row in response.json()["results"] if row["item"]["name"] == "Csípős csirke")
    assert source["matched_inferred_tags"] == []
    assert len(source["item"]["explanations"]) == 0

def test_price_currency_boundaries(catalog):
    client,_ = catalog
    def query(**filters): return client.post("/api/search",json={"filters":filters})
    assert "Chicken at limit" in names(query(max_price="5000",currency="HUF"))
    assert "Chicken at limit" not in names(query(max_price="5000",max_price_inclusive=False,currency="HUF"))
    assert names(query(min_price="5000",max_price="5000",currency="HUF")) == ["Chicken at limit"]
    assert "Chicken at limit" not in names(query(min_price="5000",min_price_inclusive=False,currency="HUF"))
    assert names(query(max_price="0",currency="HUF")) == ["Free coffee"]
    assert names(query(currency="EUR")) == ["Chicken EUR"]
    bounded = names(query(max_price="100000",currency="HUF"))
    assert "Chicken unpriced" not in bounded and "Chicken unknown currency" not in bounded
    response = query(max_price="5000").json()
    assert response["total"] == 0 and "currency" in response["clarification"]

def test_aliases_and_exact_ingredients(catalog):
    client,_ = catalog
    assert names(client.post("/api/search",json={"filters":{"ingredients":["beef","sour cream"]}})) == ["Hortobágyi húsos palacsinta"]
    assert names(client.post("/api/search",json={"filters":{"name":"hortobagyi"}})) == ["Hortobágyi húsos palacsinta"]
    assert names(client.post("/api/search",json={"filters":{"ingredients":["ham"]}})) == []
    assert names(client.post("/api/search",json={"filters":{"ingredients":["chicken","beef"]}})) == []
    assert names(client.post("/api/search",json={"filters":{"name":"%' OR 1=1 --"}})) == []
    assert "Hidden chicken" not in names(client.post("/api/search",json={"filters":{}}))

def test_pagination_and_ids_without_ai(catalog):
    client,menu_id = catalog
    with patch("app.services.search_service.get_provider",side_effect=AssertionError("No AI")):
        first = client.post("/api/search",json={"filters":{},"limit":3}).json()
        second = client.post("/api/search",json={"filters":first["intent"],"limit":3,"offset":3}).json()
        assert first["total"] == second["total"] == 10 and first["has_more"]
        assert not ({row["item"]["id"] for row in first["results"]} & {row["item"]["id"] for row in second["results"]})
        assert client.post("/api/search",json={"filters":{},"menu_id":str(uuid4())}).json()["total"] == 0
        assert client.post("/api/search",json={"filters":{},"menu_id":menu_id}).json()["total"] == 10
        assert client.post("/api/search",json={"filters":{},"offset":100}).json()["results"] == []

@pytest.mark.parametrize("unsupported",["allergy_safety","exclusions","location","nutrition","alternatives","other"])
def test_unsupported_never_returns_partial_matches(catalog,unsupported):
    provider = Interpreter([SearchIntent(ingredients=["chicken"],unsupported=[unsupported]).model_dump_json()])
    with patch("app.services.search_service.get_provider",return_value=provider):
        response = catalog[0].post("/api/search",json={"query":"unsupported constraints"}).json()
    assert response["clarification"] and response["results"] == []

def test_retry_validation():
    provider = Interpreter(["{}",SearchIntent(tags=["soup"]).model_dump_json()])
    assert asyncio.run(interpret_search(provider,"soup",1)).tags == ["soup"]
    assert len(provider.calls) == 2
    provider = Interpreter(['{"sql":"DROP TABLE menus"}'])
    with pytest.raises(ProviderError): asyncio.run(interpret_search(provider,"soup",1))
    assert len(provider.calls) == 2

def test_timeout():
    class Slow(Interpreter):
        async def interpret_search(self,*args): await asyncio.sleep(1)
    with pytest.raises(ProviderError) as error: asyncio.run(interpret_search(Slow(),"soup",0.001))
    assert error.value.status_code == 504

@pytest.mark.parametrize("adapter",[OpenAIProvider,AnthropicProvider])
def test_provider_contract(adapter):
    intent = SearchIntent(tags=["soup"]).model_dump_json()
    def respond(request):
        body = json.loads(request.content)
        if adapter == OpenAIProvider:
            assert body["text"]["format"]["name"] == "search_intent" and body["store"] is False
            content = body["input"][0]["content"]
            response = {"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":intent}]}]}
        else:
            content = body["messages"][0]["content"]
            response = {"stop_reason":"end_turn","content":[{"type":"text","text":intent}]}
        assert len(content) == 1 and content[0]["text"] == "soup"
        return httpx.Response(200,json=response)
    provider = adapter(Settings(menu_ai_model="test",openai_api_key="test",anthropic_api_key="test"),transport=httpx.MockTransport(respond))
    assert asyncio.run(interpret_search(provider,"soup",1)).tags == ["soup"]
    assert set(search_intent_schema()["required"]) == set(SearchIntent.model_fields)

@pytest.mark.parametrize("body",[{},{"query":" "},{"query":"x"*501},{"query":"soup","filters":{}},{"filters":{},"limit":51},{"filters":{},"offset":-1},{"filters":{},"menu_id":"invalid"}])
def test_request_validation(catalog,body):
    assert catalog[0].post("/api/search",json=body).status_code == 422

def test_config_empty_database_and_provider_errors(database):
    with TestClient(app) as client:
        assert client.post("/api/search",json={"filters":{}}).json()["total"] == 0
        response = client.post("/api/search",json={"query":"chicken"})
        assert response.status_code == 503 and "filters" in response.json()["detail"]
        with patch("app.services.search_service.get_provider",return_value=Interpreter([ProviderError("private provider detail")])):
            failed = client.post("/api/search",json={"query":"chicken"})
        assert failed.status_code == 502 and "private" not in failed.text

def test_database_error(database):
    from app.core.errors import ServiceError
    with TestClient(app),Session(database[0]) as session,patch.object(session,"scalars",side_effect=OperationalError("secret",{},Exception("credentials"))):
        with pytest.raises(ServiceError) as error: filter_dishes(SearchIntent(),SearchRequest(filters=SearchIntent()),session)
        assert error.value.status_code == 503 and "credentials" not in error.value.message

def test_tags_require_saved_metadata_not_incidental_words(catalog,database):
    from sqlalchemy import select
    client,_ = catalog
    with Session(database[0]) as session:
        item = session.scalar(select(MenuItem).where(MenuItem.name == "Chicken failed inference"))
        item.original_description = "Not spicy."
        session.commit()
    assert "Chicken failed inference" not in names(client.post("/api/search",json={"filters":{"tags":["spicy"]}}))
