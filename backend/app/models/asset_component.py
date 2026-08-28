import uuid
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AssetComponent(Base):
    __tablename__ = "asset_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    model_lifecycle_id = Column(UUID(as_uuid=True), ForeignKey("model_lifecycles.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    installation_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    asset = relationship("Asset", back_populates="components")
    model_lifecycle = relationship("ModelLifecycle")
