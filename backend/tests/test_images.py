import asyncio
import base64
import io
import json
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4
import httpx
import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.main import app
from app.models import GeneratedImage, MenuItem, Menu
from app.core.config import Settings
from app.services.images.base import ImageProvider, ImageProviderError
from app.services.images.openai_provider import OpenAIImageProvider
from app.services.image_service import request_image, recover_images, validate_image
from test_explanations import extracted


def png(size=(32,32)):
    output=io.BytesIO()
    metadata=PngImagePlugin.PngInfo();metadata.add_text("private_metadata","removed")
    Image.new("RGB",size,"orange").save(output,format="PNG",pnginfo=metadata)
    return output.getvalue()


class Provider(ImageProvider):
    name="test"
    model="test-image-model"
    def __init__(self, result=None): self.calls=[];self.result=result if result is not None else png()
    async def generate(self,prompt):
        self.calls.append(prompt)
        if isinstance(self.result,Exception): raise self.result
        return self.result


def test_lazy_generation_cache_and_content(database):
    engine,settings=database;provider=Provider()
    with TestClient(app) as client:
        menu_id,item=extracted(client);url=f"/api/menu-items/{item['id']}/image"
        assert item["generated_image"] is None
        assert client.get(url).status_code==404
        assert client.get(url+"/content").status_code==404
        with Session(engine) as session: assert session.scalar(select(func.count()).select_from(GeneratedImage))==0
        with patch("app.services.image_service.get_image_provider",return_value=provider):
            assert client.post(url).status_code==202
        record=client.get(url).json();assert record["status"]=="ready"
        assert "prompt" not in record and "storage_path" not in record
        image=client.get(record["image_url"])
        assert image.status_code==200 and image.headers["content-type"]=="image/png"
        assert image.headers["x-content-type-options"]=="nosniff"
        with Image.open(io.BytesIO(image.content)) as decoded: assert decoded.size==(32,32) and "private_metadata" not in decoded.info
        # Ready cache is reusable with no provider configuration.
        assert client.post(url).json()["id"]==record["id"] and len(provider.calls)==1
        refreshed=client.get(f"/api/menus/{menu_id}").json()["sections"][0]["items"][0]
        assert refreshed["generated_image"]["id"]==record["id"]
        for field in ("ingredients","price","original_description","tags"): assert refreshed[field]==item[field]
        with Session(engine) as session:
            saved=session.scalar(select(GeneratedImage));assert saved.provider=="test" and saved.prompt and saved.latency_ms>=0
        assert len(list((settings.upload_dir/"generated-images").glob("*.png")))==1


def test_missing_configuration_unknown_and_unprocessed(database):
    with TestClient(app) as client:
        menu_id,item=extracted(client);url=f"/api/menu-items/{item['id']}/image"
        assert client.post(url).status_code==503
        assert client.post(f"/api/menu-items/{uuid4()}/image").status_code==404
        assert client.post('/api/menu-items/not-a-uuid/image').status_code==422
        with Session(database[0]) as session:
            assert session.scalar(select(func.count()).select_from(GeneratedImage))==0
            session.get(Menu,UUID(menu_id)).status="failed";session.commit()
        assert client.post(url).status_code==409


@pytest.mark.parametrize("bad",[b"",b"not an image",b"<svg></svg>",png((3000,3000))])
def test_bad_raster_is_rejected(bad):
    with pytest.raises(ImageProviderError): validate_image(bad,Settings())


def test_file_size_limit():
    with pytest.raises(ImageProviderError): validate_image(b"x"*1025,Settings(image_max_bytes=1024))


def test_failure_and_explicit_retry(database):
    provider=Provider(b"corrupted")
    with TestClient(app) as client:
        menu_id,item=extracted(client);url=f"/api/menu-items/{item['id']}/image"
        with patch("app.services.image_service.get_image_provider",return_value=provider):
            client.post(url)
            assert client.get(url).json()["status"]=="failed"
            assert client.get(f"/api/menus/{menu_id}").json()["status"]=="processed"
            provider.result=png();client.post(url)
        assert client.get(url).json()["status"]=="ready" and len(provider.calls)==2


def test_deduplication_and_recovery(database):
    engine,settings=database
    with TestClient(app) as client:
        _,item=extracted(client);tasks=BackgroundTasks()
        with Session(engine) as session,patch("app.services.image_service.get_image_provider",return_value=Provider()):
            first=request_image(UUID(item["id"]),session,settings,tasks)
            second=request_image(UUID(item["id"]),session,settings,tasks)
        assert first.id==second.id and len(tasks.tasks)==1
        recover_images(engine)
        assert client.get(f"/api/menu-items/{item['id']}/image").json()["status"]=="failed"


def test_deadline(database):
    class Slow(Provider):
        async def generate(self,prompt): await asyncio.sleep(1)
    database[1].image_timeout_seconds=0.001
    with TestClient(app) as client:
        _,item=extracted(client);url=f"/api/menu-items/{item['id']}/image"
        with patch("app.services.image_service.get_image_provider",return_value=Slow()): client.post(url)
        assert "too long" in client.get(url).json()["error_message"]


def test_db_failure_removes_file(database):
    real_commit=Session.commit
    def fail_ready(session):
        if any(isinstance(row,GeneratedImage) and row.status=="ready" for row in session.identity_map.values()):
            raise OperationalError("secret",{},Exception("credentials"))
        return real_commit(session)
    with TestClient(app) as client:
        _,item=extracted(client);url=f"/api/menu-items/{item['id']}/image"
        with patch("app.services.image_service.get_image_provider",return_value=Provider()),patch.object(Session,"commit",fail_ready): client.post(url)
        result=client.get(url).json();assert result["status"]=="failed" and "secret" not in result["error_message"]
        assert list((database[1].upload_dir/"generated-images").glob("*.png"))==[]


def test_storage_failure_and_missing_cached_file(database):
    with TestClient(app) as client:
        _,item=extracted(client);url=f"/api/menu-items/{item['id']}/image"
        with patch("app.services.image_service.get_image_provider",return_value=Provider()),patch("app.services.image_service.image_path",side_effect=OSError("secret")):
            client.post(url)
        assert client.get(url).json()["status"]=="failed"
        with patch("app.services.image_service.get_image_provider",return_value=Provider()): client.post(url)
        with Session(database[0]) as session:
            record=session.scalar(select(GeneratedImage));filename=record.storage_path
            record.storage_path="../../private.png";session.commit()
        assert client.get(url+"/content").status_code==503
        with Session(database[0]) as session:
            session.scalar(select(GeneratedImage)).storage_path=filename;session.commit()
        (database[1].upload_dir/"generated-images"/filename).unlink()
        assert client.get(url+"/content").status_code==503


def test_openai_image_contract():
    calls=[]
    def respond(request):
        calls.append(request);body=json.loads(request.content)
        assert str(request.url)=="https://api.openai.com/v1/images/generations"
        assert body=={"model":"chosen-model","prompt":"Dish data","n":1,"size":"1024x1024","quality":"low","output_format":"png"}
        return httpx.Response(200,json={"data":[{"b64_json":base64.b64encode(png()).decode()}]})
    provider=OpenAIImageProvider(Settings(image_model="chosen-model",openai_api_key="dummy"),httpx.MockTransport(respond))
    assert asyncio.run(provider.generate("Dish data"))==png() and len(calls)==1


@pytest.mark.parametrize("response",[{"data":[]},{"data":[{"url":"http://127.0.0.1/private"}]},{"data":[{"b64_json":"invalid"}]},None])
def test_invalid_provider_envelopes(response):
    provider=OpenAIImageProvider(Settings(),httpx.MockTransport(lambda request:httpx.Response(200,json=response)))
    with pytest.raises(ImageProviderError): asyncio.run(provider.generate("test"))


@pytest.mark.parametrize("status",[400,401,429,500])
def test_safe_provider_errors(status):
    provider=OpenAIImageProvider(Settings(),httpx.MockTransport(lambda request:httpx.Response(status,text="secret")))
    with pytest.raises(ImageProviderError) as error: asyncio.run(provider.generate("test"))
    assert "secret" not in str(error.value)


def test_oversized_provider_response():
    provider=OpenAIImageProvider(Settings(image_max_bytes=1024),httpx.MockTransport(lambda request:httpx.Response(200,content=b"x"*70000)))
    with pytest.raises(ImageProviderError): asyncio.run(provider.generate("test"))

def test_filename_collision_never_removes_existing_file(database):
    from types import SimpleNamespace
    settings=database[1]
    path=settings.upload_dir/'generated-images'/('a'*32+'.png')
    path.parent.mkdir(parents=True);path.write_bytes(b'existing file')
    with TestClient(app) as client:
        _,item=extracted(client);url=f"/api/menu-items/{item['id']}/image"
        with patch('app.services.image_service.get_image_provider',return_value=Provider()),patch('app.services.image_service.uuid4',return_value=SimpleNamespace(hex='a'*32)):
            client.post(url)
        assert client.get(url).json()['status']=='failed'
        assert path.read_bytes()==b'existing file'
