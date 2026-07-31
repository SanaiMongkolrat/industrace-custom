import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status, Request, Query
from sqlalchemy.orm import Session

from app.errors.exceptions import ErrorCodeException
from app.errors.error_codes import ErrorCode
from app.services.audit_decorator import audit_log_action
from app.database import get_db
from app.models import User, AssetComponent
from app.schemas.asset_component import (
    AssetComponent as AssetComponentSchema,
    AssetComponentCreate,
    AssetComponentUpdate,
)
from app.services.auth import get_current_user
from app.services.rbac import require_section_access
from app.crud import asset_components as crud_components

router = APIRouter(
    prefix="/assets/{asset_id}/components",
    tags=["asset_components"],
    dependencies=[Depends(require_section_access("assets"))],
)


@router.get("", response_model=List[AssetComponentSchema])
def list_components(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all components for an asset"""
    return crud_components.list_asset_components(
        db, asset_id=asset_id, tenant_id=current_user.tenant_id
    )


@router.get("/{component_id}", response_model=AssetComponentSchema)
def get_component(
    asset_id: uuid.UUID,
    component_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single component entry"""
    component = crud_components.get_asset_component(db, component_id)
    if not component:
        raise ErrorCodeException(
            status_code=404, error_code=ErrorCode.ASSET_COMPONENT_NOT_FOUND
        )
    return component


@router.post("", response_model=AssetComponentSchema, status_code=status.HTTP_201_CREATED)
@audit_log_action("create", "AssetComponent", model_class=AssetComponent)
def create_component(
    asset_id: uuid.UUID,
    component_in: AssetComponentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a component to an asset"""
    # Ensure the asset_id in the path matches the body
    component_in.asset_id = asset_id
    return crud_components.create_asset_component(
        db, component_in, tenant_id=current_user.tenant_id
    )


@router.put("/{component_id}", response_model=AssetComponentSchema)
@audit_log_action("update", "AssetComponent", model_class=AssetComponent)
def update_component(
    asset_id: uuid.UUID,
    component_id: uuid.UUID,
    component_update: AssetComponentUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a component entry"""
    component = crud_components.update_asset_component(db, component_id, component_update)
    if not component:
        raise ErrorCodeException(
            status_code=404, error_code=ErrorCode.ASSET_COMPONENT_NOT_FOUND
        )
    return component


@router.delete("/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log_action("delete", "AssetComponent", model_class=AssetComponent)
def delete_component(
    asset_id: uuid.UUID,
    component_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a component from an asset"""
    if not crud_components.delete_asset_component(db, component_id):
        raise ErrorCodeException(
            status_code=404, error_code=ErrorCode.ASSET_COMPONENT_NOT_FOUND
        )
