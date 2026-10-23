"""Initial durable workspace schema."""
from alembic import op
import sqlalchemy as sa
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("records", sa.Column("id", sa.String(36), primary_key=True), sa.Column("kind", sa.String(32), nullable=False), sa.Column("workspace", sa.String(36), nullable=False), sa.Column("title", sa.String(300), nullable=False), sa.Column("payload", sa.Text, nullable=False), sa.Column("created_at", sa.String(40), nullable=False), sa.Column("updated_at", sa.String(40), nullable=False))
    op.create_index("ix_records_kind", "records", ["kind"])
    op.create_index("ix_records_workspace", "records", ["workspace"])
    op.create_table("messages", sa.Column("id", sa.String(36), primary_key=True), sa.Column("conversation_id", sa.String(36), sa.ForeignKey("records.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("content", sa.Text, nullable=False), sa.Column("metadata_json", sa.Text, nullable=False), sa.Column("created_at", sa.String(40), nullable=False))
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table("audit", sa.Column("id", sa.String(36), primary_key=True), sa.Column("action", sa.String(100), nullable=False), sa.Column("target", sa.String(100), nullable=False), sa.Column("detail", sa.Text, nullable=False), sa.Column("created_at", sa.String(40), nullable=False))

def downgrade():
    op.drop_table("audit")
    op.drop_table("messages")
    op.drop_table("records")
