"""Add token_hash and expires_at to password_reset_requests table."""

from alembic import op
import sqlalchemy as sa

revision = "20260928_07"
down_revision = "20260927_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("password_reset_requests", sa.Column("token_hash", sa.String(length=255), nullable=True))
    op.add_column("password_reset_requests", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_password_reset_requests_token_hash", "password_reset_requests", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_requests_token_hash", table_name="password_reset_requests")
    op.drop_column("password_reset_requests", "expires_at")
    op.drop_column("password_reset_requests", "token_hash")
