"""
Service layer for Habits operations using Supabase API
"""
from typing import List, Optional, Dict, Any
from supabase import Client
from app.schemas.habit import HabitCreate, HabitUpdate, HabitInputCreate
from app.models.enums import HabitType, HabitStatus, HabitInputSource


class HabitService:
    """Service for managing habits"""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    def create_habit(self, user_id: str, habit: HabitCreate) -> Dict[str, Any]:
        """Create a new habit"""
        data = {
            "user_id": user_id,
            "type": habit.type.value,
            "status": habit.status.value,
            "explanation": habit.explanation,
            "params": habit.params or {},
            "effects": habit.effects or {},
        }
        if habit.start_date:
            data["start_date"] = habit.start_date.isoformat()
        if habit.end_date:
            data["end_date"] = habit.end_date.isoformat()

        result = self.supabase.table("habits").insert(data).execute()
        if result.data:
            return result.data[0]
        raise Exception("Failed to create habit")

    def get_habits(self, user_id: str, type: Optional[HabitType] = None, status: Optional[HabitStatus] = None) -> List[Dict[str, Any]]:
        """Get all habits for a user"""
        query = self.supabase.table("habits").select("*").eq("user_id", user_id)
        
        if type:
            query = query.eq("type", type.value)
        if status:
            query = query.eq("status", status.value)
        
        result = query.execute()
        return result.data or []

    def get_habit(self, habit_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific habit by ID"""
        result = self.supabase.table("habits").select("*").eq("habit_id", habit_id).eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
        return None

    def update_habit(self, habit_id: str, user_id: str, habit: HabitUpdate) -> Optional[Dict[str, Any]]:
        """Update a habit"""
        data = {}
        if habit.type is not None:
            data["type"] = habit.type.value
        if habit.status is not None:
            data["status"] = habit.status.value
        if habit.explanation is not None:
            data["explanation"] = habit.explanation
        if habit.params is not None:
            data["params"] = habit.params
        if habit.effects is not None:
            data["effects"] = habit.effects
        if habit.start_date is not None:
            data["start_date"] = habit.start_date.isoformat()
        if habit.end_date is not None:
            data["end_date"] = habit.end_date.isoformat()

        data["updated_at"] = "now()"

        result = self.supabase.table("habits").update(data).eq("habit_id", habit_id).eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
        return None

    def delete_habit(self, habit_id: str, user_id: str) -> bool:
        """Delete a habit"""
        result = self.supabase.table("habits").delete().eq("habit_id", habit_id).eq("user_id", user_id).execute()
        return len(result.data) > 0

    def create_habit_input(self, user_id: str, habit_input: HabitInputCreate) -> Dict[str, Any]:
        """Create a new habit input (chat message)"""
        data = {
            "user_id": user_id,
            "source": habit_input.source.value,
            "raw_text": habit_input.raw_text,
            "extracted_json": habit_input.extracted_json or {},
        }
        if habit_input.habit_id:
            data["habit_id"] = habit_input.habit_id

        result = self.supabase.table("habit_inputs").insert(data).execute()
        if result.data:
            return result.data[0]
        raise Exception("Failed to create habit input")

    def get_habit_inputs(self, user_id: str, habit_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all habit inputs for a user"""
        query = self.supabase.table("habit_inputs").select("*").eq("user_id", user_id)
        
        if habit_id:
            query = query.eq("habit_id", habit_id)
        
        result = query.order("created_at", desc=True).execute()
        return result.data or []

    def confirm_habit_input(self, habit_input_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Confirm a habit input (mark as confirmed)"""
        from datetime import datetime
        result = self.supabase.table("habit_inputs").update({
            "confirmed_at": datetime.utcnow().isoformat()
        }).eq("habit_input_id", habit_input_id).eq("user_id", user_id).execute()
        
        if result.data:
            return result.data[0]
        return None

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences from habits (aggregated)"""
        habits = self.get_habits(user_id, status=HabitStatus.ACTIVE)
        
        preferences = {
            "household_size": None,
            "preferred_shopping_day": None,
            "shopping_frequency": None,
            "cooking_frequency": None,
            "dietary_preferences": [],
            "excluded_categories": [],
            "notes": None,
        }
        
        # Aggregate preferences from all active habits
        for habit in habits:
            if habit.get("params"):
                params = habit["params"]
                if "household_size" in params and preferences["household_size"] is None:
                    preferences["household_size"] = params["household_size"]
                if "preferred_shopping_day" in params and preferences["preferred_shopping_day"] is None:
                    preferences["preferred_shopping_day"] = params["preferred_shopping_day"]
                if "shopping_frequency" in params and preferences["shopping_frequency"] is None:
                    preferences["shopping_frequency"] = params["shopping_frequency"]
                if "cooking_frequency" in params and preferences["cooking_frequency"] is None:
                    preferences["cooking_frequency"] = params["cooking_frequency"]
                if "dietary_preferences" in params:
                    preferences["dietary_preferences"].extend(params["dietary_preferences"])
                if "excluded_categories" in params:
                    preferences["excluded_categories"].extend(params["excluded_categories"])
                if "notes" in params and preferences["notes"] is None:
                    preferences["notes"] = params["notes"]
        
        # Remove duplicates
        preferences["dietary_preferences"] = list(set(preferences["dietary_preferences"]))
        preferences["excluded_categories"] = list(set(preferences["excluded_categories"]))
        
        return preferences

