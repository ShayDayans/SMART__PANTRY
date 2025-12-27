"""
Recipe generation service using OpenAI GPT
"""
from typing import List, Optional, Dict, Any
from openai import OpenAI
import os
import json


class RecipeService:
    """Service for generating recipes using OpenAI GPT"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception:
            # Fallback for newer OpenAI versions
            import openai
            openai.api_key = self.api_key
            self.client = openai
    
    def generate_recipe(
        self,
        available_products: List[Dict[str, Any]],
        meal_type: str,
        cuisine_style: Optional[str] = None,
        servings: int = 4,
        dietary_preferences: Optional[List[str]] = None,
        cooking_time: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a recipe based on available products and user preferences.
        
        Args:
            available_products: List of products from inventory with their names
            meal_type: Type of meal (e.g., "dinner", "breakfast", "lunch")
            cuisine_style: Cuisine style (e.g., "Italian", "Asian", "Mediterranean")
            servings: Number of servings
            dietary_preferences: List of dietary preferences (e.g., ["vegetarian", "gluten-free"])
            cooking_time: Preferred cooking time (e.g., "30 minutes", "1 hour")
            difficulty: Difficulty level (e.g., "easy", "medium", "hard")
        
        Returns:
            Dictionary containing recipe details
        """
        # Build product list string
        product_names = [p.get("product_name", p.get("displayed_name", "")) for p in available_products if p.get("state") != "EMPTY"]
        product_list = ", ".join(product_names) if product_names else "No products available"
        
        # Build prompt with strict ingredient selection
        prompt = f"""You are a professional chef. Create a detailed recipe for {meal_type} using ONLY RELEVANT ingredients from the user's pantry.

Available ingredients in pantry: {product_list}

IMPORTANT RULES:
1. Select ONLY ingredients that make sense for the recipe type and cuisine style
2. Do NOT include ingredients that don't fit the recipe (e.g., don't add chocolate to pasta, don't add yogurt to a main course unless it's a yogurt-based dish)
3. Choose ingredients that complement each other and create a cohesive dish
4. If there aren't enough suitable ingredients, suggest a recipe that uses the most relevant ones and mention what additional ingredients might be needed
5. Focus on creating a REALISTIC and TASTY recipe, not a random combination

Requirements:
- Meal type: {meal_type}
- Number of servings: {servings}
"""
        
        if cuisine_style:
            prompt += f"- Cuisine style: {cuisine_style}\n"
        
        if dietary_preferences:
            prompt += f"- Dietary preferences: {', '.join(dietary_preferences)}\n"
        
        if cooking_time:
            prompt += f"- Preferred cooking time: {cooking_time}\n"
        
        if difficulty:
            prompt += f"- Difficulty level: {difficulty}\n"
        
        prompt += """
Please provide a complete recipe in JSON format with the following structure:
{
  "title": "Recipe title",
  "description": "Brief description of the recipe",
  "servings": number,
  "prep_time": "preparation time in minutes",
  "cook_time": "cooking time in minutes",
  "total_time": "total time in minutes",
  "difficulty": "easy/medium/hard",
  "ingredients": [
    {
      "name": "ingredient name",
      "amount": "quantity (e.g., '2 cups', '1 tbsp', '3 pieces')",
      "notes": "optional notes"
    }
  ],
  "instructions": [
    "Step 1 description",
    "Step 2 description",
    ...
  ],
  "tips": [
    "Optional tip 1",
    "Optional tip 2"
  ],
  "nutrition_info": {
    "calories_per_serving": number,
    "protein": "amount in grams",
    "carbs": "amount in grams",
    "fat": "amount in grams"
  }
}

CRITICAL INSTRUCTIONS:
- Select ONLY ingredients that logically fit together for this type of recipe
- Do NOT force ingredients that don't belong (e.g., don't add dessert items to main courses, don't add breakfast items to dinner unless they make sense)
- Create a COHERENT recipe that makes culinary sense
- If the available ingredients don't work well together, choose the most suitable subset and create a recipe that makes sense
- Quality over quantity: Better to use 3-4 well-matched ingredients than 10 random ones
- Make sure the recipe is practical, achievable, and actually tastes good
- Provide clear, step-by-step instructions
- Include helpful tips if relevant
- If you need to suggest additional ingredients not in the pantry, list them separately in a "suggested_additional_ingredients" field
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional chef and recipe creator. Always respond with valid JSON only, no additional text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON (might be wrapped in markdown code blocks)
            if content.startswith("```"):
                # Remove markdown code blocks
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            
            if content.startswith("```json"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            
            recipe_data = json.loads(content)
            
            # Add metadata
            recipe_data["generated_at"] = "now"
            recipe_data["meal_type"] = meal_type
            recipe_data["cuisine_style"] = cuisine_style
            recipe_data["servings"] = servings
            recipe_data["dietary_preferences"] = dietary_preferences or []
            
            return recipe_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from GPT response: {e}")
            print(f"Response content: {content[:500]}")
            raise ValueError(f"Failed to parse recipe from GPT response: {str(e)}")
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            raise ValueError(f"Failed to generate recipe: {str(e)}")

