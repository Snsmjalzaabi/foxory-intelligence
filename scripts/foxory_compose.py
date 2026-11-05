"""Compose command for this installation: the GPU overlay is added only when Docker can use an NVIDIA GPU."""
import functools,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='compose.local.yaml'
GPU='compose.local.gpu.yaml'

def setting():
 """FOXORY_GPU in the private .env: auto (default), on or off."""
 path=ROOT/'.env'
 if path.exists():
  for line in path.read_text().splitlines():
   key,sep,value=line.partition('=')
   if sep and key.strip()=='FOXORY_GPU':return value.strip().strip('"\'').lower() or 'auto'
 return 'auto'

@functools.lru_cache(maxsize=1)
def gpu_enabled():
 mode=setting()
 if mode in {'on','1','true'}:return True
 if mode in {'off','0','false'}:return False
 if not shutil.which('nvidia-smi') or subprocess.run(['nvidia-smi','-L'],capture_output=True).returncode:return False
 runtimes=subprocess.run(['docker','info','--format','{{json .Runtimes}}'],capture_output=True,text=True)
 try:docker_nvidia='nvidia' in json.loads(runtimes.stdout or '{}')
 except ValueError:docker_nvidia=False
 return docker_nvidia or bool(shutil.which('nvidia-container-cli'))

def compose():
 return ['docker','compose','-f',BASE]+(['-f',GPU] if gpu_enabled() else [])
