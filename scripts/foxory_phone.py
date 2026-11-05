"""Open FOXORY on your phone over private HTTPS with Tailscale. Only your own devices can reach it."""
import argparse,json,shutil,subprocess
from foxory_compose import compose
from foxory_ai import ROOT,update_env

APP='http://127.0.0.1:3636'

def tailscale_name():
 """This PC's private HTTPS name on your tailnet, or an explanation of what is missing."""
 if not shutil.which('tailscale'):raise SystemExit('Tailscale is not installed. Install it from https://tailscale.com/download, sign in on this PC and on your phone, then run this again.')
 info=json.loads(subprocess.run(['tailscale','status','--json'],capture_output=True,text=True,check=True).stdout)
 if info.get('BackendState')!='Running':raise SystemExit('Tailscale is not connected. Run "sudo tailscale up", then run this again.')
 name=(info.get('Self') or {}).get('DNSName','').rstrip('.')
 if not name:raise SystemExit('Tailscale has no DNS name for this PC. Enable MagicDNS and HTTPS certificates in the Tailscale admin console.')
 return name

def env_list(key):
 for line in (ROOT/'.env').read_text().splitlines():
  if line.startswith(key+'='):return [x for x in line.split('=',1)[1].strip().strip('"\'').split(',') if x]
 return []

def hosts_with(name,add=True):
 hosts=env_list('FOXORY_ALLOWED_HOSTS') or ['localhost','127.0.0.1','[::1]']
 hosts=[h for h in hosts if h!=name]+([name] if add else [])
 return ','.join(hosts)

def restart_app():
 subprocess.run([*compose(),'up','-d','--no-build','app'],cwd=ROOT,check=True)

def enable():
 name=tailscale_name()
 # Serves https://<name>/ to devices on your tailnet only; this never opens a port to your LAN or the internet.
 subprocess.run(['tailscale','serve','--bg',APP],check=True)
 update_env({'FOXORY_ALLOWED_HOSTS':hosts_with(name),'FOXORY_PUBLIC_ORIGINS':'https://'+name})
 restart_app()
 print(f'Open https://{name} on your phone (signed in to the same Tailscale account), sign in to FOXORY,\nthen use the browser menu "Add to Home Screen" or "Install app".')

def disable():
 name=tailscale_name()
 # Turns off only this HTTPS route; other Tailscale serve settings are left alone.
 subprocess.run(['tailscale','serve','--https=443','off'],check=True)
 update_env({'FOXORY_ALLOWED_HOSTS':hosts_with(name,add=False),'FOXORY_PUBLIC_ORIGINS':''})
 restart_app();print('Phone access is off. FOXORY is reachable only on this PC again.')

def status():
 name=tailscale_name();origins=env_list('FOXORY_PUBLIC_ORIGINS')
 print(f'Tailscale name: {name}\nPhone access: '+('on at https://'+name if 'https://'+name in origins else 'off (run: python3 scripts/foxory_phone.py enable)'))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['status','enable','disable']);args=p.parse_args()
 {'status':status,'enable':enable,'disable':disable}[args.action]()
if __name__=='__main__':main()
