"""Install the pinned, local-only speech-to-text service (whisper.cpp). Audio never leaves this PC."""
import argparse,json,re,subprocess
from foxory_compose import compose
from pathlib import Path
from foxory_ai import ROOT,download_pinned,update_env,wait_ready

def metadata():return json.loads((ROOT/'deployment/whisper/manifest.json').read_text())
def version():
 value=(ROOT/'VERSION').read_text().strip()
 if not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Invalid source version')
 return value
def download():return download_pinned(metadata()['model'])
def build():
 image='foxory-local-app:'+version()
 if subprocess.run(['docker','image','inspect',image],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  subprocess.run(['docker','build','--target','application','-t',image,'.'],cwd=ROOT,check=True)
 subprocess.run(['docker','build','-f','deployment/whisper/Dockerfile','--build-arg','FOXORY_APP_IMAGE='+image,'-t','foxory-whisper-cpu:'+version(),'.'],cwd=ROOT,check=True)
def enable():
 if not (ROOT/'.env').exists():raise ValueError('Use the existing FOXORY installation and its private .env')
 download();build()
 update_env({'FOXORY_WHISPER_URL':'http://127.0.0.1:11437','FOXORY_WHISPER_IMAGE':'foxory-whisper-cpu:'+version(),'FOXORY_AI_APP_IMAGE':'foxory-local-app:'+version()},'voice')
 subprocess.run([*compose(),'up','-d','whisper'],cwd=ROOT,check=True)
 wait_ready('http://127.0.0.1:11437/health','Voice service')
 subprocess.run([*compose(),'up','-d','--no-build','app'],cwd=ROOT,check=True)
 print('Voice enabled. Use the microphone button in chat; speech is transcribed on this PC.')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['download','build','enable']);args=p.parse_args()
 {'download':download,'build':build,'enable':enable}[args.action]()
if __name__=='__main__':main()
