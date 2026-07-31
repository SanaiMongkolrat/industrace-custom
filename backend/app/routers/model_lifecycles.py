import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status, Request, Query, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd
import io

from app.errors.exceptions import ErrorCodeException
from app.errors.error_codes import ErrorCode
from app.services.audit_decorator import audit_log_action
from app.database import get_db
from app.models import User, ModelLifecycle, Asset
from sqlalchemy import or_
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


@router.get("/models-by-manufacturer", response_model=List[dict])
def list_models_by_manufacturer(
    manufacturer_id: Optional[uuid.UUID] = Query(None, description="Filter by manufacturer"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List distinct model names grouped by manufacturer for dropdown selection"""
    query = (
        db.query(ModelLifecycle.model_name, ModelLifecycle.manufacturer_id)
        .filter(
            or_(ModelLifecycle.tenant_id == current_user.tenant_id, ModelLifecycle.tenant_id.is_(None))
        )
        .distinct()
    )
    if manufacturer_id:
        query = query.filter(ModelLifecycle.manufacturer_id == manufacturer_id)
    results = query.all()
    # Also include models from assets that don't have lifecycle records
    from sqlalchemy import literal_column
    asset_models = (
        db.query(Asset.model, Asset.manufacturer_id)
        .filter(
            Asset.tenant_id == current_user.tenant_id,
            Asset.deleted_at == None,
            Asset.model != None,
            Asset.model != '',
        )
        .distinct()
    )
    if manufacturer_id:
        asset_models = asset_models.filter(Asset.manufacturer_id == manufacturer_id)
    asset_results = asset_models.all()
    
    seen = set()
    output = []
    for model_name, mfr_id in results:
        key = (model_name, str(mfr_id) if mfr_id else '')
        if key not in seen:
            seen.add(key)
            output.append({"model_name": model_name, "manufacturer_id": str(mfr_id) if mfr_id else None})
    for model_name, mfr_id in asset_results:
        key = (model_name, str(mfr_id) if mfr_id else '')
        if key not in seen:
            seen.add(key)
            output.append({"model_name": model_name, "manufacturer_id": str(mfr_id) if mfr_id else None})
    return sorted(output, key=lambda x: x["model_name"])


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


@router.post("/import-csv")
async def import_model_lifecycles_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import model lifecycles from CSV file"""
    from app.models import Manufacturer, AssetType
    
    if not file.filename.lower().endswith('.csv'):
        raise ErrorCodeException(status_code=400, error_code=ErrorCode.INVALID_INPUT, detail="Only CSV files are supported")
    
    content = await file.read()
    df = pd.read_csv(io.StringIO(content.decode('utf-8')), dtype=str)
    df = df.where(pd.notnull(df), None)
    
    created, errors = [], []
    for idx, row in df.iterrows():
        try:
            manufacturer_name = row.get("manufacturer")
            model_name = row.get("model_name")
            lifecycle_status = row.get("lifecycle_status", "in_support")
            useful_life_years = row.get("useful_life_years")
            asset_type_name = row.get("asset_type")
            
            if not manufacturer_name or not model_name:
                errors.append({"row": int(idx) + 2, "error": "manufacturer and model_name are required"})
                continue
            
            # Find or create manufacturer
            manufacturer = db.query(Manufacturer).filter(
                Manufacturer.name.ilike(manufacturer_name.strip()),
                (Manufacturer.tenant_id == current_user.tenant_id) | (Manufacturer.tenant_id.is_(None))
            ).first()
            if not manufacturer:
                manufacturer = Manufacturer(
                    tenant_id=current_user.tenant_id,
                    name=manufacturer_name.strip()
                )
                db.add(manufacturer)
                db.flush()
            
            # Find asset type if provided
            asset_type_id = None
            if asset_type_name:
                asset_type = db.query(AssetType).filter(
                    AssetType.name.ilike(asset_type_name.strip()),
                    (AssetType.tenant_id == current_user.tenant_id) | (AssetType.tenant_id.is_(None))
                ).first()
                if asset_type:
                    asset_type_id = asset_type.id
            
            # Parse useful_life_years
            useful_life = None
            if useful_life_years:
                try:
                    useful_life = int(float(useful_life_years))
                except (ValueError, TypeError):
                    pass
            
            lifecycle = ModelLifecycle(
                tenant_id=current_user.tenant_id,
                manufacturer_id=manufacturer.id,
                model_name=model_name.strip(),
                lifecycle_status=lifecycle_status,
                useful_life_years=useful_life,
                asset_type_id=asset_type_id,
            )
            db.add(lifecycle)
            db.flush()
            created.append({"row": int(idx) + 2, "model_name": model_name})
        except Exception as e:
            db.rollback()
            errors.append({"row": int(idx) + 2, "error": str(e)})
            continue
    
    db.commit()
    return {"created": len(created), "errors": errors}
