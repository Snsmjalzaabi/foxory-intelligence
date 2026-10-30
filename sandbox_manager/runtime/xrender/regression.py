"""Controlled Xvfb/X11 relay regression; no public or host display is contacted."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import struct
import subprocess
import time


def malicious_reply(packet: bytes, endian: str) -> bytes:
    """Preserve a real reply, adding exactly one excess subpixel entry."""
    if len(packet)<32 or packet[0]!=1 or endian not in {'<','>'}:
        raise ValueError('Invalid controlled X11 reply')
    length=struct.unpack_from(endian+'I',packet,4)[0]
    screens=struct.unpack_from(endian+'I',packet,12)[0]
    subpixels=struct.unpack_from(endian+'I',packet,24)[0]
    if len(packet)!=32+length*4 or not 0<screens<16 or screens!=subpixels or length>250000:
        raise ValueError('Unexpected controlled Xvfb formats reply')
    modified=bytearray(packet)
    struct.pack_into(endian+'I',modified,4,length+1)
    struct.pack_into(endian+'I',modified,24,subpixels+1)
    return bytes(modified)+struct.pack(endian+'I',0)


async def case(binary: str, library: str, attack: bool, vulnerable: bool) -> dict:
    proxy=Path('/tmp/.X11-unix/X102')
    if proxy.exists():raise RuntimeError('Controlled proxy socket already exists')
    state={'intercepted':False};errors=[];connections=[]
    async def relay(reader,writer):
        connections.append(writer)
        upstream=None
        try:
            prefix=await reader.readexactly(12)
            if prefix[0] not in (ord('l'),ord('B')):raise ValueError('X11 byte order')
            endian='<' if prefix[0]==ord('l') else '>'
            name,data=struct.unpack_from(endian+'HH',prefix,6)
            auth_size=((name+3)//4)*4+((data+3)//4)*4
            if auth_size>4096:raise ValueError('X11 setup budget')
            body=await reader.readexactly(auth_size)
            incoming,upstream=await asyncio.open_unix_connection('/tmp/.X11-unix/X101')
            upstream.write(prefix+body);await upstream.drain()
            setup=await incoming.readexactly(8)
            if setup[0]!=1:raise ValueError('Controlled X server setup failed')
            setup_length=struct.unpack_from(endian+'H',setup,6)[0]*4
            if setup_length>1_000_000:raise ValueError('X11 setup reply budget')
            writer.write(setup+await incoming.readexactly(setup_length));await writer.drain()
            request={'seq':0,'query_extension':None,'opcode':None,'formats':None}
            async def client_packets():
                while True:
                    header=await reader.readexactly(4)
                    size=struct.unpack_from(endian+'H',header,2)[0]*4
                    if not 4<=size<=1_000_000:raise ValueError('X11 request budget')
                    packet=header+await reader.readexactly(size-4)
                    request['seq']+=1
                    if packet[0]==98 and packet[8:14]==b'RENDER':request['query_extension']=request['seq']
                    if packet[0]==request['opcode'] and packet[1]==1:request['formats']=request['seq']
                    upstream.write(packet);await upstream.drain()
            async def server_packets():
                while True:
                    packet=await incoming.readexactly(32)
                    kind=packet[0]&0x7f
                    size=struct.unpack_from(endian+'I',packet,4)[0]*4 if kind in (1,35) else 0
                    if size>1_000_000:raise ValueError('X11 server packet budget')
                    packet+=await incoming.readexactly(size)
                    seq=struct.unpack_from(endian+'H',packet,2)[0]
                    if kind==1 and seq==request['query_extension']:
                        if packet[8]!=1:raise ValueError('Xvfb RENDER extension missing')
                        request['opcode']=packet[9]
                    if kind==1 and seq==request['formats']:
                        state['intercepted']=True
                        if attack:packet=malicious_reply(packet,endian)
                    writer.write(packet);await writer.drain()
            tasks=[asyncio.create_task(client_packets()),asyncio.create_task(server_packets())]
            _,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
            for task in pending:task.cancel()
            results=await asyncio.gather(*tasks,return_exceptions=True)
            for result in results:
                if isinstance(result,Exception) and not isinstance(result,(asyncio.IncompleteReadError,ConnectionError)):
                    errors.append(type(result).__name__+': '+str(result))
        except (asyncio.IncompleteReadError,ConnectionError):pass
        except Exception as exc:errors.append(type(exc).__name__+': '+str(exc))
        finally:
            writer.close()
            if upstream:upstream.close()
    server=await asyncio.start_unix_server(relay,str(proxy))
    try:
        env={**os.environ,'DISPLAY':':102','XAUTHORITY':'/nonexistent/foxory-fixture',
             'LD_LIBRARY_PATH':library,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1',
             'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
        process=await asyncio.create_subprocess_exec(binary,'reject' if attack else 'healthy',env=env,
                    stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        try:out,err=await asyncio.wait_for(process.communicate(),10)
        except TimeoutError:
            process.kill();await process.wait();raise RuntimeError('Controlled Xrender client deadline') from None
        if len(out)>32000 or len(err)>32000:raise ValueError('Controlled client output budget')
        if errors or not state['intercepted']:raise RuntimeError('X11 fixture failed: '+str(errors))
        report={'attack':attack,'exit_code':process.returncode,'formats_reply_observed':True}
        if vulnerable:
            if process.returncode==0 or b'AddressSanitizer' not in err or b'heap-buffer-overflow' not in err:
                raise RuntimeError('Vulnerable control did not reproduce the expected ASan overflow: '+err.decode()[-4000:])
            report['expected_baseline_overflow_reproduced']=True
        elif process.returncode!=0 or b'AddressSanitizer' in err or b'runtime error:' in err:
            raise RuntimeError('Fixed Xrender regression failed: '+err.decode()[-4000:])
        else:report['fixed_client_result']=json.loads(out)
        return report
    finally:
        server.close();await server.wait_closed()
        for writer in connections:writer.close()
        proxy.unlink(missing_ok=True)


async def run(args) -> None:
    rows=[]
    if not args.vulnerable:rows.append(await case(args.binary,args.library,False,False))
    rows.append(await case(args.binary,args.library,True,args.vulnerable))
    print(json.dumps({'status':'passed','cases':rows}))


if __name__=='__main__':
    if os.environ.get('FOXORY_WORKER_IMAGE_BUILD')!='1' or os.getuid()!=1000:
        raise SystemExit('Non-root image-build-only X11 fixture; never run against an owner display')
    parser=argparse.ArgumentParser();parser.add_argument('--binary',required=True);parser.add_argument('--library',required=True);parser.add_argument('--vulnerable',action='store_true');args=parser.parse_args()
    sockets=Path('/tmp/.X11-unix');sockets.mkdir(exist_ok=True)
    if (sockets/'X101').exists():raise RuntimeError('Controlled Xvfb socket already exists')
    server=subprocess.Popen(['Xvfb',':101','-screen','0','64x64x24','-nolisten','tcp','-ac','-noreset'],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+5
        while not (sockets/'X101').exists():
            if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Controlled Xvfb startup failed')
            time.sleep(.05)
        asyncio.run(run(args))
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
