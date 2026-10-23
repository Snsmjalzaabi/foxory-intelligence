import os
import tempfile
from pathlib import Path
os.environ['FOXORY_DATA_DIR'] = tempfile.mkdtemp(prefix='foxory-test-')
os.environ['FOXORY_TOKEN'] = 'test-token-is-long-enough-for-tests'
os.environ['DATABASE_URL'] = 'sqlite:///' + os.environ['FOXORY_DATA_DIR'] + '/test.db'
import pytest
import httpx
from alembic import command
from alembic.config import Config
from foxory.db import Session, Record, Message, Audit
from foxory.main import app, requests_by_client, active_chats

@pytest.fixture(autouse=True)
def database():
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    cfg.set_main_option('script_location', str(Path(__file__).resolve().parents[1]/'migrations'))
    command.upgrade(cfg,'head')
    with Session() as s:
        s.query(Message).delete();s.query(Record).delete();s.query(Audit).delete();s.commit()
    requests_by_client.clear();active_chats.clear()

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver',headers={'Authorization':'Bearer '+os.environ['FOXORY_TOKEN']}) as c: yield c
