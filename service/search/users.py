"""Provides the Users business logic module for search workflows."""

# # Service Users Activities

# # Search Users
# from core.enumeration import ImageURL
# from models.auth.user import User
# from models.auth.profile_picture import ProfilePicture

# PROFILE_IMAGE_BASE = ImageURL.PROFILE_URL.value

# async def search_user(query: str, current_user, db):
#     """
#     Search users by their username or full name and include profile picture.
#     """
#     rows = db.query(User, ProfilePicture).outerjoin(
#         ProfilePicture, ProfilePicture.user_id == User.id
#     ).filter(
#         (User.username.ilike(f"%{query}%")) | (User.name.ilike(f"%{query}%")),
#         User.id != current_user
#     ).all()

#     results = []
#     for user, pic in rows:
#         pic_url = None
#         if pic is not None:
#             # get possible filename/path fields
#             dir_part = PROFILE_IMAGE_BASE.strip("/")
#             pic_url = f"{dir_part}/{pic.file_name}"
#         results.append({
#             "id": user.id,
#             "name": user.name,
#             "username": user.username,
#             "profilePicture": pic_url
#         })

#     return results


# async def recommend_user(user_id, db):
#     """
#     Recommend users logic to be implemented.
#     """
#     pass


from core.r2_config import BASE_URL
from core.enumeration import ImageDirectories
from models.auth.user import User
from models.auth.profile_picture import ProfilePicture
from pydantic_schemas.pagination import pagination_meta

PROFILE_IMAGE_BASE = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"


async def search_user(
    query: str,
    current_user,
    db,
    limit: int = 20,
    offset: int = 0,
):
    """
    Search users by their username or full name and include profile picture.
    """
    db_query = db.query(User, ProfilePicture).outerjoin(
        ProfilePicture, ProfilePicture.user_id == User.id
    ).filter(
        (User.username.ilike(f"%{query}%")) | (User.name.ilike(f"%{query}%")),
        User.id != current_user
    )
    total = db_query.count()
    rows = db_query.offset(offset).limit(limit).all()

    results = []
    for user, pic in rows:
        pic_url = None
        if pic is not None and pic.file_name:
            pic_url = f"{PROFILE_IMAGE_BASE}{pic.file_name}"

        results.append({
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "profilePicture": pic_url
        })

    return {
        "items": results,
        "pagination": pagination_meta(total=total, limit=limit, offset=offset),
    }


async def recommend_user(user_id, db, limit: int = 20, offset: int = 0):
    """
    Recommend users logic to be implemented.
    """
    return {
        "items": [],
        "pagination": pagination_meta(total=0, limit=limit, offset=offset),
    }
