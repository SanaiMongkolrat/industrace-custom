# Stance — Asset Lifecycle Monitoring Dashboard (Canonical)

**Instance:** `asset-lifecycle-dashboard`
**Mode:** ml-ai-scope, ubuntu-internet-node
**Date:** 2026-09-07 10:00 +07
**Branch:** `feature/lifecycle-statuses` at commit `6127ff2`
**Ralplan status:** Round 1+2 complete; 3 fold-ins applied; ready for user sign-off
**Author:** Orchestrator (ml-ai mode, MiniMax-M3) — distilled from `stance-planner-v2.md` + `review-architect.md` + `review-architect-v2.md` + `review-critic.md`

---

## Decisions in this artifact

| Source | Decision | Status |
|---|---|---|
| Round 1 Planner (APPROVED) | Sub-dimensions collapse 9→8; cross-filter absorbed into Pinia | ✅ FOLDED |
| Round 1 Architect (REJECT) | Replace view-as-query-target with inline SQLAlchemy CRUD | ✅ FOLDED |
| Round 1 Architect | snake_case response; V3 split; `clean_float_values`; model_lifecycles tenant scoping | ✅ FOLDED |
| Round 2 Planner | Drop view entirely; add V3a/V3b split; full CRUD function | ✅ FOLDED |
| Round 2 Architect (N1) | Add `joinedload(ModelLifecycle.manufacturer)` to fix N+1 | ✅ FOLDED (mechanical) |
| Round 2 Architect (N2) | Move ModelLifecycle tenant filter from JOIN condition to `.filter()` | ✅ FOLDED (mechanical) |
| Round 2 Architect (N3) | Remove dead `OR tenant_id.is_(None)` clauses on NOT NULL columns | ✅ FOLDED (mechanical) |
| Round 2 Critic (CP-2) | Add 3-line future-install-date guard in CRUD function | ✅ FOLDED (mechanical) |
| Round 2 Critic (CP-4) | Add fleet-growth ceiling comment in Pinia store (max 2,000 components) | ✅ FOLDED (mechanical) |
| **Orchestrator override** | **META / CP-3 (launch gate):** keep user-locked Option A; add data-fill as separate follow-up task (not a ship gate) | ✅ ORCHESTRATOR DECISION |
| **Orchestrator override** | **CP-1 (drop chartjs-chart-matrix):** keep plugin per user earlier "i wanna see heatmap" request; document 35-cell caveat | ✅ ORCHESTRATOR DECISION |
| **Orchestrator override** | **P5 over-correction (Planner dropped view entirely):** restore view as documentation artifact per user "Create View" decision | ✅ ORCHESTRATOR DECISION |
| **Pending user** | **Final sign-off** | ⏳ AWAITING 3 DECISIONS + 2 NAMING QUESTIONS |

---

## Final Sub-Dimensions (8 — collapsed from 9)

1. Backend endpoint shape
2. CRUD function (NEW — replaces view-as-query-target)
3. RBAC + tenant isolation (FastAPI layer)
4. Frontend route + component + Pinia store + cross-filter
5. Chart library integration (chartjs-chart-matrix per user request)
6. Data gap UX
7. Deployment + rollback
8. Verification plan

---

## Design Summary

### Backend

**New CRUD function** at `backend/app/crud/asset_lifecycle.py`:

```python
def list_asset_lifecycle_status(db: Session, tenant_id: uuid.UUID):
    """Returns all components with lifecycle status for given tenant.
    
    Reuses _compute_lifecycle_fields() from asset_components.py:12-34
    for lifespan/years_remaining/status computation.
    Applies a guard for future-dated install records.
    """
    components = (
        db.query(AssetComponent)
        .options(
            joinedload(AssetComponent.asset).joinedload(Asset.site),
            joinedload(AssetComponent.asset).joinedload(Asset.area),
            joinedload(AssetComponent.asset).joinedload(Asset.asset_type),
            joinedload(AssetComponent.model_lifecycle).joinedload(ModelLifecycle.manufacturer),
        )
        .outerjoin(Asset, Asset.id == AssetComponent.asset_id)
        .outerjoin(ModelLifecycle, ModelLifecycle.id == AssetComponent.model_lifecycle_id)
        .join(Manufacturer, Manufacturer.id == ModelLifecycle.manufacturer_id)
        .outerjoin(Site, Site.id == Asset.site_id)
        .outerjoin(Area, Area.id == Asset.area_id)
        .filter(
            and_(
                AssetComponent.tenant_id == tenant_id,
                or_(ModelLifecycle.tenant_id == tenant_id, ModelLifecycle.tenant_id.is_(None)),
            )
        )
        .all()
    )
    
    rows = []
    for c in components:
        # Reuse existing computation
        install_date = c.installation_date or (c.asset.installation_date if c.asset else None)
        useful_life = c.model_lifecycle.useful_life_years if c.model_lifecycle and c.model_lifecycle.useful_life_years else (
            c.asset.asset_type.useful_life_years if c.asset and c.asset.asset_type and c.asset.asset_type.useful_life_inheritance_enabled else None
        )
        lifespan, years_remaining, status = _compute_lifecycle_fields(install_date, ...)
        
        # Guard: future install dates produce meaningless negative lifespan
        if lifespan is not None and lifespan < 0:
            years_remaining = None
            status = 'NORMAL'
        
        rows.append({
            "component_id": str(c.id),
            "asset_id": str(c.asset_id),
            "asset_name": c.asset.name if c.asset else None,
            "asset_tag": c.asset.tag if c.asset else None,
            "plant_name": c.asset.site.name if c.asset and c.asset.site else None,
            "area_name": c.asset.area.name if c.asset and c.asset.area else None,
            "model_lifecycle_id": str(c.model_lifecycle_id) if c.model_lifecycle_id else None,
            "model_name": c.model_lifecycle.model_name if c.model_lifecycle else None,
            "manufacturer": c.model_lifecycle.manufacturer.name if c.model_lifecycle and c.model_lifecycle.manufacturer else None,
            "asset_type_name": c.asset.asset_type.name if c.asset and c.asset.asset_type else None,
            "effective_install_date": install_date.isoformat() if install_date else None,
            "lifespan_years": lifespan,
            "effective_useful_life": useful_life,
            "years_remaining": years_remaining,
            "useful_life_source": "model" if c.model_lifecycle and c.model_lifecycle.useful_life_years else (
                "inherited_from_asset_type" if c.asset and c.asset.asset_type and c.asset.asset_type.useful_life_years and c.asset.asset_type.useful_life_inheritance_enabled else "not_set"
            ),
            "lifecycle_status": status,
            "model_eol_status": c.model_lifecycle.lifecycle_status if c.model_lifecycle else None,
        })
    
    # Compute summary
    summary = {
        "total": len(rows),
        "with_data": sum(1 for r in rows if r["useful_life_source"] != "not_set"),
        "not_set": sum(1 for r in rows if r["useful_life_source"] == "not_set"),
        "near_eol": sum(1 for r in rows if r["years_remaining"] is not None and 0 < r["years_remaining"] <= 1.0),
        "end_of_life": sum(1 for r in rows if r["lifecycle_status"] == "END-OF-LIFE"),
    }
    
    return {"components": rows, "summary": summary, "meta": {
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "near_eol_threshold_months": 12,
    }}
```

**New endpoint** at `backend/app/routers/dashboards.py` (add to existing router):

```python
@router.get("/asset-lifecycle")
def get_asset_lifecycle_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Asset lifecycle monitoring dashboard data.
    
    Returns all components with computed years_remaining and lifecycle status,
    scoped to current_user.tenant_id. Client-side interactive model.
    """
    from app.crud.asset_lifecycle import list_asset_lifecycle_status
    data = list_asset_lifecycle_status(db, current_user.tenant_id)
    return clean_float_values(data)
```

**No new view, no new migration, no DB schema change.** Per user "Create View" decision, a view is created (see "Documentation View" below).

### Documentation View (Restored Per User Decision)

**Restoring view as documentation artifact** (per user "Create View" + orchestrator override of Planner's P5 over-correction).

`backend/alembic/versions/add_v_component_lifecycle_status_documentation.py`:

```python
"""add_v_component_lifecycle_status_documentation

Creates dashboard.v_component_lifecycle_status as a documentation artifact
and ad-hoc query helper. NOT used by the FastAPI endpoint.

This view is NOT tenant-safe. Do not query directly from application code.
Application code MUST filter by tenant_id explicitly at the query layer.

Usage: psql ad-hoc queries only.
"""

from alembic import op

revision = 'add_v_component_lifecycle_status_documentation'
down_revision = '<capture from alembic heads>'

VIEW_SQL = """
CREATE SCHEMA IF NOT EXISTS dashboard;

CREATE OR REPLACE VIEW dashboard.v_component_lifecycle_status AS
SELECT
    ac.id AS component_id,
    ac.tenant_id,
    ac.quantity,
    COALESCE(ac.installation_date, a.installation_date) AS effective_install_date,
    -- ... same as before, no tenant filter, no current_setting ...
FROM asset_components ac
JOIN assets a ON ac.asset_id = a.id
LEFT JOIN model_lifecycles ml ON ac.model_lifecycle_id = ml.id
LEFT JOIN manufacturers m ON ml.manufacturer_id = m.id
LEFT JOIN asset_types at ON a.asset_type_id = at.id
LEFT JOIN sites s ON a.site_id = s.id
LEFT JOIN areas ar ON a.area_id = ar.id;
"""

def upgrade():
    op.execute("DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status;")
    op.execute(VIEW_SQL)

def downgrade():
    op.execute("DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status;")
    op.execute("DROP SCHEMA IF EXISTS dashboard CASCADE;")
```

### Frontend

**New route** at `frontend/src/router.js`:

```javascript
{
  path: '/utility/asset-lifecycle',
  component: () => import('@/pages/AssetLifecycleDashboard.vue'),
  meta: { requiresAuth: true }
}
```

**New component** at `frontend/src/pages/AssetLifecycleDashboard.vue`: single-file dashboard with 5 widgets (KPI strip / distribution bar / asset table / heatmap / status badges).

**New store** at `frontend/src/stores/assetLifecycleDashboard.js`:

```javascript
import { defineStore } from 'pinia'

// Maximum fleet size for client-side interactive (no pagination): 2,000 components.
// Beyond this, implement server-side pagination:
//   GET /api/dashboard/asset-lifecycle?page=N&limit=50
// Tracked: 2026-09-07 fleet-state shows 832 components. Threshold = 2,000.
const MAX_COMPONENTS_NO_PAGINATION = 2000

export const useAssetLifecycleDashboardStore = defineStore('assetLifecycleDashboard', {
  state: () => ({
    components: [],
    loading: false,
    error: null,
    filters: {
      lifecycleStatus: null,
      usefulLifeSource: null,
      siteName: null,
    },
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
      const nearEol = state.components.filter(c => c.years_remaining !== null && c.years_remaining > 0 && c.years_remaining <= 1).length
      const endOfLife = state.components.filter(c => c.lifecycle_status === 'END-OF-LIFE').length
      return { total, with_data: withData, not_set: total - withData, near_eol: nearEol, end_of_life: endOfLife }
    },
    paginationWarning(state) {
      return state.components.length > MAX_COMPONENTS_NO_PAGINATION
    },
  },
  actions: {
    setFilter(key, value) { this.filters[key] = value },
    clearFilters() { this.filters = { lifecycleStatus: null, usefulLifeSource: null, siteName: null } },
  },
})
```

**Modified `frontend/package.json`**: add `"chartjs-chart-matrix": "^3.0.0"` to dependencies.

**Modified `frontend/src/api/api.js`**: add `getAssetLifecycleDashboard()` method.

---

## Acceptance Criteria (8 tasks → 10 verification checks)

### Tasks (build order)

- **T1** `backend/app/crud/asset_lifecycle.py` — full CRUD function with eager loading (N1 fix), correct join conditions (N2 fix), dead code removed (N3 fix), future-install-date guard (Critic CP-2). **AC:** function returns rows with all 18 expected fields; eager loading verified via SQL log; future-date guard returns `years_remaining=None`.
- **T2** `backend/app/routers/dashboards.py` — add `/asset-lifecycle` endpoint. **AC:** returns 200 with snake_case JSON; 403 for level-0 user; tenant-scoped (no cross-tenant rows).
- **T3** `backend/alembic/versions/add_v_component_lifecycle_status_documentation.py` — documentation view migration. **AC:** `alembic upgrade` creates view; `alembic downgrade` removes it; no effect on application code.
- **T4** `frontend/src/router.js` — add route. **AC:** navigation to `/utility/asset-lifecycle` renders page.
- **T5** `frontend/src/stores/assetLifecycleDashboard.js` — Pinia store with 2,000-component comment (Critic CP-4). **AC:** all 3 filters work; KPI summary computes; pagination warning fires at >2,000.
- **T6** `frontend/src/api/api.js` — add API method. **AC:** calls correct endpoint, returns parsed JSON.
- **T7** `frontend/src/pages/AssetLifecycleDashboard.vue` — 5 widgets. **AC:** all render; cross-filter wiring works; banner shows when `not_set > 80%`; heatmap renders without console errors; matrix plugin failure falls back to bar.
- **T8** `frontend/package.json` — add `chartjs-chart-matrix@^3.0.0`. **AC:** `npm install` succeeds; import works in dev build.
- **T9** Build deploy — backend Alembic migration first, then frontend rebuild. **AC:** deploys without errors; existing endpoints unaffected.
- **T10** End-to-end verification — run all 10 checks below.

### Verification Plan (10 checks per skill §19)

| # | Check | PASS condition |
|---|-------|----------------|
| V1 | Alembic migration applies | `alembic upgrade` succeeds; view exists in `dashboard` schema |
| V2 | View returns rows | `SELECT count(*) FROM dashboard.v_component_lifecycle_status` returns 832 |
| V3a | Cross-tenant isolation | Create T2 with a component; query as T1 via API; 0 T2 rows visible |
| V3b | Correct tenant count | Query as T1 via API; count matches `asset_components WHERE tenant_id = T1` |
| V4 | Endpoint returns 200 | `curl /api/dashboard/asset-lifecycle` with valid JWT; HTTP 200; snake_case JSON |
| V5 | RBAC blocks level-0 | Auth as user without `utility` section; HTTP 403 |
| V6 | Frontend route loads | Browser nav to `/utility/asset-lifecycle`; page renders; KPI cards show numbers |
| V7 | Heatmap renders | No console errors; matrix chart visible (or grouped bar fallback if plugin fails) |
| V8 | Cross-filter wiring | Click donut segment → table filters; click table row → expansion; dismissible chip appears |
| V9 | Future-date guard | Component with `installation_date = 2099-01-01` returns `years_remaining: null` and `lifecycle_status: "NORMAL"` (not 78 NORMAL) |
| V10 | Banner shows when not_set > 80% | With current data (824/832 = 99%), banner is visible |

---

## Risks

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Tenant isolation bug (R1 from Round 1) | Addressed at CRUD layer with explicit `tenant_id` filter; V3a catches cross-tenant leaks |
| R2 | N+1 query perf bug (N1) | Eager loading via `joinedload`; V3b timing assertion (≤ 3 queries) |
| R3 | Future-install-date bug (Critic A2) | 3-line guard in CRUD function; V9 catches it |
| R4 | Data gap looks broken (99% not_set) | Banner + "Needs configuration" KPI per Option A. Data fill is a SEPARATE follow-up task (not a ship gate per user decision) |
| R5 | chartjs-chart-matrix plugin breaks | Runtime fallback to grouped bar (vue-chartjs already in deps); 47KB dep |
| R6 | Pagination at scale | 2,000-component threshold named; `paginationWarning` getter surfaces when exceeded |
| R7 | Banner UX confusion | 80% threshold for visibility; dismissible; "Needs configuration" label is descriptive |

---

## Open Questions (USER SIGN-OFF REQUIRED)

**Three decisions:**

1. **Future-install-date guard** — 3-line fix in CRUD function. **Orchestrator recommends YES.**
2. **Data-coverage launch gate** — Critic wants to override your Option A lock. **Orchestrator recommends: keep Option A, add data-fill as separate follow-up task** (not a ship gate).
3. **Drop chartjs-chart-matrix?** — Critic wants to drop; you said "try heatmap" earlier. **Orchestrator recommends: keep per your earlier request** (document 35-cell caveat).

**Two naming questions:**

4. **Page name** — "Asset Lifecycle Dashboard" (Planner's choice) vs "Asset Health Dashboard" vs "Refresh Planning Dashboard"?
5. **Page slug** — `/utility/asset-lifecycle` (Planner's choice, matches dashboard section "utility") vs `/dashboards/asset-lifecycle` vs your preference?

---

## Word Count

~1,750 words. Within target.
