from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


class LifecycleStatusBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    color: str = "#64748b"
    active: bool = True
    order: int = 0


class LifecycleStatusCreate(LifecycleStatusBase):
    pass


class LifecycleStatusUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = None
    active: Optional[bool] = None
    order: Optional[int] = None


class LifecycleStatus(LifecycleStatusBase):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
