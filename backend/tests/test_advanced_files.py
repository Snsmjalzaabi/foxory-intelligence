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

async def test_uploaded_csv_analysis_scopes_and_exports(client):
    from foxory.agent_tools import authorize
    from foxory.agents import AgentConfig
    response=await client.post('/api/documents',files={'file':('sales.csv',b'team,revenue\nA,10\nA,20\nB,5\n','text/csv')})
    assert response.status_code==201,response.text
    id=response.json()['id']
    cfg=AgentConfig(tools=['data.csv_document'],permissions=['documents.read','calculate'],document_ids=[id]).model_dump()
    result=await execute('data.csv_document',{'document_id':id,'column':'revenue','group_by':'team'},cfg,'a')
    assert result['groups'][0]['sum']==30 and result['groups'][1]['sum']==5
    assert '30' in result['csv'] and '<svg' in result['chart_svg'] and result['source_sha256']
    with pytest.raises(PermissionError):authorize({**cfg,'document_ids':[]},'data.csv_document',{'document_id':id,'column':'revenue'})
    with pytest.raises(PermissionError):authorize({**cfg,'permissions':['documents.read']},'data.csv_document',{'document_id':id,'column':'revenue'})

async def test_csv_agent_workflow_report_and_chart_archive(client,monkeypatch):
    import xml.etree.ElementTree as ET
    from foxory.agents import AgentConfig
    from foxory import inference
    from test_agents import task,finish,prose
    monkeypatch.setattr(inference,'complete',prose)
    upload=await client.post('/api/documents',files={'file':('finance.csv',b'team,revenue\nA,10\nA,20\nB,5\n','text/csv')})
    id=upload.json()['id']
    cfg=AgentConfig(model='fixture',tools=['data.csv_document','document.generate','source.package'],permissions=['documents.read','documents.write','calculate'],document_ids=[id]).model_dump()
    response=await client.post('/api/agents',json={'name':'CSV analyst','config':cfg});assert response.status_code==201,response.text
    plan=[{'title':'Analyze authorized CSV','tool':'data.csv_document','args':{'document_id':id,'column':'revenue','group_by':'team'}},
          {'title':'Save report','tool':'document.generate','args':{'title':'CSV report','content':{'$step':0,'path':['report']}},'depends_on':[0]},
          {'title':'Package chart and calculations','tool':'source.package','args':{'title':'CSV charts','files':{'chart.svg':{'$step':0,'path':['chart_svg']},'results.csv':{'$step':0,'path':['csv']}}},'depends_on':[0]}]
    job=await task(client,response.json(),plan,key='csv-report-workflow')
    for _ in range(3):
        result=await finish(job['id'])
        if result['status']=='completed':break
        assert result['status']=='awaiting_approval',result
        assert (await client.post('/api/approvals/'+result['approval_id']+'/approve')).status_code==200
    assert result['status']=='completed',result
    report=await client.get('/api/artifacts/'+result['outputs'][1]['result']['record_id']+'/export?format=pdf')
    from pypdf import PdfReader
    assert '30' in ''.join(page.extract_text() for page in PdfReader(io.BytesIO(report.content)).pages)
    archive=await client.get('/api/artifacts/'+result['outputs'][2]['result']['record_id']+'/export?format=zip')
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        assert z.testzip() is None
        assert ET.fromstring(z.read('chart.svg')).tag.endswith('svg')
        assert b'A,2,30.0' in z.read('results.csv')
