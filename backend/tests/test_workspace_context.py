import json
import pytest
from foxory.db import Session,Record,Message
from foxory.scope import workspace_id
from foxory.workspace_context import retrieve_context,context_text
from foxory.agent_tools import execute

async def test_context_retrieves_scoped_business_history_and_deep_document_text(client):
    with Session() as s:
        project=Record(kind='project',title='Larkspur',payload=json.dumps({'body':'Finish the last Larkspur book.'}))
        doc=Record(kind='document',title='Book source',payload=json.dumps({'text':'Introduction. '*2000+'Larkspur final chapter deadline is unset.'}))
        chat=Record(kind='conversation',title='Earlier book chat');s.add_all([project,doc,chat]);s.flush()
        s.add(Message(conversation_id=chat.id,role='user',content='Larkspur needs one final revision.'))
        s.add(Record(kind='approval',title='Larkspur hidden approval',payload='{"body":"secret grant"}'))
        s.commit()
    token=workspace_id.set('other')
    with Session() as s:s.add(Record(kind='memory',title='Larkspur other workspace',payload='{"body":"PRIVATE OTHER WORKSPACE"}'));s.commit()
    workspace_id.reset(token)
    result=(await client.get('/api/context/preview',params={'q':'Larkspur chapter'})).json()
    rendered=context_text(result)
    assert 'final chapter deadline is unset' in rendered
    assert 'final revision' in rendered and 'Finish the last' in rendered
    assert 'PRIVATE OTHER' not in rendered and 'secret grant' not in rendered
    assert len(json.dumps(result['items']))<5000

async def test_context_tool_requires_explicit_broad_read_grant():
    with Session() as s:s.add(Record(kind='memory',title='your computer',payload='{"body":"Ubuntu local workflow"}'));s.commit()
    with pytest.raises(PermissionError):await execute('workspace.context',{'query':'your computer'}, {'tools':[],'permissions':[]},'agent')
    value=await execute('workspace.context',{'query':'your computer'}, {'tools':['workspace.context'],'permissions':['workspace.read']},'agent')
    assert value['items'][0]['title']=='your computer'

async def test_chat_passes_context_and_records_actual_history_budget(client,monkeypatch):
    with Session() as s:s.add(Record(kind='project',title='Larkspur',payload='{"body":"Final book remains unfinished"}'));s.commit()
    conversation=(await client.post('/api/records/conversation',json={'title':'Context check'})).json()
    calls=[]
    async def stream(model,messages,*args,**kwargs):
        calls.append(messages)
        yield {'message':{'content':'Draft reply'},'done':True}
    monkeypatch.setattr('foxory.inference.stream',stream)
    result=await client.post('/api/conversations/'+conversation['id']+'/chat',json={'content':'What remains for Larkspur?','model':'fixture'})
    assert result.status_code==200 and 'workspace_context' in result.text
    assert 'Final book remains unfinished' in calls[-1][0]['content']
    await client.post('/api/conversations/'+conversation['id']+'/chat',json={'content':'What remains for Larkspur?','model':'fixture','use_workspace_context':False})
    assert 'Final book remains unfinished' not in calls[-1][0]['content']
