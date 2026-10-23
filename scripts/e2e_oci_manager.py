"""Explicit test executable: real manager with a deterministic mocked OCI engine."""
from scripts.oci_fixture import Engine
from sandbox_manager import service
import uvicorn

class Patcher:
    def setattr(self,target,name,value):setattr(target,name,value)

engine=Engine();engine.install(Patcher())
if __name__=='__main__':
    uvicorn.run(service.app,host='127.0.0.1',port=8104,workers=1)
