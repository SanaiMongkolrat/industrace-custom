"""Add useful_life_years and asset_type_id to model_lifecycles

Revision ID: add_useful_life_asset_type
Revises: merge_all_heads
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_useful_life_asset_type'
down_revision: Union[str, None] = 'add_model_lifecycles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add useful_life_years column (replaces end_of_life_date)
    op.add_column('model_lifecycles', sa.Column('useful_life_years', sa.Integer(), nullable=True))
    
    # Add asset_type_id FK column
    op.add_column('model_lifecycles', sa.Column('asset_type_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_model_lifecycles_asset_type_id'), 'model_lifecycles', ['asset_type_id'], unique=False)
    op.create_foreign_key('fk_model_lifecycles_asset_type_id', 'model_lifecycles', 'asset_types', ['asset_type_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_model_lifecycles_asset_type_id', 'model_lifecycles', type_='foreignkey')
    op.drop_index(op.f('ix_model_lifecycles_asset_type_id'), table_name='model_lifecycles')
    op.drop_column('model_lifecycles', 'asset_type_id')
    op.drop_column('model_lifecycles', 'useful_life_years')
