"""
Predictor service using Supabase API - adapts the EMA cycle predictor model
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from supabase import Client
from app.schemas.inventory import InventoryLogCreate
from app.models.enums import InventoryState, InventorySource, InventoryAction

# Import predictor modules (we'll adapt them to work with Supabase)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from ema_cycle_predictor import (
        PredictorConfig, CycleEmaState, Forecast,
        init_state_from_category, apply_purchase, apply_feedback,
        predict, stamp_last_prediction, map_inventory_log_row_to_event,
        InventoryState as PredInventoryState, InventorySource as PredInventorySource,
        InventoryAction as PredInventoryAction, FeedbackKind
    )
    PREDICTOR_AVAILABLE = True
except ImportError:
    PREDICTOR_AVAILABLE = False
    print("Warning: Predictor modules not available. Install required dependencies.")


def get_default_category_priors_by_name() -> Dict[str, Dict[str, float]]:
    """
    Returns default category priors (mean_days, mad_days) by category name.
    These are used for new users before they have personalized data.
    
    Priors are based on typical consumption patterns:
    - mean_days: Average days until product runs out
    - mad_days: Mean Absolute Deviation (variability)
    """
    return {
        "Dairy & Eggs": {"mean_days": 5.0, "mad_days": 2.0},  # נגמר מהר
        "Bread & Bakery": {"mean_days": 4.0, "mad_days": 1.5},  # נגמר מהר מאוד
        "Meat & Poultry": {"mean_days": 4.0, "mad_days": 2.0},  # נגמר מהר
        "Fish & Seafood": {"mean_days": 3.0, "mad_days": 1.5},  # נגמר מהר מאוד
        "Fruits": {"mean_days": 6.0, "mad_days": 2.5},  # בינוני
        "Vegetables": {"mean_days": 5.0, "mad_days": 2.0},  # בינוני
        "Grains & Pasta": {"mean_days": 35.0, "mad_days": 10.0},  # נשמר הרבה זמן
        "Canned & Jarred": {"mean_days": 75.0, "mad_days": 15.0},  # נשמר הרבה זמן
        "Condiments & Sauces": {"mean_days": 45.0, "mad_days": 15.0},  # נשמר זמן
        "Snacks": {"mean_days": 10.0, "mad_days": 5.0},  # בינוני
        "Beverages": {"mean_days": 7.0, "mad_days": 3.0},  # בינוני
        "Frozen Foods": {"mean_days": 45.0, "mad_days": 15.0},  # נשמר זמן
        "Spices & Seasonings": {"mean_days": 75.0, "mad_days": 20.0},  # נשמר הרבה זמן
    }


class SupabasePantryRepository:
    """
    Adapter that makes Supabase client work like the PostgreSQL repository
    expected by the predictor service
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def _get_default_category_priors(self) -> Dict[str, Dict[str, float]]:
        """
        Get default category priors mapped by category_id.
        Loads all categories from DB and maps them to default priors by name.
        """
        try:
            # Get all categories from database
            categories_result = self.supabase.table("product_categories").select("category_id, category_name").execute()
            categories = categories_result.data if categories_result.data else []
            
            # Get default priors by name
            name_priors = get_default_category_priors_by_name()
            
            # Map category_id to priors
            category_priors = {}
            for cat in categories:
                category_name = cat.get("category_name", "")
                category_id = str(cat.get("category_id", ""))
                
                # Find matching prior by category name (case-insensitive)
                prior = None
                for name, prior_data in name_priors.items():
                    if name.lower() == category_name.lower():
                        prior = prior_data
                        break
                
                # If no match found, use default
                if prior is None:
                    prior = {"mean_days": 7.0, "mad_days": 2.0}
                
                category_priors[category_id] = prior
            
            return category_priors
        except Exception as e:
            print(f"Warning: Could not load category priors: {e}")
            # Return empty dict - will use default in init_state_from_category
            return {}
    
    def get_active_predictor_profile(self, user_id: str) -> Dict[str, Any]:
        """Get active predictor profile for user"""
        result = self.supabase.table("predictor_profiles").select("*").eq("user_id", user_id).eq("is_active", True).limit(1).execute()
        if not result.data:
            # Create default profile with category priors for all existing categories
            category_priors = self._get_default_category_priors()
            
            default_config = {
                "category_priors": category_priors,
                "alpha_strong": 0.25,
                "alpha_weak": 0.10,
                "alpha_confirm": 0.05,
                "min_cycle_days": 1.0,
                "max_cycle_days": 90.0,
                "more_less_ratio": 0.15,
                "more_less_step_cap_days": 3.0,
                "full_ratio": 0.70,
                "medium_ratio": 0.30,
                "recency_tau_days": 21.0,
            }
            result = self.supabase.table("predictor_profiles").insert({
                "user_id": user_id,
                "name": "Default Profile",
                "method": "EMA",
                "config": default_config,
                "is_active": True,
            }).execute()
        return result.data[0]
    
    def get_user_inventory_products(self, user_id: str) -> List[tuple]:
        """Get (product_id, category_id) for all products in user's inventory"""
        result = self.supabase.table("inventory").select("product_id, products(category_id)").eq("user_id", user_id).execute()
        products = []
        for item in result.data:
            product_id = item["product_id"]
            category_id = item.get("products", {}).get("category_id") if isinstance(item.get("products"), dict) else None
            products.append((product_id, category_id))
        return products
    
    def get_predictor_state(self, user_id: str, product_id: str) -> Optional[tuple]:
        """Get predictor state: (params_json, confidence, updated_at, predictor_profile_id)"""
        result = self.supabase.table("product_predictor_state").select("*").eq("user_id", user_id).eq("product_id", product_id).execute()
        if not result.data:
            return None
        row = result.data[0]
        return (row.get("params") or {}, float(row.get("confidence", 0.0)), row.get("updated_at"), row.get("predictor_profile_id"))
    
    def upsert_predictor_state(
        self,
        user_id: str,
        product_id: str,
        predictor_profile_id: str,
        params: Dict[str, Any],
        confidence: float,
        updated_at: datetime,
    ) -> None:
        """Upsert predictor state"""
        data = {
            "user_id": user_id,
            "product_id": product_id,
            "predictor_profile_id": predictor_profile_id,
            "params": params,
            "confidence": confidence,
            "updated_at": updated_at.isoformat(),
        }
        self.supabase.table("product_predictor_state").upsert(data, on_conflict="user_id,product_id").execute()
    
    def upsert_inventory_days_estimate(
        self,
        user_id: str,
        product_id: str,
        days_left: float,
        state: InventoryState,
        confidence: float,
        source: InventorySource = InventorySource.SYSTEM,
        displayed_name: Optional[str] = None,
    ) -> None:
        """Update inventory with days estimate"""
        data = {
            "user_id": user_id,
            "product_id": product_id,
            "state": state.value,
            "estimated_qty": days_left,
            "qty_unit": "days",
            "confidence": confidence,
            "last_source": source.value,
        }
        if displayed_name:
            data["displayed_name"] = displayed_name
        self.supabase.table("inventory").upsert(data, on_conflict="user_id,product_id").execute()
    
    def insert_forecast(
        self,
        user_id: str,
        product_id: str,
        forecast: 'Forecast',
        trigger_log_id: Optional[str],
    ) -> None:
        """Insert forecast snapshot"""
        data = {
            "user_id": user_id,
            "product_id": product_id,
            "generated_at": forecast.generated_at.isoformat(),
            "expected_days_left": forecast.expected_days_left,
            "predicted_state": forecast.predicted_state.value,
            "confidence": forecast.confidence,
            "trigger_log_id": trigger_log_id,
        }
        self.supabase.table("inventory_forecasts").insert(data).execute()
    
    def get_inventory_log_row(self, log_id: str) -> Dict[str, Any]:
        """Get inventory log row"""
        result = self.supabase.table("inventory_log").select("*").eq("log_id", log_id).execute()
        if not result.data:
            raise RuntimeError(f"inventory_log row not found for log_id={log_id}")
        row = result.data[0]
        return {
            "log_id": row["log_id"],
            "user_id": row["user_id"],
            "product_id": row["product_id"],
            "action": row["action"],
            "delta_state": row.get("delta_state"),
            "action_confidence": float(row.get("action_confidence", 1.0)),
            "occurred_at": row["occurred_at"],
            "source": row["source"],
            "note": row.get("note"),
        }
    
    def get_active_habit_multiplier(self, user_id: str, product_id: str, category_id: Optional[str], now: datetime) -> float:
        """Get habit multiplier from active habits"""
        try:
            result = self.supabase.table("habits").select("effects").eq("user_id", user_id).eq("status", "ACTIVE").execute()
        except Exception as e:
            # If there's a network error or any other issue, return default multiplier
            print(f"Warning: Could not fetch habits for multiplier calculation: {e}")
            return 1.0
        
        mult = 1.0
        pid = str(product_id)
        cid = str(category_id) if category_id else None
        
        if not result.data:
            return 1.0
        
        for row in result.data:
            effects = row.get("effects") or {}
            if not isinstance(effects, dict):
                continue
            
            try:
                gm = effects.get("global_multiplier")
                if gm is not None:
                    mult *= float(gm)
                
                pm = effects.get("product_multipliers") or {}
                if pid in pm:
                    mult *= float(pm[pid])
                
                if cid:
                    cm = effects.get("category_multipliers") or {}
                    if cid in cm:
                        mult *= float(cm[cid])
            except Exception:
                continue
        
        return float(max(mult, 1e-6))


class PredictorService:
    """Service for running predictions using the EMA cycle predictor"""
    
    def __init__(self, supabase: Client):
        if not PREDICTOR_AVAILABLE:
            raise RuntimeError("Predictor modules not available")
        self.repo = SupabasePantryRepository(supabase)
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Recursively convert UUID objects and other non-serializable types to strings"""
        from uuid import UUID
        
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._make_json_serializable(item) for item in obj)
        elif isinstance(obj, (datetime,)):
            return obj.isoformat()
        else:
            return obj
    
    def _load_cfg_and_profile(self, user_id: str) -> tuple:
        """Load config and profile"""
        prof = self.repo.get_active_predictor_profile(user_id)
        cfg = PredictorConfig.from_profile_config_json(prof.get("config") or {})
        return prof["predictor_profile_id"], cfg
    
    def _load_or_init_state(
        self,
        user_id: str,
        product_id: str,
        predictor_profile_id: str,
        cfg: PredictorConfig,
        category_id: Optional[str],
        now: datetime,
    ) -> CycleEmaState:
        """Load or initialize predictor state"""
        row = self.repo.get_predictor_state(user_id, product_id)
        if row is None:
            st = init_state_from_category(category_id, cfg, now=now)
            st.category_id = str(category_id) if category_id else None
            return st
        
        params_json, _conf, _updated_at, _ppid = row
        st = CycleEmaState.from_params_json(params_json)
        if st.category_id is None and category_id is not None:
            st.category_id = str(category_id)
        return st
    
    def process_inventory_log(self, log_id: str) -> None:
        """Process inventory log event and update predictions"""
        row = self.repo.get_inventory_log_row(log_id)
        user_id = row["user_id"]
        product_id = row["product_id"]
        now = datetime.now(timezone.utc)
        
        predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)
        
        products = dict(self.repo.get_user_inventory_products(user_id))
        category_id = products.get(product_id)
        
        state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
        
        purchase_ev, feedback_ev = map_inventory_log_row_to_event(row)
        
        if purchase_ev is not None:
            state = apply_purchase(state, purchase_ev)
        
        if feedback_ev is not None:
            state = apply_feedback(state, feedback_ev, cfg)
        
        mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
        fc = predict(state, now, mult, cfg)
        
        state = stamp_last_prediction(state, fc)
        
        # Convert params to JSON-serializable format
        params_json = state.to_params_json()
        params_json = self._make_json_serializable(params_json)
        
        self.repo.upsert_predictor_state(
            user_id=user_id,
            product_id=product_id,
            predictor_profile_id=predictor_profile_id,
            params=params_json,
            confidence=fc.confidence,
            updated_at=now,
        )
        
        self.repo.upsert_inventory_days_estimate(
            user_id=user_id,
            product_id=product_id,
            days_left=fc.expected_days_left,
            state=InventoryState(fc.predicted_state.value),
            confidence=fc.confidence,
            source=InventorySource.SYSTEM,
        )
        
        self.repo.insert_forecast(user_id, product_id, fc, trigger_log_id=row["log_id"])
    
    def learn_from_manual_change(self, user_id: str, product_id: str) -> None:
        """Learn from manual inventory change WITHOUT overwriting the user's state"""
        try:
            from uuid import UUID
            
            # Ensure user_id and product_id are strings
            if not isinstance(user_id, str):
                user_id = str(user_id)
            if not isinstance(product_id, str):
                product_id = str(product_id)
            
            # Get the latest log entry for this product
            result = self.repo.supabase.table("inventory_log").select("log_id").eq("user_id", user_id).eq("product_id", product_id).order("occurred_at", desc=True).limit(1).execute()
            
            if not result.data or len(result.data) == 0:
                return
            
            log_id = result.data[0]["log_id"]
            row = self.repo.get_inventory_log_row(log_id)
            
            now = datetime.now(timezone.utc)
            predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)
            
            products = dict(self.repo.get_user_inventory_products(user_id))
            category_id = products.get(product_id)
            
            state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
            
            # Process the event to update the predictor model
            purchase_ev, feedback_ev = map_inventory_log_row_to_event(row)
            
            if purchase_ev is not None:
                state = apply_purchase(state, purchase_ev)
            
            if feedback_ev is not None:
                state = apply_feedback(state, feedback_ev, cfg)
            
            mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
            fc = predict(state, now, mult, cfg)
            state = stamp_last_prediction(state, fc)
            
            # Convert params to JSON-serializable format (handle UUID objects)
            params_json = state.to_params_json()
            params_json = self._make_json_serializable(params_json)
            
            # Save the updated predictor state
            self.repo.upsert_predictor_state(
                user_id=user_id,
                product_id=product_id,
                predictor_profile_id=predictor_profile_id,
                params=params_json,
                confidence=fc.confidence,
                updated_at=now,
            )
            
            # Store the forecast but DON'T overwrite inventory (user just set it manually)
            self.repo.insert_forecast(user_id, product_id, fc, trigger_log_id=row["log_id"])
            
            print(f"Predictor learned from manual change: product={product_id}, forecast={fc.expected_days_left} days")
            
        except Exception as e:
            import traceback
            print(f"Error in predictor learning from manual change: {e}")
            print(traceback.format_exc())
    
    def learn_from_purchase(self, user_id, product_id, quantity: float = 1.0, log_id = None) -> None:
        """
        Learn from a purchase event (e.g., from receipt scanning).
        This updates the predictor with the purchase quantity and refreshes forecasts.
        """
        try:
            from uuid import UUID
            
            # Convert to UUID if needed
            if not isinstance(user_id, str):
                user_id = str(user_id)
            if not isinstance(product_id, str):
                product_id = str(product_id)
            
            now = datetime.now(timezone.utc)
            predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)
            
            products = dict(self.repo.get_user_inventory_products(user_id))
            category_id = products.get(product_id)
            
            state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
            
            # Create a purchase event with the quantity
            if PREDICTOR_AVAILABLE:
                from ema_cycle_predictor import PurchaseEvent
                
                purchase_event = PurchaseEvent(
                    ts=now,
                    source=PredInventorySource.RECEIPT,
                    reliability=1.0
                )
                
                # Apply the purchase to update the predictor state
                state = apply_purchase(state, purchase_event)
                
                # Note: The quantity information is stored in inventory.estimated_qty
                # The predictor will learn consumption patterns over time through feedback events
                
                # Generate new forecast
                mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
                fc = predict(state, now, mult, cfg)
                state = stamp_last_prediction(state, fc)
                
                # Convert params to JSON-serializable format
                params_json = state.to_params_json()
                params_json = self._make_json_serializable(params_json)
                
                # Save the updated predictor state
                self.repo.upsert_predictor_state(
                    user_id=user_id,
                    product_id=product_id,
                    predictor_profile_id=predictor_profile_id,
                    params=params_json,
                    confidence=fc.confidence,
                    updated_at=now,
                )
                
                # Store the forecast
                trigger_log = str(log_id) if log_id else None
                self.repo.insert_forecast(user_id, product_id, fc, trigger_log_id=trigger_log)
                
                print(f"[+] Predictor learned from purchase: product={product_id}, quantity={quantity}, forecast={fc.expected_days_left} days")
            
        except Exception as e:
            print(f"[!] Error in predictor learning from purchase: {e}")
    
    def update_from_inventory_event(self, user_id: str, product_id: str) -> None:
        """Update predictions for a specific product based on latest inventory log"""
        try:
            # Get the latest log entry for this product
            result = self.repo.supabase.table("inventory_log").select("log_id").eq("user_id", str(user_id)).eq("product_id", str(product_id)).order("occurred_at", desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                log_id = result.data[0]["log_id"]
                self.process_inventory_log(log_id)
        except Exception as e:
            print(f"Error updating predictor from inventory event: {e}")
    
    def refresh_user_inventory_forecasts(self, user_id: str) -> None:
        """Refresh predictions for all products in user's inventory"""
        now = datetime.now(timezone.utc)
        predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)
        
        items = self.repo.get_user_inventory_products(user_id)
        for product_id, category_id in items:
            state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
            mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
            fc = predict(state, now, mult, cfg)
            state = stamp_last_prediction(state, fc)
            
            # Convert params to JSON-serializable format
            params_json = state.to_params_json()
            params_json = self._make_json_serializable(params_json)
            
            self.repo.upsert_predictor_state(
                user_id=user_id,
                product_id=product_id,
                predictor_profile_id=predictor_profile_id,
                params=params_json,
                confidence=fc.confidence,
                updated_at=now,
            )
            self.repo.upsert_inventory_days_estimate(
                user_id=user_id,
                product_id=product_id,
                days_left=fc.expected_days_left,
                state=InventoryState(fc.predicted_state.value),
                confidence=fc.confidence,
                source=InventorySource.SYSTEM,
            )
            self.repo.insert_forecast(user_id, product_id, fc, trigger_log_id=None)

