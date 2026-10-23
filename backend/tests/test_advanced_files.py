import io
import json
import zipfile
import pytest
from foxory.advanced_files import analyze_table, source_zip, SourceProject, TableAnalysis, text_export
from foxory.agent_tools import execute
from test_agents import agent, task, finish, prose
from foxory import inference

def test_table_calculations_and_escaped_chart():
    result=analyze_table({'rows':[{'v':'10','g':'<script>'},{'v':20,'g':'<script>'},{'v':'bad'},{'v':-4},{'v':None}], 'column':'v','group_by':'g','minimum':0})
    summary=result['groups'][0]
    assert summary['sum']==30 and summary['mean']==15 and summary['median']==15
    assert summary['population_stddev']==5
    assert result['invalid_rows']==2 and result['filtered_rows']==1
    assert '<script>' not in result['chart_svg'] and '&lt;script&gt;' in result['chart_svg']
    for rows in [[{'v':float('nan')}],[{'v':'x'*21000}]]:
        with pytest.raises(ValueError):TableAnalysis(rows=rows,column='v')

@pytest.mark.parametrize('path',['../evil.py','/tmp/a','a/../b','a//b','a\\b','a:b','.git/config','.env','a/.env','a/./b','a\nfile'])
def test_source_paths_reject_escape(path):
    with pytest.raises(ValueError):SourceProject(title='test',files={path:'hello'})

def test_zip_integrity_and_no_execution():
    data=source_zip({'title':'Demo','files':{'src/main.py':'print(42)','README.md':'Demo'}})
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None and z.read('src/main.py')==b'print(42)'
    assert b"'=cmd" in text_export('=cmd','hello','csv')[0]
    assert json.loads(text_export('Title','body','json')[0])['body']=='body'

async def test_new_tool_grants_and_approval(client,monkeypatch):
    monkeypatch.setattr(inference,'complete',prose)
    with pytest.raises(PermissionError):await execute('data.table',{'rows':[{'v':1}],'column':'v'},{'tools':[]},'a')
    a=await agent(client,tools=['source.package'])
    job=await task(client,a,[{'title':'Package','tool':'source.package','args':{'title':'Example','files':{'main.py':'print(42)'}}}])
    data=await finish(job['id']);assert data['status']=='awaiting_approval'
    assert (await client.get('/api/agents/overview')).json()['artifacts']==[]
    approval=data['approval_id']
    response=await client.post('/api/approvals/'+approval+'/approve');assert response.status_code==200,response.text
    data=await finish(job['id']);assert data['status']=='completed',data
    artifact=data['outputs'][0]['result']['record_id']
    metadata=(await client.get('/api/agents/overview')).json()['artifacts'][0]['data']
    assert metadata['source_archive_available'] and 'source_project' not in metadata
    response=await client.get('/api/artifacts/'+artifact+'/export?format=zip');assert response.status_code==200
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:assert z.read('main.py')==b'print(42)'
    for format in ['json','csv','pdf','docx','xlsx']:
        assert (await client.get('/api/artifacts/'+artifact+'/export?format='+format)).status_code==200

async def test_artifact_workspace_boundary(client):
    from foxory.scope import workspace_id
    from foxory.db import Session, Record
    with Session() as session:
        row=Record(kind='artifact',title='Private',payload=json.dumps({'body':'secret','source_project':{'title':'Private','files':{'secret.txt':'private'}}}))
        session.add(row);session.flush();identity=row.id;session.commit()
    original=workspace_id.set('another-workspace')
    try:
        from foxory.agent_api import artifact
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as error:artifact(identity,'zip')
        assert error.value.status_code==404
    finally:workspace_id.reset(original)

def test_table_group_limit_and_booleans():
    with pytest.raises(ValueError):
        analyze_table({'rows':[{'v':1,'g':str(i)} for i in range(51)],'column':'v','group_by':'g'})
    with pytest.raises(ValueError):TableAnalysis(rows=[{'v':True}],column='v')
