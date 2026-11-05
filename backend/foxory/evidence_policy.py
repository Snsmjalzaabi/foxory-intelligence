"""Evidence labels and guards; a repository address is not repository source text."""
import re
REPOSITORY_SOURCE_REQUIRED = ('Repository source text is required. Model Council does not fetch or clone repository links. Upload README/source text in Documents and select it, or paste the relevant source instead of submitting only a repository address. Then start a new Council task.')
SOURCE_BASED_NOTICE = 'Source-based model analysis. References point to supplied excerpts; interpretations and claims have not been independently fact-checked.'
MODEL_ONLY_NOTICE = 'Unverified model discussion. No external or document sources were provided. Model agreement does not verify facts; no repository, files or history were inspected.'

def repository_review(prompt):
    value=str(prompt or '').strip()
    pattern=r'(?:git@github\.com:|https?://github\.com/)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[^\s`]*)?'
    if not re.search(pattern,value,re.I):return False
    rest=re.sub(pattern,'',value,flags=re.I).strip(' \n\r\t`.,?!:;()<>')
    if len(rest)>1200 or ('```' in value and len(rest)>100):return False
    return not rest or bool(re.search(r'\b(analy[sz]e|audit|review|inspect|summari[sz]e)\b',rest,re.I))

def has_text_sources(sources):
    return any(isinstance(s,dict) and isinstance(s.get('text'),str) and s['text'].strip() for s in sources or [])

def council_export_text(data):
    result=data.get('result','No result')
    if data.get('type')!='council':return result
    if not has_text_sources(data.get('sources')):
        if repository_review(data.get('prompt','')):
            from fastapi import HTTPException
            raise HTTPException(409,REPOSITORY_SOURCE_REQUIRED+' This unsupported result cannot be exported as a repository review.')
        if not result.startswith(MODEL_ONLY_NOTICE):result=MODEL_ONLY_NOTICE+'\n\n'+result
    elif not result.startswith(SOURCE_BASED_NOTICE):result=SOURCE_BASED_NOTICE+'\n\n'+result
    return result
