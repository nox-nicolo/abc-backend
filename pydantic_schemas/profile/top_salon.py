from pydantic import BaseModel
from typing import Optional, List

class TopSalonCard(BaseModel):
    salon_id: str
    name: str
    logo_url: Optional[str]
    cover_url: Optional[str]
    city: Optional[str]
    tagline: Optional[str]


class TopSalonResponse(BaseModel):
    results: List[TopSalonCard]
