"""Retrieve one permitted public source and verify a source-grounded PDF export.

No model or owner database is used. URLs are retrieved with normal robots/SSRF/TLS
controls; failures are real failures, never replaced with invented citations.
"""
import argparse
import asyncio
import io
import json
import os
from pathlib import Path
import tempfile
import sys
parser=argparse.ArgumentParser();parser.add_argument('--url',required=True);args=parser.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
with tempfile.TemporaryDirectory(prefix='foxory-research-export-') as temporary:
    os.environ['FOXORY_DATA_DIR']=temporary
    os.environ['DATABASE_URL']='sqlite:///'+temporary+'/unused.db'
    from foxory.web import retrieve_page
    from foxory.reports import report
    from pypdf import PdfReader
    source=asyncio.run(retrieve_page(args.url))
    source['id']='1'
    # This is an exact retrieved excerpt, not a generated factual claim.
    body='Retrieved excerpt [1]:\n'+source['text'][:600]+'\n\nSource uncertainty: content integrity does not prove factual accuracy.'
    content,mime=report('Source-grounded research export',body,[source],'pdf')
    reader=PdfReader(io.BytesIO(content));text=''.join(page.extract_text() for page in reader.pages)
    assert source['url'] in text and '[1]' in text and mime=='application/pdf'
    print(json.dumps({'actual_retrieval':True,'source_url':source['url'],'content_hash':source['content_hash'],'pdf_bytes':len(content),'pdf_pages':len(reader.pages),'citation_from_retrieved_source':True}))
