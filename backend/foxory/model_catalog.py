"""Curated small, free local models. Sizes are Ollama q4 downloads; licenses are summaries, not legal advice."""
from fastapi import APIRouter
from . import inference

router=APIRouter(prefix='/api/models')
GB=1000**3
GIB=1024**3
# open: an OSI-style license with no use restrictions. Custom licenses are free to use but carry their own terms.
LICENSES={
 'Apache-2.0':('https://www.apache.org/licenses/LICENSE-2.0',True),
 'MIT':('https://opensource.org/license/mit',True),
 'Gemma Terms of Use':('https://ai.google.dev/gemma/terms',False),
 'Llama 3.2 Community License':('https://www.llama.com/llama3_2/license/',False),
}
CATALOG=[
 # name, family, strengths, download GB, context, license, summary
 ('qwen3:1.7b','Qwen3',['chat','reasoning'],1.4,40960,'Apache-2.0','Very small general model with optional thinking; runs on almost any PC.'),
 ('qwen3:4b','Qwen3',['chat','writing','tools'],2.5,262144,'Apache-2.0','Strong all-rounder for its size with a long context window.'),
 ('qwen3:8b','Qwen3',['chat','writing','reasoning','tools'],5.2,40960,'Apache-2.0','Best general quality here; needs about 7 GB of GPU or system memory.'),
 ('phi4-mini:3.8b','Phi-4',['reasoning','chat','tools'],2.5,131072,'MIT','Compact model tuned for maths and logical reasoning.'),
 ('granite3.3:2b','Granite 3.3',['chat','writing','tools'],1.5,131072,'Apache-2.0','Small business-oriented model with a long context window.'),
 ('granite3.3:8b','Granite 3.3',['chat','writing','tools'],4.9,131072,'Apache-2.0','Larger Granite for summaries, drafting and tool use.'),
 ('gemma3:1b','Gemma 3',['chat'],0.81,32768,'Gemma Terms of Use','Tiny text model for quick replies on low-memory machines.'),
 ('gemma3:4b','Gemma 3',['chat','writing','vision'],3.4,131072,'Gemma Terms of Use','Multilingual writing model that can also read images.'),
 ('llama3.2:3b','Llama 3.2',['chat','tools'],2.0,131072,'Llama 3.2 Community License','Small Meta model for chat and tool calls.'),
 ('qwen2.5-coder:1.5b','Qwen2.5-Coder',['coding'],1.0,32768,'Apache-2.0','Small code model for completions and short scripts.'),
 ('qwen2.5-coder:7b','Qwen2.5-Coder',['coding'],4.7,32768,'Apache-2.0','Capable local coding assistant.'),
 ('deepseek-r1:1.5b','DeepSeek-R1',['reasoning'],1.1,131072,'MIT','Small step-by-step reasoning model; slower, shows its work.'),
 ('deepseek-r1:7b','DeepSeek-R1',['reasoning'],4.7,131072,'MIT','Stronger step-by-step reasoning for analysis tasks.'),
 ('nomic-embed-text','Nomic Embed',['embedding'],0.27,2048,'Apache-2.0','Embedding model for document and memory search; cannot chat.'),
 ('embeddinggemma:300m','EmbeddingGemma',['embedding'],0.62,2048,'Gemma Terms of Use','Multilingual embedding model; cannot chat.'),
]
ROLES=['chat','coding','reasoning','embedding']

def entry(name):
 """Catalogue entry for an installed Ollama name, treating ':latest' as the untagged name."""
 base=name.removesuffix(':latest')
 return next((c for c in CATALOG if c[0]==base or c[0]==name),None)

def strengths(name):
 found=entry(name);return found[2] if found else []

def required_bytes(size_bytes,context=4096):
 # Same estimate as automatic routing: weights + runtime overhead + KV cache for the context.
 return size_bytes+GIB+context*65536

def memory_budget():
 """Usable bytes from a fresh host hardware sample, or None when unknown."""
 from .maintenance import state
 host=state();hardware=host.get('hardware') or {}
 try:
  from .performance import age
  sample_age=age(hardware.get('sampled_at'))
  if host.get('controller')!='connected' or sample_age is None or sample_age>=90:return None
  totals=[g.get('total_bytes',0) for g in hardware.get('gpus',[]) if g.get('total_bytes',0)>0]
  if totals:return max(totals)*.85
  if hardware.get('memory',{}).get('available_bytes'):return hardware['memory']['available_bytes']*.7
 except (TypeError,ValueError):pass
 return None

def recommendations(installed_names,budget):
 rows=[]
 for name,family,roles,download,context,license,summary in CATALOG:
  size=int(download*GB);need=required_bytes(size)
  url,open_license=LICENSES[license]
  rows.append({'name':name,'family':family,'strengths':roles,'download_bytes':size,'context_length':context,
   'memory_bytes':need,'fits':None if budget is None else need<=budget,'license':license,'license_url':url,
   'open_license':open_license,'summary':summary,
   'installed':name in installed_names or name+':latest' in installed_names})
 # Starter set: per role, the largest fitting model, preferring open licenses.
 starter=[]
 for role in ROLES:
  options=[r for r in rows if role in r['strengths'] and r['fits'] is not False]
  if role!='embedding':options=[r for r in options if r['download_bytes']<=6*GB]
  # Known memory: largest that fits. Unknown memory: smallest, so the first download is safe.
  options.sort(key=lambda r:(r['open_license'],r['download_bytes'] if budget else -r['download_bytes']),reverse=True)
  if options and options[0]['name'] not in starter:starter.append(options[0]['name'])
 for r in rows:r['starter']=r['name'] in starter
 return rows

@router.get('/recommended')
async def recommended():
 try:installed={m['name'] for m in await inference.models()};available=True
 except Exception:installed=set();available=False
 budget=memory_budget()
 return {'available':available,'memory_budget_bytes':budget,'models':recommendations(installed,budget),
  'note':'Sizes are Ollama q4 downloads. Memory is an estimate for a 4K context. License summaries are not legal advice; review each license before use.'}
