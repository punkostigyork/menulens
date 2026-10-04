import asyncio
import json
from unittest.mock import patch
from uuid import UUID, uuid4
import httpx
import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.main import app
from app.models import MenuItem, Menu, ItemExplanation
from app.core.config import Settings
from app.schemas.explanation import GeneratedExplanation, DishSource, explanation_schema
from app.services.ai.base import ProviderResult, ProviderError
from app.services.ai.dish_explainer import explain_dish
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.explanation_service import request_explanation, recover_explanations
from test_extraction import FakeProvider, upload

SOURCE = DishSource(name="Gulyásleves", original_description="marhahús, paprika", ingredients=["marhahús", "paprika"])


def result(language="en"):
    return {"language": language, "description": "A Hungarian soup with beef and paprika." if language == "en" else "Magyar leves marhahússal és paprikával.", "tags": ["Hungarian", "soup", "meat"]}


class Explainer(FakeProvider):
    def __init__(self, responses=None):
        super().__init__()
        self.explanation_calls = []
        self.responses = responses
    async def generate_description(self, source, language, schema, instructions):
        self.explanation_calls.append((source, language, schema, instructions))
        response = self.responses[min(len(self.explanation_calls) - 1, len(self.responses)-1)] if self.responses else json.dumps(result(language))
        if isinstance(response, Exception): raise response
        return ProviderResult(response)


def extracted(client):
    with patch("app.services.extraction_service.get_provider", return_value=FakeProvider()):
        menu_id = upload(client)
        client.post(f"/api/menus/{menu_id}/process")
        item = client.get(f"/api/menus/{menu_id}/items").json()[0]
        return menu_id, item


@pytest.mark.parametrize("description", ["This is gluten-free.", "Nut free and delicious.", "Allergy-safe food.", "Ez gluténmentes étel.", "Tejmentes és laktózmentes.", "One. Two. Three.", "", "x" * 401])
def test_rejects_safety_claims_and_invalid_descriptions(description):
    with pytest.raises(ValidationError): GeneratedExplanation.model_validate({**result(), "description": description})


def test_tags_are_restricted_and_deduplicated():
    with pytest.raises(ValidationError): GeneratedExplanation.model_validate({**result(), "tags": ["gluten-free"]})
    with pytest.raises(ValidationError): GeneratedExplanation.model_validate({**result(), "ingredients": ["invented"]})
    assert GeneratedExplanation.model_validate({**result(), "tags": ["soup", "soup"]}).tags == ["soup"]


def test_wrong_language_retried_once():
    provider = Explainer([json.dumps(result("hu")), json.dumps(result("en"))])
    assert asyncio.run(explain_dish(provider, SOURCE, "en", 1)).language == "en"
    assert len(provider.explanation_calls) == 2
    assert "Previous output failed" in provider.explanation_calls[1][3]


def test_two_invalid_responses_fail():
    provider = Explainer(["not json"])
    with pytest.raises(ProviderError): asyncio.run(explain_dish(provider, SOURCE, "en", 1))
    assert len(provider.explanation_calls) == 2


def test_description_deadline():
    class Slow(Explainer):
        async def generate_description(self, *args): await asyncio.sleep(1)
    with pytest.raises(ProviderError) as error: asyncio.run(explain_dish(Slow(), SOURCE, "en", 0.001))
    assert error.value.status_code == 504


@pytest.mark.parametrize("adapter", [OpenAIProvider, AnthropicProvider])
def test_both_provider_description_contracts(adapter):
    def respond(request):
        payload = json.loads(request.content)
        if adapter == OpenAIProvider:
            assert payload["text"]["format"]["name"] == "dish_explanation"
            content = payload["input"][0]["content"][0]["text"]
            response = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(result())}]}]}
        else:
            content = payload["messages"][0]["content"][0]["text"]
            assert payload["max_tokens"] == 2000
            response = {"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(result())}]}
        assert json.loads(content) == SOURCE.model_dump()
        return httpx.Response(200, json=response)
    provider = adapter(Settings(menu_ai_model="test", openai_api_key="test", anthropic_api_key="test"), transport=httpx.MockTransport(respond))
    response = asyncio.run(provider.generate_description(SOURCE, "en", explanation_schema(), "Explain in English"))
    assert GeneratedExplanation.model_validate_json(response.content).language == "en"


def test_en_hu_cache_and_source_preservation(database):
    engine, _ = database
    provider = Explainer()
    with TestClient(app) as client:
        menu_id, item = extracted(client)
        for language in ("en", "hu"):
            with patch("app.services.explanation_service.get_provider", return_value=provider):
                response = client.post(f"/api/menu-items/{item['id']}/explanation", json={"language": language})
                assert response.status_code == 202, response.text
            ready = client.get(f"/api/menu-items/{item['id']}/explanation?language={language}").json()
            assert ready["status"] == "ready" and ready["language"] == language
            # Cached result succeeds even though there is no configured provider now.
            assert client.post(f"/api/menu-items/{item['id']}/explanation", json={"language": language}).json()["status"] == "ready"
        assert len(provider.explanation_calls) == 2
        updated = client.get(f"/api/menus/{menu_id}/items").json()[0]
        for key in ("name", "ingredients", "original_description", "price", "currency", "language", "tags", "dietary_info", "generated_description"):
            assert updated[key] == item[key]
        assert len(updated["explanations"]) == 2
        assert client.get(f"/api/menus/{menu_id}").json()["status"] == "processed"
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(ItemExplanation)) == 2


def test_missing_config_no_cache_or_source_changes(database):
    engine, _ = database
    with TestClient(app) as client:
        _, item = extracted(client)
        assert client.post(f"/api/menu-items/{item['id']}/explanation", json={"language": "en"}).status_code == 503
        assert client.post(f"/api/menu-items/{item['id']}/explanation", json={"language": "de"}).status_code == 422
        assert client.post(f"/api/menu-items/{uuid4()}/explanation", json={"language": "en"}).status_code == 404
        with Session(engine) as session: assert session.scalar(select(func.count()).select_from(ItemExplanation)) == 0


def test_failed_generation_then_retry(database):
    provider = Explainer(["{}", "{}", json.dumps(result())])
    with TestClient(app) as client, patch("app.services.explanation_service.get_provider", return_value=provider):
        menu_id, item = extracted(client)
        path = f"/api/menu-items/{item['id']}/explanation"
        client.post(path, json={"language": "en"})
        failed = client.get(path).json()
        assert failed["status"] == "failed" and failed["description"] is None and failed["tags"] == []
        assert client.get(f"/api/menus/{menu_id}").json()["status"] == "processed"
        client.post(path, json={"language": "en"})
        assert client.get(path).json()["status"] == "ready"
        assert len(provider.explanation_calls) == 3


def test_duplicate_jobs_and_restart_recovery(database):
    engine, settings = database
    with TestClient(app) as client:
        _, item = extracted(client)
        tasks = BackgroundTasks()
        with Session(engine) as session, patch("app.services.explanation_service.get_provider", return_value=Explainer()):
            request_explanation(UUID(item["id"]), "en", session, settings, tasks)
            request_explanation(UUID(item["id"]), "en", session, settings, tasks)
        assert len(tasks.tasks) == 1
        recover_explanations(engine)
        assert client.get(f"/api/menu-items/{item['id']}/explanation").json()["status"] == "failed"


def test_database_failure_does_not_publish_partial_explanation(database):
    from sqlalchemy.exc import OperationalError
    real_commit = Session.commit
    def fail_ready(session):
        if any(isinstance(row, ItemExplanation) and row.status == "ready" for row in session.identity_map.values()):
            raise OperationalError("private", {}, Exception("secret"))
        return real_commit(session)
    with TestClient(app) as client:
        menu_id, item = extracted(client)
        with patch("app.services.explanation_service.get_provider", return_value=Explainer()), patch.object(Session, "commit", fail_ready):
            client.post(f"/api/menu-items/{item['id']}/explanation", json={"language": "en"})
        explanation = client.get(f"/api/menu-items/{item['id']}/explanation").json()
        assert explanation["status"] == "failed" and explanation["description"] is None
        assert "secret" not in explanation["error_message"]
        assert client.get(f"/api/menus/{menu_id}").json()["status"] == "processed"
