"""Add tenant_id to vulnerabilities

Adds tenant_id to the vulnerabilities table for tenant-scoped isolation.
Drops the global unique constraint on cve_id and replaces it with a
composite unique constraint on (tenant_id, cve_id).

Revision ID: add_tenant_id_vulns
Revises: add_installation_date_to_components
Create Date: 2026-09-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_tenant_id_vulns'
down_revision: Union[str, None] = 'add_installation_date_to_components'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen alembic version_num to accommodate longer revision names.
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")

    # Step 1: Add tenant_id column as nullable (allows backfill)
    op.add_column(
        'vulnerabilities',
        sa.Column('tenant_id', sa.UUID(), nullable=True),
    )

    # Step 2: Backfill existing rows with the first tenant's ID
    op.execute("""
        UPDATE vulnerabilities
        SET tenant_id = (SELECT id FROM tenants LIMIT 1)
        WHERE tenant_id IS NULL
    """)

    # Step 3: Make tenant_id NOT NULL
    op.alter_column('vulnerabilities', 'tenant_id', nullable=False)

    # Step 4: Add foreign key to tenants(id) with CASCADE delete
    op.create_foreign_key(
        'fk_vulnerabilities_tenant_id',
        'vulnerabilities', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )

    # Step 5: Drop the global unique constraint on cve_id alone
    op.execute("ALTER TABLE vulnerabilities DROP CONSTRAINT IF EXISTS vulnerabilities_cve_id_key")

    # Step 6: Add composite unique constraint on (tenant_id, cve_id)
    op.execute("""
        ALTER TABLE vulnerabilities
        ADD CONSTRAINT uq_vulnerabilities_tenant_cve UNIQUE (tenant_id, cve_id)
    """)


def downgrade() -> None:
    # Drop composite unique constraint
    op.execute("ALTER TABLE vulnerabilities DROP CONSTRAINT IF EXISTS uq_vulnerabilities_tenant_cve")

    # Re-add global unique constraint on cve_id (for downgrade compatibility)
    op.execute("""
        ALTER TABLE vulnerabilities
        ADD CONSTRAINT vulnerabilities_cve_id_key UNIQUE (cve_id)
    """)

    # Drop FK constraint
    op.drop_constraint('fk_vulnerabilities_tenant_id', 'vulnerabilities', type_='foreignkey')

    # Drop tenant_id column
    op.drop_column('vulnerabilities', 'tenant_id')

    # Note: we don't revert the version_num widening — other migrations
    # may have taken advantage of the larger size. Downgrading that is
    # out of scope for this migration.
