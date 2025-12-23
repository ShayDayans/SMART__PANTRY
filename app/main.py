"""
FastAPI main application
"""
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

logger.info("Starting application...")
logger.info(f"Supabase URL: {settings.supabase_url}")

try:
    from app.api import inventory, products, receipts, shopping_lists, habits, predictor, auth
    logger.info("All API modules imported successfully")
except Exception as e:
    logger.error(f"Error importing API modules: {e}")
    raise

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Smart Pantry API using Supabase",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
try:
    logger.info("Including routers...")
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(inventory.router, prefix=settings.api_prefix)
    app.include_router(products.router, prefix=settings.api_prefix)
    app.include_router(receipts.router, prefix=settings.api_prefix)
    app.include_router(shopping_lists.router, prefix=settings.api_prefix)
    app.include_router(habits.router, prefix=settings.api_prefix)
    app.include_router(predictor.router, prefix=settings.api_prefix)
    logger.info("All routers included successfully")
except Exception as e:
    logger.error(f"Error including routers: {e}")
    raise


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Smart Pantry API",
        "version": settings.api_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

