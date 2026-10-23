"""Accounts, sessions, memberships and scoped audit history; preserves legacy workspace."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('users',sa.Column('id',sa.String(36),primary_key=True),sa.Column('username',sa.String(100),unique=True,nullable=False),sa.Column('password_hash',sa.Text,nullable=False),sa.Column('created_at',sa.String(40),nullable=False))
    op.create_table('workspaces',sa.Column('id',sa.String(36),primary_key=True),sa.Column('name',sa.String(100),nullable=False))
    op.create_table('memberships',sa.Column('workspace_id',sa.String(36),sa.ForeignKey('workspaces.id',ondelete='CASCADE'),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),primary_key=True),sa.Column('role',sa.String(16),nullable=False))
    op.create_table('login_sessions',sa.Column('token_hash',sa.String(64),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('expires_at',sa.String(40),nullable=False),sa.Column('csrf',sa.String(64),nullable=False))
    op.add_column('audit',sa.Column('workspace',sa.String(36),server_default='local',nullable=False))
    op.execute("INSERT INTO workspaces (id,name) VALUES ('local','Local workspace')")

def downgrade():
    op.drop_column('audit','workspace')
    for table in ['login_sessions','memberships','workspaces','users']:op.drop_table(table)
