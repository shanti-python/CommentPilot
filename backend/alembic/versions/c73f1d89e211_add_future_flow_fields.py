"""add future flow fields

Revision ID: c73f1d89e211
Revises: 2383643a4f02
Create Date: 2026-09-02 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c73f1d89e211'
down_revision = '2383643a4f02'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('automation_flows', sa.Column('is_future_flow', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('automation_flows', sa.Column('future_post_caption', sa.Text(), nullable=True))
    op.add_column('automation_flows', sa.Column('future_post_scheduled_at', sa.DateTime(), nullable=True))
    op.add_column('automation_flows', sa.Column('future_flow_status', sa.String(), nullable=True))
    op.add_column('automation_flows', sa.Column('future_flow_last_scanned_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('automation_flows', 'future_flow_last_scanned_at')
    op.drop_column('automation_flows', 'future_flow_status')
    op.drop_column('automation_flows', 'future_post_scheduled_at')
    op.drop_column('automation_flows', 'future_post_caption')
    op.drop_column('automation_flows', 'is_future_flow')
