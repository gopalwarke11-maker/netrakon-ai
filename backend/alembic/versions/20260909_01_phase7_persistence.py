"""Phase 7 persistent cameras, boundaries, alerts, and intrusion events."""

from alembic import op
import sqlalchemy as sa

revision = "20260909_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("cameras", sa.Column("id", sa.String(80), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("sector", sa.String(120), nullable=False), sa.Column("location", sa.String(255), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("stream_url", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("boundaries", sa.Column("id", sa.String(80), primary_key=True), sa.Column("camera_id", sa.String(80), sa.ForeignKey("cameras.id", ondelete="RESTRICT"), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("point_a", sa.JSON(), nullable=False), sa.Column("point_b", sa.JSON(), nullable=False), sa.Column("restricted_side", sa.String(10), nullable=False), sa.Column("severity", sa.String(10), nullable=False), sa.Column("tolerance", sa.Float(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_boundaries_camera_id", "boundaries", ["camera_id"])
    op.create_table("alerts", sa.Column("id", sa.String(80), primary_key=True), sa.Column("event_id", sa.String(80), unique=True), sa.Column("camera_id", sa.String(80), sa.ForeignKey("cameras.id", ondelete="SET NULL")), sa.Column("boundary_id", sa.String(80), sa.ForeignKey("boundaries.id", ondelete="SET NULL")), sa.Column("sector", sa.String(120), nullable=False), sa.Column("type", sa.String(80), nullable=False), sa.Column("source", sa.String(80), nullable=False), sa.Column("severity", sa.String(10), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("track_id", sa.String(80)), sa.Column("confidence", sa.Float()), sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("intrusion_events", sa.Column("id", sa.String(80), primary_key=True), sa.Column("camera_id", sa.String(80), sa.ForeignKey("cameras.id", ondelete="SET NULL")), sa.Column("boundary_id", sa.String(80), sa.ForeignKey("boundaries.id", ondelete="SET NULL")), sa.Column("boundary_name", sa.String(120), nullable=False), sa.Column("track_id", sa.Integer(), nullable=False), sa.Column("object_class", sa.String(80), nullable=False), sa.Column("confidence", sa.Float()), sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False), sa.Column("previous_anchor", sa.JSON(), nullable=False), sa.Column("current_anchor", sa.JSON(), nullable=False), sa.Column("crossing_direction", sa.String(40), nullable=False), sa.Column("severity", sa.String(10), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("event_type", sa.String(80), nullable=False), sa.Column("alert_id", sa.String(80), unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for table, columns in {"alerts": ["camera_id", "boundary_id", "track_id", "timestamp", "severity", "status"], "intrusion_events": ["camera_id", "boundary_id", "track_id", "timestamp", "severity"]}.items():
        for column in columns: op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_index("ix_intrusion_events_camera_timestamp", "intrusion_events", ["camera_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("intrusion_events")
    op.drop_table("alerts")
    op.drop_table("boundaries")
    op.drop_table("cameras")
