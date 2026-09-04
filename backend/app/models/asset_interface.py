import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class AssetInterface(Base):
    __tablename__ = "asset_interfaces"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50))  
    type = Column(String(50))   
    vlan = Column(String(50), nullable=True)
    logical_port = Column(String(100), nullable=True)
    physical_plug_label = Column(String(100), nullable=True)
    details = Column(JSONB, default={})  
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(50), nullable=True)
    subnet_mask = Column(String(50), nullable=True)
    default_gateway = Column(String(50), nullable=True)
    mac_address = Column(String(50), nullable=True)
    other = Column(String(255), nullable=True)
    protocols = Column(JSONB, default=list)  # Protocolli industriali supportati dall'interfaccia
    asset = relationship("Asset", back_populates="interfaces")
