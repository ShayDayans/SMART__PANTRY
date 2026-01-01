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
        predict, predict_after_purchase, stamp_last_prediction, map_inventory_log_row_to_event,
        derive_state, compute_confidence,
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
                "alpha_strong": 0.12,  # Reduced from 0.25 to be less sensitive to outliers
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
        # Check if inventory row exists first
        existing = self.supabase.table("inventory").select("*").eq("user_id", user_id).eq("product_id", product_id).execute()
        if not existing.data:
            print(f"[WARNING upsert_inventory_days_estimate] Inventory row doesn't exist for user_id={user_id}, product_id={product_id}. Creating it...")
        
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
        print(f"[DEBUG upsert_inventory_days_estimate] Upserting inventory: user_id={user_id}, product_id={product_id}, data={data}")
        try:
            result = self.supabase.table("inventory").upsert(data, on_conflict="user_id,product_id").execute()
            print(f"[DEBUG upsert_inventory_days_estimate] Upsert result: {result.data if result.data else 'No data returned'}")
            if result.data:
                updated_row = result.data[0]
                print(f"[DEBUG upsert_inventory_days_estimate] Updated row - estimated_qty={updated_row.get('estimated_qty')}, state={updated_row.get('state')}")
            else:
                print(f"[WARNING upsert_inventory_days_estimate] Upsert returned no data! This might indicate the row doesn't exist.")
        except Exception as e:
            print(f"[ERROR upsert_inventory_days_estimate] Failed to upsert inventory: {e}")
            import traceback
            traceback.print_exc()
            raise
    
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
    
    def _extract_multiplier_from_effects(
        self, 
        effects: Dict[str, Any], 
        product_id: str, 
        category_id: Optional[str]
    ) -> float:
        """
        Extract multiplier contribution from habit effects for a specific product.
        
        Args:
            effects: Habit effects dict containing:
                - global_multiplier: multiplier that applies to all products
                - product_multipliers: {product_id: multiplier}
                - category_multipliers: {category_id: multiplier}
            product_id: Product ID to check
            category_id: Category ID to check (optional)
        
        Returns:
            Combined multiplier for this product (global × product × category)
        """
        mult = 1.0
        pid = str(product_id)
        cid = str(category_id) if category_id else None
        
        # Global multiplier applies to all products
        gm = effects.get("global_multiplier")
        if gm is not None:
            mult *= float(gm)
        
        # Product-specific multiplier
        pm = effects.get("product_multipliers") or {}
        if pid in pm:
            mult *= float(pm[pid])
        
        # Category-specific multiplier
        if cid:
            cm = effects.get("category_multipliers") or {}
            if cid in cm:
                mult *= float(cm[cid])
        
        return float(max(mult, 1e-6))
    
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
        # Ensure params_json is a dict and has empty_at field (for backward compatibility)
        if not isinstance(params_json, dict):
            params_json = {}
        # Ensure empty_at exists (for backward compatibility with existing products)
        if "empty_at" not in params_json:
            params_json["empty_at"] = None
        
        st = CycleEmaState.from_params_json(params_json)
        if st.category_id is None and category_id is not None:
            st.category_id = str(category_id)
        return st
    
    def process_inventory_log(self, log_id: str, state_before_purchase: Optional[InventoryState] = None) -> None:
        """
        Process inventory log event and update predictions
        
        Args:
            log_id: Inventory log ID to process
            state_before_purchase: Optional state before purchase (for cases where inventory was already updated)
        """
        row = self.repo.get_inventory_log_row(log_id)
        user_id = row["user_id"]
        product_id = row["product_id"]
        now = datetime.now(timezone.utc)
        
        predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)
        
        products = dict(self.repo.get_user_inventory_products(user_id))
        category_id = products.get(product_id)
        
        state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
        
        purchase_ev, feedback_ev = map_inventory_log_row_to_event(row)
        
        # Get current inventory state before purchase (if purchase event)
        # Use provided state_before_purchase if available, otherwise read from DB
        current_state = state_before_purchase
        if purchase_ev is not None and current_state is None:
            try:
                inventory_item = self.repo.supabase.table("inventory").select("state").eq(
                    "user_id", user_id
                ).eq("product_id", product_id).limit(1).execute()
                if inventory_item.data and len(inventory_item.data) > 0:
                    state_str = inventory_item.data[0].get("state")
                    if state_str:
                        current_state = InventoryState(state_str)
            except Exception as e:
                print(f"Warning: Could not get current inventory state: {e}")
        
        if purchase_ev is not None:
            from ema_cycle_predictor import InventoryState as PredInventoryState
            pred_current_state = PredInventoryState(current_state.value) if current_state else None
            state = apply_purchase(state, purchase_ev, cfg, pred_current_state)
        
        if feedback_ev is not None:
            state = apply_feedback(state, feedback_ev, cfg)
        
        if purchase_ev is not None:
            # After purchase: habits already baked into cycle_mean_days, no multiplier needed
            fc = predict_after_purchase(state, now, cfg)
        else:
            # For non-purchase events (feedback, etc.), use regular predict with multiplier
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
            
            # Use last_pred_days_left from state (already in memory, no DB read needed)
            # This represents the model's last prediction and should be synchronized with inventory.estimated_qty
            # in normal operation. Using it ensures we apply the multiplier to the correct base value.
            base_days_left = state.last_pred_days_left if state.last_pred_days_left is not None else None
            
            mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
            # Use predict() with base_days_left to ensure correct multiplier application
            fc = predict(state, now, mult, cfg, inventory_days_left=base_days_left)
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
    
    def refresh_products_affected_by_habit(
        self, 
        user_id: str, 
        habit_effects: Dict[str, Any],
        is_deletion: bool = False
    ) -> None:
        """
        Refresh predictions for products affected by a habit's effects.
        
        When a habit is created or deleted, this method adjusts both cycle_mean_days
        and last_pred_days_left to reflect the habit's multiplier effect.
        
        Args:
            user_id: User ID
            habit_effects: Habit effects dict containing:
                - global_multiplier: multiplier that applies to all products
                - product_multipliers: {product_id: multiplier}
                - category_multipliers: {category_id: multiplier}
            is_deletion: If True, reverts the habit's effect (multiplies).
                        If False, applies the habit's effect (divides).
        """
        if not habit_effects:
            return
        
        now = datetime.now(timezone.utc)
        predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)
        
        # Collect all affected product IDs
        affected_product_ids = set()
        
        # Get products directly affected by product_multipliers
        product_multipliers = habit_effects.get("product_multipliers", {})
        if product_multipliers:
            for product_id in product_multipliers.keys():
                affected_product_ids.add(str(product_id))
        
        # Get products affected by category_multipliers or global_multiplier
        category_multipliers = habit_effects.get("category_multipliers", {})
        global_multiplier = habit_effects.get("global_multiplier")
        if category_multipliers or global_multiplier is not None:
            # Get all products in user's inventory
            user_products = self.repo.get_user_inventory_products(user_id)
            
            # Find products in affected categories (or all products if global_multiplier)
            affected_category_ids = set(category_multipliers.keys())
            for product_id, category_id in user_products:
                if global_multiplier is not None:
                    # Global multiplier affects all products
                    affected_product_ids.add(str(product_id))
                elif category_id and str(category_id) in affected_category_ids:
                    affected_product_ids.add(str(product_id))
        
        # Get user's inventory products once
        user_products = self.repo.get_user_inventory_products(user_id)
        user_product_ids = {str(pid) for pid, _ in user_products}
        
        # Refresh predictions for all affected products
        for product_id in affected_product_ids:
            try:
                # Only refresh if product is in user's inventory
                if product_id not in user_product_ids:
                    continue
                
                # Get category_id for this product
                category_id = None
                for pid, cid in user_products:
                    if str(pid) == product_id:
                        category_id = cid
                        break
                
                state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
                
                # Extract multiplier from the habit being added/removed
                habit_mult = self._extract_multiplier_from_effects(
                    habit_effects, product_id, category_id
                )
                
                # Adjust cycle_mean_days and last_pred_days_left based on habit creation/deletion
                if is_deletion:
                    # Revert: multiply by the deleted habit's multiplier
                    # This removes that habit's effect, leaving others intact
                    state.cycle_mean_days = state.cycle_mean_days * habit_mult
                    if state.last_pred_days_left is not None:
                        new_days_left = state.last_pred_days_left * habit_mult
                    else:
                        # No previous prediction - calculate from adjusted cycle_mean_days
                        new_days_left = None
                else:
                    # Apply: divide by the new habit's multiplier
                    # This applies the new habit on top of existing ones
                    state.cycle_mean_days = state.cycle_mean_days / habit_mult
                    if state.last_pred_days_left is not None:
                        new_days_left = state.last_pred_days_left / habit_mult
                    else:
                        # No previous prediction - calculate from adjusted cycle_mean_days
                        new_days_left = None
                
                # Clamp cycle_mean_days to valid range
                state.cycle_mean_days = max(cfg.min_cycle_days, min(state.cycle_mean_days, cfg.max_cycle_days))
                
                # Create forecast with the new values
                # If we have a new_days_left value, use it; otherwise calculate from cycle_mean_days
                if new_days_left is not None:
                    expected_days_left = float(new_days_left)
                else:
                    # Fallback: calculate from adjusted cycle_mean_days
                    if state.cycle_started_at is not None:
                        from ema_cycle_predictor import _days_between
                        elapsed = _days_between(now, state.cycle_started_at)
                        expected_days_left = float(max(0.0, state.cycle_mean_days - elapsed))
                    else:
                        # No active cycle - use cycle_mean_days as initial value
                        expected_days_left = float(state.cycle_mean_days)
                
                fc = Forecast(
                    expected_days_left=expected_days_left,
                    predicted_state=derive_state(expected_days_left, state.cycle_mean_days, cfg),
                    confidence=float(compute_confidence(state, now, cfg)),
                    generated_at=now,
                )
                
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
            except Exception as e:
                import logging
                action = "deletion" if is_deletion else "creation"
                logging.error(f"Error refreshing prediction for product {product_id} after habit {action}: {e}", exc_info=True)
                continue
    
    def weekly_model_update(self, user_id: str, product_id: str) -> None:
        """
        Weekly model update - DISABLED.
        Model updates now happen only on purchase events (when empty_at != null or state=LOW).
        """
        # Model updates are now handled in apply_purchase, not in weekly updates
        return
        
        now = datetime.now(timezone.utc)
        predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)
        
        products = dict(self.repo.get_user_inventory_products(user_id))
        category_id = products.get(product_id)
        
        state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
        
        # Check if there's an active cycle
        if state.cycle_started_at is None:
            # No active cycle - nothing to update
            return
        
        # Calculate days since purchase
        from ema_cycle_predictor import _days_between
        days_since_purchase = _days_between(now, state.cycle_started_at)
        
        # Condition: only update if days_since_purchase >= cycle_mean_days
        # (the cycle should have ended by now)
        if days_since_purchase < state.cycle_mean_days:
            # Cycle hasn't ended yet - don't update
            return
        
        # Calculate observed cycle length: how many days the product actually lasted
        # This is the time from cycle_started_at to when the cycle ended (EMPTY or new PURCHASE)
        observed = None
        cycle_end_time = None
        
        # 1. Check for EMPTY events since cycle_started_at
        empty_logs = self.repo.supabase.table("inventory_log").select("*").eq(
            "user_id", user_id
        ).eq("product_id", product_id).eq("action", "EMPTY").gte(
            "occurred_at", state.cycle_started_at.isoformat()
        ).order("occurred_at", desc=False).limit(1).execute()
        
        if empty_logs.data:
            # EMPTY event found - cycle ended when product ran out
            cycle_end_time_str = empty_logs.data[0].get("occurred_at")
            if cycle_end_time_str:
                from datetime import datetime
                cycle_end_time = datetime.fromisoformat(cycle_end_time_str.replace("Z", "+00:00"))
                from ema_cycle_predictor import _days_between
                observed = _days_between(cycle_end_time, state.cycle_started_at)
        
        # 2. If no EMPTY, check for PURCHASE events (new cycle started = previous cycle ended)
        if observed is None:
            purchase_logs = self.repo.supabase.table("inventory_log").select("*").eq(
                "user_id", user_id
            ).eq("product_id", product_id).in_("action", ["PURCHASE", "REPURCHASE"]).gte(
                "occurred_at", state.cycle_started_at.isoformat()
            ).order("occurred_at", desc=False).limit(1).execute()
            
            if purchase_logs.data:
                # New cycle started - the previous cycle ended when this purchase happened
                cycle_end_time_str = purchase_logs.data[0].get("occurred_at")
                if cycle_end_time_str:
                    from datetime import datetime
                    cycle_end_time = datetime.fromisoformat(cycle_end_time_str.replace("Z", "+00:00"))
                    from ema_cycle_predictor import _days_between
                    observed = _days_between(cycle_end_time, state.cycle_started_at)
        
        # 3. If still no observed, use current time (cycle is still ongoing, but we're updating weekly)
        if observed is None:
            from ema_cycle_predictor import _days_between
            observed = _days_between(now, state.cycle_started_at)
        
        # Clamp observed to valid range
        observed = max(cfg.min_cycle_days, min(observed, cfg.max_cycle_days))
        
        # Update cycle_mean_days based on observed cycle length (EMA update)
        old_mean = state.cycle_mean_days
        
        # Adaptive alpha based on history
        if state.n_strong_updates >= 5:
            a = cfg.alpha_strong * 0.7  # 30% less
        elif state.n_strong_updates >= 3:
            a = cfg.alpha_strong * 0.85  # 15% less
        else:
            a = cfg.alpha_strong
        
        # EMA update for mean
        new_mean = (1 - a) * old_mean + a * observed
        new_mean = max(cfg.min_cycle_days, min(new_mean, cfg.max_cycle_days))
        
        # Update MAD
        err = observed - old_mean
        new_mad = (1 - a) * state.cycle_mad_days + a * abs(err)
        new_mad = max(0.1, min(new_mad, cfg.max_cycle_days))
        
        state.cycle_mean_days = float(new_mean)
        state.cycle_mad_days = float(new_mad)
        state.n_strong_updates += 1
        
        # Generate new forecast
        mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
        fc = predict(state, now, mult, cfg)
        state = stamp_last_prediction(state, fc)
        
        # Save updated state
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
        
        # Update inventory
        self.repo.upsert_inventory_days_estimate(
            user_id=user_id,
            product_id=product_id,
            days_left=fc.expected_days_left,
            state=InventoryState(fc.predicted_state.value),
            confidence=fc.confidence,
            source=InventorySource.SYSTEM,
        )
        
        print(f"Weekly update: Product {product_id} - observed cycle: {observed} days, updated cycle_mean_days: {old_mean} -> {new_mean}")
        return
    
    def daily_state_update_all_products(self, user_id: str) -> None:
        """
        Daily state update for all products of a user.
        Decreases days_left by 1 for each product and updates state accordingly.
        Also updates last_pred_days_left in product_predictor_state.
        """
        if not PREDICTOR_AVAILABLE:
            return
        
        now = datetime.now(timezone.utc)
        predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)
        
        products = self.repo.get_user_inventory_products(user_id)
        updated_count = 0
        
        for product_id, category_id in products:
            try:
                # Load current state
                state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
                
                # Get current inventory item
                inventory_item = self.repo.supabase.table("inventory").select("*").eq(
                    "user_id", user_id
                ).eq("product_id", product_id).limit(1).execute()
                
                if not inventory_item.data:
                    continue
                
                current_item = inventory_item.data[0]
                current_state_str = current_item.get("state")
                
                # Skip products that are already EMPTY
                if current_state_str == "EMPTY":
                    continue
                
                current_days_left = current_item.get("estimated_qty")
                
                if current_days_left is None:
                    # If no days_left, calculate from cycle_mean_days
                    mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
                    from ema_cycle_predictor import compute_days_left
                    current_days_left = compute_days_left(state, now, mult, cfg, inventory_days_left=None)
                else:
                    try:
                        current_days_left = float(current_days_left)
                    except (ValueError, TypeError):
                        # If invalid, calculate from cycle_mean_days
                        mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
                        from ema_cycle_predictor import compute_days_left
                        current_days_left = compute_days_left(state, now, mult, cfg, inventory_days_left=None)
                
                # Decrease by 1 day (but not below 0)
                new_days_left = max(0.0, current_days_left - 1.0)
                
                # If days_left reached 0, save empty_at (if not already set)
                if new_days_left <= 0.0 and state.empty_at is None:
                    state.empty_at = now
                
                # Derive new state
                from ema_cycle_predictor import derive_state, compute_confidence
                new_state = derive_state(new_days_left, state.cycle_mean_days, cfg)
                
                # Update state.last_pred_days_left
                state.last_pred_days_left = float(new_days_left)
                state.last_update_at = now
                
                # Calculate confidence
                confidence = compute_confidence(state, now, cfg)
                
                # Update product_predictor_state
                params_json = state.to_params_json()
                params_json = self._make_json_serializable(params_json)
                self.repo.upsert_predictor_state(
                    user_id=user_id,
                    product_id=product_id,
                    predictor_profile_id=predictor_profile_id,
                    params=params_json,
                    confidence=confidence,
                    updated_at=now,
                )
                
                # Update inventory
                self.repo.upsert_inventory_days_estimate(
                    user_id=user_id,
                    product_id=product_id,
                    days_left=new_days_left,
                    state=InventoryState(new_state.value),
                    confidence=confidence,
                    source=InventorySource.SYSTEM,
                )
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error in daily state update for product {product_id}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        logger.info(f"Daily state update completed for user {user_id}: {updated_count} products updated")
    
    def weekly_model_update_all_products(self, user_id: str) -> None:
        """
        Run weekly update for all products of a user
        """
        products = self.repo.get_user_inventory_products(user_id)
        for product_id, category_id in products:
            try:
                self.weekly_model_update(user_id, product_id)
            except Exception as e:
                print(f"Error in weekly update for product {product_id}: {e}")
                import traceback
                traceback.print_exc()

