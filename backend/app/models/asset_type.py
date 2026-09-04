# backend/models/asset_type.py
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AssetType(Base):
    __tablename__ = "asset_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    icon = Column(String(50))
    color = Column(String(7), default="#6366f1")
    fields_schema = Column(JSONB, default=list)
    purdue_level = Column(Float, nullable=True)
    useful_life_years = Column(Integer, nullable=True)
    useful_life_inheritance_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
    assets = relationship("Asset", back_populates="asset_type")
    model_lifecycles = relationship("ModelLifecycle", back_populates="asset_type")
