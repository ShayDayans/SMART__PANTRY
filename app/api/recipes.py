"""
Recipes API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from supabase import Client

from app.db.supabase_client import get_supabase
from app.core.dependencies import get_current_user_id
from app.core.config import settings
from app.services.recipe_service import RecipeService
from app.services.inventory_service import InventoryService
from app.services.predictor_service import PredictorService
from app.schemas.inventory import InventoryLogCreate
from app.models.enums import InventoryAction, InventorySource, InventoryState

router = APIRouter(prefix="/recipes", tags=["recipes"])


class RecipeRequest(BaseModel):
    meal_type: str = Field(..., description="Type of meal (e.g., 'dinner', 'breakfast', 'lunch')")
    cuisine_style: Optional[str] = Field(None, description="Cuisine style (e.g., 'Italian', 'Asian', 'Mediterranean')")
    servings: int = Field(4, ge=1, le=20, description="Number of servings")
    dietary_preferences: Optional[List[str]] = Field(None, description="Dietary preferences (e.g., ['vegetarian', 'gluten-free'])")
    cooking_time: Optional[str] = Field(None, description="Preferred cooking time (e.g., '30 minutes', '1 hour')")
    difficulty: Optional[str] = Field(None, description="Difficulty level (e.g., 'easy', 'medium', 'hard')")


class RecipeIngredientUsage(BaseModel):
    ingredient_name: str = Field(..., description="Name of the ingredient used")
    amount_used: Optional[float] = Field(None, description="Amount used (if known)")
    step_index: int = Field(..., description="Step number where ingredient was used")


class RecipeStepCompleteRequest(BaseModel):
    recipe_id: Optional[str] = Field(None, description="Recipe identifier")
    step_index: int = Field(..., description="Step number that was completed")
    ingredients_used: Optional[List[RecipeIngredientUsage]] = Field(None, description="Ingredients used in this step")


def get_recipe_service() -> RecipeService:
    """Dependency to get recipe service"""
    openai_api_key = settings.openai_api_key
    if not openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key is not configured. Please set OPENAI_API_KEY in your .env file or environment variables."
        )
    return RecipeService(openai_api_key)


def get_inventory_service(supabase: Client = Depends(get_supabase)) -> InventoryService:
    """Dependency to get inventory service"""
    return InventoryService(supabase)


def get_predictor_service(supabase: Client = Depends(get_supabase)) -> PredictorService:
    """Dependency to get predictor service"""
    return PredictorService(supabase)


@router.post("/generate")
def generate_recipe(
    request: RecipeRequest,
    user_id: UUID = Depends(get_current_user_id),
    recipe_service: RecipeService = Depends(get_recipe_service),
    supabase: Client = Depends(get_supabase)
):
    """
    Generate a recipe based on user's available inventory and preferences.
    """
    try:
        # Get user's inventory
        inventory_service = InventoryService(supabase)
        inventory_response = inventory_service.get_inventory(user_id)
        
        # Filter out empty products and format for recipe service
        available_products = []
        for item in inventory_response:
            if item.get("state") != "EMPTY":
                product_info = {
                    "product_id": item.get("product_id"),
                    "product_name": item.get("products", {}).get("product_name") if isinstance(item.get("products"), dict) else item.get("displayed_name") or "Unknown",
                    "displayed_name": item.get("displayed_name"),
                    "state": item.get("state"),
                    "estimated_qty": item.get("estimated_qty")
                }
                available_products.append(product_info)
        
        if not available_products:
            raise HTTPException(
                status_code=400,
                detail="No available products in your pantry. Please add items to your pantry first."
            )
        
        # Generate recipe
        recipe = recipe_service.generate_recipe(
            available_products=available_products,
            meal_type=request.meal_type,
            cuisine_style=request.cuisine_style,
            servings=request.servings,
            dietary_preferences=request.dietary_preferences,
            cooking_time=request.cooking_time,
            difficulty=request.difficulty
        )
        
        return recipe
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error generating recipe: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recipe: {str(e)}")


@router.post("/step-complete")
def recipe_step_complete(
    request: RecipeStepCompleteRequest,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    inventory_service: InventoryService = Depends(get_inventory_service),
    predictor_service: PredictorService = Depends(get_predictor_service),
    supabase: Client = Depends(get_supabase)
):
    """
    Handle recipe step completion and update inventory/model.
    This creates inventory log entries for ingredient usage and updates the predictor model.
    """
    try:
        # Get user's inventory to find products
        inventory_response = inventory_service.get_inventory(user_id)
        inventory_map = {}
        for item in inventory_response:
            product_name = item.get("products", {}).get("product_name") if isinstance(item.get("products"), dict) else item.get("displayed_name") or ""
            if product_name:
                inventory_map[product_name.lower()] = item
        
        # Process each ingredient used
        log_ids = []
        
        if request.ingredients_used:
            for ingredient_usage in request.ingredients_used:
                ingredient_name = ingredient_usage.ingredient_name
                ingredient_name_lower = ingredient_name.lower().strip()
                
                # Find matching product in inventory
                matching_item = None
                for name, item in inventory_map.items():
                    if ingredient_name_lower in name or name in ingredient_name_lower:
                        matching_item = item
                        break
                
                if not matching_item or not matching_item.get("product_id"):
                    print(f"Warning: Could not find product '{ingredient_name}' in inventory")
                    continue
                
                product_id = matching_item.get("product_id")
                current_qty = matching_item.get("estimated_qty") or 0
                
                # Calculate new quantity (reduce by amount used or proportionally)
                if ingredient_usage.amount_used is not None:
                    new_qty = max(0, current_qty - ingredient_usage.amount_used)
                else:
                    # Default: reduce by 10% per step (simplified)
                    new_qty = max(0, current_qty * 0.9)
                
                # Determine new state
                if new_qty <= 0:
                    new_state = InventoryState.EMPTY
                elif new_qty < current_qty * 0.3:
                    new_state = InventoryState.LOW
                elif new_qty < current_qty * 0.7:
                    new_state = InventoryState.MEDIUM
                else:
                    new_state = InventoryState.FULL
                
                # Create inventory log entry for consumption
                log_create = InventoryLogCreate(
                    product_id=UUID(product_id),
                    action=InventoryAction.ADJUST,
                    delta_state=new_state,
                    action_confidence=0.9,
                    source=InventorySource.RECIPE,
                    note=f"Recipe step {request.step_index + 1}: Used {ingredient_name}"
                )
                
                try:
                    log_entry = inventory_service.create_inventory_log(user_id, log_create)
                    
                    if log_entry:
                        log_id = log_entry.get("log_id")
                        if log_id:
                            log_ids.append(str(log_id))
                            
                            # Update inventory quantity
                            from app.schemas.inventory import InventoryUpdate
                            inventory_update = InventoryUpdate(
                                estimated_qty=new_qty,
                                state=new_state,
                                last_source=InventorySource.RECIPE
                            )
                            inventory_service.update_inventory(user_id, UUID(product_id), inventory_update, log_change=False)
                            
                            # Process log to update predictor model
                            background_tasks.add_task(
                                predictor_service.process_inventory_log,
                                log_id=str(log_id)
                            )
                except Exception as e:
                    print(f"Error processing ingredient {ingredient_name}: {e}")
        
        return {
            "message": f"Step {request.step_index + 1} completed",
            "log_ids": log_ids,
            "ingredients_updated": len(log_ids)
        }
        
    except Exception as e:
        print(f"Error in recipe_step_complete: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process step completion: {str(e)}")
