
from operator import and_
import uuid
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from core.database import get_db
from models.posts.posts import Post, PostComment
from pydantic_schemas.posts.get_post import PostCommentRequestSchema, PostRepyCommentRequestSchema

async def post_comment_(comment: PostCommentRequestSchema,  db: Session = Depends(get_db)):
    # check if the post exists 
    the_post = db.query(Post).filter(Post.id == comment.post_id).first() 
    
    if not the_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # add the comment to the table 
    post_comment = PostComment(
        id = str(uuid.uuid4()),
        post_id = comment.post_id,
        user_com = comment.user_com,
        content = comment.comment
    )
    
    db.add(post_comment)
    
    db.commit()
    
    db.refresh(post_comment)
    
    # return the post_comment) 
    return post_comment




async def comment_comment_(comment: PostRepyCommentRequestSchema, db: Session = Depends(get_db)):
    
    
    comment_id = comment.comment_id
    user_comment = comment.user
    user_reply = comment.reply_user
    comment_content = comment.comment
    
    print("user_reply: ", user_reply)
    print("user_comment: ", user_comment)
    print("comment_id: ", comment_id)
    print("comment_context: ", comment_content)
    
    # check if the user comment the post
    
    the_comment = db.query(PostComment).filter(
        and_(
            PostComment.id == comment_id, 
            PostComment.user_com == user_comment
        )
    ).first() 
    
    # if the comment not found then you can't comment on it
    if not the_comment:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Comment not found")
    
    # so update the PostComment table for the comment on the comment 
    # and also we can get the post id of the post that been commented on 
    
    post_id = the_comment.post_id 
    
    save_comment = PostComment(
        id = str(uuid.uuid4()), 
        post_id = post_id, 
        user_com = user_comment, 
        user_rep = user_reply,
        comment_id = comment_id, 
        content = comment_content
    )
    
    if not save_comment: 
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = "Internal Server Error")
    
    # then add to the database 
    
    db.add(save_comment)
    db.commit()
    db.refresh(save_comment)
    
    return save_comment



async def update_comment_():
    pass 


async def update_comment():
    pass 

