import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ModelLifecycle(Base):
    __tablename__ = "model_lifecycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    manufacturer_id = Column(UUID(as_uuid=True), ForeignKey("manufacturers.id"), nullable=False, index=True)
    model_name = Column(String(255), nullable=False)
    lifecycle_status = Column(String(20), nullable=False, default="in_support")  # in_support, phase_out, limited_support, no_spare_parts, obsolete
    status_date = Column(Date, nullable=True)
    end_of_life_date = Column(Date, nullable=True)
    end_of_support_date = Column(Date, nullable=True)
    spare_part_availability = Column(String(20), nullable=True)  # available, limited, unavailable
    replacement_model = Column(String(255), nullable=True)
    replacement_manufacturer_id = Column(UUID(as_uuid=True), ForeignKey("manufacturers.id"), nullable=True)
    notes = Column(Text, nullable=True)
    last_reviewed_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    manufacturer = relationship("Manufacturer", back_populates="model_lifecycles", foreign_keys=[manufacturer_id])
    replacement_manufacturer = relationship("Manufacturer", foreign_keys=[replacement_manufacturer_id])
