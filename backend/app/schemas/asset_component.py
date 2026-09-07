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
    location_id: Optional[uuid.UUID] = Field(
        None,
        description="FK to locations.id — the cabinet/location where this component is physically placed",
    )

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

    # Lifecycle computed fields (added 2026-09-04, populated by backend)
    lifespan_years: Optional[float] = Field(
        None,
        description="Years since effective_install_date (component's own date, or parent's date as fallback)",
    )
    effective_install_date: Optional[date] = Field(
        None,
        description="Component's installation_date if set, else parent's",
    )
    effective_useful_life: Optional[int] = Field(
        None,
        description="Useful life in years: model's value if set, else inherited from asset_type",
    )
    useful_life_source: Optional[str] = Field(
        None,
        description="Where the useful life came from: 'model', 'inherited_from_asset_type', or 'not_set'",
    )
    years_remaining: Optional[float] = Field(
        None,
        description="useful_life - lifespan_years (negative when past end-of-life)",
    )
    lifecycle_status: Optional[str] = Field(
        None,
        description="END-OF-LIFE if lifespan >= useful_life, else NORMAL",
    )

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class AssetComponentLifecycleStatus(BaseModel):
    """Standalone response schema for the lifecycle-status endpoint."""
    id: uuid.UUID
    asset_id: uuid.UUID
    model_lifecycle_id: uuid.UUID
    quantity: int
    installation_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_lifecycle_manufacturer_name: Optional[str] = None
    model_lifecycle_model_name: Optional[str] = None
    model_lifecycle_asset_type_name: Optional[str] = None
    model_lifecycle_lifecycle_status: Optional[str] = None
    effective_install_date: Optional[date] = None
    lifespan_years: Optional[float] = None
    effective_useful_life: Optional[int] = None
    useful_life_source: Optional[str] = None
    years_remaining: Optional[float] = None
    lifecycle_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
