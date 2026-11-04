"""Pure validation shared by the app and host; generated code cannot edit this file."""
import hashlib,json,difflib
ALLOWED=('frontend/src/Operations.tsx','frontend/src/Performance.tsx','backend/foxory/operations.py','backend/foxory/performance.py')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def validate(proposal,sources):
 if proposal.get('path') not in ALLOWED:raise ValueError('Protected or unknown source path')
 source=sources[proposal['path']]
 if hashlib.sha256(source.encode()).hexdigest()!=proposal.get('base_sha256'):raise ValueError('Source changed; generate a fresh proposal')
 edits=proposal.get('edits',[])
 if not 1<=len(edits)<=3 or len(json.dumps(edits))>24000:raise ValueError('Use one to three small exact replacements')
 result=source
 for edit in edits:
  if set(edit)!={'old','new'} or not isinstance(edit['old'],str) or not isinstance(edit['new'],str) or not edit['old'] or edit['old']==edit['new'] or result.count(edit['old'])!=1:raise ValueError('Every replacement must match exactly once and change the source')
  result=result.replace(edit['old'],edit['new'],1)
 if len(result)>100000:raise ValueError('Candidate source exceeds limit')
 return result

def patch(proposal,sources):
 updated=validate(proposal,sources);path=proposal['path'];return ''.join(difflib.unified_diff(sources[path].splitlines(True),updated.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
