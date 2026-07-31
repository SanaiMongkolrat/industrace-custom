import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status, Request, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, LifecycleStatus
from app.schemas.lifecycle_status import (
    LifecycleStatus as LifecycleStatusSchema,
    LifecycleStatusCreate,
    LifecycleStatusUpdate,
)
from app.services.auth import get_current_user
from app.services.rbac import require_section_access
from app.crud import lifecycle_statuses as crud_lifecycle_statuses

router = APIRouter(
    prefix="/lifecycle-statuses",
    tags=["lifecycle_statuses"],
    dependencies=[Depends(require_section_access("lifecycle_statuses"))],
)


@router.post("", response_model=LifecycleStatusSchema)
def create_lifecycle_status(
    status_in: LifecycleStatusCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud_lifecycle_statuses.create_lifecycle_status(
        db, status_in, tenant_id=current_user.tenant_id
    )


@router.get("", response_model=List[LifecycleStatusSchema])
def list_lifecycle_statuses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud_lifecycle_statuses.list_lifecycle_statuses(
        db, tenant_id=current_user.tenant_id, skip=skip, limit=limit
    )


@router.get("/{status_id}", response_model=LifecycleStatusSchema)
def get_lifecycle_status(
    status_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    status = crud_lifecycle_statuses.get_lifecycle_status(db, status_id)
    if not status:
        from app.errors.exceptions import ErrorCodeException
        from app.errors.error_codes import ErrorCode
        raise ErrorCodeException(status_code=404, error_code=ErrorCode.ASSET_STATUS_NOT_FOUND)
    return status


@router.put("/{status_id}", response_model=LifecycleStatusSchema)
def update_lifecycle_status(
    status_id: uuid.UUID,
    status_update: LifecycleStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    status = crud_lifecycle_statuses.update_lifecycle_status(db, status_id, status_update)
    if not status:
        from app.errors.exceptions import ErrorCodeException
        from app.errors.error_codes import ErrorCode
        raise ErrorCodeException(status_code=404, error_code=ErrorCode.ASSET_STATUS_NOT_FOUND)
    return status


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lifecycle_status(
    status_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud_lifecycle_statuses.delete_lifecycle_status(db, status_id)
    return None
