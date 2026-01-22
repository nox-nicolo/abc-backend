# Redefine redefine ...


from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException

from core.database import get_db
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User

DEFAULT_PROFILE_PICTURE = "user.png"


def create_profile_picture(user: User, db: Session = Depends(get_db)):
    
    """
        _summary_
        
        Set the default profile picture for this new user
        
        Args: 
            user (User): The user object created (now)
            db (Session): Database session object.
        Raises:
            HTTPException: 400 if a user with the same email doesn't exists.
        Returns:
            pass.    
            
    
    """
    
    # insert data to the profile picture table
    profile_picture = ProfilePicture(
        id = str(uuid.uuid4()),
        user_id = user.id,
        file_name = DEFAULT_PROFILE_PICTURE,  # Default profile picture name
        is_custom = False,
        uploaded_at = datetime.now(),
        updated_at = datetime.now()
    )
    
    db.add(profile_picture)    # add records to the table
    db.commit()
    db.refresh(profile_picture)  # Refresh the instance to get the updated data
    # Return the created profile picture instance
    return profile_picture
    