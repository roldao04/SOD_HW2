"""
Main FastAPI application for E-Procurement NLP Chatbot.
Provides natural language query creation and analytics capabilities.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys

from src.api.config import settings
from src.api.dependencies import (
    get_llm_service,
    get_dremio_client,
    cleanup_resources
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting E-Procurement Chatbot API...")

    try:
        # Initialize LLM service (loads models)
        logger.info("Loading LLM models...")
        llm_service = get_llm_service()
        await llm_service.initialize()
        logger.info("LLM models loaded successfully")

        # Test Dremio connection
        logger.info("Testing Dremio connection...")
        dremio_client = get_dremio_client()
        if dremio_client.test_connection():
            logger.info("Dremio connection successful")
        else:
            logger.warning("Dremio connection failed - some features may not work")

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Continue anyway - some features might still work

    yield

    # Shutdown
    logger.info("Shutting down E-Procurement Chatbot API...")
    cleanup_resources()
    logger.info("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="""
    NLP-powered chatbot for European procurement data analysis.

    Features:
    - Natural language to SQL query generation
    - Automated analytics and insights
    - Interactive data exploration
    """,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )


# Health check endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns system status and service availability.
    """
    try:
        llm_service = get_llm_service()
        dremio_client = get_dremio_client()

        return {
            "status": "ok",
            "api_version": settings.API_VERSION,
            "services": {
                "llm_models_loaded": llm_service.is_initialized(),
                "dremio_connected": dremio_client.test_connection(),
            },
            "models": {
                "query_creator": settings.QUERY_CREATOR_MODEL,
                "analytics": settings.ANALYTICS_MODEL,
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": str(e)
            }
        )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "E-Procurement NLP Chatbot API",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/api/health"
    }


# Import and include routers
from src.api.routes import chat, schema

app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(schema.router, prefix="/api", tags=["Schema"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )
