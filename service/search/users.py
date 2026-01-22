# Service Users Activities

# Search Users
from core.enumeration import ImageURL
from models.auth.user import User
from models.auth.profile_picture import ProfilePicture

PROFILE_IMAGE_BASE = ImageURL.PROFILE_URL.value

async def search_user(query: str, current_user, db):
    """
    Search users by their username or full name and include profile picture.
    """
    print(f"query: {query}")
    rows = db.query(User, ProfilePicture).outerjoin(
        ProfilePicture, ProfilePicture.user_id == User.id
    ).filter(
        (User.username.ilike(f"%{query}%")) | (User.name.ilike(f"%{query}%")),
        User.id != current_user
    ).all()

    print(rows)

    results = []
    for user, pic in rows:
        pic_url = None
        if pic is not None:
            print(pic.file_name)
            # get possible filename/path fields
            dir_part = PROFILE_IMAGE_BASE.strip("/")
            pic_url = f"{dir_part}/{pic.file_name}"
        results.append({
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "profilePicture": pic_url
        })

    return results


async def recommend_user(user_id, db):
    """
    Recommend users logic to be implemented.
    """
    pass