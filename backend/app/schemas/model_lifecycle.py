from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime
import uuid


class ModelLifecycleBase(BaseModel):
    manufacturer_id: uuid.UUID
    model_name: str = Field(..., max_length=255, description="Model name")
    lifecycle_status: str = Field(default="in_support", description="Lifecycle status: in_support, phase_out, limited_support, no_spare_parts, obsolete")
    status_date: Optional[date] = None
    end_of_life_date: Optional[date] = None
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
    lifecycle_status: Optional[str] = Field(None, description="Lifecycle status: in_support, phase_out, limited_support, no_spare_parts, obsolete")
    status_date: Optional[date] = None
    end_of_life_date: Optional[date] = None
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

    model_config = ConfigDict(from_attributes=True)
