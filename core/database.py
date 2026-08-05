"""Provides the Database shared infrastructure module for the backend application."""

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker


# # Define database URI 
# DATABASE_URL = 'postgresql://neondb_owner:npg_r69uJkgvYBpW@ep-still-field-abm8djij-pooler.eu-west-2.aws.neon.tech/abc?sslmode=require&channel_binding=require'
# # DATABASE_URL = "postgresql://postgres:elocinhacker@localhost:5432/abc"


# # Create the SQLAlchemy engine
# # Starting point of sqlAlchemy and acts as, Central source of connection to the database
# engine = create_engine(DATABASE_URL)

# # Create a session maker factory (configured for non-autocommit)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 
#     # autocommit to false means sqlachemy will not commit transaction automatic, this means commit will be performed explicity
#     # autoflush decide if the database auto flush bind for each changes
#     # bind ensure the engine session should use all the time in this case bind to engine above

# # Function for dependency injection to create and close database sessions
# def get_db(): # passed as dependency injection,
#     db = SessionLocal() # get access to the database by calling the sessionlocal
#     try:
#         yield db
#     finally:
#         db.close()


# # import os
# # from sqlalchemy import create_engine
# # from sqlalchemy.orm import sessionmaker

# # # --- STEP 1: LOAD THE URL ---
# # # 'os.getenv' looks for a variable named DATABASE_URL on Render.
# # # If it doesn't find it, it uses the string after the comma.
# # DATABASE_URL = os.getenv(
# #     "DATABASE_URL", 
# #     "postgresql://neondb_owner:npg_r69uJkgvYBpW@ep-still-field-abm8djij-pooler.eu-west-2.aws.neon.tech/abc?sslmode=require"
# # )

# # # --- STEP 2: FIX FOR RENDER/HEROKU ---
# # if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
# #     DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# # # --- STEP 3: CONFIGURE THE ENGINE ---
# # engine = create_engine(
# #     DATABASE_URL,
# #     pool_pre_ping=True,      # This fixes your 'decryption failed' error
# #     pool_recycle=300,        # Prevents stale connections
# #     connect_args={
# #         "keepalives": 1,
# #         "keepalives_idle": 30,
# #         "keepalives_interval": 10,
# #         "keepalives_count": 5,
# #     }
# # )

# # SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # def get_db():
# #     db = SessionLocal()
# #     try:
# #         yield db
# #     finally:
# #         db.close()


import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Prefer environment variable in production, fallback to your current URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_r69uJkgvYBpW@ep-still-field-abm8djij-pooler.eu-west-2.aws.neon.tech/abc?sslmode=require&channel_binding=require"
)

# Render / some providers may use postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Ensure sslmode=require exists
if "sslmode=" not in DATABASE_URL:
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"

connect_args = {
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}

pool_mode = os.getenv("DB_POOL_MODE", "queue").lower()
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "300")),
    "connect_args": connect_args,
}

if pool_mode == "null":
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "5"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    engine_kwargs["pool_timeout"] = int(os.getenv("DB_POOL_TIMEOUT", "30"))

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
        
# if bad record mac use this to complete shutdown the pooling (SSL/EOF)
# import os
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.pool import NullPool

# DATABASE_URL = os.getenv(
#     "DATABASE_URL",
#     "postgresql://neondb_owner:npg_r69uJkgvYBpW@ep-still-field-abm8djij-pooler.eu-west-2.aws.neon.tech/abc?sslmode=require&channel_binding=require"
# )

# if DATABASE_URL.startswith("postgres://"):
#     DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# if "sslmode=" not in DATABASE_URL:
#     separator = "&" if "?" in DATABASE_URL else "?"
#     DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"

# engine = create_engine(
#     DATABASE_URL,
#     poolclass=NullPool,
# )

# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine,
# )

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
