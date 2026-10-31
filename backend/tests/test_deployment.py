"""Deployment boundaries: dependency health and trusted TLS termination."""
import httpx
from sqlalchemy import text
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from foxory.main import app
from foxory.db import Session


async def test_readiness_is_public_and_checks_migration_revision(client):
    client.headers.pop('authorization', None)
    response = await client.get('/api/ready')
    assert response.status_code == 200
    assert response.json() == {'status': 'ready'}
    assert response.headers['cache-control'] == 'no-store'
    with Session() as session:
        revision = session.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
        session.execute(text("UPDATE alembic_version SET version_num='outdated'"))
        session.commit()
    try:
        assert (await client.get('/api/health')).status_code == 200
        response = await client.get('/api/ready')
        assert response.status_code == 503
        assert response.json() == {'status': 'not_ready'}
    finally:
        with Session() as session:
            session.execute(text('UPDATE alembic_version SET version_num=:revision'), {'revision': revision})
            session.commit()


async def test_readiness_database_failure_does_not_leak_details(client, monkeypatch):
    def unavailable():
        raise RuntimeError('postgresql://private-password@database')
    monkeypatch.setattr('foxory.main.Session', unavailable)
    response = await client.get('/api/ready')
    assert response.status_code == 503
    assert response.json() == {'status': 'not_ready'}
    assert 'password' not in response.text


async def test_trusted_https_proxy_allows_same_origin_and_secure_session():
    import os
    proxy = ProxyHeadersMiddleware(app, trusted_hosts=['10.20.0.2'])
    transport = httpx.ASGITransport(app=proxy, client=('10.20.0.2', 12345))
    async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
        response = await client.post('/api/auth/setup', headers={
            'origin': 'https://testserver', 'x-forwarded-proto': 'https',
        }, json={'username': 'owner', 'password': 'deployment-password-123',
                 'bootstrap_token': os.environ['FOXORY_TOKEN']})
        assert response.status_code == 201
        assert 'Secure' in response.headers['set-cookie']
        assert 'HttpOnly' in response.headers['set-cookie']


async def test_untrusted_proxy_cannot_spoof_https_origin():
    proxy = ProxyHeadersMiddleware(app, trusted_hosts=['10.20.0.2'])
    transport = httpx.ASGITransport(app=proxy, client=('10.20.0.3', 12345))
    async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
        response = await client.post('/api/auth/login', headers={
            'origin': 'https://testserver', 'x-forwarded-proto': 'https',
        }, json={'username': 'owner', 'password': 'deployment-password-123'})
        assert response.status_code == 403


async def test_forced_secure_cookie_on_http_backend(client, monkeypatch):
    from foxory.auth import issue
    from starlette.requests import Request
    from starlette.responses import Response
    monkeypatch.setattr('foxory.auth.SECURE_COOKIES', True)
    response = Response()
    # Use a real account so session persistence keeps its foreign-key contract.
    import os
    await client.post('/api/auth/setup', json={
        'username': 'owner', 'password': 'deployment-password-123',
        'bootstrap_token': os.environ['FOXORY_TOKEN'],
    })
    issue('initial-administrator', Request({'type': 'http', 'scheme': 'http',
          'server': ('testserver', 80), 'path': '/', 'headers': []}), response)
    assert 'Secure' in response.headers['set-cookie']


async def test_unknown_host_is_rejected(client):
    assert (await client.get('/api/health', headers={'host': 'attacker.invalid'})).status_code == 400
