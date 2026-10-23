"""Public HTTP retrieval with DNS pinning, redirect validation and robots enforcement.

Pinned IP connections retain the original Host and TLS SNI, including through an
operator's HTTP proxy. There is no fallback to an unpinned request.
"""
import asyncio
import hashlib
import ipaddress
import re
import socket
import time
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin
from urllib.robotparser import RobotFileParser
import httpx
from bs4 import BeautifulSoup
from .db import now
AGENT='FOXORYResearch/0.2'
MAX_BYTES=2_000_000
class RetrievalError(ValueError):pass

def canonical(url:str)->str:
    try:
        p=urlsplit(url)
        if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password:raise RetrievalError('Only public HTTP(S) URLs without credentials are allowed')
        if p.port not in {None,80,443}:raise RetrievalError('Nonstandard ports are blocked')
        host=p.hostname.encode('idna').decode('ascii').lower()
        if any(ord(x)<33 for x in url) or '\\' in url:raise RetrievalError('Invalid URL')
        authority=('['+host+']') if ':' in host else host
        if p.port and p.port!=({'http':80,'https':443}[p.scheme]):authority+=':'+str(p.port)
        params=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]
        return urlunsplit((p.scheme,authority,p.path or '/',urlencode(params),''))
    except (ValueError,UnicodeError) as e:raise RetrievalError('Invalid public URL') from e

async def public_addresses(host:str,port:int)->list[str]:
    try:
        answers=await asyncio.get_running_loop().getaddrinfo(host,port,type=socket.SOCK_STREAM)
        ips=list(dict.fromkeys(x[4][0] for x in answers))
    except OSError as e:raise RetrievalError('DNS resolution failed') from e
    def allowed(address):
        ip=ipaddress.ip_address(address)
        if not ip.is_global:return False
        if isinstance(ip,ipaddress.IPv6Address):
            # Decline transition networks rather than trusting a public-looking
            # IPv6 address that can translate to a private IPv4 destination.
            if ip.ipv4_mapped or ip.sixtofour or ip.teredo:return False
            if ip in ipaddress.ip_network('64:ff9b::/96') or ip in ipaddress.ip_network('64:ff9b:1::/48'):return False
        return True
    if not ips or not all(allowed(ip) for ip in ips):
        raise RetrievalError('Private, loopback, reserved and mixed-address destinations are blocked')
    return ips

async def pinned_get(url:str,limit:int=MAX_BYTES):
    url=canonical(url);p=urlsplit(url);port=p.port or (443 if p.scheme=='https' else 80)
    ips=await public_addresses(p.hostname,port)
    address=ips[0];authority=f'[{address}]' if ':' in address else address
    pinned=urlunsplit((p.scheme,authority+':'+str(port),p.path,p.query,''))
    # trust_env preserves the managed outbound proxy and CA configuration.
    from .pinned_transport import transport
    async with httpx.AsyncClient(transport=transport(address,p.hostname,p.scheme),timeout=httpx.Timeout(15,connect=5),follow_redirects=False,trust_env=True) as client:
        async with client.stream('GET',pinned,headers={'Host':p.netloc,'User-Agent':AGENT,'Accept':'text/html,text/plain,application/xhtml+xml','Accept-Encoding':'identity'},extensions={'sni_hostname':p.hostname}) as response:
            if response.headers.get('content-encoding','identity').lower() not in {'','identity'}:raise RetrievalError('Compressed responses are declined to bound decompression')
            if int(response.headers.get('content-length','0'))>limit:raise RetrievalError('Response exceeds size budget')
            body=bytearray()
            async for part in response.aiter_raw():
                body.extend(part)
                if len(body)>limit:raise RetrievalError('Response exceeds size budget')
            return response.status_code,dict(response.headers),bytes(body)

_domain_locks:dict[str,asyncio.Lock]={}
_last_request:dict[str,float]={}
async def robots_allowed(url:str):
    p=urlsplit(url);origin=urlunsplit((p.scheme,p.netloc,'','',''))
    code,_,body=await pinned_get(origin+'/robots.txt',64_000)
    if code==404:return 1.0
    if code!=200:raise RetrievalError('Robots policy unavailable or access denied')
    robots=RobotFileParser();robots.parse(body.decode('utf-8',errors='replace').splitlines())
    if not robots.can_fetch(AGENT,url):raise RetrievalError('Robots policy disallows retrieval')
    delay=robots.crawl_delay(AGENT) or 1
    if delay>10:raise RetrievalError('Crawl delay exceeds this job budget')
    return float(delay)

async def retrieve_page(url:str,query:str=''):
    url=canonical(url)
    for _ in range(4):
        host=urlsplit(url).hostname
        if host not in _domain_locks:
            if len(_domain_locks)>1000:raise RetrievalError('Host budget exhausted')
            _domain_locks[host]=asyncio.Lock()
        async with _domain_locks[host]:
            delay=await robots_allowed(url)
            await asyncio.sleep(max(0,delay-(time.monotonic()-_last_request.get(host,0))))
            try:code,headers,body=await pinned_get(url)
            finally:_last_request[host]=time.monotonic()
        if code in {301,302,303,307,308}:
            location=headers.get('location')
            if not location:raise RetrievalError('Redirect has no destination')
            url=canonical(urljoin(url,location));continue
        if code!=200:raise RetrievalError('Source denied access or returned an error')
        if any(token in headers.get('x-robots-tag','').lower() for token in ['noarchive','nosnippet','noindex','noai']):raise RetrievalError('Source forbids indexing/archiving')
        mime=headers.get('content-type','').split(';')[0].lower()
        if mime not in {'text/html','application/xhtml+xml','text/plain'}:raise RetrievalError('Only public text and HTML pages are supported')
        return extract_page(url,body.decode('utf-8',errors='replace'),query,mime)
    raise RetrievalError('Redirect limit exceeded')

def extract_page(url:str,html:str,query:str='',mime:str='text/html'):
    soup=BeautifulSoup(html,'html.parser')
    for tag in soup.find_all('meta',attrs={'name':re.compile(r'^(robots|foxoryresearch)$',re.I)}):
        if any(token in str(tag.get('content','')).lower() for token in ['noindex','noarchive','nosnippet','noai']):raise RetrievalError('Source forbids indexing/archiving')
    if any(token in html.casefold() for token in ['cf-chl-','g-recaptcha','h-captcha','verify you are human']):raise RetrievalError('Access challenge; no bypass attempted')
    title=soup.title.get_text(' ',strip=True)[:300] if soup.title else urlsplit(url).hostname
    published=None;date_basis=None
    for key in ['article:published_time','datePublished','date','dc.date','pubdate']:
        tag=soup.find('meta',attrs={'property':key}) or soup.find('meta',attrs={'name':key})
        if tag and tag.get('content'):
            candidate=str(tag['content'])[:100]
            try:published=datetime.fromisoformat(candidate.replace('Z','+00:00')).isoformat();date_basis='page metadata';break
            except ValueError:pass
    if not published:
        tag=soup.find('time',attrs={'datetime':True})
        if tag:
            try:published=datetime.fromisoformat(str(tag['datetime']).replace('Z','+00:00')).isoformat();date_basis='time element (may not be publication date)'
            except ValueError:pass
    has_author=bool(soup.find('meta',attrs={'name':'author'}))
    for node in soup(['script','style','nav','footer','header','form','iframe','noscript']):node.decompose()
    text=soup.get_text(' ',strip=True) if mime!='text/plain' else html
    text=re.sub(r'\s+',' ',text).strip()[:60_000]
    if len(text)<80:raise RetrievalError('Insufficient readable evidence')
    terms=set(re.findall(r'\w{3,}',query.casefold()));relevance=sum(min(10,text.casefold().count(t)) for t in terms)/max(1,len(terms))
    score=0.2;reasons=['Heuristic metadata assessment; not factual verification']
    if urlsplit(url).hostname.endswith(('.gov','.edu')):score+=.25;reasons.append('Government/education domain')
    if url.startswith('https:'):score+=.1;reasons.append('HTTPS transport')
    if published:score+=.1;reasons.append('Date metadata present')
    if has_author:score+=.1;reasons.append('Author metadata present')
    if len(text)>1500:score+=.1;reasons.append('Substantial readable content')
    return {'url':url,'title':title,'text':text,'published':published,'date_basis':date_basis,'retrieved_at':now(),'content_hash':hashlib.sha256(text.encode()).hexdigest(),'relevance':round(relevance,3),'credibility':{'score':round(score,2),'reasons':reasons},'evidence_type':'retrieved_page'}
