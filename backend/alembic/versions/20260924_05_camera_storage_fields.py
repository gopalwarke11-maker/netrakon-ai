"""Add storage_key and storage_metadata to cameras table."""

from alembic import op
import sqlalchemy as sa

revision = "20260924_05"
down_revision = "20260913_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cameras", sa.Column("storage_key", sa.String(length=255), nullable=True))
    op.add_column("cameras", sa.Column("storage_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("cameras", "storage_metadata")
    op.drop_column("cameras", "storage_key")
