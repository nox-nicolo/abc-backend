# share this post to this users .. 

# user_share 
# user_to_share [ list of the user_to_share ]
# the post to be shared 

import uuid
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status


from core.database import get_db
from models.posts.posts import Post, PostShare
from pydantic_schemas.posts.get_post import PostShareRequestSchema


async def count_share_(id: str, db: Session = Depends(get_db)):
    # check if the post exist
    this_post = db.query(Post).filter(Post.id == id).first()
    
    if not this_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= '-1')
    
    
    # count from the post_share
    the_count = db.query(PostShare).filter(PostShare.post_id == id).count()
    
    # return the number of shares. 
    return the_count


async def post_share_(share: PostShareRequestSchema,  db: Session = Depends(get_db)):
    print(share)
    
    # check if the post exist
    the_post = db.query(Post).filter(Post.id == share.post_id).first()
    
    if not the_post:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = 'Error')
    
    
    # for every user shared write to the table ..
    if len(share.shared_user) < 1:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail = 'No User selected')
    print('continue')
    for user in share.shared_user:
        insert = PostShare(
            id = str(uuid.uuid4()),
            post_id = share.post_id, 
            share_user_id = share.user_share, 
            user_id = user
        )
    
    
    # save and commit the transaction
    db.add(insert)
    db.commit()
    db.refresh(insert)
    
    
    # return the successful share message
    return {
        "message": "Post successfully shared"
    }