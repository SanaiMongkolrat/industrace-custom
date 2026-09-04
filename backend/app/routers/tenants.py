# routers/tenants.py

from typing import List
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.models import User, Tenant
from app.services.audit_decorator import audit_log_action
from app.services.auth import get_current_user
from app.crud import tenants as crud_tenants
from app.services.rbac import require_section_access, check_permission

router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
    dependencies=[Depends(require_section_access("roles"))],
)


@router.post("", response_model=schemas.Tenant)
@audit_log_action("create", "Tenant", model_class=Tenant)
def create_tenant(
    tenant: schemas.Tenant,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only superadmins (tenant-level 4 on roles) can create tenants
    if not check_permission(current_user, "roles", 4):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can create tenants"
        )
    return crud_tenants.create_tenant(db, tenant)


@router.get("", response_model=List[schemas.Tenant])
@audit_log_action("list", "Tenant", model_class=Tenant)
def list_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only superadmins can list ALL tenants; regular users see only their own tenant
    if check_permission(current_user, "roles", 4):
        return crud_tenants.get_tenants(db, skip=skip, limit=limit)
    # Non-superadmins: return only their own tenant
    return [current_user.tenant] if current_user.tenant else []
