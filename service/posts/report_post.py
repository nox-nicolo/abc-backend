

# Report the Post Service .. 

from fastapi import Depends
from sqlalchemy.orm import Session

from core.database import get_db
from pydantic_schemas.posts.get_post import PostReportsRequestSchema 



# Service for get all reports that user post
async def get_reports_(db: Session = Depends(get_db)):
    # get all the report 
    pass 


# Service for get all un-issued reports


# Service for user to post their reports
async def report_(reports: PostReportsRequestSchema, db: Session = Depends(get_db)):
    
    pass 



#  Getting Self User reports
async def user_report_():
    pass 


