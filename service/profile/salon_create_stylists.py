# app/services/salon_stylist_service.py

from __future__ import annotations

from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageURL
from models.auth.user import User
from models.profile.salon import Salon, SalonStylist
from pydantic_schemas.profile.salon_stylists import SalonStylistUpdate


class SalonStylistService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        
        # Look up the salon owned by this user immediately
        # Using .first() assuming one owner has one salon for now
        salon = self.db.query(Salon).filter(Salon.user_id == user_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You do not own a salon. Please create one first."
            )
        
        self.salon = salon  # Now we have access to self.salon.id everywhere

    # ---------------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------------
    def create(self, payload) -> SalonStylist:
        """
        Creates a stylist row for the currently authenticated salon.

        Expected payload fields:
        - user_id: str
        - title: Optional[str]
        - bio: Optional[str]
        - is_owner: bool
        - is_active: bool
        """

        # Ensure salon exists for the authenticated user
        salon = (
            self.db.query(Salon)
            .filter(Salon.user_id == self.user_id)
            .first()
        )
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found",
            )

        # Ensure user exists
        user = (
            self.db.query(User)
            .filter(User.id == payload.user_id)
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Create stylist row
        stylist = SalonStylist(
            salon_id=salon.id,
            user_id=payload.user_id,
            title=getattr(payload, "title", None),
            bio=getattr(payload, "bio", None),
            is_owner=getattr(payload, "is_owner", False),
            is_active=getattr(payload, "is_active", True),
        )

        self.db.add(stylist)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already a stylist for this salon",
            )

        stylist = (
            self.db.query(SalonStylist)
            .options(joinedload(SalonStylist.user))
            .filter(SalonStylist.id == stylist.id)
            .first()
        )

        return stylist
    
    
    # ---------------------------------------------------------------
    # List Salon's Stylists
    # ---------------------------------------------------------------
    
    def list_for_salon(self, limit: int, offset: int):
        # 1) Get all salon ids owned by this user
        # salon_ids = [
        #     s[0]
        #     for s in (
        #         self.db.query(Salon.id)
        #         .filter(Salon.user_id == user_id)  # or Salon.owner_id
        #         .all()
        #     )
        # ]

        # # If user has no salon yet => empty list (not an error)
        # if not salon_ids:
        #     return {"items": [], "total": 0, "limit": limit, "offset": offset}

        # 2) Query stylists for those salons (+ eager load user + profile_picture)
        q = (
            self.db.query(SalonStylist)
            .filter(SalonStylist.salon_id == self.salon.id)
            .options(
                joinedload(SalonStylist.user).joinedload(User.profile_picture)
            )
        )

        # Optional: only active stylists
        # q = q.filter(SalonStylist.is_active == True)

        # 3) Count + paginate
        total = q.count()

        items = (
            q.order_by(SalonStylist.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # 4) Return ORM items; Pydantic builds profile_picture_url
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
        
    # ---------------------------------------------------------------
    # Search for users to add as stylists 
    # ---------------------------------------------------------------
    def search_users_to_add(self, query: str, limit: int = 10):
        # 1. Get IDs of people already in the salon to exclude them
        existing_ids = [
            r[0] for r in self.db.query(SalonStylist.user_id)
            .filter(SalonStylist.salon_id == self.salon.id)
            .all()
        ]

        # 2. Perform the search
        search_results = (
            self.db.query(User)
            .filter(
                (User.name.ilike(f"%{query}%")) | 
                (User.username.ilike(f"%{query}%"))
            )
            # EXCLUSIONS:
            .filter(~User.id.in_(existing_ids)) # Not already a stylist
            .filter(User.id != self.user_id)     # NOT THE OWNER
            .options(joinedload(User.profile_picture))
            .limit(limit)
            .all()
        )
        
        return search_results
    
    # ---------------------------------------------------------------
    # Remove stylist (soft delete or hard delete)
    # ---------------------------------------------------------------
    def remove_stylist(self, stylist_id: str):
        # Ensure the stylist actually belongs to THIS owner's salon
        stylist = (
            self.db.query(SalonStylist)
            .filter(
                SalonStylist.id == stylist_id,
                SalonStylist.salon_id == self.salon.id
            )
            .first()
        )

        if not stylist:
            raise HTTPException(status_code=404, detail="Stylist not found in your salon")

        self.db.delete(stylist)
        self.db.commit()
        return {"message": "Stylist removed successfully"}
    
    
    # ---------------------------------------------------------------
    # Update stylist details (title, bio, is_active)
    # ---------------------------------------------------------------
    def update_stylist(self, stylist_id: str, payload: SalonStylistUpdate) -> SalonStylist:
        # 1. Fetch the stylist record belonging to THIS owner's salon
        stylist = (
            self.db.query(SalonStylist)
            .filter(
                SalonStylist.id == stylist_id,
                SalonStylist.salon_id == self.salon.id
            )
            .first()
        )

        if not stylist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stylist not found in your salon."
            )

        # 2. Update only the fields provided in the payload
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(stylist, key, value)

        try:
            self.db.commit()
            self.db.refresh(stylist)
        except Exception:
            self.db.rollback()
            raise HTTPException(status_code=500, detail="Update failed")

        # 3. Return updated object with relationships for the response model
        return (
            self.db.query(SalonStylist)
            .options(joinedload(SalonStylist.user).joinedload(User.profile_picture))
            .filter(SalonStylist.id == stylist.id)
            .first()
        )
        
        
    # ---------------------------------------------------------------
    # Get stylist details (with user and profile picture)
    # ---------------------------------------------------------------
    def get_stylist(self, stylist_id: str) -> SalonStylist:
        # Fetch the stylist and eager load the user and profile picture
        stylist = (
            self.db.query(SalonStylist)
            .options(joinedload(SalonStylist.user).joinedload(User.profile_picture))
            .filter(
                SalonStylist.id == stylist_id,
                SalonStylist.salon_id == self.salon.id # Security check
            )
            .first()
        )

        if not stylist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stylist not found in your salon."
            )

        return stylist