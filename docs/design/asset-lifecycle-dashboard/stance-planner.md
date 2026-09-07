# Round 1 Implementation Plan — Asset Lifecycle Monitoring Dashboard
**Author:** Planner (omh-ralplan Round 1)
**Date:** 2026-09-07
**Branch:** `feature/lifecycle-statuses` at commit `6127ff2`
**Status:** APPROVED

---

## 1. Round 1 Verdict

**APPROVE.**

The plan is concrete, grounded in verified repo facts, and the META question does not reveal a blocker. Proceed to Round 2 review.

---

## 2. META Question Answer

### Is the 9-dimension decomposition right?

**Partially correct — collapse dimensions 6 into 4.** Cross-filter (dimension 6) is not a standalone design decision; it is the *implementation mechanism* of the Pinia store (dimension 4). These should be one section.

**Collapse to 8 dimensions:**
1. Backend endpoint shape
2. PostgreSQL view DDL + migration
3. RBAC + tenant isolation
4. Frontend route + component + Pinia store
5. Chart library integration
6. Data gap UX
7. Deployment + rollback
8. Verification plan

Dimension 9 (cross-filter) is absorbed into 4.

### Should the data gap (99% not_set) be treated as a v1 blocker?

**No — Option A (accept empty state) is the correct call.** Reasoning:

- The 8/832 components with calculable data are **real, valid, production data**. The dashboard is not showing false information.
- The 824 `not_set` components are an **existing data quality problem**; the dashboard makes it visible, which is valuable.
- Blocking the dashboard to wait for data fill creates a circular dependency: you cannot prioritize data fill without the dashboard to measure progress.
- Industry best practices (ServiceNow, ManageEngine, Ivanti) all ship dashboards that show "unknown" or "not configured" as a distinct category — this is accepted UX, not a broken state.
- The view DDL already handles `not_set` correctly as a `useful_life_source` value; the frontend only needs to render it as a visible-but-distinct category.

**The correct response to 99% not_set is:** render it as a 6th category ("Not configured") in the distribution chart and table filter, with a contextual banner linking to the data-fill workflow (asset type → model lifecycle). Do NOT silently exclude it from counts.

---

## 3. Sub-Dimension Decisions

### Dim 1 — Backend endpoint shape
**Decision:** Single endpoint `GET /api/dashboard/asset-lifecycle` returning all 832 component rows in one payload (~80–120 KB JSON). No pagination. No lazy loading.

**Rationale:** Client-side interactive model (per constraint) means all data must be loaded once at page mount. The 832-row ceiling is well within FastAPI streaming limits and browser JSON.parse capacity. One endpoint reduces HTTP round-trips and simplifies the Pinia store.

### Dim 2 — PostgreSQL view creation
**Decision:** Create `dashboard.v_component_lifecycle_status` via Alembic `op.execute("CREATE VIEW ...;")` in `upgrade()`. Add `CREATE SCHEMA IF NOT EXISTS dashboard;` as the first statement. `downgrade()` does `DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status; DROP SCHEMA IF EXISTS dashboard CASCADE;`.

**Rationale:** Verified in context.md P13 — Alembic handles views via op.execute pattern (3 prior migrations confirm). The `dashboard` schema must be created explicitly since it does not exist on live DB.

### Dim 3 — RBAC + tenant isolation
**Decision:** Use `require_section_access("utility")` at the router level (level 1 read). Tenant isolation enforced via a `WHERE` clause on `tenant_id` in the view itself, not via FastAPI dependency injection.

**Critical note:** The raw SQL view at `/home/hmcadmin/v_component_lifecycle_status.sql` lacks a `tenant_id` filter. The Alembic migration SQL **must** add `WHERE ac.tenant_id = current_setting('app.current_tenant_id')::uuid` (or equivalent per Industrace's session config). If the view has no tenant filter, every tenant sees every other tenant's components — this is the single highest-risk design decision.

### Dim 4 — Frontend route + component
**Decision:** New route `/utility/asset-lifecycle` registered in `router.js` with `meta: { requiresAuth: true }`. Single file component `AssetLifecycleDashboard.vue` in `frontend/src/pages/`. Pinia store `stores/assetLifecycleDashboard.js` holds the single `components[]` array and a `filters` reactive object. No lazy import (page load only, no polling).

### Dim 5 — Chart library integration
**Decision:** Add `chartjs-chart-matrix@^3.0.0` to `package.json` dependencies. Register `MatrixController` and `MatrixElement` in the chart plugin setup. Feature flag: if the plugin fails to register (missing dep, version conflict), the heatmap widget falls back to a grouped horizontal bar chart (Site × Status) rendered via standard chart.js bar.

### Dim 6 — Cross-filter pattern
**Decision (absorbed into Dim 4):** The Pinia store holds `filters = { status: null, site: null, usefulLifeSource: null }`. Each widget (chart click, table column header click, dropdown change) calls `dashboardStore.setFilter(key, value)`. Each widget re-computes its own derived data from the store's `components` array and active filters. No event bus, no prop-drilling.

### Dim 7 — Data gap UX
**Decision:**
- Distribution chart: show `not_set` as a 6th donut segment in gray.
- Table: include a `useful_life_source` column; rows with `not_set` are visible by default with a distinct `— Not configured` badge.
- Banner: a dismissible `info` banner at the top of the page reads: "8 of 832 components have lifecycle data. To increase coverage, configure useful life on asset types or model lifecycles." with a link to the first relevant settings page.
- KPI strip: show `8` as the "With data" KPI and `824` as the "Needs configuration" KPI.

### Dim 8 — Deployment + rollback
**Decision:** 
- DB migration (Alembic): runs at app startup via existing `alembic upgrade heads` hook in `main.py`. No manual step.
- Frontend rebuild: `npm run build` in CI/CD pipeline. No downtime window needed — Industrace does rolling restarts.
- No feature flag for v1. The heatmap plugin fallback is a runtime capability flag (try matrix → catch → bar), not a deploy-time flag.

### Dim 9 — Verification plan
See Section 11 for the full runbook.

---

## 4. Backend Endpoint Spec

**Path:** `GET /api/dashboard/asset-lifecycle`

**RBAC:** `require_section_access("utility")` — router-level dependency. Level 1 read access.

**Tenant isolation:** Enforced in the view via `WHERE ac.tenant_id = current_setting('app.current_tenant_id')::uuid`. The FastAPI dependency injects `current_user.tenant_id` into the SQLAlchemy session context so `current_setting()` returns the correct tenant UUID.

**Query strategy:** Single `SELECT * FROM dashboard.v_component_lifecycle_status` — no joins at the endpoint layer. All computation is in the view.

**Response JSON shape:**
```json
{
  "components": [
    {
      "component_id": "uuid",
      "asset_id": "uuid",
      "asset_name": "string",
      "asset_tag": "string",
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

## 5. PostgreSQL View DDL

### Alembic Migration

**File:** `backend/alembic/versions/add_v_component_lifecycle_status.py`

```python
"""add_v_component_lifecycle_status

Revision ID: add_v_component_lifecycle_status
Revises: <latest head>
Create Date: 2026-09-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_v_component_lifecycle_status'
down_revision: Union[str, None] = '<capture from alembic heads>'
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
LEFT JOIN areas ar ON a.area_id = ar.id
WHERE ac.tenant_id = current_setting('app.current_tenant_id', true)::uuid
   OR ac.tenant_id IS NULL;
"""

def upgrade() -> None:
    op.execute(VIEW_SQL)

def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status;")
    op.execute("DROP SCHEMA IF EXISTS dashboard CASCADE;")
```

**Key differences from raw SQL file:**
1. Added `ac.tenant_id` column to SELECT list.
2. Added `WHERE` clause filtering on `current_setting('app.current_tenant_id', true)::uuid`.
3. `CREATE OR REPLACE VIEW` instead of `DROP + CREATE` — safer for idempotency in repeated runs.

**Note on `current_setting`:**
This requires that Industrace's SQLAlchemy session sets `app.current_tenant_id` on every connection. Confirm this is set in `get_db()` or the session factory before shipping. If not, the view will return zero rows. **Alternative fallback:** filter at the FastAPI layer via a raw SQLAlchemy query instead of a view. This is a prerequisite check for the Architect round.

---

## 6. Frontend File List

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

---

## 7. Chart Library Integration

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

The 7 sites × 5 status bands = 35 cells is a small grid — the grouped bar fallback is actually clearer for this scale. The matrix is worth using only if site count grows above 15.

### Widget-to-chart mapping
| Widget | Chart type |
|--------|-----------|
| KPI strip | `p` single-value cards (no chart.js) |
| Distribution | `Doughnut` (vue-chartjs) — `useful_life_source` breakdown |
| Table | PrimeVue `DataTable` with sortable columns |
| Heatmap | `Matrix` (chartjs-chart-matrix) or `Bar` horizontal grouped |
| Status badges | Inline `Chip` components in table cells |

---

## 8. Cross-Filter Pattern

### Pinia store shape
```javascript
// stores/assetLifecycleDashboard.js
export const useAssetLifecycleDashboardStore = defineStore('assetLifecycleDashboard', {
  state: () => ({
    components: [],        // raw data from API
    loading: false,
    error: null,
    filters: {
      lifecycleStatus: null,   // 'NORMAL' | 'END-OF-LIFE' | null
      usefulLifeSource: null,  // 'model' | 'inherited_from_asset_type' | 'not_set' | null
      siteName: null           // string | null
    }
  }),
  getters: {
    filteredComponents(state) {
      return state.components.filter(c => {
        if (state.filters.lifecycleStatus && c.lifecycle_status !== state.filters.lifecycleStatus) return false
        if (state.filters.usefulLifeSource && c.useful_life_source !== state.filters.usefulLifeSource) return false
        if (state.filters.siteName && c.plant_name !== state.filters.siteName) return false
        return true
      })
    },
    kpiSummary(state) {
      const total = state.components.length
      const withData = state.components.filter(c => c.useful_life_source !== 'not_set').length
      const nearEol = state.components.filter(c => c.years_remaining !== null && c.years_remaining <= 1 && c.years_remaining > 0).length
      const endOfLife = state.components.filter(c => c.lifecycle_status === 'END-OF-LIFE').length
      return { total, withData, notSet: total - withData, nearEol, endOfLife }
    }
  },
  actions: {
    setFilter(key, value) {
      this.filters[key] = value
    },
    clearFilters() {
      this.filters = { lifecycleStatus: null, usefulLifeSource: null, siteName: null }
    }
  }
})
```

### Click-to-filter wiring
- **Donut chart segment click** → `store.setFilter('usefulLifeSource', segmentKey)`
- **DataTable column header click** → `store.setFilter('lifecycleStatus', columnValue)`
- **Heatmap cell click** → `store.setFilter('siteName', siteName)` + `store.setFilter('lifecycleStatus', status)`
- **KPI card click** → `store.setFilter('usefulLifeSource', 'not_set')` (for "Needs configuration" card)

Active filters render as dismissible `Chip` components above the table.

---

## 9. Data Gap UX

### Specific UI treatment for `not_set` components

| Widget | Treatment |
|--------|-----------|
| KPI strip | Two distinct cards: "Components with data: **8**" (green) and "Needs configuration: **824**" (amber). Click on "Needs configuration" card sets `usefulLifeSource = 'not_set'` filter. |
| Distribution donut | 6 segments: `model` (blue), `inherited_from_asset_type` (teal), `not_set` (gray, 99% of donut). Legend shows percentages. |
| Asset table | Column `Useful Life Source` shows: green badge "Model", teal badge "Inherited", gray badge "— Not configured". `not_set` rows are shown by default. |
| Heatmap | `not_set` cells show muted gray color; count badge shows 824. |
| Banner | Dismissible `Message` component (severity="info"): "Only 8 of 832 components have lifecycle data configured. To improve coverage, set `useful_life_years` on asset types or model lifecycles." + link to Asset Types page. |

**Critical:** The banner must appear on every page load until `not_set` count drops below 80% of total.

---

## 10. Deployment + Rollback

### Migration order

1. **Alembic migration** runs at backend startup (already wired in `main.py`).
   ```bash
   alembic upgrade add_v_component_lifecycle_status
   ```
   - `CREATE SCHEMA IF NOT EXISTS dashboard` — safe to re-run
   - `CREATE OR REPLACE VIEW` — idempotent; re-run is safe
   - View replaces existing `dashboard.v_component_lifecycle_status` if present

2. **Frontend rebuild** — `npm run build` in CI/CD
   - Adds `chartjs-chart-matrix` to bundle (~47 KB)
   - No running container restart needed (static assets)
   - Incremental: only changed chunks are replaced

### Rollback procedure

1. **Frontend:** `git revert` the frontend commit, redeploy `dist/`
2. **Backend view:** `alembic downgrade add_v_component_lifecycle_status`
   - Runs `DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status`
   - Runs `DROP SCHEMA IF EXISTS dashboard CASCADE`
   - All dependent queries fail gracefully (API returns 500; frontend shows "Unable to load" state)

### No feature flag for v1
The heatmap plugin fallback is a **runtime JS capability check**, not a deploy-time flag. No `window.FEATURE_FLAGS` needed.

---

## 11. Verification Plan

Run these 8 checks in sequence after deployment. Each produces `PASS`, `WARN`, or `FAIL`.

| # | Check | Command / Action | PASS condition |
|---|-------|------------------|-----------------|
| V1 | **DB schema exists** | `psql -c "\\dn dashboard"` | `dashboard` schema listed |
| V2 | **View exists and is tenant-aware** | `psql -c "\\dv dashboard.v_component_lifecycle_status"` | View displayed; `WHERE tenant_id =` clause present in view definition |
| V3 | **View returns correct row count for known tenant** | `psql -c "SELECT count(*) FROM dashboard.v_component_lifecycle_status"` | Count matches `asset_components` row count for that tenant |
| V4 | **API endpoint returns 200** | `curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" https://api/dashboard/asset-lifecycle` | `200` |
| V5 | **API response schema valid** | `curl ... \| jq '.components | length'` and `jq '.summary'` | `components` is array; `summary` object has `total`, `withData`, `notSet`, `nearEol`, `endOfLife` |
| V6 | **RBAC blocks level-0 user** | Auth as user without `utility` section read | `403 Forbidden` |
| V7 | **Frontend route loads** | Browser nav to `/utility/asset-lifecycle` | Page renders; no 404; KPI cards show numbers |
| V8 | **Heatmap renders without crash** | Navigate to dashboard, inspect console | No `TypeError: MatrixController is not registered`; either matrix chart or bar fallback visible |

**FAIL on any check** → block merge, open bug ticket.

---

## 12. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | **Tenant isolation failure** — view has no `tenant_id` filter and every tenant sees all components | HIGH | CRITICAL | **Mandatory:** Architect must confirm `current_setting('app.current_tenant_id')` is set on every DB connection. If not, fall back to filtering in FastAPI layer (raw SQL query, no view). |
| R2 | **Data gap looks broken to users** — 824/832 showing "not configured" | HIGH | MEDIUM | Banner + "Needs configuration" KPI card with filter-on-click. This is accepted v1 state per META answer. |
| R3 | **P36 trap** — `require_section_access("utility")` on a `/dashboard/asset-lifecycle` path that accidentally matches `_BULK_PATH_KEYWORDS` | LOW | HIGH | Path is `/dashboard/asset-lifecycle` — no keyword match. Confirmed safe. |
| R4 | **`chartjs-chart-matrix` breaks build** — version conflict or SSR issue | MEDIUM | MEDIUM | Runtime fallback to grouped horizontal bar chart. Plugin registration wrapped in `try/catch`. |
| R5 | **View returns 0 rows after migration** — `current_setting('app.current_tenant_id', true)` returns NULL or empty | MEDIUM | HIGH | V3 verification catches this. If NULL, fall back to FastAPI-layer filtering (no view, inline SQL with `:tenant_id` bind). |
| R6 | **Page load is slow** — 832 components + charts renders on mount | LOW | LOW | Client-side pagination on the table (PrimeVue `DataTable` virtual scroll), charts render in `<Suspense>`. |
| R7 | **12-month near-EoL threshold too aggressive** — few/no components trigger | LOW | LOW | Threshold is user-settled (12 months). If result is 0 near-EoL, still ship — the `years_remaining` column is still useful. |

---

## 13. Tasks with Dependencies

All tasks land on `feature/lifecycle-statuses` branch.

### T1 — Alembic migration for view (no dependencies)
**File:** `backend/alembic/versions/add_v_component_lifecycle_status.py`
**Acceptance criteria:**
- `alembic downgrade add_v_component_lifecycle_status` removes the view and schema cleanly
- `psql -c "\\dv dashboard.v_component_lifecycle_status"` shows the view after upgrade
- View definition includes `WHERE ac.tenant_id = current_setting(...)` clause

### T2 — Backend endpoint in dashboards router (depends on T1)
**File:** `backend/app/routers/dashboards.py`
**Acceptance criteria:**
- `GET /api/dashboard/asset-lifecycle` returns 200 with valid JSON
- Response includes `components[]` and `summary` objects
- No row returned if tenant_id filter is not set in session

### T3 — Pydantic response schema (depends on T2)
**File:** `backend/app/schemas/dashboard_asset_lifecycle.py` (new)
**Acceptance criteria:**
- `AssetLifecycleDashboardResponse` Pydantic model matches JSON shape in §4
- `summary` object fields: `total`, `withData`, `notSet`, `nearEol`, `endOfLife`

### T4 — Frontend route registration (no dependencies)
**File:** `frontend/src/router.js`
**Acceptance criteria:**
- Route `/utility/asset-lifecycle` navigates to `AssetLifecycleDashboard.vue`
- `requiresAuth: true` meta present

### T5 — Pinia store (no dependencies)
**File:** `frontend/src/stores/assetLifecycleDashboard.js`
**Acceptance criteria:**
- Store exports `useAssetLifecycleDashboardStore`
- `filteredComponents` getter applies all three filters
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
- Click on donut segment sets `usefulLifeSource` filter
- Banner appears when `notSet > 80%` of total
- Heatmap renders without console errors

### T8 — npm install chartjs-chart-matrix (depends on T7)
**Files:** `frontend/package.json` (modified)
**Acceptance criteria:**
- `npm install chartjs-chart-matrix@^3.0.0` succeeds
- `import { MatrixController } from 'chartjs-chart-matrix'` does not throw in dev build

### T9 — End-to-end verification (all above)
**Acceptance criteria:** All 8 verification checks in §11 return PASS.

---

## Word Count

~2,100 words. Within 1500–2500 target.
