"""Actual Unix HTTP transport with a controlled server, not OCI isolation proof."""
import asyncio
import os
import socket

from fastapi import FastAPI,Request
import pytest
import uvicorn

from foxory import sandbox_client
from foxory.scope import workspace_id


@pytest.fixture
def configured_socket(tmp_path,monkeypatch):
    directory=tmp_path/'ipc';directory.mkdir(mode=0o750)
    path=directory/'manager.sock'
    server=socket.socket(socket.AF_UNIX);server.bind(str(path));os.chmod(path,0o660)
    monkeypatch.setenv('FOXORY_ENABLE_SANDBOX','1')
    monkeypatch.setenv('FOXORY_SANDBOX_KEY','x'*40)
    monkeypatch.setenv('FOXORY_SANDBOX_URL','')
    monkeypatch.setenv('FOXORY_SANDBOX_SOCKET',str(path))
    try:yield path,server
    finally:server.close()


async def test_actual_private_unix_http_transport_preserves_auth_scope_and_bypasses_proxies(configured_socket,monkeypatch):
    path,socket=configured_socket
    calls=[];app=FastAPI()
    @app.get('/v1/health')
    def health(request:Request):
        calls.append((request.headers['authorization'],request.headers['x-foxory-workspace']))
        return {'enabled':True,'fixture':'controlled-unix-http'}
    monkeypatch.setenv('HTTP_PROXY','http://127.0.0.1:1')
    monkeypatch.setenv('HTTPS_PROXY','http://127.0.0.1:1')
    token=workspace_id.set('unix-fixture')
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',lifespan='off'))
    task=asyncio.create_task(server.serve(sockets=[socket]))
    try:
        for _ in range(100):
            if server.started:break
            if task.done():await task
            await asyncio.sleep(.01)
        assert server.started
        assert await sandbox_client.capabilities()=={'enabled':True,'fixture':'controlled-unix-http'}
        assert calls==[('Bearer '+'x'*40,'unix-fixture')]
    finally:
        server.should_exit=True
        await asyncio.wait_for(task,5)
        workspace_id.reset(token)


@pytest.mark.parametrize('unsafe',['world-socket','writable-parent','symlink','relative','both','short-key','disabled','absent'])
async def test_unsafe_socket_configuration_fails_closed(configured_socket,monkeypatch,unsafe):
    path,_=configured_socket
    if unsafe=='world-socket':os.chmod(path,0o666)
    elif unsafe=='writable-parent':os.chmod(path.parent,0o770)
    elif unsafe=='symlink':
        link=path.with_name('link.sock');link.symlink_to(path);monkeypatch.setenv('FOXORY_SANDBOX_SOCKET',str(link))
    elif unsafe=='relative':monkeypatch.setenv('FOXORY_SANDBOX_SOCKET','relative.sock')
    elif unsafe=='both':monkeypatch.setenv('FOXORY_SANDBOX_URL','http://127.0.0.1:8104')
    elif unsafe=='short-key':monkeypatch.setenv('FOXORY_SANDBOX_KEY','short')
    elif unsafe=='disabled':monkeypatch.setenv('FOXORY_ENABLE_SANDBOX','0')
    elif unsafe=='absent':monkeypatch.setenv('FOXORY_SANDBOX_SOCKET',str(path.with_name('absent.sock')))
    with pytest.raises(PermissionError):sandbox_client.settings()
    assert not (await sandbox_client.capabilities())['enabled']


@pytest.mark.parametrize('url',['http://[::1','http://127.0.0.1:invalid','http://127.0.0.1:99999','http://127.0.0.1:0'])
async def test_invalid_http_manager_configuration_reports_disabled(monkeypatch,url):
    monkeypatch.setenv('FOXORY_ENABLE_SANDBOX','1')
    monkeypatch.setenv('FOXORY_SANDBOX_KEY','x'*40)
    monkeypatch.setenv('FOXORY_SANDBOX_SOCKET','')
    monkeypatch.setenv('FOXORY_SANDBOX_URL',url)
    assert not (await sandbox_client.capabilities())['enabled']
