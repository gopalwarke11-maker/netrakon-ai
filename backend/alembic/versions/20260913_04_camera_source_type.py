"""Add explicit camera source type."""

from alembic import op
import sqlalchemy as sa

revision = "20260913_04"
down_revision = "20260912_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cameras",
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="FILE"),
    )


def downgrade() -> None:
    op.drop_column("cameras", "source_type")
