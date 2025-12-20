"""
Pydantic schemas for Habits
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.enums import HabitType, HabitStatus, HabitInputSource


class HabitParams(BaseModel):
    """Structured parameters for habits"""
    household_size: Optional[int] = None
    preferred_shopping_day: Optional[str] = None  # יום בשבוע
    shopping_frequency: Optional[str] = None  # יומי/שבועי/דו-שבועי/חודשי
    cooking_frequency: Optional[str] = None  # יומי/שבועי/דו-שבועי/חודשי
    dietary_preferences: Optional[List[str]] = None  # צמחונות, טבעונות, כשר, וכו'
    excluded_categories: Optional[List[str]] = None  # קטגוריות שלא נאכלות
    notes: Optional[str] = None


class HabitCreate(BaseModel):
    """Schema for creating a habit"""
    type: HabitType = HabitType.OTHER
    status: HabitStatus = HabitStatus.ACTIVE
    explanation: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    effects: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class HabitUpdate(BaseModel):
    """Schema for updating a habit"""
    type: Optional[HabitType] = None
    status: Optional[HabitStatus] = None
    explanation: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    effects: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class HabitResponse(BaseModel):
    """Schema for habit response"""
    habit_id: str
    user_id: str
    type: HabitType
    status: HabitStatus
    explanation: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    effects: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HabitInputCreate(BaseModel):
    """Schema for creating a habit input (chat message)"""
    habit_id: Optional[str] = None
    source: HabitInputSource = HabitInputSource.CHAT
    raw_text: str
    extracted_json: Optional[Dict[str, Any]] = None


class HabitInputResponse(BaseModel):
    """Schema for habit input response"""
    habit_input_id: str
    user_id: str
    habit_id: Optional[str] = None
    source: HabitInputSource
    raw_text: str
    extracted_json: Optional[Dict[str, Any]] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    """Schema for chat message"""
    message: str
    user_id: str


class ChatResponse(BaseModel):
    """Schema for chat response"""
    response: str
    extracted_data: Optional[Dict[str, Any]] = None
    suggested_habits: Optional[List[Dict[str, Any]]] = None

