from fastapi import FastAPI
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from core.observability import install_observability
from routes import auth, booking, chat, crash_reports, notifications, posts, profile, search, service, setup_profile, users

app = FastAPI(docs_url=None)  # Disable default Swagger UI
install_observability(app)
BASE_DIR = Path(__file__).resolve().parent

# Mount static files for assets (user images, etc.)
# app.mount("/assets", StaticFiles(directory="assets"), name="abc_files")

# Mount static files for Swagger UI (downloaded locally)
app.mount("/swagger", StaticFiles(directory=BASE_DIR / "swagger_static"), name="swagger_files")


# ----------------------------
# CORS Middleware
# ----------------------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

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

# Temporary compatibility for older app builds and deep links.
# Keep these out of OpenAPI so /api/v1 is the documented contract.
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
