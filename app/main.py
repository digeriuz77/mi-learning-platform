"""
MI Learning Platform - FastAPI Main Application

A gamified learning platform for Motivational Interviewing techniques.
Built with FastAPI and Supabase.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi import Request

from app.config import settings
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

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    # If directories don't exist yet, continue without them
    templates = None

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["Modules"])
app.include_router(dialogue.router, prefix="/api/v1/dialogue", tags=["Dialogue"])
app.include_router(progress.router, prefix="/api/v1/progress", tags=["Progress"])
app.include_router(leaderboard.router, prefix="/api/v1/leaderboard", tags=["Leaderboard"])


# Root endpoint
@app.get("/")
async def root():
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
    """Health check endpoint"""
    return {"status": "healthy"}


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
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting up...")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"🎯 API v1 Prefix: {settings.API_V1_PREFIX}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print(f"👋 {settings.APP_NAME} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
