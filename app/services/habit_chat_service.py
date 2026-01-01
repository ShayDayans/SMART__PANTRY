"""
Habit Chat Service using OpenAI GPT
Extracts user preferences and consumption patterns from natural language
"""
from typing import List, Optional, Dict, Any
from openai import OpenAI
import os
import json
import logging

logger = logging.getLogger(__name__)


class HabitChatService:
    """Service for chatting with GPT to extract habits and preferences"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            # Fallback for newer OpenAI versions (should not be needed with openai>=1.55.3)
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def chat_with_user(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        user_inventory_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Chat with GPT to extract user preferences and consumption patterns.
        
        Args:
            user_message: User's message
            conversation_history: Previous messages in the conversation
            user_preferences: Current user preferences (to provide context)
            user_inventory_summary: Summary of user's inventory (to provide context)
        
        Returns:
            Dictionary containing:
            - response: GPT's response text
            - extracted_data: Extracted preferences/patterns
            - suggested_habits: Suggested habits to create
            - model_insights: Insights that can update the predictor model
        """
        
        # Build system prompt
        system_prompt = """You are a helpful AI assistant for a smart pantry management system. 
Your role is to:
1. Extract user preferences and habits from natural language
2. Understand consumption patterns
3. Suggest improvements to the user's pantry management
4. Provide insights that can help improve the AI prediction model

IMPORTANT: Extract ALL information you can find, even if it's implicit. For example:
- "we are 4 people" → household_size: 4
- "I shop every Sunday" → preferred_shopping_day: "Sunday", shopping_frequency: "weekly"
- "we don't eat meat" → excluded_categories: ["meat"], dietary_preferences: ["vegetarian"]

Extract information about:
- Household size (look for numbers + "people", "family", "household")
- Shopping frequency and preferred days (look for "shop", "buy", "grocery", days of week)
- Cooking frequency (look for "cook", "prepare meals", "kitchen")
- Dietary preferences (vegetarian, vegan, kosher, halal, etc.)
- Excluded food categories (meat, dairy, gluten, etc.)
- Special events or habits that affect consumption

Return your response in JSON format with the following structure (ALL fields are required, use null for missing values):
{
  "response": "Your friendly response to the user acknowledging what you learned",
  "extracted_data": {
    "household_size": number or null,
    "preferred_shopping_day": "Monday" or null,
    "shopping_frequency": "weekly" or null,
    "cooking_frequency": "daily" or null,
    "dietary_preferences": ["vegetarian", "kosher", ...] or [],
    "excluded_categories": ["meat", "dairy", ...] or [],
    "notes": "Any additional notes" or null
  },
  "model_insights": {
    "new_habits": [
      {
        "name": "Short, user-friendly name (e.g., 'Weekly Shopping', 'Vegetarian Diet', 'Sunday Meal Prep')",
        "type": "DIET" or "HOUSEHOLD" or "SHOPPING_SCHEDULE" or "OTHER",
        "description": "Detailed explanation of the habit",
        "effects": {
          "product_multipliers": {"product_name": multiplier} or {},
          "category_multipliers": {"category_name": multiplier} or {},
          "global_multiplier": number or null
        }
      }
    ]
  }
}

IMPORTANT: 
- new_habits: This is the ONLY way to create habits. When suggesting habits, always include a concise "name" field (2-4 words) that clearly identifies the habit. The name should be user-friendly and descriptive (e.g., "Weekly Shopping", "Vegetarian Diet", "Sunday Meal Prep", "High Protein Intake"). The "description" field should contain more detailed explanation.
- Use new_habits for ALL habit creation - whether it's a dietary preference, consumption pattern, or any other habit that affects product consumption.
- effects in new_habits:
  * product_multipliers: Use product NAMES (e.g., "milk", "bread"), NOT product IDs. Use names from the user's inventory if available (see user_products in context).
  * category_multipliers: Use category NAMES (e.g., "Dairy", "Bakery"), NOT category IDs. Only use categories that exist in the system (see all_available_categories in context). If a name is not in all_available_categories, it's likely a product, not a category.
  * The system will automatically convert these names to IDs. If a name doesn't exist, that effect will be skipped.
  * When in doubt whether something is a product or category, check the all_available_categories list in the context. If it's not there, it's likely a product."""
        
        # Build user context
        context_parts = []
        
        if user_preferences:
            context_parts.append(f"Current user preferences: {json.dumps(user_preferences, indent=2)}")
        
        if user_inventory_summary:
            context_parts.append(f"Inventory summary: {json.dumps(user_inventory_summary, indent=2)}")
        
        context = "\n\n".join(context_parts) if context_parts else "No previous context available."
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"User context:\n{context}"}
        ]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            logger.info(f"GPT raw response: {response_text}")
            
            parsed_response = json.loads(response_text)
            logger.info(f"GPT parsed response: {json.dumps(parsed_response, indent=2)}")
            
            # Extract data
            extracted_data = parsed_response.get("extracted_data", {}) or {}
            model_insights = parsed_response.get("model_insights", {}) or {}
            gpt_response = parsed_response.get("response", "I've updated your preferences.")
            
            logger.info(f"Final extracted_data: {extracted_data}")
            logger.info(f"Final model_insights: {model_insights}")
            
            return {
                "response": gpt_response,
                "extracted_data": extracted_data,
                "model_insights": model_insights,
                "suggested_habits": model_insights.get("new_habits", [])
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from GPT response: {e}")
            logger.error(f"Response text: {response_text}")
            # Fallback: return basic response
            return {
                "response": "I understand. Let me help you update your preferences.",
                "extracted_data": {},
                "model_insights": {},
                "suggested_habits": []
            }
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise ValueError(f"Failed to get response from GPT: {str(e)}")

