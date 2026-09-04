"""add_on_delete_cascade_to_asset_fks

Add ON DELETE CASCADE to all foreign keys referencing assets.id
so that deleting an asset removes its child rows (components,
connections, documents, photos, interfaces, capabilities).

Revision ID: add_cascade_asset_fks
Revises: add_tenant_id_vulns
Create Date: 2026-09-04 15:00:00.000000

"""
from alembic import op


revision = 'add_cascade_asset_fks'
down_revision = 'add_tenant_id_vulns'
branch_labels = None
depends_on = None


# Tables that have FKs pointing at assets.id and need ON DELETE CASCADE
TABLES_WITH_ASSET_FK = [
    'asset_components',
    'asset_connections',
    'asset_documents',
    'asset_photos',
    'asset_interfaces',
    'asset_capabilities',
]


def upgrade() -> None:
    for table in TABLES_WITH_ASSET_FK:
        # Find the FK constraint name dynamically
        rows = op.get_bind().execute(
            f"""
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = '{table}'::regclass
              AND contype = 'f'
              AND pg_get_constraintdef(oid) LIKE '%REFERENCES assets%'
            """
        ).fetchall()
        for (conname,) in rows:
            op.execute(f'ALTER TABLE {table} DROP CONSTRAINT {conname}')
            op.execute(
                f'ALTER TABLE {table} ADD CONSTRAINT {conname} '
                f'FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE'
            )


def downgrade() -> None:
    # Revert: remove CASCADE
    for table in TABLES_WITH_ASSET_FK:
        rows = op.get_bind().execute(
            f"""
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = '{table}'::regclass
              AND contype = 'f'
              AND pg_get_constraintdef(oid) LIKE '%REFERENCES assets%'
            """
        ).fetchall()
        for (conname,) in rows:
            op.execute(f'ALTER TABLE {table} DROP CONSTRAINT {conname}')
            op.execute(
                f'ALTER TABLE {table} ADD CONSTRAINT {conname} '
                f'FOREIGN KEY (asset_id) REFERENCES assets(id)'
            )
