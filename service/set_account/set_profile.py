from datetime import datetime
import json
import os
import shutil
import uuid
from sqlalchemy.orm import Session, joinedload
from fastapi import Depends, File, Form, HTTPException, UploadFile, status

from core.database import get_db
from core.enumeration import ImageDirectories, ImageURL
from models.auth.profile_picture import ProfilePicture
from models.auth.user import User
from models.services.service import UserSelectServices
from pydantic_schemas.services.service import ServiceListRequest
from pydantic_schemas.set_account.set_account import SetupProfileRequest, UserProfileResponse, UsernameCheckRequest

PROFILE_IMAGE_BASE = ImageURL.PROFILE_URL.value # Based URL for all the profile pictures 

UPLOAD_DIR = ImageDirectories.PROFILE_DIR.value # Directory where profile pictures are saved


# get account informations 
async def get_account(user_id: str, db: Session = Depends(get_db)) -> UserProfileResponse:
    """_summary_
        Retrieve the profile of the currently authenticated user.
        
        Args:
            (user_id, db: Session) -> user_id and the database session

        This function fetches the user's profile data, including their username and profile picture.

        Returns:
            - If the user is authenticated:
                → Returns 200 OK with the user's profile information (username and profile picture).
                
            - If the user is not authenticated:
                → Returns 401 Unauthorized with a message indicating that authentication is required.
                
    """
    
    # search for this user id. 
    user = db.query(User).options(joinedload(User.profile_picture)).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or unauthorized.",
        )
    
    return UserProfileResponse(
        username=user.username,
        pictureUrl=f"{PROFILE_IMAGE_BASE + user.profile_picture.file_name}" if user.profile_picture else None
    )
    

# Check username validity
async def check_username(request: UsernameCheckRequest, user_id: str, db: Session = Depends(get_db)):
    """_summary_

        Check if a username is valid and available.
        
        update ui after every 500milsec from last typing 

        This function performs two main checks:
        1. Validates the format of the provided username.
        2. Checks whether the username is already taken by another user [ except the current username ].

        Validation Rules:
            - Username must be between 6 and 20 characters long.
            - Only alphanumeric characters and underscores are allowed.
            - Must be unique (not taken by another user).

        Returns:
            - If the username is invalid:
                → Returns 400 Bad Request with a message explaining the issue.
                
            - If the username is valid but taken:
                → Returns 400 Bad Request with a message and a list of suggested alternatives.
                
            - If the username is valid and available:
                → Returns 200 OK indicating success.
        """
    user = db.query(User).filter(User.username == request.username).first()
    
    if user:
        # genereate suggestions options, 
        suggestions = [
            f"_{request.username[0:5]}_{str(uuid.uuid4()).split('-')[0]}_"
            for _ in range(3)
        ]
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Username '{request.username}' is already taken.",
                "suggestions": suggestions
            }
        )
    
    
    return {"message": f"{request.username} is available ✅"}

# upload new username and profile picture
async def upload_account_(user_id: str, data: SetupProfileRequest, image_name: UploadFile = File(None), db: Session = Depends(get_db)):
    """_summary_
    
        Update the profile of the currently authenticated user.

        This function allows the user to update their profile information, including:
        - Username
        - Profile picture

        Returns:
            - If the update is successful:
                → Returns 200 OK with a message confirming the update.
                
            - If the update fails:
                → Returns 400 Bad Request with a message describing the issue (e.g., invalid data or username already taken).
    """
    
    # is username valid
    # call the check_username function to see if the user is valid:
    username_check = await check_username(UsernameCheckRequest(username=data), user_id, db)
    if username_check == f"{data} is available ✅":
        raise HTTPException(
            status_code=400, detail="Username is un acceptable.")
        
    # find the user 
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
        
    # update the username 
    user.username = data
           
    
    # validate file type
        # if no file input don't send any file just usr_profile metadata to the database
    # Handle file saving if provided.. 
    
    if image_name != None:
        # update profile picture to the table
        profile_pic = db.query(ProfilePicture).filter(
            ProfilePicture.user_id == user.id
        ).first()
        
        # get_previous file name
        prev_filename = profile_pic.file_name
        
        if not profile_pic:
            raise HTTPException(
                status_code = 404, 
                detail = "Profile Picture record not found"
            )
            
        
        # if no any file uploaded do nothing: else
        # Here
        if image_name:
            filename = image_name.filename
            extension = os.path.splitext(filename)[1].lower()
            if extension not in [".jpg", ".jpeg", ".png", ".svg", ".webp", ".tiff"]:
                raise HTTPException(
                    status_code= status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Only .jpg, .jpeg, .png, .svg, .webp, .tiff files are allowed"
                )

            # Create a directory if not exit
            os.makedirs(UPLOAD_DIR, exist_ok=True)

            unique_filename = f"{user.role}/{uuid.uuid4().hex}{extension}"
            file_location = os.path.join(UPLOAD_DIR, unique_filename)

            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(image_name.file, buffer)

            profile_pic.file_name = unique_filename
            profile_pic.updated_at = datetime.now()
            profile_pic.is_custom = True
            
            # Remove the prevous profile picture
        
        flag = True
    
    else:
        flag = False
        
        
    # save metadata in the db
    try:
        db.commit()
        
        if flag:
            print(prev_filename)
        # remove the previos profile picture
        # leave the default profile picture
        # the rest remove
        
            print('here')
            if not (prev_filename == 'user.png'):
                
                file_location = os.path.join(UPLOAD_DIR, prev_filename)
                
                if os.path.isfile(file_location):
                    os.remove(file_location)
        
        return {
            "message": "Profile updated successfuly"
        }
        
    except Exception as e:
        db.rollback() 
        raise HTTPException(
            status_code = 500, 
            detail = f"Failed to update the profile: {str(e)}"
        )


# select default services for the users.. 

async def selected_(selected: ServiceListRequest, user_id: str, db: Session = Depends(get_db)):
    
    # print(selected.service)
    # check if user exist 
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND, 
            detail = "User not found"
        )
        
    # check the list of the services if are found int the, database
    
    # decide if the user service is to be updated or inserted
    # check user in the selected services
    user_select = db.query(UserSelectServices).filter(UserSelectServices.user_id == user_id).first()
    
    # if user found update the table otherwise write new record
    # unique selection to the database
    # user found
    if user_select:
        if user_select.services is None:
            user_select.services = []
        
        for service in selected.service:
            if service not in user_select.services:
                # Future check if the services are in Major Service table
                user_select.services.append(service)
        
    else:
        # populate user select service table
        user_select = UserSelectServices(
            id = str(uuid.uuid4()), 
            user_id = user_id, 
            services = selected.service
        )
        
        db.add(user_select)
    
    try:
        
        db.commit()
        
        db.refresh(user_select)
        
        
    
    except HTTPException as e:
        HTTPException(
            status_code = status.HTTP_406_NOT_ACCEPTABLE, 
            detail = f"An unexpected error occured: {e}"
        )
    
    return {
        "message": "Successful updated"
    }

