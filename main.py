from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from routes import auth, booking, posts, profile, search, service, setup_profile, users
from core.database import engine
from models.base import Base

app = FastAPI(docs_url=None)  # Disable default Swagger UI

# Mount static files for assets (user images, etc.)
app.mount("/assets", StaticFiles(directory="assets"), name="abc_files")

# Mount static files for Swagger UI (downloaded locally)
app.mount("/swagger", StaticFiles(directory="swagger_static"), name="swagger_files")


# ----------------------------
# Routers
# ----------------------------
app.include_router(auth.auth)
app.include_router(setup_profile.setup)
app.include_router(service.service)
app.include_router(posts.posts)
app.include_router(users.users)
app.include_router(profile.profile)
app.include_router(search.search)
app.include_router(booking.booking)


# ----------------------------
# Swagger UI (Offline Version)
# ----------------------------
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Africa Beauty API Docs",
        swagger_js_url="/swagger/swagger-ui-bundle.js",
        swagger_css_url="/swagger/swagger-ui.css",
    )


# ----------------------------
# Database
# ----------------------------
Base.metadata.create_all(engine)
