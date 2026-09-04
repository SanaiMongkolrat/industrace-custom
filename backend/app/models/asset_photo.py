# backend/models/asset_photo.py
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AssetPhoto(Base):
    __tablename__ = "asset_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=func.now())
    asset = relationship("Asset", back_populates="photos")
