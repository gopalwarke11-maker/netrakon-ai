"""Phase 8: Add risk assessment fields to intrusion events and alerts.

Revision ID: 20260912_02
Revises: 20260909_01
Create Date: 2026-09-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260912_02'
down_revision = '20260909_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add risk fields to intrusion_events table
    op.add_column('intrusion_events', sa.Column('risk_score', sa.Integer(), nullable=True))
    op.add_column('intrusion_events', sa.Column('risk_level', sa.String(length=10), nullable=True))
    op.add_column('intrusion_events', sa.Column('risk_factors', sa.JSON(), nullable=True))
    op.create_index('ix_intrusion_events_risk_level', 'intrusion_events', ['risk_level'])
    
    # Add risk fields to alerts table for consistency
    op.add_column('alerts', sa.Column('risk_score', sa.Integer(), nullable=True))
    op.add_column('alerts', sa.Column('risk_level', sa.String(length=10), nullable=True))
    op.create_index('ix_alerts_risk_level', 'alerts', ['risk_level'])


def downgrade() -> None:
    # Remove risk indices and fields from alerts
    op.drop_index('ix_alerts_risk_level', table_name='alerts')
    op.drop_column('alerts', 'risk_level')
    op.drop_column('alerts', 'risk_score')
    
    # Remove risk indices and fields from intrusion_events
    op.drop_index('ix_intrusion_events_risk_level', table_name='intrusion_events')
    op.drop_column('intrusion_events', 'risk_factors')
    op.drop_column('intrusion_events', 'risk_level')
    op.drop_column('intrusion_events', 'risk_score')
