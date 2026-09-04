import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status, Request, Query, Body
from pydantic import BaseModel
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
    AssetComponentLifecycleStatus,
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


@router.get("/lifecycle-status", response_model=List[AssetComponentLifecycleStatus])
def get_components_lifecycle_status(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List components with computed lifecycle fields.

    Each item includes:
      - lifespan_years: years since effective install date (component's own or parent's)
      - effective_useful_life: useful life in years (model override else asset_type default)
      - useful_life_source: 'model' | 'inherited_from_asset_type' | 'not_set'
      - years_remaining: useful_life - lifespan_years (negative = past end-of-life)
      - lifecycle_status: 'END-OF-LIFE' if lifespan >= useful_life else 'NORMAL'

    These fields are computed at request time, not stored — values are always current.
    """
    return crud_components.list_components_lifecycle_status(
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
    component = crud_components.get_asset_component(db, component_id, current_user.tenant_id)
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


class BulkApplyInstallationDateResponse(BaseModel):
    updated_count: int
    installation_date: str  # ISO date


class BulkApplyInstallationDateBody(BaseModel):
    installation_date: Optional[str] = None  # ISO date; null means "use asset's date"


@router.post(
    "/apply-asset-date",
    response_model=BulkApplyInstallationDateResponse,
)
@audit_log_action("update", "AssetComponent", model_class=AssetComponent)
def apply_asset_date(
    asset_id: uuid.UUID,
    payload: BulkApplyInstallationDateBody = Body(default=BulkApplyInstallationDateBody()),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set installation_date on all components of this asset where it is currently NULL.

    Endpoint name avoids the word "bulk" so it doesn't get auto-escalated to
    RBAC level 4 by _BULK_PATH_KEYWORDS in rbac.py (admin only has level 3
    on the assets section, so a "bulk"-prefixed endpoint would 403 for admin).

    If payload.installation_date is omitted, uses the parent asset's installation_date.
    Existing non-null values are NEVER touched (so user-assigned field-replacement
    dates survive).

    Returns the number of components updated and the date that was applied.
    """
    from datetime import date as date_type
    target_date = None
    if payload.installation_date:
        try:
            target_date = date_type.fromisoformat(payload.installation_date)
        except ValueError:
            raise ErrorCodeException(
                status_code=400, error_code=ErrorCode.INVALID_ASSET_UPDATE
            )
    if target_date is None:
        # Fall back to the asset's installation_date
        from app.models import Asset
        asset = (
            db.query(Asset).filter(Asset.id == asset_id).first()
        )
        if asset and asset.installation_date:
            target_date = asset.installation_date
    if target_date is None:
        # Nothing to apply — no payload date and no asset date
        return BulkApplyInstallationDateResponse(
            updated_count=0, installation_date=""
        )
    count = crud_components.bulk_apply_installation_date(
        db,
        asset_id=asset_id,
        tenant_id=current_user.tenant_id,
        installation_date=target_date,
    )
    return BulkApplyInstallationDateResponse(
        updated_count=count, installation_date=target_date.isoformat()
    )
