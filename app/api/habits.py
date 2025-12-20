"""
Habits API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
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
    user_id: UUID,
    type: Optional[HabitType] = None,
    status: Optional[HabitStatus] = None,
    service: HabitService = Depends(get_habit_service)
):
    """Get all habits for a user"""
    habits = service.get_habits(str(user_id), type, status)
    return habits


@router.get("/preferences", response_model=dict)
def get_user_preferences(
    user_id: UUID,
    service: HabitService = Depends(get_habit_service)
):
    """Get aggregated user preferences from habits"""
    preferences = service.get_user_preferences(str(user_id))
    return preferences


@router.get("/{habit_id}", response_model=HabitResponse)
def get_habit(
    user_id: UUID,
    habit_id: UUID,
    service: HabitService = Depends(get_habit_service)
):
    """Get a specific habit by ID"""
    habit = service.get_habit(str(habit_id), str(user_id))
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(
    user_id: UUID,
    habit: HabitCreate,
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
    user_id: UUID,
    habit_id: UUID,
    habit: HabitUpdate,
    service: HabitService = Depends(get_habit_service)
):
    """Update a habit"""
    updated_habit = service.update_habit(str(habit_id), str(user_id), habit)
    if not updated_habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return updated_habit


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(
    user_id: UUID,
    habit_id: UUID,
    service: HabitService = Depends(get_habit_service)
):
    """Delete a habit"""
    success = service.delete_habit(str(habit_id), str(user_id))
    if not success:
        raise HTTPException(status_code=404, detail="Habit not found")
    return None


@router.post("/inputs", response_model=HabitInputResponse, status_code=status.HTTP_201_CREATED)
def create_habit_input(
    user_id: UUID,
    habit_input: HabitInputCreate,
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
    user_id: UUID,
    habit_id: Optional[UUID] = None,
    service: HabitService = Depends(get_habit_service)
):
    """Get all habit inputs for a user"""
    habit_id_str = str(habit_id) if habit_id else None
    inputs = service.get_habit_inputs(str(user_id), habit_id_str)
    return inputs


@router.post("/chat", response_model=ChatResponse)
def chat_with_llm(
    user_id: UUID,
    message: ChatMessage,
    service: HabitService = Depends(get_habit_service)
):
    """
    Chat with LLM to parse user input and extract habit information.
    This endpoint simulates LLM parsing - in production, integrate with actual LLM API.
    """
    # TODO: Integrate with actual LLM (OpenAI, Anthropic, etc.)
    # For now, return a mock response
    
    import re
    from app.models.enums import HabitInputSource
    
    user_text = message.message.lower()
    extracted_data = {}
    suggested_habits = []
    
    # Simple keyword-based parsing (replace with actual LLM)
    if "אנשים" in user_text or "בית" in user_text:
        # Try to extract number
        numbers = re.findall(r'\d+', user_text)
        if numbers:
            extracted_data["household_size"] = int(numbers[0])
    
    if "קניות" in user_text:
        if "ראשון" in user_text:
            extracted_data["preferred_shopping_day"] = "ראשון"
        elif "שני" in user_text:
            extracted_data["preferred_shopping_day"] = "שני"
        elif "שלישי" in user_text:
            extracted_data["preferred_shopping_day"] = "שלישי"
        elif "רביעי" in user_text:
            extracted_data["preferred_shopping_day"] = "רביעי"
        elif "חמישי" in user_text:
            extracted_data["preferred_shopping_day"] = "חמישי"
        elif "שישי" in user_text:
            extracted_data["preferred_shopping_day"] = "שישי"
        elif "שבת" in user_text:
            extracted_data["preferred_shopping_day"] = "שבת"
    
    if "צמחונות" in user_text or "צמחוני" in user_text:
        extracted_data.setdefault("dietary_preferences", []).append("צמחונות")
    if "טבעונות" in user_text or "טבעוני" in user_text:
        extracted_data.setdefault("dietary_preferences", []).append("טבעונות")
    if "כשר" in user_text:
        extracted_data.setdefault("dietary_preferences", []).append("כשר")
    
    # Save the chat input
    habit_input = HabitInputCreate(
        source=HabitInputSource.CHAT,
        raw_text=message.message,
        extracted_json=extracted_data if extracted_data else None
    )
    
    try:
        service.create_habit_input(str(user_id), habit_input)
    except Exception as e:
        pass  # Log error but don't fail the request
    
    # Generate response
    response_text = "תודה על המידע! עדכנתי את ההעדפות שלך."
    if extracted_data:
        response_text += " זיהיתי: " + ", ".join([f"{k}: {v}" for k, v in extracted_data.items()])
    
    return ChatResponse(
        response=response_text,
        extracted_data=extracted_data if extracted_data else None,
        suggested_habits=suggested_habits
    )

