"""Fixed read-only host counters. No application commands or user data."""
import csv,datetime,os,subprocess
from pathlib import Path
def collect():
 result={'sampled_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gpus':[],'gpu_status':'unavailable'}
 try:
  fields=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines());result['memory']={k:int(fields[v].strip().split()[0])*1024 for k,v in [('total_bytes','MemTotal'),('available_bytes','MemAvailable')]};result['load_average']=list(os.getloadavg())
 except (OSError,ValueError,KeyError):pass
 try:
  p=subprocess.run(['/usr/bin/nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3,check=True)
  for row in list(csv.reader(p.stdout[:16000].splitlines()))[:16]:
   name,total,used,util,temp=row;result['gpus'].append({'name':name.strip(),'total_bytes':int(total)*1024**2,'used_bytes':int(used)*1024**2,'utilization_percent':float(util),'temperature_c':float(temp)})
  result['gpu_status']='measured' if result['gpus'] else 'unavailable'
 except (OSError,ValueError,subprocess.SubprocessError):pass
 return result
