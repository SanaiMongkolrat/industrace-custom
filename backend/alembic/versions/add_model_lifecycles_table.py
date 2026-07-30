"""add_model_lifecycles_table

Revision ID: add_model_lifecycles
Revises: add_mfa_totp
Create Date: 2026-07-30 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_model_lifecycles'
down_revision: Union[str, None] = 'add_mfa_totp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create model_lifecycles table for tracking lifecycle per model."""
    op.create_table('model_lifecycles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=True),
        sa.Column('manufacturer_id', sa.UUID(), nullable=False),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('lifecycle_status', sa.String(length=20), nullable=False, server_default='in_support'),
        sa.Column('status_date', sa.Date(), nullable=True),
        sa.Column('end_of_life_date', sa.Date(), nullable=True),
        sa.Column('end_of_support_date', sa.Date(), nullable=True),
        sa.Column('spare_part_availability', sa.String(length=20), nullable=True),
        sa.Column('replacement_model', sa.String(length=255), nullable=True),
        sa.Column('replacement_manufacturer_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_reviewed_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['manufacturer_id'], ['manufacturers.id'], ),
        sa.ForeignKeyConstraint(['replacement_manufacturer_id'], ['manufacturers.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_model_lifecycles_manufacturer',
        'model_lifecycles',
        ['manufacturer_id'],
    )
    op.create_index(
        'idx_model_lifecycles_status',
        'model_lifecycles',
        ['lifecycle_status'],
    )


def downgrade() -> None:
    """Drop model_lifecycles table."""
    op.drop_index('idx_model_lifecycles_status', table_name='model_lifecycles')
    op.drop_index('idx_model_lifecycles_manufacturer', table_name='model_lifecycles')
    op.drop_table('model_lifecycles')
