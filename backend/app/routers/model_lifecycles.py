import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status, Request, Query
from sqlalchemy.orm import Session

from app.errors.exceptions import ErrorCodeException
from app.errors.error_codes import ErrorCode
from app.services.audit_decorator import audit_log_action
from app.database import get_db
from app.models import User, ModelLifecycle
from app.schemas.model_lifecycle import (
    ModelLifecycle as ModelLifecycleSchema,
    ModelLifecycleCreate,
    ModelLifecycleUpdate,
)
from app.services.auth import get_current_user
from app.services.rbac import require_section_access
from app.crud import model_lifecycles as crud_model_lifecycles


router = APIRouter(
    prefix="/model-lifecycles",
    tags=["model_lifecycles"],
    dependencies=[Depends(require_section_access("model_lifecycles"))],
)


@router.post("", response_model=ModelLifecycleSchema)
@audit_log_action("create", "ModelLifecycle", model_class=ModelLifecycle)
def create_model_lifecycle(
    lifecycle_in: ModelLifecycleCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud_model_lifecycles.create_model_lifecycle(
        db, lifecycle_in, tenant_id=current_user.tenant_id
    )


@router.get("", response_model=List[ModelLifecycleSchema])
def list_model_lifecycles(
    manufacturer_id: Optional[uuid.UUID] = Query(None, description="Filter by manufacturer"),
    lifecycle_status: Optional[str] = Query(None, description="Filter by lifecycle status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud_model_lifecycles.list_model_lifecycles(
        db,
        tenant_id=current_user.tenant_id,
        manufacturer_id=manufacturer_id,
        lifecycle_status=lifecycle_status,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=dict)
def get_lifecycle_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud_model_lifecycles.get_lifecycle_stats(db, tenant_id=current_user.tenant_id)


@router.get("/{lifecycle_id}", response_model=ModelLifecycleSchema)
def get_model_lifecycle(
    lifecycle_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lifecycle = crud_model_lifecycles.get_model_lifecycle(db, lifecycle_id)
    if not lifecycle:
        raise ErrorCodeException(
            status_code=404, error_code=ErrorCode.MODEL_LIFECYCLE_NOT_FOUND
        )
    return lifecycle


@router.put("/{lifecycle_id}", response_model=ModelLifecycleSchema)
@audit_log_action("update", "ModelLifecycle", model_class=ModelLifecycle)
def update_model_lifecycle(
    lifecycle_id: uuid.UUID,
    lifecycle_update: ModelLifecycleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lifecycle = crud_model_lifecycles.get_model_lifecycle(db, lifecycle_id)
    if not lifecycle:
        raise ErrorCodeException(
            status_code=404, error_code=ErrorCode.MODEL_LIFECYCLE_NOT_FOUND
        )
    return crud_model_lifecycles.update_model_lifecycle(db, lifecycle_id, lifecycle_update)


@router.delete("/{lifecycle_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log_action("delete", "ModelLifecycle", model_class=ModelLifecycle)
def delete_model_lifecycle(
    lifecycle_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lifecycle = crud_model_lifecycles.get_model_lifecycle(db, lifecycle_id)
    if not lifecycle:
        raise ErrorCodeException(
            status_code=404, error_code=ErrorCode.MODEL_LIFECYCLE_NOT_FOUND
        )
    crud_model_lifecycles.delete_model_lifecycle(db, lifecycle_id)
    return None
