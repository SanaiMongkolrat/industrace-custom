from sqlalchemy.orm import Session
from sqlalchemy import func, or_, case
from app.models import AssetComponent, ModelLifecycle, Manufacturer, AssetType, Asset, Location
from app.schemas.asset_component import AssetComponentCreate, AssetComponentUpdate
import uuid
from datetime import date
from typing import List, Optional


# ---------- Lifecycle computation helpers ----------

def _compute_lifecycle_fields(install_date, useful_life_override, useful_life_inherited):
    """Compute lifespan_years, years_remaining, and lifecycle_status."""
    if install_date is None:
        return None, None, 'NORMAL'
    # Years since install (fractional: years + months/12)
    today = date.today()
    years_delta = today.year - install_date.year
    months_delta = today.month - install_date.month
    if today.day < install_date.day:
        months_delta -= 1
    if months_delta < 0:
        years_delta -= 1
        months_delta += 12
    lifespan = round(years_delta + months_delta / 12.0, 2)

    # Determine effective useful life
    eff_useful = useful_life_override if useful_life_override is not None else useful_life_inherited
    if eff_useful is None:
        return lifespan, None, 'NORMAL'

    years_remaining = round(eff_useful - lifespan, 2)
    status = 'END-OF-LIFE' if lifespan >= eff_useful else 'NORMAL'
    return lifespan, years_remaining, status


def _annotate_with_lifecycle(component_dict, ml_useful_life, at_useful_life, at_inheritance_enabled):
    """Mutate a component dict in place to add lifecycle computed fields."""
    install_date = component_dict.get('installation_date')
    effective_install = install_date

    eff_useful = None
    source = 'not_set'
    if ml_useful_life is not None:
        eff_useful = ml_useful_life
        source = 'model'
    elif at_useful_life is not None and at_inheritance_enabled:
        eff_useful = at_useful_life
        source = 'inherited_from_asset_type'

    lifespan, years_remaining, status = _compute_lifecycle_fields(
        install_date, ml_useful_life, at_useful_life if at_inheritance_enabled else None
    )
    component_dict['effective_install_date'] = effective_install
    component_dict['lifespan_years'] = lifespan
    component_dict['effective_useful_life'] = eff_useful
    component_dict['useful_life_source'] = source
    component_dict['years_remaining'] = years_remaining
    component_dict['lifecycle_status'] = status
    return component_dict


# ---------- CRUD functions ----------

def get_asset_component(db: Session, component_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[dict]:
    """Retrieve a single asset component by ID, with lifecycle fields populated. Tenant-scoped."""
    result = (
        db.query(
            AssetComponent,
            Manufacturer.name.label("model_lifecycle_manufacturer_name"),
            ModelLifecycle.model_name.label("model_lifecycle_model_name"),
            ModelLifecycle.useful_life_years.label("ml_useful_life"),
            AssetType.name.label("model_lifecycle_asset_type_name"),
            AssetType.useful_life_years.label("at_useful_life"),
            AssetType.useful_life_inheritance_enabled.label("at_inheritance"),
            ModelLifecycle.lifecycle_status.label("model_lifecycle_lifecycle_status"),
            Location.name.label("location_name"),
            Location.code.label("location_code"),
        )
        .join(ModelLifecycle, ModelLifecycle.id == AssetComponent.model_lifecycle_id)
        .outerjoin(Manufacturer, Manufacturer.id == ModelLifecycle.manufacturer_id)
        .outerjoin(AssetType, AssetType.id == ModelLifecycle.asset_type_id)
        .outerjoin(Location, Location.id == AssetComponent.location_id)
        .filter(AssetComponent.id == component_id, AssetComponent.tenant_id == tenant_id)
        .first()
    )
    if not result:
        return None
    (comp, mfr_name, model_name, ml_useful, at_name, at_useful, at_inheritance, ls, loc_name, loc_code) = result
    d = comp.__dict__.copy()
    d.pop('_sa_instance_state', None)
    d["model_lifecycle_manufacturer_name"] = mfr_name
    d["model_lifecycle_model_name"] = model_name
    d["model_lifecycle_asset_type_name"] = at_name
    d["model_lifecycle_lifecycle_status"] = ls
    d["location_name"] = loc_name
    d["location_code"] = loc_code
    _annotate_with_lifecycle(d, ml_useful, at_useful, at_inheritance)
    return d


def list_asset_components(
    db: Session,
    asset_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    """List all components for a given asset, with lifecycle fields populated."""
    query = (
        db.query(
            AssetComponent,
            Manufacturer.name.label("model_lifecycle_manufacturer_name"),
            ModelLifecycle.model_name.label("model_lifecycle_model_name"),
            ModelLifecycle.useful_life_years.label("ml_useful_life"),
            AssetType.name.label("model_lifecycle_asset_type_name"),
            AssetType.useful_life_years.label("at_useful_life"),
            AssetType.useful_life_inheritance_enabled.label("at_inheritance"),
            ModelLifecycle.lifecycle_status.label("model_lifecycle_lifecycle_status"),
            Location.name.label("location_name"),
            Location.code.label("location_code"),
        )
        .join(ModelLifecycle, ModelLifecycle.id == AssetComponent.model_lifecycle_id)
        .outerjoin(Manufacturer, Manufacturer.id == ModelLifecycle.manufacturer_id)
        .outerjoin(AssetType, AssetType.id == ModelLifecycle.asset_type_id)
        .outerjoin(Location, Location.id == AssetComponent.location_id)
        .filter(AssetComponent.asset_id == asset_id)
    )
    if tenant_id:
        query = query.filter(
            or_(AssetComponent.tenant_id == tenant_id, AssetComponent.tenant_id.is_(None))
        )
    query = query.order_by(Manufacturer.name, ModelLifecycle.model_name)
    results = query.all()
    output = []
    for row in results:
        (comp, mfr_name, model_name, ml_useful, at_name, at_useful, at_inheritance, ls, loc_name, loc_code) = row
        d = comp.__dict__.copy()
        d.pop('_sa_instance_state', None)
        d["model_lifecycle_manufacturer_name"] = mfr_name
        d["model_lifecycle_model_name"] = model_name
        d["model_lifecycle_asset_type_name"] = at_name
        d["model_lifecycle_lifecycle_status"] = ls
        d["location_name"] = loc_name
        d["location_code"] = loc_code
        _annotate_with_lifecycle(d, ml_useful, at_useful, at_inheritance)
        output.append(d)
    return output


def list_components_lifecycle_status(
    db: Session,
    asset_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    """Alias of list_asset_components that ensures lifecycle fields are populated.

    Used by GET /assets/{id}/components/lifecycle-status endpoint.
    """
    return list_asset_components(db, asset_id, tenant_id)


def create_asset_component(
    db: Session, component_in: AssetComponentCreate, tenant_id: Optional[uuid.UUID] = None
) -> AssetComponent:
    """Add a component to an asset"""
    db_component = AssetComponent(
        tenant_id=tenant_id, **component_in.model_dump(exclude_unset=True)
    )
    db.add(db_component)
    db.commit()
    db.refresh(db_component)
    return db_component


def update_asset_component(
    db: Session, component_id: uuid.UUID, component_update: AssetComponentUpdate, tenant_id: uuid.UUID
) -> Optional[AssetComponent]:
    """Update an asset component entry. Tenant-scoped to prevent cross-tenant modification."""
    db_component = (
        db.query(AssetComponent)
        .filter(AssetComponent.id == component_id, AssetComponent.tenant_id == tenant_id)
        .first()
    )
    if db_component:
        for key, value in component_update.model_dump(exclude_unset=True).items():
            setattr(db_component, key, value)
        db.commit()
        db.refresh(db_component)
    return db_component


def delete_asset_component(db: Session, component_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
    """Remove a component from an asset. Tenant-scoped to prevent cross-tenant deletion."""
    db_component = (
        db.query(AssetComponent)
        .filter(AssetComponent.id == component_id, AssetComponent.tenant_id == tenant_id)
        .first()
    )
    if db_component:
        db.delete(db_component)
        db.commit()
        return True
    return False


def bulk_apply_installation_date(
    db: Session,
    asset_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
    installation_date,
) -> int:
    """Set installation_date on all components of the asset where it is NULL.

    Used when user clicks "Pull asset date to all empty". Existing non-null
    values are NEVER touched — only empty slots are filled.

    Returns the number of components updated.
    """
    if installation_date is None:
        return 0
    query = (
        db.query(AssetComponent)
        .filter(AssetComponent.asset_id == asset_id)
        .filter(AssetComponent.installation_date.is_(None))
    )
    if tenant_id:
        query = query.filter(
            or_(AssetComponent.tenant_id == tenant_id, AssetComponent.tenant_id.is_(None))
        )
    rows = query.all()
    for row in rows:
        row.installation_date = installation_date
    db.commit()
    return len(rows)
