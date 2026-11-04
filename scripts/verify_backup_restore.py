"""Verify a private backup by restoring to disposable offline containers/volumes.

Never changes live application volumes or publishes a test database port.
"""
import argparse,hashlib,json,os,secrets,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
from backup_checks import COUNTS_SQL

def execute(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def capture(args):return subprocess.check_output(args,text=True).strip()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path)
    parser.add_argument('--image',default='foxory-postgres:modern-17-community')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();backup=args.backup.resolve()
    manifest=json.loads((backup/'checksums.json').read_text())
    for name,digest in manifest.items():
        if Path(name).name!=name:raise ValueError('Invalid recovery file name')
        if hashlib.sha256((backup/name).read_bytes()).hexdigest()!=digest:raise ValueError('Recovery checksum mismatch: '+name)
    expected=json.loads((backup/'counts.json').read_text())
    uploads={}
    with tarfile.open(backup/'app-data.tar') as archive:
        total=0
        for member in archive:
            path=PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isdir() or member.isfile()):raise ValueError('Unsafe recovery archive member')
            total+=member.size
            if total>2_000_000_000:raise ValueError('Recovery archive exceeds verification budget')
            if member.isfile():uploads[str(path)]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    suffix=secrets.token_hex(6);name='foxory-restore-check-'+suffix;db_volume=name+'-db';app_volume=name+'-app'
    report={'backup':str(backup),'database_counts_match':False,'application_files_match':False,'network':'none','published_ports':False}
    os.umask(0o077)
    try:
        execute(['docker','volume','create',db_volume],stdout=subprocess.DEVNULL)
        execute(['docker','volume','create',app_volume],stdout=subprocess.DEVNULL)
        execute(['docker','run','-d','--pull=never','--name',name,'--network','none','--memory','512m','-e','POSTGRES_USER=foxory','-e','POSTGRES_DB=foxory','-e','POSTGRES_PASSWORD='+secrets.token_hex(24),'-v',db_volume+':/var/lib/postgresql/data',args.image],stdout=subprocess.DEVNULL)
        for i in range(60):
            if subprocess.run(['docker','exec',name,'pg_isready','-U','foxory','-d','foxory'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
            time.sleep(1)
        else:raise RuntimeError('Disposable restore database did not become ready')
        with (backup/'database.dump').open('rb') as stream:
            execute(['docker','exec','-i',name,'pg_restore','-U','foxory','-d','foxory','--exit-on-error','--no-owner','--no-privileges'],stdin=stream,stdout=subprocess.DEVNULL)
        actual=json.loads(capture(['docker','exec',name,'psql','-U','foxory','-d','foxory','-At','-c',COUNTS_SQL]))
        if actual!=expected:raise RuntimeError('Restored database counts or migration do not match the backup')
        report['database_counts_match']=True;report['database_counts']=actual
        with (backup/'app-data.tar').open('rb') as stream:
            execute(['docker','run','--rm','--pull=never','-i','--network','none','-v',app_volume+':/data','alpine:latest','tar','-C','/data','-xf','-'],stdin=stream)
        with subprocess.Popen(['docker','run','--rm','--pull=never','--network','none','-v',app_volume+':/data:ro','alpine:latest','tar','-C','/data','-cf','-','.'],stdout=subprocess.PIPE) as process:
            restored={}
            with tarfile.open(fileobj=process.stdout,mode='r|') as archive:
                for member in archive:
                    if member.isfile():restored[str(PurePosixPath(member.name))]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            if process.wait()!=0:raise RuntimeError('Restored application archive could not be read')
        if restored!=uploads:raise RuntimeError('Restored application file hashes do not match')
        report.update(application_files_match=True,verified_application_files=len(uploads),status='passed')
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')
        print('Recovery verification passed: database/migration counts and',len(uploads),'application file hashes match. Live volumes were not modified.')
    finally:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for volume in [db_volume,app_volume]:subprocess.run(['docker','volume','rm',volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__':main()
