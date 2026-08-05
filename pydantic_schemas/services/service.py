"""Provides the Service request and response schema module for the backend application."""

from pydantic import BaseModel

from pydantic_schemas.pagination import Page


class ChooseServiceRequest(BaseModel):
    name: str
    
    
class DetailsServicesRequest(BaseModel):
    description: str = None
    

class ServiceListRequest(BaseModel):
    service: list  
    



# Responses 

class ServiceSummaryResponse(BaseModel):
    id: str
    name: str
    service_picture: str | None = None


class ServiceSummaryPage(Page[ServiceSummaryResponse]):
    pass


class MajorServiceResponse(BaseModel):
    id: str 
    name: str 
    fileName: str 
    description: str 
    rated: float


class MajorServicePage(Page[MajorServiceResponse]):
    pass
    

class MinorServiceResponse(BaseModel):
    id: str 
    serviceId: str
    name: str
    fileName: str = None
    description: str = None
    rated: float = None


class MinorServicePage(Page[MinorServiceResponse]):
    pass
    
    
