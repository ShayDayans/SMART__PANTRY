"""
Script to update predictor configuration for more responsive MORE/LESS buttons
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_KEY environment variables")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# NEW CONFIGURATION - More responsive to MORE/LESS clicks
new_config = {
    "category_priors": {},
    "alpha_strong": 0.25,      # Keep same - strong observations (EMPTY)
    "alpha_weak": 0.30,        # CHANGED: 0.10 -> 0.30 (3x more responsive!)
    "alpha_confirm": 0.05,     # Keep same
    "min_cycle_days": 1.0,
    "max_cycle_days": 90.0,
    
    # MORE/LESS impact - DOUBLED!
    "more_less_ratio": 0.30,          # CHANGED: 0.15 -> 0.30 (30% instead of 15%)
    "more_less_step_cap_days": 7.0,   # CHANGED: 3.0 -> 7.0 (bigger max step)
    
    "full_ratio": 0.70,
    "medium_ratio": 0.30,
    "recency_tau_days": 21.0,
}

# Update all active predictor profiles
try:
    result = supabase.table("predictor_profiles").select("*").eq("is_active", True).execute()
    
    if result.data:
        for profile in result.data:
            profile_id = profile["predictor_profile_id"]
            print(f"Updating profile: {profile_id}")
            
            supabase.table("predictor_profiles").update({
                "config": new_config
            }).eq("predictor_profile_id", profile_id).execute()
            
            print(f"✅ Updated profile {profile_id}")
    else:
        print("No active profiles found. Creating default profile...")
        # Create a default profile for demonstration
        supabase.table("predictor_profiles").insert({
            "name": "Responsive Profile",
            "method": "EMA",
            "config": new_config,
            "is_active": True,
        }).execute()
        print("✅ Created new default profile")
        
    print("\n🎯 Configuration updated successfully!")
    print("\nChanges:")
    print("- alpha_weak: 0.10 → 0.30 (3x faster learning from MORE/LESS)")
    print("- more_less_ratio: 0.15 → 0.30 (2x bigger impact per click)")
    print("- more_less_step_cap_days: 3.0 → 7.0 (bigger maximum change)")
    print("\nExample impact (product with 10 days forecast):")
    print("- Before: MORE/LESS = ±0.15 days (barely noticeable)")
    print("- After:  MORE/LESS = ±0.9 days (3 clicks = ±2.7 days!)")
    
except Exception as e:
    print(f"ERROR: {e}")

