"""Atomic duplicate prevention for leads and pending draft reviews."""
import json
import hashlib
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('records',sa.Column('dedupe_key',sa.String(300),nullable=True))
    connection=op.get_bind()
    rows=connection.execute(sa.text("SELECT id, workspace, kind, title, payload FROM records WHERE kind IN ('lead','approval')")).mappings().all()
    seen=set()
    for r in rows:
        data=json.loads(r['payload'])
        key=str(data.get('email') or r['title']).strip().casefold() if r['kind']=='lead' else data.get('draft_id') if data.get('status')=='pending' else None
        if key is None:continue
        unique=(r['workspace'],r['kind'],key)
        if unique in seen:raise ValueError('Existing duplicate records must be resolved before migration 0002; no data removed')
        seen.add(unique)
        connection.execute(sa.text('UPDATE records SET dedupe_key=:key WHERE id=:id'),{'key':hashlib.sha256(key.encode()).hexdigest() if r['kind']=='lead' else key,'id':r['id']})
    op.create_index('uq_record_dedupe','records',['workspace','kind','dedupe_key'],unique=True)

def downgrade():
    op.drop_index('uq_record_dedupe',table_name='records')
    op.drop_column('records','dedupe_key')
