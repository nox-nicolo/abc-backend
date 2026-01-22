
import random
import string
import uuid
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from core.database import get_db
from core.hash_pass import Hash
from models.auth.user import User
from models.profile.salon import Salon
from pydantic_schemas.auth.user_create import UserCreate
from service.auth.profile_pictuer import create_profile_picture
from service.auth.verify_user import create_verification


async def create_user(user: UserCreate, db: Session = Depends(get_db)): 
    """
        Creates a new user in the database
        
        Args:
            user(UserCreate): Pydantic model containing user data
            db (Session): Database session object.
            
        Raises:
            HTTPException: 400 if a user with the same email already exists.
            
        Function: 
            Populate the user table with the User information, also initiate the verificaton process
            
        Returns:
            User: The newly created user object.
    """
    
    # check if user exitst
    existing_user = db.query(User).filter(User.email == user.email).first() # return the first result
    
    # if the user exist in the database
    if existing_user:
        raise HTTPException(
            status_code = 400, 
            detail = 'Email Address Taken!'
        )
        
    # check if the phone number already used.. 
    existing_phone = db.query(User).filter(User.phone == user.phone).first()
    if existing_phone: 
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = "Phone number Taken!"
        )
    
    # if user not found in the database
    # hash password
    # Hashing class used to hass the user password
    hash_passwd = Hash.hashing(user.password)
    
    # Generate random 6-character string
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6)).lower()
    
    # generate user name for now but user will change if she doesn't like it during setup profile
    generated_username = f"{(user.name).replace(" ", "_")[0:6]}_{random_str}"
    
    
    
    # insert user
    new_user = User (
        id = str(uuid.uuid4()), 
        username = generated_username,
        name = user.name,
        email = user.email, 
        phone = user.phone, 
        role = user.role,
        password = hash_passwd
    )
    
    # add user
    db.add(new_user)
    
    # commit transaction
    db.commit()
    
    # refresh object after commit
    db.refresh(new_user)
    
    # set a default profile picture for the new user
    create_profile_picture(new_user, db)
    
    # Create verification record After user creation
    await create_verification(new_user, "email", db)
    
    return {"message": "Account Created"}