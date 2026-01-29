"""
MI Learning Platform - FastAPI Main Application

A gamified learning platform for Motivational Interviewing techniques.
Built with FastAPI and Supabase.
"""
import os
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi import Request

from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Log startup configuration
logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
logger.info(f"Debug mode: {settings.DEBUG}")
logger.info(f"CORS origins: {settings.CORS_ORIGINS}")
logger.info(f"Supabase URL configured: {bool(settings.SUPABASE_URL)}")

# Import routers after config is validated
from app.api.v1 import auth, modules, dialogue, progress, leaderboard

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A gamified learning platform for Motivational Interviewing techniques"
)

# Configure CORS
# Note: When using "*" for origins, credentials must be False
# This is fine for JWT-based auth (tokens in headers, not cookies)
allow_all_origins = "*" in settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else settings.CORS_ORIGINS,
    allow_credentials=not allow_all_origins,  # Can't use credentials with "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files - use absolute path for Docker
templates = None
static_dir = Path(__file__).parent.parent / "static"
templates_dir = Path(__file__).parent.parent / "templates"

if static_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"Static files mounted from {static_dir}")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")

if templates_dir.exists():
    try:
        templates = Jinja2Templates(directory=str(templates_dir))
        logger.info(f"Templates loaded from {templates_dir}")
    except Exception as e:
        logger.warning(f"Could not load templates: {e}")

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["Modules"])
app.include_router(dialogue.router, prefix="/api/v1/dialogue", tags=["Dialogue"])
app.include_router(progress.router, prefix="/api/v1/progress", tags=["Progress"])
app.include_router(leaderboard.router, prefix="/api/v1/leaderboard", tags=["Leaderboard"])


# Root endpoint - serve frontend if available, otherwise API info
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - serve frontend or API info"""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "message": "MI Learning Platform API",
            "docs": "/docs",
            "api_v1": settings.API_V1_PREFIX
        }


@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "MI Learning Platform API",
        "docs": "/docs",
        "api_v1": settings.API_V1_PREFIX
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration (non-sensitive)"""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "cors_origins": settings.CORS_ORIGINS,
        "supabase_url_set": bool(settings.SUPABASE_URL),
        "supabase_key_set": bool(settings.SUPABASE_KEY),
        "supabase_service_key_set": bool(settings.SUPABASE_SERVICE_ROLE_KEY),
        "jwt_secret_set": bool(settings.SUPABASE_JWT_SECRET),
        "static_dir_exists": static_dir.exists(),
        "templates_dir_exists": templates_dir.exists()
    }


# Serve frontend (if templates exist)
if templates:
    @app.get("/app", response_class=HTMLResponse)
    async def serve_frontend(request: Request):
        """Serve the frontend application"""
        return templates.TemplateResponse("index.html", {"request": request})


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started successfully")
    logger.info(f"📚 API Documentation available at /docs")
    logger.info(f"🔧 Debug config available at /debug/config")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info(f"👋 {settings.APP_NAME} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
