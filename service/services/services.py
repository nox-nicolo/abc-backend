import os
import shutil
import uuid
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session 
from fastapi import Depends, File, HTTPException, UploadFile, status

from core.database import get_db
from core.enumeration import ADDRESS, ImageDirectories
from models.services.service import Services, SubServices
from pydantic_schemas.services.service import ChooseServiceRequest, DetailsServicesRequest


# save directory for service images
ImageDirMajor = ImageDirectories.SERVICE_DIR.value + "/major/"
ImageDirMinor = ImageDirectories.SERVICE_DIR.value + "/minor/"

        
# get all services major one and minor services
async def all_services(db: Session = Depends(get_db)):
    """"
    __summary__
        Get all major services from the database.
        
        This function retrieves all available services from the database and returns them in a structured format.
        
        Returns:
            - A list of dictionaries containing service details (ID, name, picture URL).
    """
    
    all_services = db.query(Services).all()
    
    result = [
        {
            "id": service.id,
            "name": service.name,
            "service_picture": service.service_picture
        } for service in all_services
    ]
    
    return JSONResponse(
        content=result,
        status_code=200
    )

# Major
async def _get_major(db: Session = Depends(get_db)):
    
    # Select * services from db..
    data = db.query(Services).all()
    all_services = []
    for service in data:
        all_services.append({
            'id': service.id,
            'name': service.name,
            'fileName': f'{ADDRESS}/{ImageDirMajor}{service.service_picture}',
            'description': service.description,
            'rated': service.rated
        })
        
    return all_services



# Insert the major services to the system
async def major_upload(major: ChooseServiceRequest, details: DetailsServicesRequest, img_upload: UploadFile = File(...), db: Session = Depends(get_db)):
    
    # check if service name exist
    service_name = db.query(Services).filter(major == Services.name).first()
    
    if service_name:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = "The service already exist"
        )
    
    # if image of the service not provided 
    if not img_upload:
        raise HTTPException(
            status_code = status.HTTP_204_NO_CONTENT, 
            detail = "No image input"
        )
        
    # else image provided
    filename = img_upload.filename 
    extension = os.path.splitext(filename)[1].lower()
    
    # check the file extension if its image
    if extension not in [".jpg", ".jpeg", ".png", ".svg", ".webp", ".tiff"]:
        raise HTTPException(
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail = "Only .jpg, .jpeg, .png, .svg, .webp, .tiff files are allowed"
        )
        
    # create a directory if not exit
    os.makedirs(ImageDirMajor, exist_ok=True)
    
    unique_filename = f"{uuid.uuid4().hex}{extension}"
    file_location = os.path.join(ImageDirMajor, unique_filename)
    
    # save the image in the directory
    try:
        with open(file_location, "wb")as buffer:    
            shutil.copyfileobj(img_upload.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_501_NOT_IMPLEMENTED, 
            detail = f"Something happening: {e}"
        )
    
    # Upload data to the major service table
    service = Services(
        id = str(uuid.uuid4()), 
        name = major, 
        service_picture = unique_filename, 
        description = details,
        rated = 0
    )
    
    try: 
        db.add(service)
        
        db.commit() 
        
        return {
            "message": "Major service uploaded successfuly"
        }
    except Exception as e:
        return HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, 
            details = {f"Failed to upload major service: {e}"}
        )
 


async def delete_major():
    pass


# Minor

# Get minor 
async def _get_minor(db: Session = Depends(get_db)):
    """
    Get minor service from the database.
    """
    # Select * services from db..
    data = db.query(SubServices).all()
    all_services = []
    
    for sub_service in data:
        if sub_service.description:
            description = sub_service.description
        elif sub_service.services and sub_service.services.description:
            description = sub_service.services.description
        else:
            description = 'This is for minor description but not provided!'


        if sub_service.file_name:
            # Use minor image
            file_url = f"{ADDRESS}/{ImageDirMinor}{sub_service.file_name}"
        elif sub_service.services and sub_service.services.service_picture:
            # Use major image from the parent service
            file_url = f"{ADDRESS}/{ImageDirMajor}{sub_service.services.service_picture}"
        else:
            file_url = None  # Or a default image URL if needed

        all_services.append({
            'id': sub_service.id,
            'serviceId': sub_service.service_id,
            'name': sub_service.name,
            'fileName': file_url,
            'description': description,
            'rated': sub_service.rated
        })

    return all_services
    


# Insert the minor services to the database
async def _minor_upload(
    parent_service: ChooseServiceRequest, 
    name: ChooseServiceRequest, 
    description: DetailsServicesRequest, 
    db: Session = Depends(get_db), 
    file_name: UploadFile = File(None), 
):
    """
    
    __summary__
        Upload minor service to the database.
        
        This function handles the upload of a minor service, including its name, associated major service ID, file name, description, and rating.
        
        Returns:
            - A JSON response indicating the success or failure of the upload operation.
    """
    
    # Check if the parent service exists
    parent_service_exists = db.query(Services).filter(Services.id == parent_service).first()
    
    if not parent_service_exists:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND, 
            detail = "Parent service not found"
        )

    # Check if the service name already exists
    sub_service_exists = db.query(SubServices).filter(SubServices.name == name).first()
    
    if sub_service_exists:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT, 
            detail = "Sub service already exists"
        )
    
    # upload the image to the directory
    if file_name:
        filename = file_name.filename 
        extension = os.path.splitext(filename)[1].lower()
        
        # Check the file extension if its image
        if extension not in [".jpg", ".jpeg", ".png", ".svg", ".webp", ".tiff"]:
            raise HTTPException(
                status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
                detail = "Only .jpg, .jpeg, .png, .svg, .webp, .tiff files are allowed"
            )
        
        # Create a directory if not exist
        os.makedirs(ImageDirMinor, exist_ok=True)
        
        unique_filename = f"{uuid.uuid4().hex}{extension}"
        file_location = os.path.join(ImageDirMinor, unique_filename)
        
        # Save the image in the directory
        try:
            with open(file_location, "wb") as buffer:    
                shutil.copyfileobj(file_name.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_501_NOT_IMPLEMENTED, 
                detail = f"Something happening: {e}"
            )
    
    # Upload data to the minor service table
    service = SubServices(
        id = str(uuid.uuid4()),
        name = name,
        service_id = parent_service,
        file_name = unique_filename,
        description = description,
        rated = 0
    )
    
    try: 
        db.add(service)
        
        db.commit() 
        
        return {
            "message": "Minor service uploaded successfuly"
        }
    except Exception as e:
        return HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, 
            details = {f"Failed to upload minor service: {e}"}
        )



async def delete_minor():
    pass