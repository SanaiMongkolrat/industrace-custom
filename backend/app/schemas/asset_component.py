from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
import uuid


class AssetComponentBase(BaseModel):
    asset_id: uuid.UUID
    model_lifecycle_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, description="Number of units")
    installation_date: Optional[date] = Field(
        None,
        description="When this component was installed in the parent asset (overwritten on field replacement)",
    )
    notes: Optional[str] = Field(None, max_length=10000)

    model_config = ConfigDict(protected_namespaces=())


class AssetComponentCreate(AssetComponentBase):
    # asset_id is optional on create — the router sets it from the URL path
    # (/assets/{asset_id}/components). Making it optional here prevents
    # Pydantic VALIDATION_ERROR when the frontend omits it from the body.
    asset_id: Optional[uuid.UUID] = None
    tenant_id: Optional[uuid.UUID] = None


class AssetComponentUpdate(BaseModel):
    model_lifecycle_id: Optional[uuid.UUID] = None
    quantity: Optional[int] = Field(None, ge=1)
    installation_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=10000)


class AssetComponent(AssetComponentBase):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_lifecycle_manufacturer_name: Optional[str] = None
    model_lifecycle_model_name: Optional[str] = None
    model_lifecycle_asset_type_name: Optional[str] = None
    model_lifecycle_lifecycle_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
