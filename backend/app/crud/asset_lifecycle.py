"""CRUD for the Asset Lifecycle Monitoring Dashboard.

Returns all components for a given tenant with computed lifecycle fields
(years_remaining, lifespan_years, lifecycle_status) and joined context
(asset, site, area, manufacturer, model, asset_type).

Pattern reference: backend/app/crud/asset_components.py:97-136 (list_asset_components)
Tenant scoping: backend/app/routers/dashboards.py:73-83 (Asset.tenant_id == current_user.tenant_id)
Computation reuse: backend/app/crud/asset_components.py:37-60 (_annotate_with_lifecycle)
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.models import AssetComponent, ModelLifecycle, Manufacturer, Asset, Site, Area, AssetType
from app.crud.asset_components import _annotate_with_lifecycle


def list_asset_lifecycle_status(
    db: Session,
    tenant_id: uuid.UUID,
) -> dict:
    """Return all components for a tenant with computed lifecycle fields.

    Single query with eager loading (joinedload) to avoid N+1.
    Tenant-scoped at both AssetComponent and ModelLifecycle layers
    (matches existing codebase pattern for nullable tenant_id columns).

    Returns:
        dict with shape:
        {
            "components": [<row dict>, ...],
            "summary": {
                "total": int,
                "with_data": int,
                "not_set": int,
                "near_eol": int,        # 0 < years_remaining <= 1.0
                "end_of_life": int,
            },
            "meta": {
                "computed_at": ISO timestamp,
                "near_eol_threshold_months": 12,
            }
        }
    """
    rows = (
        db.query(AssetComponent)
        .options(
            joinedload(AssetComponent.asset).joinedload(Asset.site),
            joinedload(AssetComponent.asset).joinedload(Asset.area),
            joinedload(AssetComponent.asset).joinedload(Asset.asset_type),
            joinedload(AssetComponent.model_lifecycle).joinedload(ModelLifecycle.manufacturer),
        )
        .join(Asset, Asset.id == AssetComponent.asset_id)
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

    components = []
    for c in rows:
        asset = c.asset
        ml = c.model_lifecycle
        mfr = ml.manufacturer if ml else None
        at = asset.asset_type if asset else None

        # Build the component dict (mirror _annotate_with_lifecycle's input shape)
        d = {
            "id": c.id,
            "asset_id": c.asset_id,
            "model_lifecycle_id": c.model_lifecycle_id,
            "quantity": c.quantity,
            "installation_date": c.installation_date,
            "notes": c.notes,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }

        # Attach the joined fields the existing helper expects via setattr
        # on a wrapper object — simplest path is to call the helper with
        # a dict copy and then override the join field names.
        ml_useful = ml.useful_life_years if ml else None
        at_useful = at.useful_life_years if at else None
        at_inheritance = at.useful_life_inheritance_enabled if at else None

        _annotate_with_lifecycle(d, ml_useful, at_useful, at_inheritance)

        # Architect R2 N2 fix: future-install-date guard
        # If installation_date is in the future, lifespan is negative and
        # years_remaining is misleadingly large positive. Set to None.
        if d.get("lifespan_years") is not None and d["lifespan_years"] < 0:
            d["years_remaining"] = None
            d["lifecycle_status"] = "NORMAL"

        # Build the dashboard-specific response shape
        components.append({
            "component_id": str(d["id"]),
            "asset_id": str(d["asset_id"]),
            "asset_name": asset.name if asset else None,
            "asset_tag": asset.tag if asset else None,
            "plant_name": asset.site.name if asset and asset.site else None,
            "area_name": asset.area.name if asset and asset.area else None,
            "model_lifecycle_id": str(d["model_lifecycle_id"]) if d["model_lifecycle_id"] else None,
            "model_name": ml.model_name if ml else None,
            "manufacturer": mfr.name if mfr else None,
            "asset_type_name": at.name if at else None,
            "effective_install_date": (
                d["effective_install_date"].isoformat()
                if d.get("effective_install_date") is not None
                else None
            ),
            "lifespan_years": d.get("lifespan_years"),
            "effective_useful_life": d.get("effective_useful_life"),
            "years_remaining": d.get("years_remaining"),
            "useful_life_source": d.get("useful_life_source"),
            "lifecycle_status": d.get("lifecycle_status"),
            "model_eol_status": ml.lifecycle_status if ml else None,
            "model_useful_life_years": ml_useful,
            "asset_type_useful_life_years": at_useful,
            "useful_life_inheritance_enabled": at_inheritance,
        })

    # Summary
    total = len(components)
    with_data = sum(1 for r in components if r["useful_life_source"] != "not_set")
    near_eol = sum(
        1 for r in components
        if r["years_remaining"] is not None and 0 < r["years_remaining"] <= 1.0
    )
    end_of_life = sum(1 for r in components if r["lifecycle_status"] == "END-OF-LIFE")

    return {
        "components": components,
        "summary": {
            "total": total,
            "with_data": with_data,
            "not_set": total - with_data,
            "near_eol": near_eol,
            "end_of_life": end_of_life,
        },
        "meta": {
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "near_eol_threshold_months": 12,
        },
    }
