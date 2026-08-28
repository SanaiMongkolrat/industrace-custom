"""Add installation_date to asset_components

Records when each component slot was installed in its parent asset. In-place
update semantics — when a component is replaced in the field, the user edits
the row and overwrites the installation_date (no append-only history).

Revision ID: add_installation_date_to_components
Revises: add_asset_components
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_installation_date_to_components'
down_revision: Union[str, None] = 'add_asset_components'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable Date column to asset_components."""
    # Widen alembic version_num to accommodate longer revision names.
    # The default VARCHAR(32) truncates revision IDs like
    # 'add_installation_date_to_components' (39 chars).
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")
    op.add_column(
        'asset_components',
        sa.Column('installation_date', sa.Date(), nullable=True),
    )


def downgrade() -> None:
    """Drop the installation_date column."""
    op.drop_column('asset_components', 'installation_date')
    # Note: we don't revert the version_num widening — other migrations
    # may have taken advantage of the larger size. Downgrading that is
    # out of scope for this migration.