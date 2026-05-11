from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship

from models.base import Base


class SavedSalon(Base):
    __tablename__ = "saved_salons"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="saved_salons")
    salon = relationship("Salon", back_populates="saved_by")

    __table_args__ = (
        UniqueConstraint("user_id", "salon_id", name="uq_saved_salons_user_salon"),
        Index("ix_saved_salons_user_created", "user_id", "created_at"),
        Index("ix_saved_salons_salon_created", "salon_id", "created_at"),
    )


class SavedService(Base):
    __tablename__ = "saved_services"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(String(36), ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True)
    sub_service_id = Column(String(36), ForeignKey("sub_services.id", ondelete="CASCADE"), nullable=True, index=True)
    salon_service_price_id = Column(String(36), ForeignKey("salon_service_prices.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="saved_services")
    service = relationship("Services", back_populates="saved_by")
    sub_service = relationship("SubServices", back_populates="saved_by")
    salon_service_price = relationship("SalonServicePrice", back_populates="saved_by")

    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="uq_saved_services_user_service"),
        UniqueConstraint("user_id", "sub_service_id", name="uq_saved_services_user_sub_service"),
        UniqueConstraint("user_id", "salon_service_price_id", name="uq_saved_services_user_salon_price"),
        Index("ix_saved_services_user_created", "user_id", "created_at"),
        Index("ix_saved_services_service_created", "service_id", "created_at"),
        Index("ix_saved_services_sub_service_created", "sub_service_id", "created_at"),
        Index("ix_saved_services_salon_price_created", "salon_service_price_id", "created_at"),
    )
