"""
Main FastAPI application
Personal Learning Agent API
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import sentry_sdk

from backend.core.config import settings
from backend.db import init_databases, close_databases


# Initialize Sentry if configured
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Personal Learning Agent API...")
    await init_databases()
    print("✅ Databases initialized")

    yield

    # Shutdown
    print("👋 Shutting down...")
    await close_databases()
    print("✅ Databases closed")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered personal learning assistant with adaptive micro-learning sessions",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Import and include routers
from backend.api.routers import auth_router, users_router, sessions_router, progress_router, content_router

app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users_router.router, prefix="/api/users", tags=["Users"])
app.include_router(sessions_router.router, prefix="/api/sessions", tags=["Learning Sessions"])
app.include_router(progress_router.router, prefix="/api/progress", tags=["Progress & Analytics"])
app.include_router(content_router.router, prefix="/api/content", tags=["Content & Problems"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    if settings.DEBUG:
        raise exc

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "server_error"
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Personal Learning Agent API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.API_WORKERS
    )
