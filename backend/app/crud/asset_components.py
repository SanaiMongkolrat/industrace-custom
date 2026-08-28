from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models import AssetComponent, ModelLifecycle, Manufacturer, AssetType
from app.schemas.asset_component import AssetComponentCreate, AssetComponentUpdate
import uuid
from typing import List, Optional


def get_asset_component(db: Session, component_id: uuid.UUID) -> Optional[dict]:
    """Retrieve a single asset component by ID"""
    result = (
        db.query(
            AssetComponent,
            Manufacturer.name.label("model_lifecycle_manufacturer_name"),
            ModelLifecycle.model_name.label("model_lifecycle_model_name"),
            AssetType.name.label("model_lifecycle_asset_type_name"),
            ModelLifecycle.lifecycle_status.label("model_lifecycle_lifecycle_status"),
        )
        .join(ModelLifecycle, ModelLifecycle.id == AssetComponent.model_lifecycle_id)
        .outerjoin(Manufacturer, Manufacturer.id == ModelLifecycle.manufacturer_id)
        .outerjoin(AssetType, AssetType.id == ModelLifecycle.asset_type_id)
        .filter(AssetComponent.id == component_id)
        .first()
    )
    if not result:
        return None
    comp, mfr_name, model_name, at_name, ls = result
    d = comp.__dict__.copy()
    d["model_lifecycle_manufacturer_name"] = mfr_name
    d["model_lifecycle_model_name"] = model_name
    d["model_lifecycle_asset_type_name"] = at_name
    d["model_lifecycle_lifecycle_status"] = ls
    return d


def list_asset_components(
    db: Session,
    asset_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    """List all components for a given asset"""
    query = (
        db.query(
            AssetComponent,
            Manufacturer.name.label("model_lifecycle_manufacturer_name"),
            ModelLifecycle.model_name.label("model_lifecycle_model_name"),
            AssetType.name.label("model_lifecycle_asset_type_name"),
            ModelLifecycle.lifecycle_status.label("model_lifecycle_lifecycle_status"),
        )
        .join(ModelLifecycle, ModelLifecycle.id == AssetComponent.model_lifecycle_id)
        .outerjoin(Manufacturer, Manufacturer.id == ModelLifecycle.manufacturer_id)
        .outerjoin(AssetType, AssetType.id == ModelLifecycle.asset_type_id)
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
        comp, mfr_name, model_name, at_name, ls = row
        d = comp.__dict__.copy()
        d["model_lifecycle_manufacturer_name"] = mfr_name
        d["model_lifecycle_model_name"] = model_name
        d["model_lifecycle_asset_type_name"] = at_name
        d["model_lifecycle_lifecycle_status"] = ls
        output.append(d)
    return output


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
    db: Session, component_id: uuid.UUID, component_update: AssetComponentUpdate
) -> Optional[AssetComponent]:
    """Update an asset component entry"""
    db_component = (
        db.query(AssetComponent).filter(AssetComponent.id == component_id).first()
    )
    if db_component:
        for key, value in component_update.model_dump(exclude_unset=True).items():
            setattr(db_component, key, value)
        db.commit()
        db.refresh(db_component)
    return db_component


def delete_asset_component(db: Session, component_id: uuid.UUID) -> bool:
    """Remove a component from an asset"""
    db_component = (
        db.query(AssetComponent).filter(AssetComponent.id == component_id).first()
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
