"""add_v_component_lifecycle_status_documentation

Revision ID: add_v_component_lifecycle_status_doc
Revises: merge_all_heads
Create Date: 2026-09-07 10:00:00.000000

Creates dashboard.v_component_lifecycle_status as a DOCUMENTATION ARTIFACT
and ad-hoc query helper for DB users. NOT used by the FastAPI endpoint
(the application uses inline SQLAlchemy CRUD with explicit tenant filter).

This view is NOT tenant-safe. Do not query directly from application code.
Application code MUST filter by tenant_id explicitly at the query layer.

The view exists for:
- Ad-hoc psql queries by admins
- Documentation of the lifecycle computation (matches the SQL pattern
  used in the live test on 2026-09-04)
- Future migration if the application layer ever moves back to a view

Usage:
    psql -c "SELECT * FROM dashboard.v_component_lifecycle_status LIMIT 10;"
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_v_component_lifecycle_status_doc'
down_revision: Union[str, None] = 'merge_all_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VIEW_SQL = """
CREATE SCHEMA IF NOT EXISTS dashboard;

CREATE OR REPLACE VIEW dashboard.v_component_lifecycle_status AS
SELECT
    ac.id AS component_id,
    ac.tenant_id,
    ac.quantity,
    COALESCE(ac.installation_date, a.installation_date) AS effective_install_date,

    CASE
        WHEN COALESCE(ac.installation_date, a.installation_date) IS NULL THEN NULL
        ELSE EXTRACT(YEAR FROM AGE(CURRENT_DATE, COALESCE(ac.installation_date, a.installation_date)))::numeric
             + EXTRACT(MONTH FROM AGE(CURRENT_DATE, COALESCE(ac.installation_date, a.installation_date)))::numeric / 12
    END AS lifespan_years,

    CASE
        WHEN at.useful_life_years IS NULL AND ml.useful_life_years IS NULL THEN NULL
        ELSE COALESCE(ml.useful_life_years, at.useful_life_years)
             - CASE
                 WHEN COALESCE(ac.installation_date, a.installation_date) IS NULL THEN 0
                 ELSE EXTRACT(YEAR FROM AGE(CURRENT_DATE, COALESCE(ac.installation_date, a.installation_date)))::numeric
                      + EXTRACT(MONTH FROM AGE(CURRENT_DATE, COALESCE(ac.installation_date, a.installation_date)))::numeric / 12
               END
    END AS years_remaining,

    CASE
        WHEN at.useful_life_inheritance_enabled = FALSE THEN NULL
        ELSE COALESCE(ml.useful_life_years, at.useful_life_years)
    END AS effective_useful_life,

    CASE
        WHEN ml.useful_life_years IS NOT NULL THEN 'model'
        WHEN at.useful_life_years IS NOT NULL AND at.useful_life_inheritance_enabled = TRUE THEN 'inherited_from_asset_type'
        ELSE 'not_set'
    END AS useful_life_source,

    CASE
        WHEN COALESCE(ac.installation_date, a.installation_date) IS NULL THEN 'NORMAL'
        WHEN at.useful_life_inheritance_enabled = FALSE THEN 'NORMAL'
        WHEN COALESCE(ml.useful_life_years, at.useful_life_years) IS NULL THEN 'NORMAL'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, COALESCE(ac.installation_date, a.installation_date)))::numeric
             + EXTRACT(MONTH FROM AGE(CURRENT_DATE, COALESCE(ac.installation_date, a.installation_date)))::numeric / 12
             >= COALESCE(ml.useful_life_years, at.useful_life_years) THEN 'END-OF-LIFE'
        ELSE 'NORMAL'
    END AS lifecycle_status,

    ac.asset_id,
    a.name AS asset_name,
    a.tag AS asset_tag,
    s.name AS plant_name,
    ar.name AS area_name,
    ac.model_lifecycle_id,
    ml.model_name,
    ml.lifecycle_status AS model_eol_status,
    m.name AS manufacturer,
    ml.useful_life_years AS model_useful_life_years,
    at.useful_life_years AS asset_type_useful_life_years,
    at.useful_life_inheritance_enabled,
    at.name AS asset_type_name

FROM asset_components ac
JOIN assets a ON ac.asset_id = a.id
LEFT JOIN model_lifecycles ml ON ac.model_lifecycle_id = ml.id
LEFT JOIN manufacturers m ON ml.manufacturer_id = m.id
LEFT JOIN asset_types at ON a.asset_type_id = at.id
LEFT JOIN sites s ON a.site_id = s.id
LEFT JOIN areas ar ON a.area_id = ar.id;
"""


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status;")
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status;")
    op.execute("DROP SCHEMA IF EXISTS dashboard CASCADE;")
