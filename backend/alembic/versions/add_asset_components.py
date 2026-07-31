"""Add asset_components table for BOM (Bill of Materials)

Revision ID: add_asset_components
Revises: add_useful_life_asset_type
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_asset_components'
down_revision: Union[str, None] = 'add_useful_life_asset_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('asset_components',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('model_lifecycle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_lifecycles.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_asset_components_asset_id', 'asset_components', ['asset_id'])
    op.create_index('ix_asset_components_model_lifecycle_id', 'asset_components', ['model_lifecycle_id'])


def downgrade() -> None:
    op.drop_index('ix_asset_components_model_lifecycle_id', table_name='asset_components')
    op.drop_index('ix_asset_components_asset_id', table_name='asset_components')
    op.drop_table('asset_components')
