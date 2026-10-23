"""Request scope is fail-closed; only the internal worker can explicitly bypass it."""
from contextvars import ContextVar
from contextlib import contextmanager
workspace_id: ContextVar[str] = ContextVar('workspace_id', default='__unauthorized__')
system_access: ContextVar[bool] = ContextVar('system_access', default=False)

@contextmanager
def system_scope():
    token=system_access.set(True)
    try: yield
    finally: system_access.reset(token)

actor_id: ContextVar[str] = ContextVar('actor_id',default='internal')
