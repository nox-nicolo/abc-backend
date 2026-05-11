from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from alembic.config import Config
from alembic import command
import logging

from core.observability import install_observability
from routes import auth, booking, chat, crash_reports, notifications, posts, profile, search, service, setup_profile, users

logger = logging.getLogger(__name__)

def run_migrations():
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise  # re-raise so Render knows the startup failed

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield

app = FastAPI(docs_url=None, lifespan=lifespan)
install_observability(app)

# Mount static files for Swagger UI (downloaded locally)
app.mount("/swagger", StaticFiles(directory="swagger_static"), name="swagger_files")

# ----------------------------
# Routers
# ----------------------------
API_V1_PREFIX = "/api/v1"
API_ROUTERS = (
    auth.auth,
    setup_profile.setup,
    service.service,
    posts.posts,
    users.users,
    profile.profile,
    search.search,
    booking.booking,
    notifications.notifications,
    chat.chat,
    crash_reports.crash_reports,
)

for router in API_ROUTERS:
    app.include_router(router, prefix=API_V1_PREFIX)

for router in API_ROUTERS:
    app.include_router(router, include_in_schema=False)

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