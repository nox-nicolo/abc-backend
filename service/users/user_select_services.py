
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.enumeration import ImageURL
from models.auth.user import User
from models.services.service import Services, UserSelectServices
from pydantic_schemas.users.user_select_service import UserSelectedServiceDetail

pic_url = ImageURL.SERVICE_URL.value

async def user_select_services_(user_id: str, db: Session):
    # 1. Fetch the user's selection record
    print(user_id)
    selection = db.query(UserSelectServices).filter(
        UserSelectServices.user_id == user_id
    ).first()
    
    print(selection.services)

    if not selection or not selection.services:
        raise HTTPException(status_code=404, detail="No services selected by user")

    # 2. Query SubServices where the ID is in the user's selection list
    # SQLAlchemy's .in_() handles the list comparison automatically
    detailed_services = db.query(Services).filter(
        Services.id.in_(selection.services)
    ).all()
    print(detailed_services)
    # 3. Map the DB results to your Pydantic Schema
    # Note: Using s.service_picture to match your DB column name
    results = [
        UserSelectedServiceDetail(
            service_id=str(s.id),
            service_name=s.name,
            service_picture= f"{pic_url}major/{s.service_picture}"
        ) for s in detailed_services
    ]
    

    return {
        "user_id": user_id,
        "selected_services": results
    }