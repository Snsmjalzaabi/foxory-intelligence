"""TLS hostname preservation for IP-pinned HTTP proxy tunnels.

httpcore 1.0.x uses the CONNECT target as TLS hostname and does not honor its SNI
extension in proxy tunnels. A per-transport network-stream wrapper preserves
hostname checking without disabling TLS or changing the operator's proxy path.
The private backend hook is pinned/tested with httpcore 1.0.9 in requirements.lock.
"""
from urllib.request import getproxies,proxy_bypass
import httpx
from httpcore._backends.auto import AutoBackend
from httpcore._backends.base import AsyncNetworkStream

class HostnameStream(AsyncNetworkStream):
    def __init__(self,stream,address,hostname):self.stream=stream;self.address=address;self.hostname=hostname
    async def read(self,max_bytes,timeout=None):return await self.stream.read(max_bytes,timeout)
    async def write(self,buffer,timeout=None):return await self.stream.write(buffer,timeout)
    async def aclose(self):return await self.stream.aclose()
    def get_extra_info(self,info):return self.stream.get_extra_info(info)
    async def start_tls(self,ssl_context,server_hostname=None,timeout=None):
        name=self.hostname if server_hostname==self.address else server_hostname
        stream=await self.stream.start_tls(ssl_context=ssl_context,server_hostname=name,timeout=timeout)
        return HostnameStream(stream,self.address,self.hostname)

class HostnameBackend(AutoBackend):
    def __init__(self,address,hostname):super().__init__();self.address=address;self.hostname=hostname
    async def connect_tcp(self,*args,**kwargs):return HostnameStream(await super().connect_tcp(*args,**kwargs),self.address,self.hostname)

def transport(address,hostname,scheme):
    proxies=getproxies()
    proxy=None if proxy_bypass(hostname) else proxies.get(scheme,proxies.get('all'))
    result=httpx.AsyncHTTPTransport(proxy=proxy,trust_env=True,retries=0)
    result._pool._network_backend=HostnameBackend(address,hostname)
    return result
