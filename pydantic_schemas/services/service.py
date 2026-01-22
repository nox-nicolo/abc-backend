from pydantic import BaseModel


class ChooseServiceRequest(BaseModel):
    name: str
    
    
class DetailsServicesRequest(BaseModel):
    description: str = None
    

class ServiceListRequest(BaseModel):
    service: list  
    



# Responses 

class MajorServiceResponse(BaseModel):
    id: str 
    name: str 
    fileName: str 
    description: str 
    rated: float
    

class MinorServiceResponse(BaseModel):
    id: str 
    serviceId: str
    name: str
    fileName: str = None
    description: str = None
    rated: float = None
    
    
