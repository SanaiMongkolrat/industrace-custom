from sqlalchemy.orm import Session
from app.models import LifecycleStatus
from app.schemas.lifecycle_status import LifecycleStatusCreate, LifecycleStatusUpdate
import uuid
from typing import List, Optional


def get_lifecycle_status(db: Session, status_id: uuid.UUID) -> Optional[LifecycleStatus]:
    return db.query(LifecycleStatus).filter(LifecycleStatus.id == status_id).first()


def list_lifecycle_statuses(
    db: Session, tenant_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100
) -> List[LifecycleStatus]:
    query = db.query(LifecycleStatus)
    if tenant_id:
        query = query.filter(
            (LifecycleStatus.tenant_id == tenant_id) | (LifecycleStatus.tenant_id.is_(None))
        )
    return query.order_by(LifecycleStatus.order).offset(skip).limit(limit).all()


def create_lifecycle_status(
    db: Session, status_in: LifecycleStatusCreate, tenant_id: Optional[uuid.UUID] = None
) -> LifecycleStatus:
    db_obj = LifecycleStatus(tenant_id=tenant_id, **status_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_lifecycle_status(
    db: Session, status_id: uuid.UUID, status_update: LifecycleStatusUpdate
) -> Optional[LifecycleStatus]:
    db_obj = get_lifecycle_status(db, status_id)
    if db_obj:
        for key, value in status_update.model_dump(exclude_unset=True).items():
            setattr(db_obj, key, value)
        db.commit()
        db.refresh(db_obj)
    return db_obj


def delete_lifecycle_status(db: Session, status_id: uuid.UUID) -> bool:
    db_obj = get_lifecycle_status(db, status_id)
    if db_obj:
        db.delete(db_obj)
        db.commit()
        return True
    return False
