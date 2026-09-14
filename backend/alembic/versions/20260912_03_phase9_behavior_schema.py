"""Phase 9 behavior analysis schema migration.

Revision ID: 20260912_03
Revises: 20260912_02
Create Date: 2026-09-12

Adds behavior_observations table for storing behavior analysis results.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260912_03"
down_revision = "20260912_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create behavior_observations table."""
    op.create_table(
        "behavior_observations",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("camera_id", sa.String(80), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("intrusion_event_id", sa.String(80), nullable=True),
        sa.Column("behavior_type", sa.String(30), nullable=False),
        sa.Column("behavior_score", sa.Integer(), nullable=False),
        sa.Column("observations", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("duration_window_seconds", sa.Float(), nullable=False),
        sa.Column(
            "assessed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indices for efficient querying
    op.create_index(
        "ix_behavior_observations_camera_id",
        "behavior_observations",
        ["camera_id"],
    )
    op.create_index(
        "ix_behavior_observations_track_id",
        "behavior_observations",
        ["track_id"],
    )
    op.create_index(
        "ix_behavior_observations_intrusion_event_id",
        "behavior_observations",
        ["intrusion_event_id"],
    )
    op.create_index(
        "ix_behavior_observations_behavior_type",
        "behavior_observations",
        ["behavior_type"],
    )
    op.create_index(
        "ix_behavior_observations_behavior_score",
        "behavior_observations",
        ["behavior_score"],
    )
    op.create_index(
        "ix_behavior_observations_camera_track",
        "behavior_observations",
        ["camera_id", "track_id"],
    )
    op.create_index(
        "ix_behavior_observations_created_at",
        "behavior_observations",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop behavior_observations table."""
    op.drop_index("ix_behavior_observations_created_at", table_name="behavior_observations")
    op.drop_index("ix_behavior_observations_camera_track", table_name="behavior_observations")
    op.drop_index("ix_behavior_observations_behavior_score", table_name="behavior_observations")
    op.drop_index("ix_behavior_observations_behavior_type", table_name="behavior_observations")
    op.drop_index("ix_behavior_observations_intrusion_event_id", table_name="behavior_observations")
    op.drop_index("ix_behavior_observations_track_id", table_name="behavior_observations")
    op.drop_index("ix_behavior_observations_camera_id", table_name="behavior_observations")
    op.drop_table("behavior_observations")
