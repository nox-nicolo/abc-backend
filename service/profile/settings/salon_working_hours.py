import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.profile.salon import Salon, SalonWorkingHour
from pydantic_schemas.profile.settings import SalonWorkingHoursUpdateRequest

async def update_salon_working_hours_(
    user_id: str,
    payload: SalonWorkingHoursUpdateRequest,
    db: Session,
):
    # 1. Ownership check
    salon = db.query(Salon).filter(Salon.user_id == user_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="This Salon not found")

    # 2. Fetch existing hours in one query and map them by day_of_week
    existing_hours = {
        wh.day_of_week: wh 
        for wh in db.query(SalonWorkingHour).filter(SalonWorkingHour.salon_id == salon.id).all()
    }

    try:
        updated_records = []
        for day_data in payload.working_days:
            if day_data.day_of_week in existing_hours:
                # Update existing record
                record = existing_hours[day_data.day_of_week]
            else:
                # Create new record
                record = SalonWorkingHour(
                    id=str(uuid.uuid4()),
                    salon_id=salon.id,
                    day_of_week=day_data.day_of_week
                )
                db.add(record)

            # Assign values
            record.is_open = day_data.is_open
            # If closed, we store NULL in the DB for times to keep data clean
            record.open_time = day_data.open_time if day_data.is_open else None
            record.close_time = day_data.close_time if day_data.is_open else None
            
            updated_records.append(record)

        db.commit()

        # Sort response by day of week (Monday to Sunday)
        payload.working_days.sort(key=lambda x: x.day_of_week)
        
        return {"working_days": payload.working_days}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update working hours: {str(e)}"
        )