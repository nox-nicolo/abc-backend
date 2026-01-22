from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class UserSelectedServiceDetail(BaseModel):
    service_id: str
    service_name: str
    service_picture: Optional[str] = None

class UserSelectServicesResponse(BaseModel):
    user_id: str
    selected_services: List[UserSelectedServiceDetail]

    model_config = ConfigDict(from_attributes=True)