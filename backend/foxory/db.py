import json
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, event, Column, String, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}, pool_pre_ping=True)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def sqlite_settings(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
Session = sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()
def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc).isoformat()

class Record(Base):
    __tablename__ = "records"
    id = Column(String(36), primary_key=True, default=uid)
    dedupe_key = Column(String(300), nullable=True)
    __table_args__ = (Index("uq_record_dedupe", "workspace", "kind", "dedupe_key", unique=True),)
    kind = Column(String(32), nullable=False, index=True)
    workspace = Column(String(36), nullable=False, default="local", index=True)
    title = Column(String(300), nullable=False)
    payload = Column(Text, nullable=False, default="{}")
    created_at = Column(String(40), nullable=False, default=now)
    updated_at = Column(String(40), nullable=False, default=now)
    def public(self):
        return dict(id=self.id, kind=self.kind, title=self.title, data=json.loads(self.payload), created_at=self.created_at, updated_at=self.updated_at)

class Message(Base):
    __tablename__ = "messages"
    id = Column(String(36), primary_key=True, default=uid)
    conversation_id = Column(String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(String(40), nullable=False, default=now)
    def public(self): return dict(id=self.id, role=self.role, content=self.content, metadata=json.loads(self.metadata_json), created_at=self.created_at)

class Audit(Base):
    __tablename__ = "audit"
    id = Column(String(36), primary_key=True, default=uid)
    action = Column(String(100), nullable=False)
    target = Column(String(100), nullable=False)
    detail = Column(Text, nullable=False, default="{}")
    created_at = Column(String(40), nullable=False, default=now)

def audit(s, action, target, **detail): s.add(Audit(action=action, target=target, detail=json.dumps(detail)))
def get_record(s, id, kind=None):
    r = s.get(Record, id)
    if not r or r.workspace != "local" or (kind and r.kind != kind):
        from fastapi import HTTPException
        raise HTTPException(404, "Record not found")
    return r
