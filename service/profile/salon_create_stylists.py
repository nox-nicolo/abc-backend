# app/services/salon_stylist_service.py

from __future__ import annotations

from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.auth.user import User
from models.profile.salon import Salon, SalonStylist


class SalonStylistService:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------------
    # CREATE (for testing first)
    # ---------------------------------------------------------------
    def create(self, payload) -> SalonStylist:
        """
        Creates a stylist row for a salon.

        Expected payload fields:
          - salon_id: str
          - user_id: str
          - title: Optional[str]
          - bio: Optional[str]
          - is_owner: bool
          - is_active: bool
        """

        # Ensure salon exists
        salon = (
            self.db.query(Salon)
            .filter(Salon.id == payload.salon_id)
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
            salon_id=payload.salon_id,
            user_id=payload.user_id,
            title=getattr(payload, "title", None),
            bio=getattr(payload, "bio", None),
            is_owner=getattr(payload, "is_owner", False),
            is_active=getattr(payload, "is_active", True),
        )

        self.db.add(stylist)

        # Commit + handle unique constraint (uq_salon_stylist)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already a stylist for this salon",
            )

        # Return with user relationship loaded (for SalonStylistOut.user)
        stylist = (
            self.db.query(SalonStylist)
            .options(joinedload(SalonStylist.user))
            .filter(SalonStylist.id == stylist.id)
            .first()
        )

        return stylist
