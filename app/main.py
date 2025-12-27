"""
FastAPI main application
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

logger.info("Starting application...")
logger.info(f"Supabase URL: {settings.supabase_url}")

try:
    from app.api import inventory, products, receipts, shopping_lists, habits, predictor, auth, recipes
    logger.info("All API modules imported successfully")
except Exception as e:
    logger.error(f"Error importing API modules: {e}")
    raise


async def run_daily_weekly_updates():
    """
    Background task that runs daily and updates products based on their creation day.
    Each product is updated on the same day of the week it was created (based on first inventory_log entry).
    """
    from app.services.predictor_service import PredictorService
    from app.db.supabase_client import get_supabase
    
    # Wait 5 seconds after startup before first run
    await asyncio.sleep(5)
    
    while True:
        try:
            now = datetime.now(timezone.utc)
            current_weekday = now.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday
            current_hour = now.hour
            current_minute = now.minute
            
            # Run at 00:00 every day
            if current_hour == 0 and current_minute == 0:
                logger.info(f"[WEEKLY UPDATE] Running daily weekly update check for weekday {current_weekday} ({['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][current_weekday]})")
                
                supabase = get_supabase()
                service = PredictorService(supabase)
                
                # Get all users
                users_result = supabase.table("users").select("user_id").execute()
                if not users_result.data:
                    logger.info("[WEEKLY UPDATE] No users found")
                    # Sleep for 24 hours minus 1 minute
                    await asyncio.sleep(24 * 60 * 60 - 60)
                    continue
                
                updated_count = 0
                skipped_count = 0
                
                for user_row in users_result.data:
                    user_id = user_row["user_id"]
                    try:
                        # Get all products for this user
                        products = service.repo.get_user_inventory_products(str(user_id))
                        
                        for product_id, category_id in products:
                            try:
                                # Get the first inventory_log entry for this product (creation date)
                                first_log = supabase.table("inventory_log").select("occurred_at").eq(
                                    "user_id", str(user_id)
                                ).eq("product_id", str(product_id)).order(
                                    "occurred_at", desc=False
                                ).limit(1).execute()
                                
                                if not first_log.data:
                                    # No log entry - skip this product
                                    skipped_count += 1
                                    continue
                                
                                # Get creation date
                                created_at_str = first_log.data[0].get("occurred_at")
                                if not created_at_str:
                                    skipped_count += 1
                                    continue
                                
                                # Parse creation date
                                try:
                                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                                    created_weekday = created_at.weekday()
                                    
                                    # Check if today is the same weekday as creation
                                    if current_weekday == created_weekday:
                                        logger.info(f"[WEEKLY UPDATE] Updating product {product_id} for user {user_id} (created on {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][created_weekday]})")
                                        service.weekly_model_update(str(user_id), str(product_id))
                                        updated_count += 1
                                    else:
                                        skipped_count += 1
                                except (ValueError, AttributeError) as e:
                                    logger.warning(f"[WEEKLY UPDATE] Could not parse date for product {product_id}: {e}")
                                    skipped_count += 1
                                    continue
                                    
                            except Exception as e:
                                logger.error(f"[WEEKLY UPDATE] Error updating product {product_id} for user {user_id}: {e}")
                                import traceback
                                traceback.print_exc()
                                continue
                                
                    except Exception as e:
                        logger.error(f"[WEEKLY UPDATE] Error processing user {user_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                logger.info(f"[WEEKLY UPDATE] Completed: {updated_count} products updated, {skipped_count} products skipped")
                
                # Sleep for 24 hours minus 1 minute to avoid running multiple times
                await asyncio.sleep(24 * 60 * 60 - 60)
            else:
                # Not 00:00 yet, calculate seconds until next midnight
                seconds_until_midnight = (24 - current_hour) * 3600 - current_minute * 60 - now.second
                # Sleep until 1 minute before midnight, then check every minute
                if seconds_until_midnight > 60:
                    await asyncio.sleep(seconds_until_midnight - 60)
                else:
                    await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"[WEEKLY UPDATE] Error in daily weekly update task: {e}")
            import traceback
            traceback.print_exc()
            # Sleep for 1 hour before retrying
            await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Starts background task on startup and stops it on shutdown.
    """
    # Startup: Start background task
    logger.info("Starting background weekly update task...")
    task = asyncio.create_task(run_daily_weekly_updates())
    
    yield
    
    # Shutdown: Cancel task
    logger.info("Stopping background weekly update task...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Background weekly update task cancelled successfully")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Smart Pantry API using Supabase",
    lifespan=lifespan,
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
    app.include_router(recipes.router, prefix=settings.api_prefix)
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

