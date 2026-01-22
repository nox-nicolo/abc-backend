from fastapi import APIRouter, status, HTTPException
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.database import get_db
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.users.user_select_service import UserSelectServicesResponse
from service.auth.JWT.oauth2 import get_current_user
from service.search.users import recommend_user, search_user
from service.users.user_select_services import user_select_services_


users = APIRouter(
    prefix="/users",
    tags=["Users"], # Add your dependencies here
)





# ---------------------------------------------------
# Customer End Point
# ---------------------------------------------------


# ++++++++++++++++++++++@GET+++++++++++++++++++++++++

# Header informations
@users.get('/customers/header')
async def get_customer_header():
    return {
        'Customer Informations'
    }

# Settings
@users.get('/customers/settings')
async def get_customer_header_settings():
    return {
        'Customer Settings'
    }
    
# Menu
@users.get('/customers/menu')
async def get_customer_menu():
    return {
        'This are the helping Data'
    }



# ++++++++++++++++++++++@POST++++++++++++++++++++++++


#                       END
# ---------------------------------------------------





# ---------------------------------------------------
# Service  EndPoint
# ---------------------------------------------------



# ++++++++++++++++++++++@GET+++++++++++++++++++++++++

# Header infomration
@users.get('/services/header')
async def get_service_header():
    return {
        'Salon Information header'
    }
    
# Settings
@users.get('/services/settings')
async def get_service_settings():
    return {
        'Service Settings'
    }
    
# Menu
@users.get('services/menu')
async def get_service_menu():
    return {
        'Return the menu of the service'
    }
    

# ++++++++++++++++++++++@POST++++++++++++++++++++++++


#                       END
# ---------------------------------------------------



# ---------------------------------------------------
# Admin EndPoint
# ---------------------------------------------------



# ++++++++++++++++++++++@GET+++++++++++++++++++++++++
# ++++++++++++++++++++++@POST++++++++++++++++++++++++

#                       END
# ---------------------------------------------------



# ---------------------------------------------------
# ShareHolders EndPoint
# ---------------------------------------------------



# ++++++++++++++++++++++@GET+++++++++++++++++++++++++
# ++++++++++++++++++++++@POST++++++++++++++++++++++++

#                       END
# ---------------------------------------------------


# ---------------------------------------------------
# UserTagging Endpoints
# ---------------------------------------------------



# ++++++++++++++++++++++@GET+++++++++++++++++++++++++

@users.get("/tags/search/")
async def get_user_tags(query: str = "", current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    
    user_id = current_user.user_id
    
    try:
        return await search_user(query, user_id, db)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    
        
@users.get("/tags/recent") 
async def get_recent_user_tags():
    # Best implemented in font-end with local storage/cache
    # pass
    return [
        {
            "id": "12d5690b-3c1b-46fc-9664-1b106df1f984",
            "username": "nicolo",
            "name": "Nicolo",
            "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
        },
        {
            "id": "142bd2f1-42f9-4527-afa5-eca024709644",
            "username": "Nicolo_xcnj4a",
            "name": "Nicoloo",
            "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
        },
        {
            "id": "af956e0d-9b52-4cea-9944-0f340038f62d",
            "username": "nick_n_nbiqec",
            "name": "Nick",
            "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
        },
    ]
    
@users.get("/tags/recommended")
async def get_recommended_user_tags(current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    
    user_id = current_user.user_id
    try:
        return await recommend_user(user_id, db)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    
    
    # return [
    #     {
    #         "id": "12d5690b-3c1b-46fc-9664-1b106df1f984",
    #         "username": "nicolo",
    #         "name": "Nicolo",
    #         "profile_picture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
    #     },
    #     {
    #         "id": "142bd2f1-42f9-4527-afa5-eca024709644",
    #         "username": "Nicolo_xcnj4a",
    #         "name": "Nicoloo",
    #         "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
    #     },
    #     {
    #         "id": "af956e0d-9b52-4cea-9944-0f340038f62d",
    #         "username": "nick_n_nbiqec",
    #         "name": "Nick",
    #         "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
    #     },
    # ]
    
@users.get("/user_select_services", response_model=UserSelectServicesResponse)
async def get_user_select_services(
    current_user: TokenData = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        # Simply call the service
        return await user_select_services_(current_user.user_id, db)
        
    except HTTPException as e:
        raise e # FastAPI handles HTTPExceptions automatically if you raise them
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred: {str(e)}"
        )

# ++++++++++++++++++++++@POST++++++++++++++++++++++++

#                       END
# ---------------------------------------------------