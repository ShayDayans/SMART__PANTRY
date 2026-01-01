"""
Habits API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
from app.core.dependencies import get_current_user_id
from app.services.habit_service import HabitService
from app.schemas.habit import (
    HabitCreate, HabitResponse, HabitUpdate,
    HabitInputCreate, HabitInputResponse,
    ChatMessage, ChatResponse
)
from app.models.enums import HabitType, HabitStatus

router = APIRouter(prefix="/habits", tags=["habits"])


def get_habit_service(supabase: Client = Depends(get_supabase)) -> HabitService:
    """Dependency to get habit service"""
    return HabitService(supabase)


@router.get("", response_model=List[HabitResponse])
def get_habits(
    type: Optional[HabitType] = Query(None, description="Filter by habit type"),
    status: Optional[HabitStatus] = Query(None, description="Filter by habit status"),
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service)
):
    """Get all habits for a user"""
    habits = service.get_habits(str(user_id), type, status)
    return habits


@router.get("/preferences", response_model=dict)
def get_user_preferences(
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service)
):
    """Get aggregated user preferences from habits"""
    preferences = service.get_user_preferences(str(user_id))
    return preferences


@router.get("/{habit_id}", response_model=HabitResponse)
def get_habit(
    habit_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service)
):
    """Get a specific habit by ID"""
    habit = service.get_habit(str(habit_id), str(user_id))
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(
    habit: HabitCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
    supabase: Client = Depends(get_supabase)
):
    """Create a new habit"""
    try:
        created_habit = service.create_habit(str(user_id), habit)
        
        # If habit is ACTIVE and has effects, refresh predictions for affected products
        if habit.status == HabitStatus.ACTIVE and habit.effects:
            try:
                from app.services.predictor_service import PredictorService
                predictor_service = PredictorService(supabase)
                predictor_service.refresh_products_affected_by_habit(
                    str(user_id),
                    habit.effects,
                    is_deletion=False
                )
            except Exception as e:
                import logging
                logging.error(f"Error refreshing predictions after habit creation: {e}")
                # Don't fail the request if prediction refresh fails
        
        return created_habit
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: UUID,
    habit: HabitUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service)
):
    """Update a habit"""
    updated_habit = service.update_habit(str(habit_id), str(user_id), habit)
    if not updated_habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return updated_habit


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(
    habit_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
    supabase: Client = Depends(get_supabase)
):
    """Delete a habit and refresh predictions for affected products"""
    import logging
    
    # Get the habit first to retrieve its effects before deletion
    habit = service.get_habit(str(habit_id), str(user_id))
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    
    # Store effects before deletion
    habit_effects = habit.get("effects") or {}
    habit_status = habit.get("status")
    
    logging.info(f"Deleting habit {habit_id} (status: {habit_status}, has_effects: {bool(habit_effects)})")
    
    # Delete the habit
    success = service.delete_habit(str(habit_id), str(user_id))
    if not success:
        # Verify if it still exists
        still_exists = service.get_habit(str(habit_id), str(user_id))
        if still_exists:
            logging.error(f"Failed to delete habit {habit_id} - habit still exists in database with status: {still_exists.get('status')}")
            raise HTTPException(status_code=500, detail="Failed to delete habit. The habit may be referenced by other records.")
        else:
            # Habit doesn't exist, might have been deleted already
            raise HTTPException(status_code=404, detail="Habit not found")
    
    logging.info(f"Successfully deleted habit {habit_id}")
    
    # Refresh predictions for products affected by this habit
    # This recalculates using current DB state (without the deleted habit)
    if habit_effects:
        try:
            from app.services.predictor_service import PredictorService
            predictor_service = PredictorService(supabase)
            
            logging.info(f"Refreshing predictions for products affected by deleted habit {habit_id}")
            predictor_service.refresh_products_affected_by_habit(
                str(user_id),
                habit_effects,
                is_deletion=True
            )
            logging.info(f"Successfully refreshed predictions after deleting habit {habit_id}")
        except Exception as e:
            logging.error(f"Error refreshing predictions after habit deletion: {e}", exc_info=True)
            # Don't fail the request if prediction refresh fails, but log it for debugging
    else:
        logging.info(f"No effects to refresh for habit {habit_id}")
    
    return None


@router.post("/inputs", response_model=HabitInputResponse, status_code=status.HTTP_201_CREATED)
def create_habit_input(
    habit_input: HabitInputCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service)
):
    """Create a new habit input (chat message)"""
    try:
        created_input = service.create_habit_input(str(user_id), habit_input)
        return created_input
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inputs", response_model=List[HabitInputResponse])
def get_habit_inputs(
    habit_id: Optional[UUID] = Query(None, description="Optional habit ID to filter inputs"),
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service)
):
    """Get all habit inputs for a user"""
    habit_id_str = str(habit_id) if habit_id else None
    inputs = service.get_habit_inputs(str(user_id), habit_id_str)
    return inputs


@router.post("/chat", response_model=ChatResponse)
def chat_with_llm(
    message: ChatMessage,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
    supabase: Client = Depends(get_supabase)
):
    """
    Chat with GPT to parse user input and extract habit information.
    Also provides insights to update the predictor model.
    """
    from app.core.config import settings
    from app.services.habit_chat_service import HabitChatService
    from app.models.enums import HabitInputSource, HabitType, HabitStatus
    from app.services.predictor_service import PredictorService
    from app.services.inventory_service import InventoryService
    from datetime import datetime, timezone
    
    # Initialize GPT service
    openai_api_key = settings.openai_api_key
    if not openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key is not configured. Please set OPENAI_API_KEY in your .env file."
        )
    
    chat_service = HabitChatService(openai_api_key)
    
    # Conversation history disabled - each message is processed independently
    conversation_history = []
    
    # Get current user preferences
    try:
        user_preferences = service.get_user_preferences(str(user_id))
    except Exception:
        user_preferences = {}
    
    # Get inventory summary for context
    try:
        inventory_service = InventoryService(supabase)
        inventory = inventory_service.get_inventory(user_id)
        
        # Get all available categories (not just user's inventory)
        all_categories_result = supabase.table("product_categories").select("category_name").order("category_name").execute()
        all_categories = [cat["category_name"] for cat in (all_categories_result.data or [])]
        
        # Get product names from user's inventory
        product_names = []
        if inventory:
            product_names = [
                item.get("products", {}).get("product_name") 
                for item in inventory 
                if item.get("products", {}).get("product_name")
            ]
            product_names = list(set([p for p in product_names if p]))  # Remove duplicates and None
        
        inventory_summary = {
            "total_items": len(inventory),
            "user_categories": list(set([
                item.get("products", {}).get("category_name", "Unknown")
                if isinstance(item.get("products"), dict)
                else "Unknown"
                for item in inventory
            ])),
            "all_available_categories": all_categories,  # All categories in system
            "user_products": product_names[:50]  # User's products (limit to avoid token limits)
        }
    except Exception:
        inventory_summary = {}
    
    # Call GPT
    try:
        gpt_response = chat_service.chat_with_user(
            user_message=message.message,
            conversation_history=conversation_history,
            user_preferences=user_preferences,
            user_inventory_summary=inventory_summary
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get response from GPT: {str(e)}"
        )
    
    extracted_data = gpt_response.get("extracted_data", {})
    model_insights = gpt_response.get("model_insights", {})
    suggested_habits = gpt_response.get("suggested_habits", [])
    
    # Save the chat input with full GPT response
    full_extracted_data = {
        "extracted_data": extracted_data,
        "model_insights": model_insights
    }
    
    habit_input = HabitInputCreate(
        source=HabitInputSource.CHAT,
        raw_text=message.message,
        extracted_json=full_extracted_data if full_extracted_data else None
    )
    
    try:
        service.create_habit_input(str(user_id), habit_input)
    except Exception as e:
        pass  # Log error but don't fail the request
    
    # Initialize predictor service for refreshing predictions
    from app.services.predictor_service import PredictorService
    predictor_service = PredictorService(supabase)
    
    # Create suggested habits if any
    created_habits = []
    for suggested_habit in suggested_habits:
        try:
            # Convert product/category names to IDs in effects
            effects = suggested_habit.get("effects", {})
            converted_effects = {}
            
            # Convert product names to product IDs
            product_multipliers = effects.get("product_multipliers", {})
            if product_multipliers:
                converted_product_multipliers = {}
                for product_name, multiplier in product_multipliers.items():
                    # Find product by name
                    products_result = supabase.table("products").select("product_id").ilike(
                        "product_name", f"%{product_name}%"
                    ).limit(1).execute()
                    
                    if products_result.data:
                        product_id = products_result.data[0]["product_id"]
                        converted_product_multipliers[str(product_id)] = multiplier
                    else:
                        import logging
                        logging.warning(f"Product '{product_name}' not found, skipping from habit effects")
                
                if converted_product_multipliers:
                    converted_effects["product_multipliers"] = converted_product_multipliers
            
            # Convert category names to category IDs (with fallback to product lookup)
            category_multipliers = effects.get("category_multipliers", {})
            if category_multipliers:
                converted_category_multipliers = {}
                converted_product_multipliers_from_category = {}  # For fallback
                
                for category_name, multiplier in category_multipliers.items():
                    # First try to find as category
                    categories_result = supabase.table("product_categories").select("category_id").ilike(
                        "category_name", f"%{category_name}%"
                    ).limit(1).execute()
                    
                    if categories_result.data:
                        category_id = categories_result.data[0]["category_id"]
                        converted_category_multipliers[str(category_id)] = multiplier
                    else:
                        # Fallback: try to find as product
                        products_result = supabase.table("products").select("product_id").ilike(
                            "product_name", f"%{category_name}%"
                        ).limit(1).execute()
                        
                        if products_result.data:
                            product_id = products_result.data[0]["product_id"]
                            converted_product_multipliers_from_category[str(product_id)] = multiplier
                            import logging
                            logging.info(f"Category '{category_name}' not found, but found as product - using product_multiplier instead")
                        else:
                            import logging
                            logging.warning(f"Neither category nor product '{category_name}' found, skipping from habit effects")
                
                if converted_category_multipliers:
                    converted_effects["category_multipliers"] = converted_category_multipliers
                
                # Merge any product multipliers from category fallback
                if converted_product_multipliers_from_category:
                    if "product_multipliers" not in converted_effects:
                        converted_effects["product_multipliers"] = {}
                    converted_effects["product_multipliers"].update(converted_product_multipliers_from_category)
            
            # Add global_multiplier if present
            if effects.get("global_multiplier") is not None:
                converted_effects["global_multiplier"] = effects["global_multiplier"]
            
            # Only create habit if we have valid effects after conversion
            if not converted_effects:
                import logging
                logging.warning(f"Skipping habit '{suggested_habit.get('name')}' - no valid effects after conversion")
                continue
            
            habit_create = HabitCreate(
                type=HabitType(suggested_habit.get("type", "OTHER")),
                status=HabitStatus.ACTIVE,
                name=suggested_habit.get("name"),
                explanation=suggested_habit.get("description", ""),
                effects=converted_effects,  # Use converted effects
                params={}
            )
            created_habit = service.create_habit(str(user_id), habit_create)
            created_habits.append(created_habit)
            
            # Refresh predictions for products affected by this habit
            if habit_create.effects:
                try:
                    predictor_service.refresh_products_affected_by_habit(
                        str(user_id),
                        habit_create.effects,
                        is_deletion=False
                    )
                except Exception as e:
                    import logging
                    logging.error(f"Error refreshing predictions after suggested habit creation: {e}")
        except Exception as e:
            import logging
            logging.error(f"Error creating suggested habit: {e}", exc_info=True)
            pass  # Log error but don't fail
    
    return ChatResponse(
        response=gpt_response.get("response", "I've updated your preferences."),
        extracted_data=extracted_data if extracted_data else None,
        suggested_habits=[h.get("habit_id") for h in created_habits] if created_habits else []
    )

