from unittest.mock import patch
import pytest
import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.main import app
from app.models import Menu, MenuItem, MenuSection, MenuExtraction
from app.services.demo_service import seed_demo, DEMO_ID, DEMO_FILENAME, DATA_DIR


def test_demo_seed_roundtrip_and_idempotency(database):
    engine, settings = database
    with TestClient(app) as client:
        assert client.get('/api/demo').json() == {'menu_id': None}
        assert seed_demo(engine, settings)
        with Session(engine) as session:
            session.add(Menu(original_filename='user.pdf', stored_filename='unrelated.pdf', content_type='application/pdf'))
            session.commit()
        assert seed_demo(engine, settings) is False
        assert client.get('/api/demo').json() == {'menu_id': str(DEMO_ID)}
        menu = client.get(f'/api/menus/{DEMO_ID}').json()
        assert menu['is_demo'] is True and menu['status'] == 'processed'
        assert len(menu['sections']) == 3
        items = client.get(f'/api/menus/{DEMO_ID}/items').json()
        assert len(items) == 4
        assert all(i['currency'] == 'HUF' and not i['explanations'] and i['generated_image'] is None for i in items)
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(Menu)) == 2
            assert session.scalar(select(func.count()).select_from(MenuItem)) == 4
            assert session.get(MenuExtraction, DEMO_ID).provider == 'hand-authored'
        source = client.get('/api/demo/source')
        assert source.status_code == 200 and source.headers['content-type'] == 'application/pdf'
        assert source.content == (settings.upload_dir / DEMO_FILENAME).read_bytes()
        with pymupdf.open(stream=source.content, filetype='pdf') as pdf:
            assert len(pdf) == 1
            text = pdf[0].get_text()
            for item in items:
                assert item['name'] in text
                assert str(int(float(item['price']))) + ' HUF' in text
                for ingredient in item['ingredients']: assert ingredient in text
                for tag in item['tags']: assert tag in text
        response = client.post('/api/search', json={'menu_id':str(DEMO_ID), 'filters':{'ingredients':['chicken'], 'max_price':6000, 'currency':'HUF'}})
        assert response.status_code == 200
        assert [r['item']['name'] for r in response.json()['results']] == ['Csirkepaprikas']
        dessert = client.post('/api/search', json={'menu_id':str(DEMO_ID), 'filters':{'tags':['dessert'],'max_price':3000,'currency':'HUF'}})
        assert [r['item']['name'] for r in dessert.json()['results']] == ['Somloi galuska']


def test_seed_does_not_overwrite_colliding_file(database):
    engine, settings = database
    with TestClient(app):
        settings.upload_dir.mkdir()
        target = settings.upload_dir / DEMO_FILENAME
        target.write_bytes(b'other data')
        with pytest.raises(RuntimeError): seed_demo(engine, settings)
        assert target.read_bytes() == b'other data'
        with Session(engine) as session: assert session.get(Menu, DEMO_ID) is None


def test_failed_seed_rolls_back_new_file_and_rows(database):
    engine, settings = database
    with TestClient(app), patch('app.services.demo_service.Session.commit', side_effect=OperationalError('insert',{},Exception('db secret'))):
        with pytest.raises(OperationalError): seed_demo(engine, settings)
        assert not (settings.upload_dir / DEMO_FILENAME).exists()
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(Menu)) == 0
            assert session.scalar(select(func.count()).select_from(MenuSection)) == 0


def test_seed_reuses_identical_orphan_source(database):
    engine, settings = database
    with TestClient(app):
        settings.upload_dir.mkdir()
        (settings.upload_dir / DEMO_FILENAME).write_bytes((DATA_DIR / 'hungarian-menu.pdf').read_bytes())
        assert seed_demo(engine, settings)


def test_startup_seed_is_repeatable(database):
    engine, settings = database
    settings.seed_demo = True
    with patch('app.main.get_settings',return_value=settings):
        with TestClient(app) as client: assert client.get('/api/demo').json()['menu_id'] == str(DEMO_ID)
        with TestClient(app) as client:
            assert len(client.get(f'/api/menus/{DEMO_ID}/items').json()) == 4


def test_demo_database_error_is_safe(database):
    with TestClient(app) as client, patch('app.api.demo.Session.get',side_effect=OperationalError('secret query',{},Exception('private credentials'))):
        response = client.get('/api/demo')
    assert response.status_code == 503
    assert 'temporarily unavailable' in response.json()['detail']
    assert 'private' not in response.text and 'secret' not in response.text
