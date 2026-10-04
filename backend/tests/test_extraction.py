import asyncio
import json
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4
import httpx
import pymupdf
import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.main import app
from app.models import Menu, MenuSection, MenuItem, MenuExtraction
from app.core.config import Settings
from app.core.errors import ServiceError
from app.schemas.document import PreparedDocument, TextPage, ImagePage
from app.schemas.extraction import ExtractedMenu, provider_schema
from app.services.ai.base import AIProvider, ProviderResult, ProviderError
from app.services.ai.menu_extractor import extract_menu, ExtractionStats
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.factory import get_provider
from app.services.extraction_service import start_extraction, recover_interrupted

DATA = {"restaurant_name": "Teszt Étterem", "currency": "HUF", "language": "hu", "sections": [{"name": "Levesek", "items": [{"name": "Gulyásleves", "price": 2990, "currency": None, "original_description": "marhahús, paprika", "ingredients": ["marhahús", "paprika"]}]}]}
DOCUMENT = PreparedDocument(page_count=1, pages=[TextPage(page_number=1, text="Gulyásleves 2990 HUF marhahús paprika")])


class FakeProvider(AIProvider):
    name = "test"
    model = "fixture-model"
    def __init__(self, results=None):
        self.results = results or [json.dumps(DATA)]
        self.calls = []
    async def extract_menu(self, document, schema, instructions):
        self.calls.append((document, schema, instructions))
        result = self.results[min(len(self.calls) - 1, len(self.results) - 1)]
        if isinstance(result, Exception): raise result
        return ProviderResult(result, 100, 50)


def upload(client):
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((30, 40), "Hungarian menu Gulyasleves 2990 HUF marhahus paprika")
        body = doc.tobytes()
    result = client.post("/api/menus", files={"file": ("menu.pdf", body, "application/pdf")})
    assert result.status_code == 201, result.text
    return result.json()["id"]


def test_schema_preserves_decimal_and_accents():
    menu = ExtractedMenu.model_validate_json(json.dumps(DATA))
    assert menu.sections[0].items[0].price == Decimal("2990")
    assert menu.sections[0].items[0].name == "Gulyásleves"


@pytest.mark.parametrize("price", [-1, True, "NaN", "Infinity", "3.456", 10000000000])
def test_invalid_prices(price):
    data = json.loads(json.dumps(DATA))
    data["sections"][0]["items"][0]["price"] = price
    with pytest.raises(ValidationError): ExtractedMenu.model_validate(data)


@pytest.mark.parametrize("change", ["empty", "empty_name", "extra", "currency", "ingredients"])
def test_schema_rejects_bad_content(change):
    data = json.loads(json.dumps(DATA))
    if change == "empty": data["sections"] = []
    if change == "empty_name": data["sections"][0]["items"][0]["name"] = "   "
    if change == "extra": data["sections"][0]["items"][0]["allergy_safe"] = True
    if change == "currency": data["currency"] = "forint"
    if change == "ingredients": data["sections"][0]["items"][0]["ingredients"] = [""]
    with pytest.raises(ValidationError): ExtractedMenu.model_validate(data)


def test_validation_retries_once_and_records_usage():
    provider = FakeProvider(["not JSON", json.dumps(DATA)])
    stats = ExtractionStats()
    result = asyncio.run(extract_menu(provider, DOCUMENT, 1, stats))
    assert result.currency == "HUF" and stats.attempts == 2
    assert stats.input_tokens == 200 and stats.output_tokens == 100
    assert "previous result failed" in provider.calls[1][2]


def test_invalid_twice_stops():
    provider = FakeProvider(["{}"])
    stats = ExtractionStats()
    with pytest.raises(ProviderError): asyncio.run(extract_menu(provider, DOCUMENT, 1, stats))
    assert len(provider.calls) == 2


def test_timeout_is_bounded():
    class Slow(FakeProvider):
        async def extract_menu(self, *args): await asyncio.sleep(1)
    with pytest.raises(ProviderError) as error:
        asyncio.run(extract_menu(Slow(), DOCUMENT, 0.001, ExtractionStats()))
    assert error.value.status_code == 504


@pytest.mark.parametrize("provider_type", [OpenAIProvider, AnthropicProvider])
def test_real_adapter_contracts(provider_type):
    requests = []
    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if provider_type == OpenAIProvider:
            assert request.url == "https://api.openai.com/v1/responses"
            assert request.headers["Authorization"] == "Bearer test-key"
            assert payload["store"] is False
            assert payload["text"]["format"]["strict"] is True
            assert any(part["type"] == "input_image" for part in payload["input"][0]["content"])
            return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(DATA)}]}], "usage": {"input_tokens": 111, "output_tokens": 222}})
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert payload["output_config"]["format"]["type"] == "json_schema"
        assert any(part["type"] == "image" for part in payload["messages"][0]["content"])
        return httpx.Response(200, json={"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(DATA)}], "usage": {"input_tokens": 111, "output_tokens": 222}})
    settings = Settings(openai_api_key="test-key", anthropic_api_key="test-key", menu_ai_model="test-model")
    provider = provider_type(settings, transport=httpx.MockTransport(respond))
    document = PreparedDocument(page_count=2, pages=[DOCUMENT.pages[0], ImagePage(page_number=2, data_base64="test-image", width=10, height=10)])
    result = asyncio.run(provider.extract_menu(document, provider_schema(), "Extract source only."))
    assert result.input_tokens == 111 and result.output_tokens == 222
    assert ExtractedMenu.model_validate_json(result.content).currency == "HUF"
    assert requests[0]["model"] == "test-model"


@pytest.mark.parametrize("provider_type", [OpenAIProvider, AnthropicProvider])
@pytest.mark.parametrize("failure", ["rate_limit", "timeout", "malformed", "incomplete", "refusal"])
def test_provider_failures_are_clean(provider_type, failure):
    def respond(request):
        if failure == "rate_limit": return httpx.Response(429, text="secret-provider-details")
        if failure == "timeout": raise httpx.ReadTimeout("secret-provider-details")
        if failure == "malformed": return httpx.Response(200, json={"content": 7, "output": 7, "status": "completed", "stop_reason": "end_turn"})
        if failure == "refusal": return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "secret"}]}], "stop_reason": "refusal"})
        return httpx.Response(200, json={"status": "incomplete", "stop_reason": "max_tokens"})
    provider = provider_type(Settings(menu_ai_model="test"), transport=httpx.MockTransport(respond))
    with pytest.raises(ProviderError) as error:
        asyncio.run(provider.extract_menu(DOCUMENT, provider_schema(), "test"))
    assert "secret" not in str(error.value)


def test_successful_processing_persists_and_is_idempotent(database):
    engine, _ = database
    provider = FakeProvider()
    with TestClient(app) as client, patch("app.services.extraction_service.get_provider", return_value=provider):
        menu_id = upload(client)
        response = client.post(f"/api/menus/{menu_id}/process")
        assert response.status_code == 202, response.text
        menu = client.get(f"/api/menus/{menu_id}").json()
        assert menu["status"] == "processed" and menu["processed_at"]
        assert menu["restaurant_name"] == "Teszt Étterem"
        item = client.get(f"/api/menus/{menu_id}/items").json()[0]
        assert item["name"] == "Gulyásleves" and Decimal(item["price"]) == Decimal("2990")
        assert item["ingredients"] == ["marhahús", "paprika"]
        assert item["tags"] == [] and item["dietary_info"] == [] and item["generated_description"] is None
        assert item["currency"] == "HUF" and item["language"] == "hu"
        client.post(f"/api/menus/{menu_id}/process")
        assert len(provider.calls) == 1
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(MenuItem)) == 1
            record = session.scalar(select(MenuExtraction))
            assert record.attempts == 1 and record.prompt_version == "menu-extract-v1"


def test_failed_validation_then_explicit_retry(database):
    engine, _ = database
    provider = FakeProvider(["{}", "{}", json.dumps(DATA)])
    with TestClient(app) as client, patch("app.services.extraction_service.get_provider", return_value=provider):
        menu_id = upload(client)
        client.post(f"/api/menus/{menu_id}/process")
        menu = client.get(f"/api/menus/{menu_id}").json()
        assert menu["status"] == "failed" and menu["processing_error"]
        assert menu["sections"] == []
        assert len(provider.calls) == 2
        client.post(f"/api/menus/{menu_id}/process")
        assert client.get(f"/api/menus/{menu_id}").json()["status"] == "processed"
        assert len(provider.calls) == 3


def test_provider_error_marks_failed(database):
    with TestClient(app) as client, patch("app.services.extraction_service.get_provider", return_value=FakeProvider([ProviderError("Please try again.")])):
        menu_id = upload(client)
        client.post(f"/api/menus/{menu_id}/process")
        result = client.get(f"/api/menus/{menu_id}").json()
        assert result["status"] == "failed" and result["processing_error"] == "Please try again."


def test_missing_config_leaves_upload_untouched(database):
    with TestClient(app) as client:
        menu_id = upload(client)
        assert client.post(f"/api/menus/{menu_id}/process").status_code == 503
        assert client.get(f"/api/menus/{menu_id}").json()["status"] == "uploaded"
        assert client.post(f"/api/menus/{uuid4()}/process").status_code == 404


def test_duplicate_starts_queue_one_job_and_restart_recovers(database):
    engine, settings = database
    with TestClient(app) as client:
        menu_id = upload(client)
        from uuid import UUID
        tasks = BackgroundTasks()
        with patch("app.services.extraction_service.get_provider", return_value=FakeProvider()), Session(engine) as session:
            start_extraction(UUID(menu_id), session, settings, tasks)
            start_extraction(UUID(menu_id), session, settings, tasks)
        assert len(tasks.tasks) == 1
        recover_interrupted(engine)
        result = client.get(f"/api/menus/{menu_id}").json()
        assert result["status"] == "failed" and "interrupted" in result["processing_error"]


def test_persistence_failure_rolls_back_all_dishes(database):
    engine, _ = database
    real_commit = Session.commit
    def fail_final_commit(session):
        if any(isinstance(obj, Menu) and obj.status == "processed" for obj in session.identity_map.values()):
            raise OperationalError("secret", {}, Exception("secret"))
        return real_commit(session)
    with TestClient(app) as client, patch("app.services.extraction_service.get_provider", return_value=FakeProvider()):
        menu_id = upload(client)
        with patch.object(Session, "commit", fail_final_commit):
            client.post(f"/api/menus/{menu_id}/process")
        result = client.get(f"/api/menus/{menu_id}").json()
        assert result["status"] == "failed" and "secret" not in result["processing_error"]
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(MenuItem)) == 0
            assert session.scalar(select(func.count()).select_from(MenuSection)) == 0


def test_factory_and_wire_schema():
    for provider in ("", "gemini"):
        with pytest.raises(ServiceError): get_provider(Settings(menu_ai_provider=provider))
    assert isinstance(get_provider(Settings(menu_ai_provider="openai", menu_ai_model="chosen-model", openai_api_key="test")), OpenAIProvider)
    assert isinstance(get_provider(Settings(menu_ai_provider="anthropic", menu_ai_model="chosen-model", anthropic_api_key="test")), AnthropicProvider)
    schema = provider_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert "minimum" not in json.dumps(schema)
