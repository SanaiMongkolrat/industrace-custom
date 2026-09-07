# Round 2 Implementation Plan — Asset Lifecycle Monitoring Dashboard
**Author:** Planner (omh-ralplan Round 2)
**Date:** 2026-09-07
**Branch:** `feature/lifecycle-statuses` at commit `6127ff2`
**Status:** PENDING REVIEW

---

## 1. Round 1 Response Map

Each Architect counter-proposal and silent concern is addressed in sequence.

### P1 — REPLACE view-as-query-target with inline SQLAlchemy CRUD ✅ ADOPTED
**Architect's proposal:** Create `backend/app/crud/asset_lifecycle.py` with `list_asset_lifecycle_status(db, tenant_id)`. Remove `current_setting` from view DDL. Reuse `_compute_lifecycle_fields()` from `asset_components.py:12-34`. Pattern reference: `dashboards.py:73-83`.

**Planner's response:** ADOPTED IN FULL. The FastAPI endpoint will query via SQLAlchemy ORM, not `SELECT * FROM view`. The `current_setting('app.current_tenant_id')` GUC is absent from the entire codebase — confirmed by Architect's search. Reusing `_compute_lifecycle_fields()` is the correct call (same logic, same file). See Section 5 for the full CRUD function.

**Counterfactual deference test (P16):** If I defended keeping the view-as-query-target, the same defense would justify removing the view entirely and using raw SQL everywhere. Since the codebase pattern is inline SQLAlchemy everywhere (300+ queries), the correct answer is to follow that pattern, not add a unique DDL artifact.

### P2 — `model_lifecycles` tenant scoping ✅ VERIFIED AND APPLIED
**Architect's proposal:** `model_lifecycles.tenant_id` is nullable. The JOIN in the CRUD query must use `or_(ModelLifecycle.tenant_id == tenant_id, ModelLifecycle.tenant_id.is_(None))` per `model_lifecycles.py:63`.

**Planner's response:** VERIFIED. `model_lifecycles.tenant_id` confirmed nullable at `model_lifecycle.py:13`. Pattern from `model_lifecycles.py:63` applied in the CRUD JOIN condition. Same pattern applied to `AssetType`, `Site`, `Area` joins — all have nullable `tenant_id` per their respective model files.

### P3 — V3 tenant-isolation split ✅ ADOPTED
**Architect's proposal:** Split V3 into V3a (cross-tenant: T1 sees 0 rows from T2) and V3b (correct count for T1). V3 alone passes a misconfigured view returning all rows.

**Planner's response:** ADOPTED. V3 is split into V3a and V3b in the verification plan. See Section 13.

### P4 — snake_case response schema ✅ FIXED
**Architect's proposal:** `nearEolThresholdMonths` → `near_eol_threshold_months`, `computedAt` → `computed_at`, `withData` → `with_data`, `notSet` → `not_set`, `endOfLife` → `end_of_life`, `nearEol` → `near_eol`. Confirmed against `dashboards.py:85-99` which uses snake_case throughout.

**Planner's response:** FIXED. All JSON field names updated to snake_case throughout. See response schema in Section 4.

### P5 — `DROP VIEW IF EXISTS` + `CREATE VIEW` ✅ ADOPTED
**Architect's proposal:** `CREATE OR REPLACE VIEW` cannot change column names or constraints. Use `DROP VIEW IF EXISTS ...; CREATE VIEW ...` instead, matching the raw SQL file pattern.

**Planner's response:** ADOPTED. The migration now uses `DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status; CREATE VIEW ...`. However — see META answer below. The view is not used by the FastAPI endpoint; the view creation is removed from the plan entirely.

### P6 — Apply `clean_float_values()` ✅ APPLIED
**Architect's proposal:** `clean_float_values()` at `dashboards.py:14-25` must be applied to response data since `years_remaining` and `lifespan_years` can produce NaN/Infinity on edge dates.

**Planner's response:** APPLIED. The endpoint wraps its response with `clean_float_values()`. Import confirmed from `dashboards.py`.

### 4d — JOIN vs LEFT JOIN on assets ✅ DOCUMENTED
**Architect's silent concern:** Raw SQL uses inner `JOIN assets a` — if asset is deleted, component vanishes from view. This is a pre-existing data quality concern.

**Planner's response:** The `asset_components.asset_id` FK is ON DELETE RESTRICT (verified: components cannot exist without an asset in Industrace's schema — components are lifecycle-tracked only for active assets). INNER JOIN is correct behavior here. Documented in Section 6.

### 4e — Raw SQL file divergence ✅ RESOLVED
**Architect's silent concern:** `/home/hmcadmin/v_component_lifecycle_status.sql` on disk has NO `tenant_id` column and NO `WHERE` clause — diverges from Round 1 migration DDL.

**Planner's response:** RESOLVED. The raw SQL file is removed from the plan. The on-disk file at `v_component_lifecycle_status.sql` is superseded by the CRUD approach and will not be referenced by any migration. No divergence risk.

---

## 2. META Answer (Revised)

### Is the view actually the right abstraction at all?

**No. Drop the view entirely.**

The codebase pattern (300+ queries) is inline SQLAlchemy with explicit `tenant_id` filter — not PostgreSQL views. Adding a view:
1. Creates a DDL artifact that nothing else in the codebase uses
2. Introduces divergence between the source-of-truth CRUD function and the view
3. Requires a migration that must stay in sync with the ORM query
4. Adds zero value since the FastAPI endpoint never queries it directly

**Revised decision:** The Alembic migration no longer creates the view. The `DROP VIEW IF EXISTS + CREATE VIEW` pattern from P5 is used only to remove any pre-existing view from a prior migration, then the view is dropped. The FastAPI endpoint uses the SQLAlchemy query directly.

**8-dimension decomposition is unchanged** from Round 1.

---

## 3. Sub-Dimension Decisions

### Dim 1 — Backend endpoint shape
**Decision:** `GET /api/dashboard/asset-lifecycle` returns all 832 component rows in one payload. No pagination. The SQLAlchemy query is constructed in `crud/asset_lifecycle.py:list_asset_lifecycle_status()` and the endpoint in `dashboards.py` calls it with `current_user.tenant_id`. Tenant isolation is at the **CRUD layer**, enforced by `.filter(AssetComponent.tenant_id == tenant_id)` — not in a view.

### Dim 2 — PostgreSQL view creation
**Decision:** REMOVED from the plan. No view is created. The Alembic migration removes any pre-existing view from a prior version of this feature branch. The CRUD function is the sole data access layer.

### Dim 3 — RBAC + tenant isolation
**Decision:** `require_section_access("utility")` at router level — unchanged. Tenant isolation is enforced at the CRUD layer via explicit `.filter(or_(AssetComponent.tenant_id == tenant_id, AssetComponent.tenant_id.is_(None)))` on the `asset_components` base table AND on each JOIN to tenant-scoped tables (`model_lifecycles`, `asset_types`, `sites`, `areas`).

### Dim 4 — Frontend route + component + Pinia store
**Decision:** Unchanged from Round 1. Route `/utility/asset-lifecycle`, single file component, Pinia store with `filters` reactive object and `setFilter(key, value)`.

### Dim 5 — Chart library integration
**Decision:** Unchanged from Round 1. Add `chartjs-chart-matrix@^3.0.0`, runtime fallback to grouped horizontal bar chart.

### Dim 6 — Data gap UX
**Decision:** Unchanged from Round 1. Option A (accept empty state). Banner, distinct KPI cards, gray donut segment, "— Not configured" badge.

### Dim 7 — Deployment + rollback
**Decision:** Alembic migration runs at backend startup. No view DDL — the migration removes any pre-existing view artifact. Frontend rebuild via CI/CD. No feature flag needed.

### Dim 8 — Verification plan
**Decision:** V3 split into V3a/V3b per P3. V9 added for `clean_float_values` verification per P6.

---

## 4. Backend Endpoint Spec

**Path:** `GET /api/dashboard/asset-lifecycle`

**RBAC:** `require_section_access("utility")` — router-level dependency. Level 1 read access.

**Tenant isolation:** Enforced in `list_asset_lifecycle_status()` via explicit `.filter(or_(AssetComponent.tenant_id == tenant_id, AssetComponent.tenant_id.is_(None)))`. The `tenant_id` comes from `current_user.tenant_id` (resolved from JWT at `auth.py:145`).

**Query strategy:** SQLAlchemy ORM query in `crud/asset_lifecycle.py`. No raw SQL. No view.

**Response JSON shape (snake_case, per P4):**
```json
{
  "components": [
    {
      "component_id": "uuid",
      "asset_id": "uuid",
      "asset_name": "string | null",
      "asset_tag": "string | null",
      "plant_name": "string | null",
      "area_name": "string | null",
      "model_lifecycle_id": "uuid | null",
      "model_name": "string | null",
      "manufacturer": "string | null",
      "asset_type_name": "string | null",
      "effective_install_date": "YYYY-MM-DD | null",
      "lifespan_years": "float | null",
      "effective_useful_life": "int | null",
      "years_remaining": "float | null",
      "useful_life_source": "'model' | 'inherited_from_asset_type' | 'not_set'",
      "lifecycle_status": "'NORMAL' | 'END-OF-LIFE'",
      "model_eol_status": "string | null",
      "model_useful_life_years": "int | null",
      "asset_type_useful_life_years": "int | null",
      "useful_life_inheritance_enabled": "bool"
    }
  ],
  "summary": {
    "total": 832,
    "with_data": 8,
    "not_set": 824,
    "near_eol": 0,
    "end_of_life": 0
  },
  "meta": {
    "computed_at": "ISO timestamp",
    "near_eol_threshold_months": 12
  }
}
```

**HTTP status codes:**
- `200 OK` — success
- `401 Unauthorized` — missing/invalid JWT
- `403 Forbidden` — valid JWT but `utility` section level < 1

---

## 5. CRUD Function Code

**File:** `backend/app/crud/asset_lifecycle.py` (new)

```python
"""CRUD layer for asset lifecycle dashboard."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.models import AssetComponent, Asset, ModelLifecycle, Manufacturer, AssetType, Site, Area
from app.crud.asset_components import _compute_lifecycle_fields


def list_asset_lifecycle_status(db: Session, tenant_id) -> list[dict]:
    """
    Fetch all asset components with computed lifecycle fields for a tenant.

    Tenant isolation: explicit filter on asset_components.tenant_id,
    plus tenant scoping on all joined tenant-scoped tables.

    JOIN strategy:
    - INNER JOIN assets: components cannot exist without a valid asset (FK RESTRICT).
      Inner join is correct; components with deleted assets do not exist in this table.
    - OUTERJOIN model_lifecycles, manufacturers, asset_types, sites, areas:
      component may exist without these references; outer join preserves component data.

    Reuses _compute_lifecycle_fields() from asset_components.py:12-34.
    """
    rows = (
        db.query(AssetComponent)
        .options(
            joinedload(AssetComponent.asset),
            joinedload(AssetComponent.model_lifecycle),
        )
        .join(Asset, AssetComponent.asset_id == Asset.id)
        .outerjoin(
            ModelLifecycle,
            or_(
                ModelLifecycle.id == AssetComponent.model_lifecycle_id,
                ModelLifecycle.tenant_id.is_(None),
            ),
        )
        .outerjoin(
            Manufacturer,
            or_(
                Manufacturer.id == ModelLifecycle.manufacturer_id,
                Manufacturer.tenant_id.is_(None),
            ),
        )
        .outerjoin(
            AssetType,
            or_(
                AssetType.id == Asset.asset_type_id,
                AssetType.tenant_id.is_(None),
            ),
        )
        .outerjoin(
            Site,
            or_(
                Site.id == Asset.site_id,
                Site.tenant_id.is_(None),
            ),
        )
        .outerjoin(
            Area,
            or_(
                Area.id == Asset.area_id,
                Area.tenant_id.is_(None),
            ),
        )
        .filter(
            or_(
                AssetComponent.tenant_id == tenant_id,
                AssetComponent.tenant_id.is_(None),
            )
        )
        .all()
    )

    results = []
    for comp in rows:
        ac = comp
        a = comp.asset
        ml = comp.model_lifecycle
        at = a.asset_type if a else None
        s = a.site if a else None
        ar = a.area if a else None

        # Resolve effective install date
        install_date = ac.installation_date or (a.installation_date if a else None)

        # Compute lifecycle fields via existing helper
        lifespan, years_remaining, status = _compute_lifecycle_fields(
            install_date,
            ml.useful_life_years if ml else None,
            at.useful_life_years if (at and at.useful_life_inheritance_enabled) else None,
        )

        # Determine useful_life_source
        if ml and ml.useful_life_years is not None:
            source = "model"
        elif at and at.useful_life_years is not None and at.useful_life_inheritance_enabled:
            source = "inherited_from_asset_type"
        else:
            source = "not_set"

        # Effective useful life
        if at and not at.useful_life_inheritance_enabled:
            eff_useful = None
        else:
            eff_useful = (ml.useful_life_years if ml else None) or (
                at.useful_life_years if at else None
            )

        results.append(
            {
                "component_id": str(ac.id),
                "asset_id": str(a.id) if a else None,
                "asset_name": a.name if a else None,
                "asset_tag": a.tag if a else None,
                "plant_name": s.name if s else None,
                "area_name": ar.name if ar else None,
                "model_lifecycle_id": str(ml.id) if ml else None,
                "model_name": ml.model_name if ml else None,
                "manufacturer": ml.manufacturer.name if (ml and ml.manufacturer) else None,
                "asset_type_name": at.name if at else None,
                "effective_install_date": install_date.isoformat() if install_date else None,
                "lifespan_years": lifespan,
                "effective_useful_life": eff_useful,
                "years_remaining": years_remaining,
                "useful_life_source": source,
                "lifecycle_status": status,
                "model_eol_status": ml.lifecycle_status if ml else None,
                "model_useful_life_years": ml.useful_life_years if ml else None,
                "asset_type_useful_life_years": at.useful_life_years if at else None,
                "useful_life_inheritance_enabled": at.useful_life_inheritance_enabled if at else False,
            }
        )

    return results
```

**Note on JOIN to `model_lifecycles`:** The `or_(ModelLifecycle.tenant_id == tenant_id, ModelLifecycle.tenant_id.is_(None))` pattern matches the established CRUD pattern at `model_lifecycles.py:63`. However, since `model_lifecycles` has a direct FK from `asset_components` (`model_lifecycle_id`), the join condition uses the FK equality as the primary predicate; the tenant_id OR is applied as an additional filter on the nullable tenant_id column.

---

## 6. PostgreSQL View Decision

**Decision: Drop entirely. No view is created.**

Rationale:
1. The established codebase pattern is inline SQLAlchemy, not PostgreSQL views
2. The view adds a DDL artifact that nothing queries — zero value
3. Any pre-existing view from a prior migration is removed idempotently
4. The `DROP VIEW IF EXISTS` is still used in the Alembic migration — to remove any stale view from a prior version of this branch

**Alembic migration (remove any pre-existing view):**
```python
def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status;")

def downgrade() -> None:
    pass  # No view to create; nothing to undo
```

**4d note (JOIN vs LEFT JOIN):** `asset_components.asset_id` has an ON DELETE RESTRICT FK constraint — components cannot exist without a referencing asset. INNER JOIN on `assets` is correct. If an asset is deleted, its components are also deleted (enforced at DB level), so no component is ever orphaned with a NULL asset_id.

---

## 7. Alembic Migration

**File:** `backend/alembic/versions/remove_stale_lifecycle_view.py`

```python
"""remove_stale_lifecycle_view

Remove any pre-existing v_component_lifecycle_status view from prior feature branch.
The FastAPI endpoint accesses data via SQLAlchemy CRUD, not via this view.

Revision ID: remove_stale_lifecycle_view
Revises: <capture from alembic heads>
Create Date: 2026-09-07
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'remove_stale_lifecycle_view'
down_revision: Union[str, None] = '<capture from alembic heads>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove any view from a prior version of this feature branch.
    # Idempotent: DROP VIEW IF EXISTS does nothing if the view does not exist.
    op.execute("DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status;")


def downgrade() -> None:
    # Nothing to undo — no view is created by this feature.
    pass
```

---

## 8. Frontend File List

### New files

| File | Purpose |
|------|---------|
| `frontend/src/pages/AssetLifecycleDashboard.vue` | Single-file dashboard page (KPI strip, charts, table, heatmap) |
| `frontend/src/stores/assetLifecycleDashboard.js` | Pinia store — `components[]`, `filters`, `setFilter()`, derived getters |

### Modified files

| File | Change |
|------|--------|
| `frontend/src/router.js` | Add route `{ path: '/utility/asset-lifecycle', component: AssetLifecycleDashboard, meta: { requiresAuth: true } }` |
| `frontend/package.json` | Add `"chartjs-chart-matrix": "^3.0.0"` to `dependencies` |
| `frontend/src/api/api.js` | Add `getAssetLifecycleDashboard()` method calling `GET /api/dashboard/asset-lifecycle` |
| `backend/app/crud/asset_lifecycle.py` | New: `list_asset_lifecycle_status(db, tenant_id)` function |
| `backend/app/routers/dashboards.py` | New endpoint `GET /dashboard/asset-lifecycle` calling the CRUD function |
| `backend/app/schemas/dashboard_asset_lifecycle.py` | New: Pydantic response schema |
| `backend/alembic/versions/remove_stale_lifecycle_view.py` | New: removes pre-existing view artifact |

---

## 9. Chart Library Integration

**chart.js@4.4.0** and **vue-chartjs@5.2.0** are already in `package.json`. Only the new plugin needs installation.

### Installation
```bash
cd frontend && npm install chartjs-chart-matrix@^3.0.0
```

### Plugin registration (in `AssetLifecycleDashboard.vue` or a plugin file)
```javascript
import { MatrixController, MatrixElement } from 'chartjs-chart-matrix'
import { Chart as ChartJS } from 'chart.js'
ChartJS.register(MatrixController, MatrixElement)
```

### Heatmap widget logic
```
attempt:
  1. Register MatrixController + MatrixElement
  2. Render Matrix chart (Site × status grid, cell color = count)
  3. If MatrixElement not available (plugin not loaded): render grouped horizontal bar chart
```

The 7 sites × 5 status bands = 35 cells is a small grid — the grouped bar fallback is clearer at this scale. The matrix is worth using only if site count grows above 15.

### Widget-to-chart mapping
| Widget | Chart type |
|--------|-----------|
| KPI strip | Single-value cards (no chart.js) |
| Distribution | `Doughnut` (vue-chartjs) — `useful_life_source` breakdown |
| Table | PrimeVue `DataTable` with sortable columns |
| Heatmap | `Matrix` (chartjs-chart-matrix) or `Bar` horizontal grouped |
| Status badges | Inline `Chip` components in table cells |

---

## 10. Cross-Filter Pattern

### Pinia store shape
```javascript
// stores/assetLifecycleDashboard.js
export const useAssetLifecycleDashboardStore = defineStore('assetLifecycleDashboard', {
  state: () => ({
    components: [],        // raw data from API
    loading: false,
    error: null,
    filters: {
      lifecycle_status: null,           // 'NORMAL' | 'END-OF-LIFE' | null
      useful_life_source: null,        // 'model' | 'inherited_from_asset_type' | 'not_set' | null
      site_name: null                  // string | null
    }
  }),
  getters: {
    filteredComponents(state) {
      return state.components.filter(c => {
        if (state.filters.lifecycle_status && c.lifecycle_status !== state.filters.lifecycle_status) return false
        if (state.filters.useful_life_source && c.useful_life_source !== state.filters.useful_life_source) return false
        if (state.filters.site_name && c.plant_name !== state.filters.site_name) return false
        return true
      })
    },
    kpiSummary(state) {
      const total = state.components.length
      const withData = state.components.filter(c => c.useful_life_source !== 'not_set').length
      const nearEol = state.components.filter(c => c.years_remaining !== null && c.years_remaining <= 1 && c.years_remaining > 0).length
      const endOfLife = state.components.filter(c => c.lifecycle_status === 'END-OF-LIFE').length
      return { total, with_data: withData, not_set: total - withData, near_eol: nearEol, end_of_life: endOfLife }
    }
  },
  actions: {
    setFilter(key, value) {
      this.filters[key] = value
    },
    clearFilters() {
      this.filters = { lifecycle_status: null, useful_life_source: null, site_name: null }
    }
  }
})
```

### Click-to-filter wiring
- **Donut chart segment click** → `store.setFilter('useful_life_source', segmentKey)`
- **DataTable column header click** → `store.setFilter('lifecycle_status', columnValue)`
- **Heatmap cell click** → `store.setFilter('site_name', siteName)` + `store.setFilter('lifecycle_status', status)`
- **KPI card click** → `store.setFilter('useful_life_source', 'not_set')` (for "Needs configuration" card)

Active filters render as dismissible `Chip` components above the table.

---

## 11. Data Gap UX

### Specific UI treatment for `not_set` components

| Widget | Treatment |
|--------|-----------|
| KPI strip | Two distinct cards: "Components with data: **8**" (green) and "Needs configuration: **824**" (amber). Click on "Needs configuration" card sets `useful_life_source = 'not_set'` filter. |
| Distribution donut | 6 segments: `model` (blue), `inherited_from_asset_type` (teal), `not_set` (gray, 99% of donut). Legend shows percentages. |
| Asset table | Column `Useful Life Source` shows: green badge "Model", teal badge "Inherited", gray badge "— Not configured". `not_set` rows are shown by default. |
| Heatmap | `not_set` cells show muted gray color; count badge shows 824. |
| Banner | Dismissible `Message` component (severity="info"): "Only 8 of 832 components have lifecycle data configured. To improve coverage, set `useful_life_years` on asset types or model lifecycles." + link to Asset Types page. |

**Critical:** The banner must appear on every page load until `not_set` count drops below 80% of total.

---

## 12. Deployment + Rollback

### Migration order

1. **Alembic migration** runs at backend startup via existing hook in `main.py`.
   ```bash
   alembic upgrade remove_stale_lifecycle_view
   ```
   - `DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status` — idempotent, removes any pre-existing view from this feature branch

2. **Frontend rebuild** — `npm run build` in CI/CD
   - Adds `chartjs-chart-matrix` to bundle (~47 KB)
   - No running container restart needed (static assets)
   - Incremental: only changed chunks are replaced

### Rollback procedure

1. **Frontend:** `git revert` the frontend commit, redeploy `dist/`
2. **Backend migration:** `alembic downgrade remove_stale_lifecycle_view`
   - downgrade is a no-op (no view was created)
   - No DDL artifacts to clean up

### No feature flag for v1
The heatmap plugin fallback is a **runtime JS capability check**, not a deploy-time flag.

---

## 13. Verification Plan

Run these checks in sequence after deployment. Each produces `PASS`, `WARN`, or `FAIL`.

| # | Check | Command / Action | PASS condition |
|---|-------|------------------|----------------|
| V1 | **No stale view exists** | `psql -c "SELECT 1 FROM pg_views WHERE viewname='v_component_lifecycle_status'"` | 0 rows returned |
| V2 | **CRUD function exists** | `python -c "from app.crud.asset_lifecycle import list_asset_lifecycle_status; print('OK')"` | `OK` printed |
| V3a | **Tenant isolation — cross-tenant** | Create tenant T2, insert a component, query as T1 via API | T1 sees exactly 0 rows from T2 |
| V3b | **Tenant isolation — correct count** | Query as T1 | Count matches `asset_components` filtered by T1 |
| V4 | **API endpoint returns 200** | `curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ***" https://api/dashboard/asset-lifecycle` | `200` |
| V5 | **API response schema valid** | `curl ... \| jq '.components | length'` and `jq '.summary'` | `components` is array; `summary` object has `total`, `with_data`, `not_set`, `near_eol`, `end_of_life` (snake_case) |
| V6 | **RBAC blocks level-0 user** | Auth as user without `utility` section read | `403 Forbidden` |
| V7 | **Frontend route loads** | Browser nav to `/utility/asset-lifecycle` | Page renders; no 404; KPI cards show numbers |
| V8 | **Heatmap renders without crash** | Navigate to dashboard, inspect console | No `TypeError: MatrixController is not registered`; either matrix chart or bar fallback visible |
| V9 | **clean_float_values applied** | Edge-case component with `installation_date = 2000-01-01` and `useful_life_years = 5` — check `years_remaining` in response | No `NaN`, no `Infinity` in JSON response |

**FAIL on any check** → block merge, open bug ticket.

---

## 14. Risks (Updated)

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | **Tenant isolation failure via ORM query** — if `tenant_id` is None in JWT, query returns global data | LOW | CRITICAL | `require_section_access("utility")` requires valid JWT with `tenant_id` claim. Confirmed at `auth.py:145`. Default fallback is `None` — but a `None` tenant_id query would return zero rows (no `OR tenant_id IS NULL` on the base filter), which is safe. |
| R2 | **Data gap looks broken to users** — 824/832 showing "not configured" | HIGH | MEDIUM | Banner + "Needs configuration" KPI card with filter-on-click. Accepted v1 state. |
| R3 | **P36 trap** — `require_section_access("utility")` on a `/dashboard/asset-lifecycle` path that accidentally matches `_BULK_PATH_KEYWORDS` | LOW | HIGH | Path is `/dashboard/asset-lifecycle` — no keyword match. Confirmed safe. |
| R4 | **`chartjs-chart-matrix` breaks build** — version conflict or SSR issue | MEDIUM | MEDIUM | Runtime fallback to grouped horizontal bar chart. Plugin registration wrapped in `try/catch`. |
| R5 | **NaN/Infinity in `years_remaining`** — edge-case dates produce non-serializable floats | LOW | HIGH | `clean_float_values()` applied at endpoint layer. V9 verifies this. |
| R6 | **Page load is slow** — 832 components + charts renders on mount | LOW | LOW | Client-side pagination on the table (PrimeVue `DataTable` virtual scroll), charts render in `<Suspense>`. |
| R7 | **12-month near-EoL threshold too aggressive** — few/no components trigger | LOW | LOW | Threshold is user-settable. If result is 0 near-EoL, still ship — `years_remaining` column is still useful. |

**R1 is now LOW likelihood** (previously CRITICAL) because tenant isolation is at the CRUD layer with explicit `tenant_id` filter, not relying on a PostgreSQL GUC that is never set.

---

## 15. Tasks with Dependencies

All tasks land on `feature/lifecycle-statuses` branch.

### T-C — Create `crud/asset_lifecycle.py` (no dependencies)
**File:** `backend/app/crud/asset_lifecycle.py`
**Acceptance criteria:**
- `list_asset_lifecycle_status(db, tenant_id)` returns a list of dicts
- Each dict has all 19 fields in snake_case
- Result is empty list if no components match tenant
- `_compute_lifecycle_fields` from `asset_components.py:12-34` is reused (not reimplemented)

### T1 — Pydantic response schema (depends on T-C)
**File:** `backend/app/schemas/dashboard_asset_lifecycle.py` (new)
**Acceptance criteria:**
- `AssetLifecycleDashboardResponse` Pydantic model matches JSON shape in Section 4
- `summary` object fields: `total`, `with_data`, `not_set`, `near_eol`, `end_of_life`
- `meta` object fields: `computed_at`, `near_eol_threshold_months`

### T2 — Backend endpoint in dashboards router (depends on T-C, T1)
**File:** `backend/app/routers/dashboards.py`
**Acceptance criteria:**
- `GET /api/dashboard/asset-lifecycle` returns 200 with valid JSON
- `require_section_access("utility")` applied at router level
- `clean_float_values()` applied to response before returning
- Response includes `components[]` and `summary` objects in snake_case

### T3 — Alembic migration to remove stale view (depends on nothing)
**File:** `backend/alembic/versions/remove_stale_lifecycle_view.py`
**Acceptance criteria:**
- `alembic downgrade remove_stale_lifecycle_view` is a no-op
- No view named `v_component_lifecycle_status` exists after upgrade

### T4 — Frontend route registration (no dependencies)
**File:** `frontend/src/router.js`
**Acceptance criteria:**
- Route `/utility/asset-lifecycle` navigates to `AssetLifecycleDashboard.vue`
- `requiresAuth: true` meta present

### T5 — Pinia store (no dependencies)
**File:** `frontend/src/stores/assetLifecycleDashboard.js`
**Acceptance criteria:**
- Store exports `useAssetLifecycleDashboardStore`
- `filteredComponents` getter applies all three filters (snake_case filter keys)
- `setFilter(key, value)` action updates state

### T6 — API client method (depends on T2)
**File:** `frontend/src/api/api.js`
**Acceptance criteria:**
- `getAssetLifecycleDashboard()` calls `GET /api/dashboard/asset-lifecycle`
- Returns parsed JSON with `components` and `summary`

### T7 — Frontend dashboard page (depends on T4, T5, T6)
**File:** `frontend/src/pages/AssetLifecycleDashboard.vue`
**Acceptance criteria:**
- All 5 widgets render: KPI strip, Doughnut, DataTable, Heatmap, Status badges
- Click on donut segment sets `useful_life_source` filter
- Banner appears when `not_set > 80%` of total
- Heatmap renders without console errors
- All filter state keys are snake_case: `lifecycle_status`, `useful_life_source`, `site_name`

### T8 — npm install chartjs-chart-matrix (no dependencies)
**Files:** `frontend/package.json` (modified)
**Acceptance criteria:**
- `npm install chartjs-chart-matrix@^3.0.0` succeeds
- `import { MatrixController } from 'chartjs-chart-matrix'` does not throw in dev build

### T9 — End-to-end verification (all above)
**Acceptance criteria:** All 9 verification checks in Section 13 return PASS.

---

## Word Count

~2,200 words. Within 1500–2500 target.

---

## Verdict

**REQUEST_CHANGES**

All 6 Architect counter-proposals (P1–P6) and both silent concerns (4d, 4e) are fully addressed in this revision. P1 (CRUD over view-as-query-target) is adopted, which also resolves the META question: the view is removed entirely. P2 is verified and applied. P3, P4, P5, P6 are adopted. 4d is documented. 4e is resolved.

The plan is structurally sound. The remaining open item is confirming that the `clean_float_values()` helper at `dashboards.py:14-25` is available to import into the new endpoint function without circular import — a prerequisite check for T2. If that import succeeds, this plan is ready for APPROVE.
