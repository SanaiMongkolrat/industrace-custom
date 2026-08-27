from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, or_
from app.models import ModelLifecycle, Manufacturer, Asset, AssetType
from app.schemas.model_lifecycle import ModelLifecycleCreate, ModelLifecycleUpdate
import uuid
from typing import List, Optional


def get_model_lifecycle(db: Session, lifecycle_id: uuid.UUID) -> Optional[dict]:
    """Retrieve a model lifecycle record by ID"""
    repl_mfr = aliased(Manufacturer)
    result = (
        db.query(
            ModelLifecycle,
            Manufacturer.name.label("manufacturer_name"),
            repl_mfr.name.label("replacement_manufacturer_name"),
            AssetType.name.label("asset_type_name"),
        )
        .outerjoin(Manufacturer, Manufacturer.id == ModelLifecycle.manufacturer_id)
        .outerjoin(
            repl_mfr,
            repl_mfr.id == ModelLifecycle.replacement_manufacturer_id,
        )
        .outerjoin(AssetType, AssetType.id == ModelLifecycle.asset_type_id)
        .filter(ModelLifecycle.id == lifecycle_id)
        .first()
    )
    if not result:
        return None
    lifecycle, mfr_name, repl_mfr_name, at_name = result
    lifecycle_dict = lifecycle.__dict__.copy()
    lifecycle_dict["manufacturer_name"] = mfr_name
    lifecycle_dict["replacement_manufacturer_name"] = repl_mfr_name
    lifecycle_dict["asset_type_name"] = at_name
    lifecycle_dict["asset_count"] = (
        db.query(func.count(Asset.id))
        .filter(Asset.model == lifecycle.model_name)
        .scalar()
    )
    return lifecycle_dict


def list_model_lifecycles(
    db: Session,
    tenant_id: Optional[uuid.UUID] = None,
    manufacturer_id: Optional[uuid.UUID] = None,
    lifecycle_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[dict]:
    """List model lifecycle records with optional filters"""
    query = (
        db.query(
            ModelLifecycle,
            Manufacturer.name.label("manufacturer_name"),
            AssetType.name.label("asset_type_name"),
        )
        .outerjoin(Manufacturer, Manufacturer.id == ModelLifecycle.manufacturer_id)
        .outerjoin(AssetType, AssetType.id == ModelLifecycle.asset_type_id)
    )
    if tenant_id:
        query = query.filter(
            or_(ModelLifecycle.tenant_id == tenant_id, ModelLifecycle.tenant_id.is_(None))
        )
    if manufacturer_id:
        query = query.filter(ModelLifecycle.manufacturer_id == manufacturer_id)
    if lifecycle_status:
        query = query.filter(ModelLifecycle.lifecycle_status == lifecycle_status)
    query = query.order_by(Manufacturer.name, ModelLifecycle.model_name)
    results = query.offset(skip).limit(limit).all()
    output = []
    for row in results:
        lifecycle, mfr_name, at_name = row
        lifecycle_dict = lifecycle.__dict__.copy()
        lifecycle_dict["manufacturer_name"] = mfr_name
        lifecycle_dict["asset_type_name"] = at_name
        lifecycle_dict["asset_count"] = (
            db.query(func.count(Asset.id))
            .filter(Asset.model == lifecycle.model_name)
            .scalar()
        )
        output.append(lifecycle_dict)
    return output


def create_model_lifecycle(
    db: Session, lifecycle_in: ModelLifecycleCreate, tenant_id: Optional[uuid.UUID] = None
) -> ModelLifecycle:
    """Create a new model lifecycle record"""
    db_lifecycle = ModelLifecycle(
        tenant_id=tenant_id, **lifecycle_in.model_dump(exclude_unset=True, exclude={"tenant_id"})
    )
    db.add(db_lifecycle)
    db.commit()
    db.refresh(db_lifecycle)
    return db_lifecycle


def update_model_lifecycle(
    db: Session, lifecycle_id: uuid.UUID, lifecycle_update: ModelLifecycleUpdate
) -> Optional[ModelLifecycle]:
    """Update an existing model lifecycle record"""
    db_lifecycle = (
        db.query(ModelLifecycle).filter(ModelLifecycle.id == lifecycle_id).first()
    )
    if db_lifecycle:
        for key, value in lifecycle_update.model_dump(exclude_unset=True).items():
            setattr(db_lifecycle, key, value)
        db.commit()
        db.refresh(db_lifecycle)
    return db_lifecycle


def delete_model_lifecycle(db: Session, lifecycle_id: uuid.UUID) -> bool:
    """Delete a model lifecycle record"""
    db_lifecycle = (
        db.query(ModelLifecycle).filter(ModelLifecycle.id == lifecycle_id).first()
    )
    if db_lifecycle:
        db.delete(db_lifecycle)
        db.commit()
        return True
    return False


def get_lifecycle_stats(
    db: Session, tenant_id: Optional[uuid.UUID] = None
) -> dict:
    """Get lifecycle statistics grouped by status"""
    query = db.query(
        ModelLifecycle.lifecycle_status,
        func.count(ModelLifecycle.id).label("count"),
    )
    if tenant_id:
        query = query.filter(
            or_(ModelLifecycle.tenant_id == tenant_id, ModelLifecycle.tenant_id.is_(None))
        )
    query = query.group_by(ModelLifecycle.lifecycle_status)
    results = query.all()
    stats = {row.lifecycle_status: row.count for row in results}
    stats["total"] = sum(stats.values())
    return stats
