# Brief — Asset Lifecycle Monitoring Dashboard

**Instance:** `asset-lifecycle-dashboard`
**Mode:** ml-ai-scope, ubuntu-internet-node
**Date:** 2026-09-07 09:55 +07
**Status:** Ralplan Round 2 complete; Architect re-review pending
**Your reading time:** ~3 minutes

---

## TL;DR

The plan is **close to ready**. The Critic (Round 1+2) caught 4 issues — 2 real bugs to fix, 1 principle to add, 1 judgment call to confirm. The Architect's Round 2 re-review is still running but the design is structurally sound. I want your sign-off on **3 decisions** before I move refine → ready and start building.

## Where the design landed

A read-only Vue page inside Industrace frontend at `/utility/asset-lifecycle`, backed by one new SQLAlchemy CRUD function (`list_asset_lifecycle_status()` in `crud/asset_lifecycle.py`). Tenant isolation enforced at the FastAPI layer via `current_user.tenant_id` (matches 300+ existing queries — the view-as-query-target idea from Round 1 was wrong for this codebase). 5 widgets (KPI strip, distribution bar, asset table, heatmap, status badges), client-side interactive, 12-month near-EoL threshold, snake_case JSON response. Chart.js 4.4.0 + vue-chartjs 5.2.0 already in deps; `chartjs-chart-matrix@^3.0.0` is a new 47KB dep for true heatmap (per your earlier request).

## 3 decisions you need to make

### Decision 1 — Future-install-date guard (RECOMMEND YES)

**The bug:** `_compute_lifecycle_fields()` in `asset_components.py:12-34` computes `years_remaining` by subtracting `lifespan` (today minus install_date) from `effective_useful_life`. If `install_date` is in the future (e.g., a misconfigured record with `installation_date = 2099-01-01`), `lifespan` is ~-73, and `years_remaining` becomes **+78 with NORMAL status** — a future-dated asset looks like it has 78 years of useful life. This is a real correctness issue, not a hypothetical.

**My take:** Add a 3-line guard in the CRUD function that sets `years_remaining = None` and `status = 'NORMAL'` when `lifespan < 0`. Tiny cost, fixes a real bug. **Recommend YES.**

### Decision 2 — Data-coverage launch gate (RECOMMEND: SEPARATE TASK, NOT A GATE)

**The Critic's argument:** 99% of components have no useful_life data. Shipping a dashboard that shows 824/832 components as "Not configured" with a banner is documenting the gap, not solving it. The Critic wants a hard launch gate: don't expose the dashboard to end users until `not_set < 50%` of total, with a data-fill task list as part of the project.

**My take:** The Critic's principle is correct (it IS a data quality problem, not a UX problem) — but **you already locked Option A** ("accept empty state for now") in our 09:25 conversation. I want to honor that lock. **My recommendation:** keep Option A in the dashboard plan, but **add the data-fill task list as a separate follow-up deliverable** (out of scope for this iteration, but tracked). The dashboard ships with empty state per your decision; data fill is the next project.

**Counter-question:** Do you want to override the Option A lock and add a data-fill dependency to the dashboard project? (Would push the ship date out.)

### Decision 3 — Drop chartjs-chart-matrix? (RECOMMEND: KEEP — per your earlier request)

**The Critic's argument:** The Planner's own analysis says "the grouped bar fallback is clearer at 35 cells" — so installing a 47KB plugin to use the fallback is wasteful.

**My take:** This is correct math (matrix is suboptimal at 7 sites × 5 bands = 35 cells), **but you explicitly said "i wanna see heatmap if you applicable. if impossiable to be added group bar"** in our 09:08 conversation. The user lock is "try heatmap, fallback to grouped bar." Dropping the plugin overrides your decision. **My recommendation:** install the plugin, render the heatmap, document the 35-cell caveat in the plan, and add a note that the plugin is kept for future scale (if site count grows past 15, the matrix becomes the right choice).

**Counter-question:** Drop the plugin and use only grouped bar? (Would override your earlier decision.)

## Other changes I'm folding in (no decision needed)

- **CP-4: Fleet-growth ceiling** — Add a 1-line comment in the Pinia store: "Max 2,000 components for no-pagination. Beyond: implement server pagination." Cheap, future-proofing.
- **P5 over-correction** — The Planner dropped the view entirely (per your "Create View" lock, the view should STAY as a documentation artifact). I'll fold the view back in as a no-tenant-filter DDL artifact with a comment "not tenant-safe; API does not use this view; do not query directly."

## What I'd build (when you sign off)

14 tasks, ~10 dev hours total. Order: Alembic migration + CRUD function (T1-T3) → endpoint + schema (T4-T5) → frontend store + route (T6-T7) → dashboard component (T8-T9) → verify (T10). Backend ships first via existing deploy pipeline (no downtime). Frontend rebuild is a static-asset change (~3-5 min). Verification: 10 specific checks (PASS/WARN/FAIL per skill §19).

## Open questions for you

1. **Decision 1 (future-date guard):** YES / NO?
2. **Decision 2 (launch gate):** Override Option A and add data-fill to this project / Keep Option A + separate follow-up task / No follow-up?
3. **Decision 3 (heatmap plugin):** Keep per your earlier request / Drop and use only grouped bar?
4. **Naming:** "Asset Lifecycle Dashboard" (per refine v2.1) vs "Asset Health Dashboard" vs "Refresh Planning Dashboard"? This is the page title and dashboard title in the UI.
5. **Page slug:** `/utility/asset-lifecycle` (Planner's choice, matches dashboard section "utility") vs `/dashboards/asset-lifecycle` vs your preference?

## Where I'm overriding the loop

- **META reframe (CP-3):** Critic wants to re-open Option A. I'm holding your lock.
- **CP-1 (drop plugin):** Critic wants to drop the heatmap plugin. I'm holding your earlier request.
- **P5 over-correction:** Planner dropped the view entirely. I'm restoring it as documentation artifact per your "Create View" decision.

These overrides are explicit per ralplan-driver P25 (orchestrator holds the altitude, applies own bar, doesn't surface every loop catch as a question to the user).

## Files written so far

```
/home/hmcadmin/industrace-v2.3.1/docs/design/asset-lifecycle-dashboard/
├── context.md               (13.1 KB) — design question, sub-dimensions, constraints
├── stance-planner.md        (25.0 KB) — Round 1 Planner, REJECTED
├── review-architect.md      (16.8 KB) — Round 1 Architect, REJECT
├── stance-planner-v2.md     (Round 2 Planner, REQUEST_CHANGES, all P1-P6 + 4d/4e addressed)
└── review-critic.md        (15.5 KB) — Round 1+2 Critic, REQUEST_CHANGES, 4 CPs)

/home/hmcadmin/industrace-v2.3.1/docs/design/asset-lifecycle-dashboard/pending/
├── brief.md                (THIS FILE) — what you read
├── stance.md                (canonical, distilled — NOT YET WRITTEN, pending your sign-off)
├── <orchestrator>-review-deep.md (NOT YET WRITTEN)
└── .omh/plans/ralplan-asset-lifecycle-dashboard.md  (NOT YET WRITTEN)
```

## Pipeline state

```
[intake] ✓ superseded → [refine v2.1] ✓ active → [ready ⏳] → [building] → [shipped]
                                              ↑
                                       WE ARE HERE
                              Architect Round 2 still running
                              Brief written, awaiting your decisions
```

After your sign-off, I write `stance.md` (canonical) + deep review + commit, then promote to `ready/`, then start building.
