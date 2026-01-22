
from datetime import datetime, timedelta
import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from core.database import get_db
from core.enumeration import AccountAccessStatus, Status
from core.hash_pass import Hash
from models.auth.user import User
from models.auth.verification import Verification
from models.profile.salon import Salon
from pydantic_schemas.auth.user_verification import UserVerification
from service.auth.JWT.JWT_token import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, create_refresh_token
from service.auth.send_code import mail_send

# Base URL (adjust to your server IP/domain)
BASE_URL = "http://192.168.43.160:8000/assets/images"

# Code generete
def code_generete():
    return str(uuid.uuid4())[:6]

def expire_time():
    return datetime.now() + timedelta(days=1)  # Set expiration code date to 1 day 


#insert verificaton details to the table and send code through email or phone number
async def create_verification(user: User, via: str, db: Session = Depends(get_db)):
    """

        Creates a new verification record for a user.
        
        Args:
            user (User): The user object created (now)
            db (Session): Database session object. 
            
        str(uuid.uuid4())[:6]
    """
    
    verificatin_code = code_generete()  # Generating a 6-digit verification code
    
    expires_at = expire_time()  # Code expiration time, set to 1 Hour
    
    # Hashing the verification code
    hashed_verificatin_code = verificatin_code
    
    # insert data to verification table
    verification = Verification(
        id = str(uuid.uuid4()), 
        user_id = user.id, 
        code = hashed_verificatin_code,
        via = via, 
        expires_at = expires_at, 
        status = Status.PENDING
    )
    
    db.add(verification)    # add records to the table
    
    db.commit()
    
    # Mechanism to send code though email 
    await mail_send(code = verificatin_code, email = user.email)
    
    
# verify the code 
# There need to limit the number of user verification attempts to prevent brute-force attacks
# and also include user_id in the verification process-ish
# also hash the code before send to the database
def verify_user(code: UserVerification, db: Session = Depends(get_db)):
    """

        Verifies a user based on the provided verification code.
        
        Args: 
            verification_data (UserVerification): Pydantic model containing verificaiton data
            db (Session): Database session object. 
            
        Raises:
            HTTPException: 400 if the verification code is invalid or expired. 
            
        Returns:
            User: The verified user object if  successful
            
    """ 
    
    # Check if code is same, code is expired and status is pending
    verification = db.query(Verification).filter(
        # checking if verification code is same
         Verification.code == code, 
        Verification.expires_at > datetime.now(), 
        Verification.status == Status.PENDING
    ).first()
    
    if not verification:
        # Handle the expiration case more explicitly
        verification = db.query(Verification).filter(
            Verification.code == code
        ).first()
        
        if verification and verification.status == Status.SUCCESS:
            raise HTTPException(
                status_code = 400, 
                detail = "Account is Verified"
            )
        
        if verification and verification.expires_at < datetime.now():
            raise HTTPException(
                status_code=400,
                detail="Verification code expired, Get new Code "
            )
        
        # If the code is invalid, return a general error
        raise HTTPException(
            status_code=400,
            detail="Invalid verification code"
        )
        
    verification.status = Status.SUCCESS
    
    user = db.query(User)\
             .options(joinedload(User.verification))\
             .filter(User.id == verification.user_id)\
             .first()
             
    # Check if the user exists 
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    
    user.is_verified = True
    user.account_access = AccountAccessStatus.ACTIVE
     
        
    db.commit()
    
    db.refresh(user)  # Refresh the user object to get the updated data
    
    # Construct response with profile picture
    # You have to consider the response returned thing
    # So if user is verified ehy not return the user_id and the jwt?
    
    # lets generate the JWT and return it
    
    
    access_token_expires = timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data = {
            "sub": user.id
        }, 
        expire_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data = {"sub": str(user.id)}
    )
    
    print(user.role)
    if user.role == "service":
        # Additional setup for service users can be added here
        salon = Salon(
            id = str(uuid.uuid4()),
            user_id = user.id,
            title = f"{user.name}'s Salon",
            slogan = "Your beauty, our duty",
            description = "Welcome to our salon! We offer top-notch beauty services to make you look and feel your best.",
            address = "Not Set",
            coordinates = "0.0000,0.0000",
            phone_number = "Not Set",
            email = "Not Set",
            working_hours = "Not Set",
            display_ads = "Not Set",
        )   
        
        db.add(salon)
        
        db.commit()

    return {
        "user_id": user.id, 
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    
    

# if codes expire change the status to failure
async def code_expires(code: UserVerification, db: Session = Depends(get_db)):
    """

        Re-generate new code a user based on the provided verification code.
        
        Args: 
            code (UserVerification): Pydantic model containing verificaiton data
            db (Session): Database session object. 
            
        Raises:
            HTTPException: 400 if the verification code is invalid or not expired. 
            
        Returns:
            User: The verified user object if  successful
            
    """
    
    # check if code exist in the database
    valid_code = db.query(Verification).filter(
        Verification.code == code, 
        Verification.expires_at < datetime.now(), 
        Verification.status == Status.PENDING
    ).first()
    
    if not valid_code:
        # Handle the status case more explicitly
        verification = db.query(Verification).filter(
            Verification.code == code
        ).first()
        
        if verification and verification.status == Status.SUCCESS:
            raise HTTPException(
                status_code = 400, 
                detail = "Account is Verified"
            )
            
        if verification and verification.expires_at > datetime.now():
            raise HTTPException(
                status_code= status.HTTP_200_OK,
                detail="Go to your mail"
            )
            
        raise HTTPException (
            status_code = 400, 
            detail = "Input Code is invalid"
        )

    # Get user email from the code using the user_id from the valid_code
    user = db.query(User).filter(User.id == valid_code.user_id).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="User not found"
        )

    # Access the email of the user
    user_mail = user.email
    
    # generate new code
    new_code = code_generete()
    
    # Update code
    valid_code.code = new_code
    valid_code.expires_at = expire_time()
    
    db.commit()
    
    # send code
    await mail_send(code = new_code, email = user_mail)
    
    return {"message": "New Code sent to your mail"}
    
    
     
    