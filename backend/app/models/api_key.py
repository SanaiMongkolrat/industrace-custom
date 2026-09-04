# backend/models/api_key.py
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    scopes = Column(Text, nullable=False, default="read")  # JSON string of scopes
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Rate limiting settings
    rate_limit = Column(String(50), nullable=False, default="100/hour")

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    created_by_user = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


# Alias for routers that import APIKey (uppercase)
APIKey = ApiKey
