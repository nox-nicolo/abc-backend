from sqlalchemy import ARRAY, FLOAT, TEXT, Column, ForeignKey, String, BOOLEAN, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList

from models.base import Base

# Services offered by the application
# This table contains the main services
class Services(Base):
    
    __tablename__ = 'services'
    
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    service_picture = Column(String, nullable=False)  
    description = Column(TEXT, nullable=True)  
    rated = Column(FLOAT, nullable=True)   
    
    # relations here 
    sub_services = relationship('SubServices', back_populates='services', cascade="all, delete-orphan")
    salon_service_prices = relationship("SalonServicePrice",back_populates="service",cascade="all, delete-orphan",)

    
    def __repr__(self):
        return f"<name = {self.name}>"
    
    
# Sub services of the main service
class SubServices(Base):
    
    __tablename__ = 'sub_services'
    
    id = Column(String(36), primary_key=True, index=True)
    service_id = Column(String(36), ForeignKey("services.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    file_name = Column(String, nullable = True)
    description = Column(TEXT, nullable=True)
    rated = Column(FLOAT, nullable=True)
    is_event = Column(BOOLEAN, default=False, nullable=False)
    
    # Relation here
    services = relationship('Services', back_populates='sub_services')
    salon_service_prices = relationship("SalonServicePrice", back_populates="sub_service")

    
    posts = relationship("Post", back_populates="sub_service")
     
    __table_args__ = (
        UniqueConstraint("service_id", "name", name="uq_service_subservice"),
    )
    
    def __repr__(self):
        return f"<Sub_Service name: {self.name}>"
    
    
# List of services selected by the user
class UserSelectServices(Base):
    
    __tablename__ = 'user_select_services'
    
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True,  nullable=False)   
    services = Column(MutableList.as_mutable(ARRAY(String)), default=list)
    
    # relationships
    user = relationship('User', back_populates='select_service')
    
    
    
