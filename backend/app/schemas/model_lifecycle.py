from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime
import uuid


class ModelLifecycleBase(BaseModel):
    manufacturer_id: uuid.UUID
    model_name: str = Field(..., max_length=255, description="Model name")
    asset_type_id: Optional[uuid.UUID] = None
    lifecycle_status: str = Field(default="not_applicable", description="Lifecycle status: in_support, phase_out, limited_support, no_spare_parts, obsolete, not_applicable")
    status_date: Optional[date] = None
    useful_life_years: Optional[int] = Field(None, description="Useful life in years (e.g. 10, 15)")
    end_of_support_date: Optional[date] = None
    spare_part_availability: Optional[str] = Field(None, description="Spare part availability: available, limited, unavailable")
    replacement_model: Optional[str] = Field(None, max_length=255, description="Recommended replacement model")
    replacement_manufacturer_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=10000, description="Notes")
    last_reviewed_date: Optional[date] = None


class ModelLifecycleCreate(ModelLifecycleBase):
    tenant_id: Optional[uuid.UUID] = None


class ModelLifecycleUpdate(BaseModel):
    manufacturer_id: Optional[uuid.UUID] = None
    model_name: Optional[str] = Field(None, max_length=255, description="Model name")
    asset_type_id: Optional[uuid.UUID] = None
    lifecycle_status: Optional[str] = Field(None, description="Lifecycle status: in_support, phase_out, limited_support, no_spare_parts, obsolete, not_applicable")
    status_date: Optional[date] = None
    useful_life_years: Optional[int] = Field(None, description="Useful life in years (e.g. 10, 15)")
    end_of_support_date: Optional[date] = None
    spare_part_availability: Optional[str] = Field(None, description="Spare part availability: available, limited, unavailable")
    replacement_model: Optional[str] = Field(None, max_length=255, description="Recommended replacement model")
    replacement_manufacturer_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=10000, description="Notes")
    last_reviewed_date: Optional[date] = None


class ModelLifecycle(ModelLifecycleBase):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    manufacturer_name: Optional[str] = None
    replacement_manufacturer_name: Optional[str] = None
    asset_count: Optional[int] = None
    asset_type_name: Optional[str] = None

    # Useful-life inheritance resolved value (model override → asset_type fallback)
    # Added 2026-09-07: when model.useful_life_years is NULL and asset_type has it
    # (with inheritance_enabled), this is the asset_type's value.
    effective_useful_life: Optional[int] = Field(
        None,
        description="Resolved useful life in years: model.useful_life_years if set, else asset_type.useful_life_years if inherited, else NULL",
    )
    useful_life_source: Optional[str] = Field(
        None,
        description="Where the effective value came from: 'model', 'inherited_from_asset_type', or 'not_set'",
    )

    model_config = ConfigDict(from_attributes=True)
