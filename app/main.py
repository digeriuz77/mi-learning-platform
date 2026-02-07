"""
MI Learning Platform - FastAPI Main Application
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Configure logging first
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import settings with error handling
try:
    from app.config import settings
except Exception as e:
    logger.error(f"Failed to load settings: {e}")

    # Create minimal settings for startup
    class MinimalSettings:
        APP_NAME = "MI Learning Platform"
        APP_VERSION = "1.0.0"

    settings = MinimalSettings()

# Import routers
try:
    from app.api.v1 import (
        auth,
        modules,
        dialogue,
        progress,
        leaderboard,
        chat_practice,
        admin,
        feedback,
        report_export,
    )

    ROUTERS_LOADED = True
except Exception as e:
    logger.error(f"Failed to load routers: {e}")
    ROUTERS_LOADED = False

# Create FastAPI app
app = FastAPI(
    title=getattr(settings, "APP_NAME", "MI Learning Platform"),
    version=getattr(settings, "APP_VERSION", "1.0.0"),
    description="MI Learning Platform API",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all exceptions"""
    logger.error(f"Error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"error": str(exc), "type": type(exc).__name__}
    )


# Include API routers
if ROUTERS_LOADED:
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(modules.router, prefix="/api/v1/modules", tags=["Modules"])
    app.include_router(dialogue.router, prefix="/api/v1/dialogue", tags=["Dialogue"])
    app.include_router(progress.router, prefix="/api/v1/progress", tags=["Progress"])
    app.include_router(
        leaderboard.router, prefix="/api/v1/leaderboard", tags=["Leaderboard"]
    )
    app.include_router(chat_practice.router, prefix="/api/v1", tags=["Chat Practice"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
    app.include_router(report_export.router, prefix="/api/v1", tags=["Export"])

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Setup templates
templates = None
templates_dir = Path(__file__).parent.parent / "templates"
if templates_dir.exists():
    templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/")
async def root(request: Request):
    """Root endpoint - serve the frontend HTML"""
    if templates:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "supabase_url": getattr(settings, "SUPABASE_URL", ""),
                "supabase_anon_key": getattr(settings, "SUPABASE_KEY", ""),
            },
        )
    # Fallback to JSON if templates not found
    return {
        "name": getattr(settings, "APP_NAME", "MI Learning Platform"),
        "version": getattr(settings, "APP_VERSION", "1.0.0"),
        "status": "running",
        "docs": "/docs",
    }


@app.get("/admin")
async def admin_dashboard(request: Request):
    """Admin dashboard endpoint - serve the admin HTML with Supabase config"""
    if templates:
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "supabase_url": getattr(settings, "SUPABASE_URL", ""),
                "supabase_anon_key": getattr(settings, "SUPABASE_KEY", ""),
            },
        )
    return {"error": "Templates not configured"}


@app.get("/reset-password")
async def reset_password_page(request: Request):
    """Password reset page - serves the SPA for password reset flow"""
    if templates:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "supabase_url": getattr(settings, "SUPABASE_URL", ""),
                "supabase_anon_key": getattr(settings, "SUPABASE_KEY", ""),
            },
        )
    return {"error": "Templates not configured"}


@app.get("/health")
async def health_check():
    """Basic health check for Railway"""
    return {"status": "healthy"}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including Supabase connectivity"""
    from app.core.supabase import get_supabase, get_supabase_admin
    from app.config import settings

    health = {
        "status": "healthy",
        "app": {
            "name": getattr(settings, "APP_NAME", "MI Learning Platform"),
            "version": getattr(settings, "APP_VERSION", "1.0.0"),
        },
        "config": {
            "supabase_url_set": bool(getattr(settings, "SUPABASE_URL", None)),
            "supabase_key_set": bool(getattr(settings, "SUPABASE_KEY", None)),
            "service_role_set": bool(
                getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
            ),
        },
    }

    try:
        client = get_supabase()
        # Try a simple query
        response = client.table("learning_modules").select("id").limit(1).execute()
        health["supabase"] = {
            "status": "connected",
            "modules_count": len(response.data) if response.data else 0,
        }
    except Exception as e:
        health["supabase"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"

    return health


@app.on_event("startup")
async def startup():
    """Startup event"""
    app_name = getattr(settings, "APP_NAME", "MI Learning Platform")
    app_version = getattr(settings, "APP_VERSION", "1.0.0")
    logger.info(f"🚀 {app_name} v{app_version} started")
    logger.info(f"Routers loaded: {ROUTERS_LOADED}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
