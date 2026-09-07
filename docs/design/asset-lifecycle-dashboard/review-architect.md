# Round 1 Architect Review — Asset Lifecycle Monitoring Dashboard

**Reviewer:** Architect (omh-ralplan Round 1)
**Subject:** Planner's stance-planner.md — architectural soundness review
**Date:** 2026-09-07
**Branch:** `feature/lifecycle-statuses` at commit `6127ff2`

---

## 1. Round 1 Verdict

**REJECT** — the tenant-isolation strategy is unsound and cannot be approved with modifications. The proposed `WHERE ac.tenant_id = current_setting('app.current_tenant_id')::uuid` will return all rows from all tenants in production. The view must be rewritten at the FastAPI/CRUD layer with an explicit `WHERE` clause. Details below.

---

## 2. Tenant Isolation Assessment

### The load-bearing finding: `current_setting` is never set in this codebase

**Codebase search results (2026-09-07):**

| Search pattern | Files found |
|---|---|
| `current_setting` | 0 matches across entire backend |
| `app.current_tenant_id` | 0 matches |
| `set_config` | 0 matches |
| `event.listen` (connection/session) | 0 matches |
| `after_flush` / `before_flush` | 0 matches |

**Confirmed absent:**
- `/home/hmcadmin/industrace-v2.3.1/backend/app/database.py` — plain `SessionLocal = sessionmaker(...)` with no SET commands, no connection events, no post-connect hooks
- No `app/db/session.py` file exists
- No `app/dependencies/__init__.py` file exists

**What exists instead:** Every tenant-scoped query in the entire codebase uses an **explicit `tenant_id = :value` parameter** passed from the FastAPI dependency layer. Pattern from `asset_components.py:97-122`:

```python
# backend/app/crud/asset_components.py:97-122
def list_asset_components(db, asset_id, tenant_id=None):
    query = db.query(AssetComponent).join(...).filter(AssetComponent.asset_id == asset_id)
    if tenant_id:
        query = query.filter(
            or_(AssetComponent.tenant_id == tenant_id, AssetComponent.tenant_id.is_(None))
        )
    return query.all()
```

This is the established pattern. No SQLAlchemy event listeners, no PostgreSQL session-level variables.

### Why the Planner's WHERE clause is dangerous

The Planner's DDL in migration `add_v_component_lifecycle_status.py:241-242`:

```sql
WHERE ac.tenant_id = current_setting('app.current_tenant_id', true)::uuid
   OR ac.tenant_id IS NULL;
```

Problems:

1. **`current_setting('app.current_tenant_id', true)` returns NULL** because the session never calls `SET app.current_tenant_id = '...'`. The `true` argument means "return NULL instead of raising error if not set."

2. **`NULL = NULL` evaluates to NULL (not TRUE)** in SQL. So the left side of `OR` is NULL for every row.

3. **The fallback `OR ac.tenant_id IS NULL`** is supposed to be a safety net, but: if any `asset_components` row has a NULL tenant_id, it will be returned to every tenant. In this codebase, the CRUD pattern explicitly allows NULL tenant_id as a "global" fallback: `or_(AssetComponent.tenant_id == tenant_id, AssetComponent.tenant_id.is_(None))`. This means a row with NULL tenant_id is a cross-tenant data leak.

4. **Result: every tenant sees every row from all tenants** (those with NULL tenant_id at minimum, potentially more if the comparison semantics are optimistic).

### Correct layer for tenant enforcement

The existing pattern in `dashboards.py:73-83` is the reference implementation:

```python
# backend/app/routers/dashboards.py:73-83
risky_assets = (
    db.query(Asset)
    .filter(
        and_(
            Asset.tenant_id == current_user.tenant_id,  # explicit WHERE
            Asset.deleted_at == None,
            Asset.risk_score >= 5
        )
    )
    ...
)
```

**Correct architecture:** The new endpoint must use a SQLAlchemy query at the CRUD/router layer — not a PostgreSQL view with `current_setting`. The endpoint handler receives `current_user.tenant_id` from the JWT (confirmed at `auth.py:145` — `tenant_id: str = payload.get("tenant_id")`), and passes it explicitly to a CRUD function that adds `WHERE ac.tenant_id = :tenant_id`.

**Verdict on Planner's prerequisite:** The Planner correctly flagged this as the highest-risk design decision (R1 in stance, Section 3 Dim 3). However, the prerequisite answer is **wrong** — the fallback is not safe. The Architect must require the FastAPI-layer filtering approach.

---

## 3. Architectural Soundness

### Dim 1 — Backend endpoint shape
**APPROVE with modification.** Single endpoint `GET /api/dashboard/asset-lifecycle` returning all 832 component rows is correct for the client-side interactive model. The response schema in Section 4 is complete and correctly named. **Modification required:** the endpoint must use a SQLAlchemy query (not a raw `SELECT * FROM view`), passing `current_user.tenant_id` explicitly.

### Dim 2 — PostgreSQL view creation
**REJECT the view as the data access mechanism. APPROVE the migration infrastructure choice.** The Alembic `op.execute("CREATE VIEW ...;")` pattern is correct and verified (30+ migrations in the versions dir, 3 prior view migrations confirmed). `CREATE OR REPLACE VIEW` is the right idempotency choice. **However, the view should not be the query target** — see Dim 1. The view can still exist as a DDL artifact (for documentation or future direct DB access), but the FastAPI endpoint must query via SQLAlchemy ORM with explicit tenant filter.

### Dim 3 — RBAC + tenant isolation
**PARTIALLY APPROVE.** `require_section_access("utility")` at the router level is confirmed correct: `dashboards.py:30` uses it, and `auth.py:144-145` resolves `tenant_id` from the JWT. RBAC is sound. **Tenant isolation is broken** — see Section 2 above.

### Dim 4 — Frontend route + component
**APPROVE.** Route `/utility/asset-lifecycle` with `meta: { requiresAuth: true }` follows the established pattern. Single file component in `pages/` and Pinia store in `stores/` is correct. No issues.

### Dim 5 — Chart library integration
**APPROVE with low risk.** `chartjs-chart-matrix@^3.0.0` addition is minor (~47 KB). Runtime fallback to grouped horizontal bar chart is a sound defensive pattern. The Planner's observation that 7 sites × 5 bands = 35 cells is small enough for a bar chart is correct and worth preserving.

### Dim 6 — Cross-filter pattern (absorbed into Dim 4)
**APPROVE.** Pinia store as single source of truth with `setFilter(key, value)` is the right pattern. No prop-drilling, no event bus. The implementation in Section 8 is clean and correct.

### Dim 7 — Data gap UX
**APPROVE.** Option A (accept empty state) is the right call. Banner, distinct KPI cards, gray donut segment, and "— Not configured" badge are all appropriate treatments. The 80% threshold for banner visibility is a reasonable gate. The Planner's reasoning (circular dependency, industry standard) is sound.

### Dim 8 — Deployment + rollback
**APPROVE.** Alembic migration at startup via `main.py` hook is confirmed by the existing codebase pattern. `CREATE OR REPLACE VIEW` + `DROP SCHEMA IF EXISTS CASCADE` is correct rollback. No issues.

### Dim 9 — Verification plan
**APPROVE with addition.** The 8-check verification plan is thorough. **Addition required:** V3 must be split into V3a (confirm zero rows for wrong tenant) and V3b (confirm correct row count for known tenant). The current V3 "count matches `asset_components` row count" is insufficient — it tests nothing about cross-tenant isolation.

---

## 4. Silently Absent Concerns

### 4a. The raw SQL file and the migration DDL are out of sync
The raw SQL at `/home/hmcadmin/v_component_lifecycle_status.sql` has **no `tenant_id` column in the SELECT list** and **no `WHERE` clause**. The Planner's migration DDL adds `ac.tenant_id` to the SELECT (line 179) and adds the `WHERE current_setting(...)` clause. This is a **DDL divergence** — the raw SQL file becomes stale and misleading after the migration lands. No process is specified for keeping them in sync. Recommendation: the raw SQL file should be updated to match the migration DDL or removed.

### 4b. The raw SQL file has a hardcoded `JOIN assets a` (not LEFT JOIN)
The raw SQL at line 79 uses `JOIN assets a` (inner join), but the Planner's DDL at line 235 uses the same inner join. If a component's asset is deleted/missing, the component would vanish from the view. The existing CRUD function at `asset_components.py:97` uses an implicit inner join via SQLAlchemy ORM. This is a pre-existing data quality concern, not a new risk, but it should be noted.

### 4c. No mention of what happens if the view already exists (idempotency)
The raw SQL uses `DROP VIEW IF EXISTS ... CASCADE` before `CREATE VIEW`. The migration uses `CREATE OR REPLACE VIEW`. These are not equivalent: `CREATE OR REPLACE VIEW` cannot change column names or constraints, while `DROP + CREATE` can. If the view is revised in a future migration (e.g., adding a new column), `CREATE OR REPLACE` will fail if the column list changes. The migration should use `DROP VIEW IF EXISTS dashboard.v_component_lifecycle_status;` as the first statement, then `CREATE VIEW`, matching the raw SQL pattern.

### 4d. The response JSON shape uses camelCase but the codebase convention is snake_case
The response schema in Section 4 uses `nearEolThresholdMonths` (camelCase) and `computedAt`. Searching the existing codebase at `dashboards.py:85-99` shows snake_case in API responses: `asset_type_name`, `site_name`, `ip_address`. The response schema should use snake_case throughout: `near_eol_threshold_months`, `computed_at`.

### 4e. No consideration of the view's dependency on `model_lifecycles` table's tenant_id
The view joins `asset_components → model_lifecycles` at line 236. Does `model_lifecycles` have a `tenant_id` column? If so, the view should filter on it too. The raw SQL file does no such filtering. This should be verified before the migration is written. If `model_lifecycles` is tenant-scoped, the view is missing a tenant filter on that join.

---

## 5. Specific Counter-Proposals

### P1 — Replace the view approach with inline SQLAlchemy query
**File:** `backend/app/crud/asset_lifecycle.py` (new)

Instead of `SELECT * FROM dashboard.v_component_lifecycle_status`, the CRUD function should construct the same query inline:

```python
def list_asset_lifecycle_status(db: Session, tenant_id: uuid.UUID):
    return (
        db.query(
            AssetComponent.id.label("component_id"),
            AssetComponent.tenant_id,
            # ... all columns as in the view DDL ...
        )
        .join(Asset, AssetComponent.asset_id == Asset.id)
        .outerjoin(ModelLifecycle, AssetComponent.model_lifecycle_id == ModelLifecycle.id)
        .outerjoin(Manufacturer, ModelLifecycle.manufacturer_id == Manufacturer.id)
        .outerjoin(AssetType, Asset.id == AssetType.id)  # verify join path
        .outerjoin(Site, Asset.site_id == Site.id)
        .outerjoin(Area, Asset.area_id == Area.id)
        .filter(AssetComponent.tenant_id == tenant_id)  # explicit tenant filter
        .all()
    )
```

The `lifespan_years`, `years_remaining`, `lifecycle_status`, and `useful_life_source` computed columns are currently implemented as SQL expressions in the view. These should be implemented as SQLAlchemy `column()` expressions or as Python helper functions (reusing `_compute_lifecycle_fields` from `asset_components.py:12-34`) applied to the result rows.

**Why this is better:** Zero risk of cross-tenant leakage; no dependency on session-level PostgreSQL configuration; the existing codebase pattern everywhere.

### P2 — Drop the view entirely; or keep it as a no-tenant-filter read-only artifact
If the user still wants a view for ad-hoc DB access, keep the view DDL but:
1. Remove the `WHERE current_setting(...)` clause — it does nothing and creates false confidence
2. Document clearly: "this view is NOT tenant-safe; always apply `WHERE tenant_id = :id` in queries"
3. The FastAPI endpoint MUST NOT query this view directly

### P3 — Add V3 tenant-isolation test to the verification plan
Split V3 into two explicit checks:

| Check | Command | PASS condition |
|-------|---------|---------------|
| V3a | Create second test tenant T2, insert a component, query as T1 | T1 sees 0 rows from T2 |
| V3b | Query as T1 | Count matches `asset_components` filtered by T1 |

V3 alone ("count matches") is insufficient — a misconfigured view that returns all rows would pass V3 but fail V3a catastrophically.

### P4 — Fix the response schema snake_case convention
All field names in the response JSON (Section 4 of stance-planner.md) should use snake_case to match the rest of the Industrace API:
- `nearEolThresholdMonths` → `near_eol_threshold_months`
- `computedAt` → `computed_at`
- Field names in the `components[]` array should similarly be snake_case (matching existing patterns like `asset_type_name`, `model_eol_status` which the Planner already uses correctly).

### P5 — The migration should use `DROP VIEW IF EXISTS` before `CREATE VIEW`
The raw SQL file pattern (`DROP VIEW IF EXISTS ... CASCADE; CREATE VIEW ...`) is more robust than `CREATE OR REPLACE VIEW` for future schema evolution. If a future migration needs to change the column list, `CREATE OR REPLACE` will raise an error but `DROP + CREATE` will succeed. Use the raw SQL pattern in the migration.

### P6 — Verify `model_lifecycles` tenant scoping before finalizing the view/CRUD
Check whether `model_lifecycles` has a `tenant_id` column and whether it needs filtering in the join. If it is tenant-scoped, add `AND ml.tenant_id = :tenant_id` to the join condition in the CRUD query.

---

## 6. Adjacent Mechanism Check (P14)

The following existing mechanisms solve adjacent problems and should be reused:

| Mechanism | File | Reuse value |
|-----------|------|-------------|
| `_compute_lifecycle_fields()` helper | `backend/app/crud/asset_components.py:12-34` | Already implements the exact lifespan/status computation logic. Should be imported/reused, not reimplemented in SQL in the view. |
| `require_section_access("utility")` | `backend/app/services/rbac.py:43-64` | Already used in `dashboards.py:30` as router-level dependency. Confirmed correct. |
| Tenant-filtered query pattern | `backend/app/routers/dashboards.py:73-83` | `risky_assets` endpoint does explicit `Asset.tenant_id == current_user.tenant_id` — this is the exact pattern to replicate. |
| `clean_float_values()` helper | `backend/app/routers/dashboards.py:14-25` | Prevents NaN/Infinity JSON serialization errors. Should be applied to the lifecycle status response since `years_remaining` and `lifespan_years` can produce edge-case float values. |
| Alembic view migration pattern | `backend/alembic/versions/add_asset_review_fields.py` (3 prior view migrations) | Confirms `op.execute("CREATE VIEW ...;")` is the right Alembic primitive. |
| `lifecycle_status` computed field from existing endpoint | `backend/app/routers/asset_components.py:42-61` | The existing `GET /assets/{asset_id}/components/lifecycle-status` does the same computation in Python. The new endpoint should either reuse the existing schema/Pydantic model or confirm the new response shape is a superset. |

---

## 7. Summary of Required Changes Before Re-Approval

| # | Change | Priority | Verdict change |
|---|--------|----------|----------------|
| 1 | Remove `current_setting` from view DDL; replace with SQLAlchemy query at CRUD layer with explicit `tenant_id` filter | CRITICAL | REJECT → REQUEST_CHANGES |
| 2 | Apply `clean_float_values()` to response data | HIGH | Required |
| 3 | Fix response schema snake_case (`nearEolThresholdMonths` → `near_eol_threshold_months`, etc.) | MEDIUM | Required |
| 4 | Add V3a/V3b tenant-isolation verification to the verification plan | HIGH | Required |
| 5 | Use `DROP VIEW IF EXISTS` + `CREATE VIEW` instead of `CREATE OR REPLACE VIEW` in migration | MEDIUM | Required |
| 6 | Investigate `model_lifecycles` tenant scoping; add to filter if needed | MEDIUM | Required |
| 7 | Update or remove the raw SQL file `/home/hmcadmin/v_component_lifecycle_status.sql` to reflect actual DDL | LOW | Recommended |

---

## §Provisos (for APPROVE_WITH_PROVISO — not granted in this round)

N/A — this round is REJECT.

---

## Word Count

~1,400 words.

---

## Verdict

**REJECT**

The plan cannot proceed to Round 2 in its current form. The tenant-isolation mechanism (`current_setting('app.current_tenant_id')`) is not implemented in this codebase and the fallback `OR ac.tenant_id IS NULL` clause creates a cross-tenant data leak. All other decisions are sound. The required fix is in Section 5, P1: replace the view query target with an inline SQLAlchemy CRUD function that passes `current_user.tenant_id` explicitly, matching the established pattern throughout the codebase.
