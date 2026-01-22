from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Define database URI 
DATABASE_URL = 'postgresql://neondb_owner:npg_r69uJkgvYBpW@ep-still-field-abm8djij-pooler.eu-west-2.aws.neon.tech/abc?sslmode=require&channel_binding=require'
DATABASE_URL = "postgresql://postgres:elocinhacker@localhost:5432/abc"


# Create the SQLAlchemy engine
# Starting point of sqlAlchemy and acts as, Central source of connection to the database
engine = create_engine(DATABASE_URL)

# Create a session maker factory (configured for non-autocommit)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 
    # autocommit to false means sqlachemy will not commit transaction automatic, this means commit will be performed explicity
    # autoflush decide if the database auto flush bind for each changes
    # bind ensure the engine session should use all the time in this case bind to engine above

# Function for dependency injection to create and close database sessions
def get_db(): # passed as dependency injection,
    db = SessionLocal() # get access to the database by calling the sessionlocal
    try:
        yield db
    finally:
        db.close()
