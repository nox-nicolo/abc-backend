import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.profile.salon import Salon, SalonContact, SalonLocation
from pydantic_schemas.profile.settings import SalonContactUpdateRequest

async def update_salon_contact_(
    user_id: str,
    payload: SalonContactUpdateRequest,
    db: Session,
):
    # 1. Verify Salon Ownership
    salon = db.query(Salon).filter(Salon.user_id == user_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    # --- UNIQUENESS CHECKS ---
    
    # Check Email Uniqueness
    if payload.email:
        existing_email = db.query(SalonContact).filter(
            SalonContact.type == "email",
            SalonContact.value == str(payload.email),
            SalonContact.salon_id != salon.id  # Ignore the current salon's own email
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="This email is already in use by another salon.")

    # Check Website Uniqueness
    if payload.website:
        existing_web = db.query(SalonContact).filter(
            SalonContact.type == "website",
            SalonContact.value == str(payload.website),
            SalonContact.salon_id != salon.id
        ).first()
        if existing_web:
            raise HTTPException(status_code=400, detail="This website is already registered.")

    # Check Phone Numbers Uniqueness
    if payload.phone_numbers:
        for phone in payload.phone_numbers:
            existing_phone = db.query(SalonContact).filter(
                SalonContact.type == "phone",
                SalonContact.value == phone,
                SalonContact.salon_id != salon.id
            ).first()
            if existing_phone:
                raise HTTPException(status_code=400, detail=f"Phone number {phone} is already in use.")
            
    # 2. Update Location (One-to-One)
    address = db.query(SalonLocation).filter(SalonLocation.salon_id == salon.id).first()
    if not address:
        address = SalonLocation(id=str(uuid.uuid4()), salon_id=salon.id)
        db.add(address)

    if payload.country is not None: address.country = payload.country.strip()
    if payload.city is not None: address.city = payload.city.strip()
    if payload.street is not None: address.street = payload.street.strip()
    if payload.address is not None: address.region = payload.address.strip() # Mapping address to region or similar
    if payload.latitude is not None: address.latitude = payload.latitude
    if payload.longitude is not None: address.longitude = payload.longitude

    # 3. Update Contacts (Row-based logic)
    # If phone_numbers is provided in payload, we replace the old ones
    if payload.phone_numbers is not None:
        # Delete existing phone contacts for this salon
        db.query(SalonContact).filter(
            SalonContact.salon_id == salon.id, 
            SalonContact.type == "phone"
        ).delete()
        
        # Add new ones (up to 3 as per Pydantic validation)
        for i, phone in enumerate(payload.phone_numbers):
            new_phone = SalonContact(
                id=str(uuid.uuid4()),
                salon_id=salon.id,
                type="phone",
                value=phone,
                is_primary=(i == 0) # First one is primary
            )
            db.add(new_phone)

    if payload.email is not None:
        # Update or Create Email row
        email_contact = db.query(SalonContact).filter(
            SalonContact.salon_id == salon.id, 
            SalonContact.type == "email"
        ).first()
        if not email_contact:
            email_contact = SalonContact(id=str(uuid.uuid4()), salon_id=salon.id, type="email")
            db.add(email_contact)
        email_contact.value = str(payload.email)

    if payload.website is not None:
        # Update or Create Website row
        web_contact = db.query(SalonContact).filter(
            SalonContact.salon_id == salon.id, 
            SalonContact.type == "website"
        ).first()
        if not web_contact:
            web_contact = SalonContact(id=str(uuid.uuid4()), salon_id=salon.id, type="website")
            db.add(web_contact)
        web_contact.value = str(payload.website)

    try:
        db.commit()
        
        # Re-fetch for response
        phones = db.query(SalonContact).filter(SalonContact.salon_id == salon.id, SalonContact.type == "phone").all()
        email_val = db.query(SalonContact).filter(SalonContact.salon_id == salon.id, SalonContact.type == "email").first()
        web_val = db.query(SalonContact).filter(SalonContact.salon_id == salon.id, SalonContact.type == "website").first()

        return {
            "phone_numbers": [p.value for p in phones],
            "email": email_val.value if email_val else None,
            "website": web_val.value if web_val else None,
            "country": address.country,
            "city": address.city,
            "street": address.street,
            "address": address.region, 
            "latitude": address.latitude,
            "longitude": address.longitude,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")