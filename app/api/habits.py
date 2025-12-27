"""
Habits API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
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
    type: Optional[HabitType] = None,
    status: Optional[HabitStatus] = None,
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
    service: HabitService = Depends(get_habit_service)
):
    """Create a new habit"""
    try:
        created_habit = service.create_habit(str(user_id), habit)
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
    service: HabitService = Depends(get_habit_service)
):
    """Delete a habit"""
    success = service.delete_habit(str(habit_id), str(user_id))
    if not success:
        raise HTTPException(status_code=404, detail="Habit not found")
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
    habit_id: Optional[UUID] = None,
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
    
    # Get conversation history
    try:
        previous_inputs = service.get_habit_inputs(str(user_id))
        conversation_history = []
        for inp in previous_inputs[-10:]:  # Last 10 messages
            if inp.get("raw_text"):
                conversation_history.append({"role": "user", "content": inp["raw_text"]})
            if inp.get("extracted_json"):
                # Add assistant response based on extracted data
                conversation_history.append({
                    "role": "assistant",
                    "content": f"I've updated your preferences based on: {inp.get('raw_text', '')}"
                })
    except Exception as e:
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
        inventory_summary = {
            "total_items": len(inventory),
            "categories": list(set([
                item.get("products", {}).get("category_name", "Unknown")
                if isinstance(item.get("products"), dict)
                else "Unknown"
                for item in inventory
            ]))
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
    consumption_patterns = gpt_response.get("consumption_patterns", [])
    model_insights = gpt_response.get("model_insights", {})
    suggested_habits = gpt_response.get("suggested_habits", [])
    
    # Save the chat input with full GPT response
    full_extracted_data = {
        "extracted_data": extracted_data,
        "consumption_patterns": consumption_patterns,
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
    
    # Create suggested habits if any
    created_habits = []
    for suggested_habit in suggested_habits:
        try:
            habit_create = HabitCreate(
                type=HabitType(suggested_habit.get("type", "OTHER")),
                status=HabitStatus.ACTIVE,
                explanation=suggested_habit.get("description", ""),
                effects=suggested_habit.get("effects", {}),
                params={}
            )
            created_habit = service.create_habit(str(user_id), habit_create)
            created_habits.append(created_habit)
        except Exception as e:
            pass  # Log error but don't fail
    
    # Apply model insights to update predictor (if any)
    predictor_service = PredictorService(supabase)
    try:
        if model_insights.get("suggested_adjustments"):
            for adjustment in model_insights["suggested_adjustments"]:
                product_name = adjustment.get("product_name")
                suggested_multiplier = adjustment.get("suggested_multiplier")
                
                if product_name and suggested_multiplier:
                    # Find product by name
                    products_result = supabase.table("products").select("product_id").ilike(
                        "product_name", f"%{product_name}%"
                    ).limit(1).execute()
                    
                    if products_result.data:
                        product_id = products_result.data[0]["product_id"]
                        # Update habit multiplier for this product
                        # This will be applied through get_active_habit_multiplier
                        # For now, we create a habit with product-specific multiplier
                        habit_create = HabitCreate(
                            type=HabitType.OTHER,
                            status=HabitStatus.ACTIVE,
                            explanation=f"AI-suggested adjustment for {product_name}: {adjustment.get('reason', '')}",
                            effects={
                                "product_multipliers": {
                                    str(product_id): suggested_multiplier
                                }
                            },
                            params={}
                        )
                        try:
                            service.create_habit(str(user_id), habit_create)
                        except Exception:
                            pass
    except Exception as e:
        pass  # Log error but don't fail
    
    return ChatResponse(
        response=gpt_response.get("response", "I've updated your preferences."),
        extracted_data=extracted_data if extracted_data else None,
        suggested_habits=[h.get("habit_id") for h in created_habits] if created_habits else []
    )

