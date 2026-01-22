from pydantic import BaseModel
from typing import Optional

class EventCard(BaseModel):
    event_id: str
    title: str
    description: Optional[str] = None

    price: Optional[float] = None
    currency: Optional[str] = None

    duration_hours: Optional[int] = None  

    salon_id: Optional[str] = None         
    salon_name: Optional[str] = None       
    salon_logo: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
