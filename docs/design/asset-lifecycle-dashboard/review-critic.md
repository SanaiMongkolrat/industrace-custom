# Round 1+2 Critic Review — Asset Lifecycle Monitoring Dashboard

**Reviewer:** Critic (omh-ralplan Round 1+2)
**Subject:** `stance-planner-v2.md` — principle audit and load-bearing assumption stress-test
**Date:** 2026-09-07
**Branch:** `feature/lifecycle-statuses` at commit `6127ff2`

---

## 1. Round 1+2 Verdict

**REQUEST_CHANGES**

The plan is closer to ready than in Round 1, but three unresolved issues remain: (1) a silently-absent data-fill workflow, (2) an unvalidated edge case in `_compute_lifecycle_fields` for future install dates, and (3) a self-contradicting rationale for the `chartjs-chart-matrix` install. Additionally, two of the eight sub-dimensions have mechanical Architect-adoption that warrant independent scrutiny.

---

## 2. META Question Answer

**Should the 99% not_set data gap be treated as a v1 blocker requiring data fill, or as an acceptable empty-state UX challenge?**

The Planner adopted Option A (accept empty state) and the Architect agreed. **I disagree with the framing of that decision.**

The data gap is not a UX problem. It is a **data quality problem being papered over with a UX treatment.** Shipping a dashboard that shows 824/832 components as "not configured" with zero actionable lifecycle data is not an acceptable v1 state — it is a dashboard that tells users their fleet is 99% unmonitored, then asks them to fix it themselves. The banner ("fill data") does not solve the gap; it documents it.

**What the plan should include:** A parallel v1 data-fill workflow — a prioritized list of asset types with `useful_life_years` already set but `useful_life_inheritance_enabled = false` (which would activate the inheritance cascade), plus a one-time seeding script or admin UI hint for the 24 asset types that have `useful_life_years` but aren't contributing. The dashboard and the data fill are one project. Shipping only the dashboard while the data gap remains 99% will result in user complaints that look like product failures, not data quality issues.

**Proposed alternative:** Accept empty state for the KPI cards and distribution chart (which would show near-100% gray), but include a mandatory data-coverage gate: the banner threshold of 80% not_set (Section 11) is arbitrary. The plan should define a hard launch gate: do not ship the dashboard to end users until `not_set < 50%` of total components, with a documented data-fill task list as part of the same project.

---

## 3. Principle Audit — Silently Absent Principles

### P-A: The dashboard has no write-path story, but "read-only" is not permanent

The plan states "read-only dashboard" as a constraint. But the context package says this is "the foundation for closing the open backlog item 'dashboard widget'... and unlocking future lifecycle-driven dashboards (compliance rollups, refresh planning)." The "compliance rollups" and "refresh planning" use cases will require write paths (triggering refresh workflows, setting target dates). The plan should name this as an **architectural principle**: the dashboard's data model and component shape must be designed to accommodate future write-path extensions without a schema break. Specifically, `lifecycle_status` and `years_remaining` are computed fields today — if they become user-settable override fields in v2, the response schema changes.

### P-B: The plan optimizes for the current 832-component snapshot, not a 5-year growth trajectory

The constraint "client-side interactive, load all, no pagination" (Dim 1) is locked based on the current fleet size. At 832 components, this is defensible (~50KB JSON). But:
- The plan has 37 assets today, 7 sites, 35 areas, 105 manufacturers
- If the fleet grows to 5,000 components (plausible over 3 years), the 50KB payload becomes ~300KB
- The `filteredComponents` getter re-runs a full O(n) filter on every store update, every chart click
- No mention of whether the Pinia store pagination strategy or a virtual-scroll table is planned for scale

**The principle the plan should state explicitly:** The client-side interactive model is acceptable for the current fleet size. The plan must include a **load test threshold** — a specific component count (e.g., 2,000) at which pagination becomes required, with the frontend component architected to support that migration without a full rewrite.

### P-C: The useful_life inheritance cascade is documented but its complement is not

The context.md states: "must reuse existing `asset_types.useful_life_years` + `useful_life_inheritance_enabled` cascade (already shipped 2026-09-04)." The plan correctly reuses it.

**What is not documented:** What happens when `useful_life_inheritance_enabled = false` on an asset type? The cascade is disabled, but the plan does not state what signal the user should use in that case. Does the dashboard show "not_set" for those components? Does the user need to set `useful_life_years` directly on the model lifecycle? This is a **silent gap in the data-filling UX** — the banner tells users to "set useful_life_years on asset types or model lifecycles" but does not address the inheritance-disabled case. The plan should state this as a known data-filling constraint.

---

## 4. Stress-Test Results: A1–A5

### A1: "832 components is small enough to load once — no pagination"
**FAIL.** The assumption is defensible today but unvalidated over a 5-year horizon. See P-B above. The plan provides no growth ceiling, no load test, and no pagination trigger. This is acceptable only if the plan explicitly documents the fleet-growth principle (P-B).

### A2: "years_remaining is the right primary signal"
**FAIL — edge case unhandled.** I verified `_compute_lifecycle_fields` (asset_components.py:12-34):

```python
years_delta = today.year - install_date.year  # could be -70+ for 2099 install
# ...
years_remaining = round(eff_useful - lifespan, 2)  # negative lifespan → large positive years_remaining
status = 'END-OF-LIFE' if lifespan >= eff_useful else 'NORMAL'
```

**The bug:** If `install_date` is in the future (e.g., a misconfigured record with `installation_date = 2099-01-01` and `eff_useful = 5`), `lifespan` is approximately -73 years (negative), `years_remaining` is approximately +78, and `status` is `'NORMAL'` because `lifespan >= eff_useful` evaluates to `False`. An asset supposedly installed in 2099 shows 78 years of useful life remaining and NORMAL status. This is not a hypothetical — the DB has 37 assets and 832 components, and future-dated install dates are a known data quality issue in asset management systems.

**Required fix:** Add a guard in `_compute_lifecycle_fields` or in the CRUD function:
```python
if lifespan < 0:
    years_remaining = None  # future install date — not meaningful
    status = 'NORMAL'
```
Or clamp: `years_remaining = max(round(eff_useful - lifespan, 2), 0)`.

### A3: "Client-side interactive is the right model for this use case"
**CONDITIONALLY PASS.** The constraint is user-locked ("client-side interactive, load all, JS filter/sort"), so the Critic cannot contest it. However, I note: with 99% not_set, there is literally nothing to filter in v1. The client-side interactive model is appropriate for the *target state* (after data fill), but for the v1 state it adds complexity (Pinia store, cross-filter wiring, chart registration) for a payload that is 99% uninformative. The argument for client-side interactive would be stronger if the data-coverage launch gate (see META answer) were included.

### A4: "chartjs-chart-matrix is worth the install cost"
**FAIL — self-contradicting rationale.** The Planner writes in Section 9:
> "The 7 sites × 5 status bands = 35 cells is a small grid — **the grouped bar fallback is clearer at this scale**. The matrix is worth using only if site count grows above 15."

This is a direct self-contradiction. The Planner acknowledges the matrix is *not* the right choice for the current data scale, yet the plan still installs it. The rationale "install the plugin but use the fallback at runtime" is the worst of all worlds: 47KB added to the bundle, additional complexity in the component, and the fallback is what the user sees 100% of the time.

**Counter-proposal CP-1 (named, specific, costed):**
- **Drop the `chartjs-chart-matrix` install entirely.**
- Use `vue-chartjs` `Bar` chart (already in dependencies) with a grouped horizontal bar for the heatmap widget.
- Effort: remove 3 lines of plugin registration + 1 npm dep entry. Risk: zero — this is a removal, not an addition.
- The heatmap widget is explicitly acknowledged as suboptimal at this scale. Do not install a plugin you will never use.

### A5: "12-month near-EoL threshold is a defensible industry default"
**PASS with a caveat.** The industry research (Teqtivity: 12–18 months; Microsoft Intune: 18 months; ServiceNow: boolean flag only) is consistent enough to defend 12 months as a user choice. The Planner correctly notes the threshold is user-settable (R7). However, the threshold is **not surfaced in the UI** — it is only in the API response metadata. If the user cannot change it from the dashboard, it is not user-settable; it is hardcoded. The plan should state whether the threshold is a compile-time constant or a runtime UI control.

---

## 5. Specific Counter-Proposals

### CP-1: Drop `chartjs-chart-matrix` install entirely
**Problem:** A4 stress-test failure. The Planner's own analysis says the matrix is wrong at 7 sites. Installing it adds bundle size for a component that will never render.

**Counter-proposal:** Remove `"chartjs-chart-matrix": "^3.0.0"` from `package.json` additions. Use `vue-chartjs` `Bar` chart with grouped horizontal mode for the heatmap widget. This is already in the existing dependencies (vue-chartjs@5.2.0 + chart.js@4.4.0). No new install.

**Cost:** ~1 line removed from package.json, ~5 lines changed in the heatmap widget section. Risk: zero.

### CP-2: Add future-install-date guard to `_compute_lifecycle_fields`
**Problem:** A2 stress-test failure. Future-dated `installation_date` produces large positive `years_remaining` and `NORMAL` status — misleading.

**Counter-proposal:** Add a guard in the CRUD function (not in the helper, which is shared):
```python
lifespan, years_remaining, status = _compute_lifecycle_fields(...)
# Guard: future install dates produce meaningless negative lifespan
if lifespan is not None and lifespan < 0:
    years_remaining = None
    status = 'NORMAL'
```

**Cost:** 3 lines in the CRUD function. Risk: minimal — it only affects the 0 (zero) components that have future install dates.

### CP-3: Add a data-coverage launch gate to the plan
**Problem:** META question. The 99% data gap is treated as an acceptable UX state, not a quality gate.

**Counter-proposal:** Add a launch gate in the deployment section:
> "The dashboard must not be exposed to end users until `not_set / total < 0.5` (i.e., less than 50% of components show not_set). A data-fill task list is part of this project's deliverable: identify all asset types with `useful_life_years` set but `useful_life_inheritance_enabled = false`, and surface them in a prioritized admin list."

**Cost:** Documentation addition + one admin-facing task (no code). Risk: delays ship date — but prevents shipping a dashboard that users will reject as broken.

### CP-4: Explicitly name the fleet-growth ceiling for the no-pagination model
**Problem:** P-B silent principle. The plan locks "no pagination" based on the current 832-component snapshot.

**Counter-proposal:** Add a named constant or comment in the frontend store and API response schema:
```javascript
// Maximum fleet size for client-side interactive (no pagination): 2,000 components
// Beyond this, implement server-side pagination (GET /api/dashboard/asset-lifecycle?page=N&limit=50)
```

**Cost:** 1 comment line. Risk: none.

---

## 6. Counterfactual Deference Test (P16)

P16: Did the Planner adopt Architect feedback because it holds on its own logic, or because the Architect said so?

**P1 (CRUD over view-as-query-target):** Genuine adoption. The Planner's counterfactual ("if we kept the view, we'd justify removing all views everywhere") is sound and self-standing. The Architect's framing was the prompt, but the Planner's defense of the decision is principled and not merely deferential. **PASS.**

**P2 (model_lifecycles tenant scoping):** Genuine adoption. The Planner verified the nullable `tenant_id` pattern against the source code and applied the same filter to all four JOINs. Not deferential — verified independently. **PASS.**

**P3 (V3a/V3b split):** Genuine adoption. The split is clearly necessary (a misconfigured global query passes V3b but fails V3a). **PASS.**

**P4 (snake_case):** Deferential but correct. The Architect pointed at `dashboards.py:85-99` for convention. The Planner fixed it without independent verification of whether the rest of the API uses snake_case — but the convention is well-established in the codebase. **BORDERLINE** — the Planner should have verified against `asset_components.py` schema directly, not just accepted the Architect's citation.

**P5 (DROP VIEW IF EXISTS):** **OVER-CORRECTED.** The Architect said "use `DROP VIEW IF EXISTS + CREATE VIEW` instead of `CREATE OR REPLACE VIEW`." The Planner's response was to remove the view *entirely*. The Architect's point was about migration robustness, not "remove the view." The Planner's META answer (drop the view) was a logical extension but not a necessary consequence of P5. The view could still exist as a documentation artifact or for ad-hoc DB queries, even if the API doesn't use it. The Planner adopted a stronger-than-necessary version of P5 without explaining why the stronger version was warranted. **PARTIAL FAIL on counterfactual — the Planner overcorrected.**

**P6 (clean_float_values):** Genuine adoption. Applied at the endpoint layer as specified. **PASS.**

---

## 7. Round 1 Architect Coverage Assessment

The Architect correctly identified the highest-risk issue (tenant isolation via `current_setting`). The P1–P6 counter-proposals are all sound. The Architect's two silent concerns (4d JOIN strategy, 4e raw SQL divergence) are both valid and addressed.

**What the Architect missed:**
- The future-install-date edge case in `_compute_lifecycle_fields` (my A2 finding)
- The self-contradiction in the chartjs-chart-matrix rationale (my A4 finding)
- The data-coverage launch gate (my META answer)
- The fleet-growth ceiling (my P-B finding)

---

## 8. Verdict

**REQUEST_CHANGES** — the plan requires changes before it can be approved.

| Issue | Severity | Action Required |
|-------|----------|-----------------|
| CP-1: Drop chartjs-chart-matrix | MEDIUM | Remove from package.json additions; update heatmap widget section to use vue-chartjs Bar |
| CP-2: Future-install-date guard | MEDIUM | Add 3-line guard in CRUD function after `_compute_lifecycle_fields` call |
| CP-3: Data-coverage launch gate | HIGH | Add launch gate + data-fill task to deployment section |
| CP-4: Fleet-growth ceiling | LOW | Add comment naming the pagination trigger threshold |
| META: Data gap is a quality problem, not a UX problem | HIGH | Reframe the data gap treatment from "accept empty state" to "conditional launch gate" |

**If CP-1, CP-2, and CP-3 are addressed, I would approve.** CP-4 is optional. The plan is structurally sound; the changes are targeted and low-risk.

**Word count:** ~1,650 words.
