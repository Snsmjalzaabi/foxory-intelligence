"""Trusted report writers; generated text is plain data, never executable markup."""
import io
import re
from html import escape
from docx import Document
from openpyxl import Workbook
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4

def report(title:str,text:str,sources:list,format:str):
    refs=[f"[{s['id']}] {s['title']} — {s.get('url','')} | retrieved {s.get('retrieved_at','n/a')} | hash {s.get('content_hash','')}" for s in sources]
    if not refs:refs=['No source material supplied.']
    lines=(text+'\n\nSources\n'+'\n'.join(refs)).splitlines()
    out=io.BytesIO()
    if format=='pdf':
        style=getSampleStyleSheet();title_style=ParagraphStyle('ReportTitle',parent=style['Title'],fontSize=12 if len(title)>60 else 18,leading=16 if len(title)>60 else 22);story=[Paragraph(escape(title),title_style),Spacer(1,12)]
        def inline(value):
            value=escape(value)
            value=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',value)
            return re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',value)
        for line in lines:
            heading=re.match(r'^(#{1,6})\s+(.+)$',line)
            body=line;kind='BodyText'
            if heading:
                kind='Heading'+str(min(3,len(heading.group(1))))
                body=heading.group(2)
            elif re.match(r'^\s*[-*]\s+',line):body='- '+re.sub(r'^\s*[-*]\s+','',line)
            for i in range(0,max(1,len(body)),1500):
                story.append(Paragraph(inline(body[i:i+1500]) or ' ',style[kind]));story.append(Spacer(1,5))
        SimpleDocTemplate(out,pagesize=A4).build(story);mime='application/pdf'
    elif format=='docx':
        doc=Document();doc.add_heading(title,0)
        for line in lines:doc.add_paragraph(line)
        doc.save(out);mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif format=='xlsx':
        book=Workbook();sheet=book.active;sheet.title='Report'
        def safe(v):
            v=str(v)[:32000]
            return "'"+v if v.startswith(('=','+','-','@','\t','\r')) else v
        sheet.append([safe(title)])
        for line in text.splitlines():sheet.append([safe(line)])
        evidence=book.create_sheet('Sources');evidence.append(['ID','Title','URL','Retrieved','Hash','Evidence'])
        for source in sources:evidence.append([safe(source.get(k,'')) for k in ['id','title','url','retrieved_at','content_hash','text']])
        book.save(out);mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:raise ValueError('Unknown report format')
    return out.getvalue(),mime
