# Context Package: Asset Lifecycle Monitoring Dashboard

**Instance:** `asset-lifecycle-dashboard`
**Mode:** design-shaped (architecture decisions, not feature list)
**Date:** 2026-09-07 09:35 +07
**Author:** orchestrator (ml-ai mode, ubuntu-internet-node)

---

## The design question

Build a read-only asset-lifecycle monitoring dashboard inside the Industrace Vue frontend that surfaces **years_remaining as the primary signal** for every component in the fleet, with **manufacturer EoS shown only as a status badge**. The dashboard must be cheap to maintain, tenant-isolated, and resilient to the current data gap (99% of components have no useful_life data).

What the design must do:
- Ship 5 widgets (KPI strip / years distribution / asset table / site heatmap / status badges) in one Vue page
- Backed by a single new endpoint `GET /api/dashboard/asset-lifecycle` (read-only, RBAC level 1)
- Data source: a new PostgreSQL view `dashboard.v_component_lifecycle_status` (per user decision; NOT inline SQL)
- Client-side interactive (load all, JS filter/sort, no per-click HTTP)
- Use existing chart.js@4.4.0 + vue-chartjs@5.2.0 + add chartjs-chart-matrix@^3.0.0 for true heatmap
- Plan-first per user standing rule: no code until this plan is APPROVED

What the design must honor:
- User's standing STANDING RULE (WS-8 of 2026-09-05 handoff): NO new areas without explicit user approval
- P36 trap: `/api/dashboard/*` path must NOT trigger `_BULK_PATH_KEYWORDS` (`"bulk"`, `"recalculate-all"`, `"recalculate"`, `"/empty"`)
- Useful life inheritance: must reuse existing `asset_types.useful_life_years` + `useful_life_inheritance_enabled` cascade (already shipped 2026-09-04)
- The existing endpoint `GET /api/assets/{asset_id}/components/lifecycle-status` is unchanged
- Refine note v2.1 (`main/hmc-ml-ai/ideas/refine/refine-2026-09-07-asset-lifecycle-monitoring-dashboard`) is the input spec

What it is the foundation for: closing the open backlog item "dashboard widget" from the Industrace OT pilot (15/29 passing as of 2026-08), and unlocking future lifecycle-driven dashboards (compliance rollups, refresh planning).

---

## Sub-dimensions (orchestrator's first cut — Critic may rework)

1. **Backend endpoint shape** — response schema, query strategy (single SQL with joins vs paginated)
2. **PostgreSQL view creation** — DDL location, idempotency, rollback, schema naming
3. **RBAC + tenant isolation** — how RBAC level 1 maps to dashboards section "utility", how tenant_id filter applies
4. **Frontend route + component** — Vue 3 composition API, Pinia store, single file vs split
5. **Chart library integration** — chart.js + vue-chartjs + chartjs-chart-matrix plugin registration
6. **Cross-filter pattern** — Pinia store as single source, click handlers update shared filter
7. **Data gap UX** — how 824/832 components showing `not_set` should appear (badge, filter, banner)
8. **Deployment + rollback** — DB migration + frontend rebuild, feature flag, downtime window
9. **Verification plan** — ad-hoc verify script per skill §19 (PASS/WARN/FAIL summary)

---

## Constraints (user-settled, NOT open for debate)

These are non-negotiable per the conversation 2026-09-07 08:35–09:25 +07:

- **Scope:** years_remaining primary; EoS as status indicator only; NO financials
- **Interactive model:** client-side (load all, JS filter/sort)
- **Host:** new Vue page inside Industrace frontend (same JWT, same RBAC, same deploy pipeline)
- **Refresh cadence:** page load only, no polling
- **Near-EoL threshold:** 12 months (planning lead time for cost)
- **Widget set:** 5 widgets (KPI / distribution / table / heatmap / badges); timeline widget REMOVED
- **Heatmap:** try `chartjs-chart-matrix@^3.0.0` plugin first, fallback grouped bar (Site × status counts)
- **DB approach:** CREATE the view (`dashboard.v_component_lifecycle_status`) per user decision; not inline SQL
- **Response to data gap:** Option A — build the dashboard, accept empty state for now (user locked this 09:25)
- **Process:** ralplan consensus (Planner+Architect+Critic) before ready → building (user standing rule)

---

## Out of scope

- Financial / cost / depreciation layer (explicitly OUT)
- Asset CRUD operations (read-only dashboard)
- New RBAC sections (use existing "utility" section)
- New audit log entries (dashboard is read-only consumer)
- Mobile app or standalone SPA (host inside Industrace Vue frontend)
- Bulk actions / write endpoints (P36 trap risk)
- Per-component time-series charts (single snapshot only)
- Notifications / alerts / email digests
- AI / LLM-generated insights (out of scope for v1)

---

## Required reading (absolute paths, must open not summarize)

### Principles + directives
- `/home/hmcadmin/.hermes/profiles/ml-ai-scope/skills/omh/omh-ralplan-driver/SKILL.md` (ralplan playbook, esp. P1–P26 pitfalls)
- `/home/hmcadmin/.hermes/profiles/ml-ai-scope/skills/core/agent-startup-protocol/SKILL.md` (verify-after-edit pattern §19)
- `/home/hmcadmin/.hermes/profiles/ml-ai-scope/skills/productivity/ideas-pipeline/SKILL.md` (pipeline gates)

### Inspiration / prior art
- `/home/hmcadmin/it-asset-lifecycle-dashboard-best-practices.md` (21KB Agent 2 industry research)
- `main/hmc-ml-ai/ideas/refine/_research/research-2026-09-07-industry-standards-asset-lifecycle-dashboards.md` (BM research summary)

### Internal-repo investigation (Agent 1)
- `main/hmc-ml-ai/ideas/refine/_research/research-2026-09-07-industrace-repo-investigation.md`
- `main/hmc-ml-ai/ideas/refine/refine-2026-09-07-asset-lifecycle-monitoring-dashboard` (refine v2.1 — current input spec)

### Target platform (Industrace v2.3.x)

**Backend:**
- `/home/hmcadmin/industrace-v2.3.1/backend/app/models/model_lifecycle.py` (model schema)
- `/home/hmcadmin/industrace-v2.3.1/backend/app/models/asset.py` (assets.installation_date)
- `/home/hmcadmin/industrace-v2.3.1/backend/app/models/asset_type.py` (useful_life_years + inheritance_enabled)
- `/home/hmcadmin/industrace-v2.3.1/backend/app/models/asset_component.py`
- `/home/hmcadmin/industrace-v2.3.1/backend/app/services/rbac.py` (`_BULK_PATH_KEYWORDS`)
- `/home/hmcadmin/industrace-v2.3.1/backend/app/routers/asset_components.py` (existing lifecycle-status endpoint pattern)
- `/home/hmcadmin/industrace-v2.3.1/backend/app/routers/dashboards.py` (existing dashboard router using `require_section_access("utility")`)
- `/home/hmcadmin/industrace-v2.3.1/backend/app/main.py` (router registration)
- `/home/hmcadmin/industrace-v2.3.1/backend/app/schemas/asset_component.py` (Pydantic response shape)

**Frontend:**
- `/home/hmcadmin/industrace-v2.3.1/frontend/package.json` (chart.js@4.4.0, vue-chartjs@5.2.0)
- `/home/hmcadmin/industrace-v2.3.1/frontend/src/router.js` (route registration)
- `/home/hmcadmin/industrace-v2.3.1/frontend/src/views/Dashboard.vue` (existing dashboard pattern — read for style)

**DB:**
- `/home/hmcadmin/v_component_lifecycle_status.sql` (the view SQL to be executed on live DB)

### Adjacent mechanism in tree
- `/home/hmcadmin/industrace-v2.3.1/backend/app/crud/asset_components.py` (lifecycle computation logic — `_compute_lifecycle_fields`)

### Existing skill references
- `/home/hmcadmin/.hermes/profiles/ml-ai-scope/skills/mlops/openwebui-ops/SKILL.md` (PersistentConfig quirk — NOT relevant here, but read to confirm not confused)

---

## Live DB facts (probed 2026-09-07 09:20 +07)

| Fact | Value | Source |
|---|---|---|
| Live DB has zero views | `dashboard` schema does not exist | bridge.sh → psql |
| Live DB has zero materialized views | 0 rows in `pg_matviews` (non-system) | psql |
| Component count | 832 | `SELECT count(*) FROM asset_components` |
| Asset count | 37 | `SELECT count(*) FROM assets` |
| Model lifecycle count | 1041 | `SELECT count(*) FROM model_lifecycles` |
| Asset type count | 39 (24 with useful_life) | psql |
| Components with calculable years_remaining | 8 / 832 (1%) | inline SQL test |
| Components with `useful_life_source='not_set'` | 824 / 832 (99%) | inline SQL test |
| Site count | 7 | psql |
| Area count | 35 | psql |
| Manufacturer count | 105 | psql |
| Postgres role | `industrace_user` / `Hmcepks301!` | env on container |

---

## Contested questions (seed contests for the Critic)

1. **Is creating the view the right choice?** User chose option C (create view) over option A (inline SQL). But: creating a view touches DB schema (needs migration), and a future schema change requires updating the view. Inline SQL has no migration cost. Is the user's choice right given the maintenance trade-off?

2. **Single endpoint vs multiple endpoints:** Should the response include all 5 widgets' data in one payload (~50KB JSON), or split into 5 endpoints (KPI / distribution / heatmap / table / badges) for lazy loading? User locked "client-side interactive, load all once" — does that foreclose lazy loading per widget?

3. **Heatmap plugin vs grouped bar fallback:** `chartjs-chart-matrix@3.0.8` is 47KB unpacked, MIT, compatible. But: it adds a frontend dep, requires rebuild, and the heatmap visual may not render well at our site count (7 sites × 5 status bands = 35 cells — small enough that grouped bar may be clearer). When does grouped bar become the better choice?

4. **12-month threshold computation in backend or frontend?** User said "compute bands from years_remaining" but didn't say where. Backend is more reusable (the band value becomes queryable via API); frontend is faster to iterate. Which is right?

5. **Tenant isolation enforcement:** Refine note says add `WHERE tenant_id = :current`. But: `dashboard.v_component_lifecycle_status` joins across tenants by default. If the view is created without a tenant filter, every tenant sees every other tenant's data. Is the view definition tenant-aware (parameterized), or tenant-filtered at query time, or filtered at the FastAPI dependency layer?

6. **Data gap UX:** 824/832 components show `not_set`. Options: (a) prominent banner "fill data" with link, (b) silently filter them out of counts, (c) show as a 6th category in the donut, (d) require explicit "show not_set" toggle. Which?

7. **View migration strategy:** Should the view creation be: (a) raw psql via migration script, (b) Alembic migration version, (c) admin-only psql documented in DEPLOY.md? Industrace uses Alembic per the project structure — does Alembic handle views, or do we need raw SQL?

8. **RBAC level required:** The dashboards router uses `require_section_access("utility")` (level 1 read). But the asset lifecycle data may be considered more sensitive than utility-level. Should we add a new section `"lifecycle"` with explicit grants, or trust the existing `"utility"` level? The existing endpoint `/api/assets/{asset_id}/components/lifecycle-status` uses what level?

9. **Ad-hoc verification scope:** Per skill §19, verify script must produce `PASS: N / WARN: N / FAIL: N`. What are the 5–10 specific verifications? (e.g., backend health, view exists, response shape, frontend route loads, RBAC blocks forbidden role, tenant isolation, heatmap renders, etc.)

---

## META question (licenses Critic to contest framing)

> **Are these the right sub-dimensions?** Should the plan treat the data gap (99% not_set) as a blocker requiring data fill before shipping, or as an acceptable v1 state to build the dashboard around? User said "Option A — accept empty state" — but is that the right choice given that a dashboard showing 8/832 components will look broken to end users?

---

## What done looks like

- Plan document (this ralplan output) covers all 9 sub-dimensions with specific decisions
- Each decision has acceptance criteria a code reviewer can check
- View DDL is concrete and idempotent (DROP VIEW IF EXISTS … CREATE VIEW …)
- Endpoint response schema is locked (no "TBD")
- Frontend file list is concrete (no "TBD")
- Verification script has 5–10 specific checks, each runnable in <5 min
- Risks list includes the data gap, P36 trap, tenant isolation, plugin compat
- Brief.md is decisions-first and ≤1 page (per P26)

---

## Premises verified (P13)

- **Premise:** "Alembic handles view migrations" — **VERIFIED 2026-09-07 09:40**
  - Alembic versions dir exists at `/home/hmcadmin/industrace-v2.3.1/backend/alembic/versions/` with 30+ migrations
  - 3 migrations mention views (`add_asset_review_fields.py`, `add_model_lifecycles_table.py`, `add_review_configuration_fields.py`)
  - Pattern: use `op.execute("CREATE VIEW ...")` in `upgrade()` + `op.execute("DROP VIEW ...")` in `downgrade()`
  - **Conclusion:** new view creation goes as an Alembic revision; do not use raw psql in deploy
- **Premise:** "frontend rebuild adds 3–5 min downtime"
  - PILOT_DEPLOYMENT_CHECKLIST.md has no downtime/rebuild procedure
  - **Conclusion:** assume conservative — plan includes feature flag for heatmap plugin so deploy can be staged

## Branch state (P9 freshness check)

- **Branch:** `feature/lifecycle-statuses` at commit `6127ff2`
- **Ahead/behind upstream:** 5 ahead / 0 behind (clean)
- **Last commit:** `fix(rbac-p36): rename /assets/bulk-* routes to /multi-* to avoid keyword escalation`
- All design work will land on this branch as new commits

---

## Round budget

Up to 3 rounds. Fast-track mode is NOT applicable — user explicitly asked for "see overall plan before initial build" which requires consensus loop. Default to full mode.
