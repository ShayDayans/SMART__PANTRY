from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple
import json
import math


# ----------------------------
# Enums (match your DB enums)
# ----------------------------
class InventoryState(str, Enum):
    EMPTY = "EMPTY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    FULL = "FULL"
    UNKNOWN = "UNKNOWN"


class InventorySource(str, Enum):
    RECEIPT = "RECEIPT"
    SHOPPING_LIST = "SHOPPING_LIST"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class InventoryAction(str, Enum):
    PURCHASE = "PURCHASE"
    ADJUST = "ADJUST"
    CONSUME = "CONSUME"
    RESET = "RESET"


class FeedbackKind(str, Enum):
    MORE = "MORE"
    LESS = "LESS"
    EXACT = "EXACT"
    EMPTY = "EMPTY"     # "נגמר"
    WASTED = "WASTED"   # "נזרק"


# ----------------------------
# Config / State / Forecast
# ----------------------------
@dataclass(frozen=True)
class CategoryPrior:
    mean_days: float
    mad_days: float


@dataclass(frozen=True)
class PredictorConfig:
    # category_id -> prior
    category_priors: Dict[str, CategoryPrior]

    # EMA weights
    alpha_strong: float = 0.12    # for EMPTY / observed cycles (reduced from 0.25 to be less sensitive)
    alpha_weak: float = 0.10      # for MORE/LESS
    alpha_confirm: float = 0.05   # for EXACT

    # bounds
    min_cycle_days: float = 1.0
    max_cycle_days: float = 90.0

    # MORE/LESS correction magnitude
    more_less_ratio: float = 0.15
    more_less_step_cap_days: float = 3.0

    # state thresholds by ratio of days_left / mean
    full_ratio: float = 0.70
    medium_ratio: float = 0.30

    # confidence shaping
    recency_tau_days: float = 21.0

    @staticmethod
    def from_profile_config_json(cfg: Dict[str, Any]) -> "PredictorConfig":
        """
        Expected predictor_profiles.config format (suggested):
        {
          "category_priors": {
            "<category_uuid>": {"mean_days": 7, "mad_days": 2},
            ...
          },
          "alpha_strong": 0.25,
          "alpha_weak": 0.10,
          ...
        }
        """
        priors_raw = cfg.get("category_priors", {}) or {}
        priors: Dict[str, CategoryPrior] = {}
        for k, v in priors_raw.items():
            try:
                priors[str(k)] = CategoryPrior(
                    mean_days=float(v.get("mean_days", 7.0)),
                    mad_days=float(v.get("mad_days", 2.0)),
                )
            except Exception:
                continue

        return PredictorConfig(
            category_priors=priors,
            alpha_strong=float(cfg.get("alpha_strong", 0.25)),
            alpha_weak=float(cfg.get("alpha_weak", 0.10)),
            alpha_confirm=float(cfg.get("alpha_confirm", 0.05)),
            min_cycle_days=float(cfg.get("min_cycle_days", 1.0)),
            max_cycle_days=float(cfg.get("max_cycle_days", 90.0)),
            more_less_ratio=float(cfg.get("more_less_ratio", 0.15)),
            more_less_step_cap_days=float(cfg.get("more_less_step_cap_days", 3.0)),
            full_ratio=float(cfg.get("full_ratio", 0.70)),
            medium_ratio=float(cfg.get("medium_ratio", 0.30)),
            recency_tau_days=float(cfg.get("recency_tau_days", 21.0)),
        )


@dataclass
class CycleEmaState:
    cycle_mean_days: float
    cycle_mad_days: float

    cycle_started_at: Optional[datetime]  # None means no active cycle (EMPTY)
    last_purchase_at: Optional[datetime]

    last_update_at: datetime

    n_strong_updates: int = 0
    n_total_updates: int = 0
    n_completed_cycles: int = 0  # Number of completed cycles (for cumulative average calculation)

    last_pred_days_left: Optional[float] = None
    censored_cycles: int = 0
    waste_events: int = 0

    # Optional for convenience
    category_id: Optional[str] = None
    last_feedback_at: Optional[datetime] = None  # Track last MORE/LESS feedback for adaptive learning
    empty_at: Optional[datetime] = None  # Date when product ran out (state=EMPTY for first time)

    def to_params_json(self) -> Dict[str, Any]:
        d = asdict(self)
        # datetimes -> iso
        for k in ["cycle_started_at", "last_purchase_at", "last_update_at", "empty_at", "last_feedback_at"]:
            if d[k] is not None:
                d[k] = d[k].astimezone(timezone.utc).isoformat()
        return d

    @staticmethod
    def from_params_json(params: Dict[str, Any]) -> "CycleEmaState":
        # Ensure params is a dict (for backward compatibility)
        if not isinstance(params, dict):
            params = {}
        
        def parse_dt(x: Any) -> Optional[datetime]:
            if x is None:
                return None
            if isinstance(x, datetime):
                return x
            if isinstance(x, str) and x.strip():
                # expects ISO string; timezone recommended
                try:
                    # Fix microsecond precision if needed
                    x_str = x.replace("Z", "+00:00")
                    import re
                    match = re.search(r'\.(\d{1,6})([+-]\d{2}:\d{2})$', x_str)
                    if match:
                        microseconds = match.group(1)
                        timezone_part = match.group(2)
                        if len(microseconds) < 6:
                            microseconds = microseconds.ljust(6, '0')
                        x_str = re.sub(r'\.\d{1,6}([+-]\d{2}:\d{2})$', f'.{microseconds}\\1', x_str)
                    return datetime.fromisoformat(x_str)
                except (ValueError, AttributeError):
                    try:
                        from dateutil import parser
                        return parser.isoparse(x)
                    except (ImportError, ValueError):
                        return None
            return None

        return CycleEmaState(
            cycle_mean_days=float(params.get("cycle_mean_days", 7.0)),
            cycle_mad_days=float(params.get("cycle_mad_days", 2.0)),
            cycle_started_at=parse_dt(params.get("cycle_started_at")),
            last_purchase_at=parse_dt(params.get("last_purchase_at")),
            last_update_at=parse_dt(params.get("last_update_at")) or datetime.now(timezone.utc),
            n_strong_updates=int(params.get("n_strong_updates", 0)),
            n_total_updates=int(params.get("n_total_updates", 0)),
            n_completed_cycles=int(params.get("n_completed_cycles", 0)),  # NEW: Add n_completed_cycles
            last_pred_days_left=(None if params.get("last_pred_days_left") is None else float(params["last_pred_days_left"])),
            censored_cycles=int(params.get("censored_cycles", 0)),
            waste_events=int(params.get("waste_events", 0)),
            category_id=(None if params.get("category_id") is None else str(params["category_id"])),
            last_feedback_at=parse_dt(params.get("last_feedback_at")),  # Track last MORE/LESS feedback
            empty_at=parse_dt(params.get("empty_at")),  # Date when product ran out
        )


@dataclass(frozen=True)
class Forecast:
    expected_days_left: float
    predicted_state: InventoryState
    confidence: float
    generated_at: datetime


# ----------------------------
# Helpers
# ----------------------------
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _days_between(a: datetime, b: datetime) -> float:
    """Return |a - b| in days as float."""
    return abs((a - b).total_seconds()) / 86400.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _sigmoid(x: float) -> float:
    # stable-ish sigmoid
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    else:
        z = math.exp(x)
        return z / (1 + z)


def derive_state(days_left: float, mean_days: float, cfg: PredictorConfig) -> InventoryState:
    if days_left <= 0:
        return InventoryState.EMPTY
    denom = max(mean_days, 1e-6)
    ratio = days_left / denom
    # If ratio is very small (< 2%), consider it EMPTY
    if ratio < 0.02:
        return InventoryState.EMPTY
    if ratio >= cfg.full_ratio:
        return InventoryState.FULL
    if ratio >= cfg.medium_ratio:
        return InventoryState.MEDIUM
    return InventoryState.LOW


def compute_confidence(state: CycleEmaState, now: datetime, cfg: PredictorConfig) -> float:
    # evidence: relies on completed cycles (more reliable than just strong updates)
    # Use n_completed_cycles if available and > 0, otherwise fall back to n_strong_updates
    cycles_for_evidence = state.n_completed_cycles if state.n_completed_cycles > 0 else state.n_strong_updates
    # Normalize: sigmoid(cycles / 2.0) means ~0.88 at 2 cycles, ~0.98 at 4 cycles
    evidence = _sigmoid(cycles_for_evidence / 2.0)
    
    # For products with no cycles yet, give minimum evidence of 0.3 (not 0.5)
    if cycles_for_evidence == 0:
        evidence = 0.3  # Fixed minimum for new products

    # stability: penalize large mad relative to mean, but don't let it go below 0.2
    stability = 1.0 - (state.cycle_mad_days / max(state.cycle_mean_days, 1.0))
    stability = _clamp(stability, 0.2, 1.0)  # Minimum stability of 0.2

    # recency: exponential decay, but slower (tau increased to 60 days)
    days_since = _days_between(now, state.last_update_at)
    recency = math.exp(-days_since / max(cfg.recency_tau_days, 1e-6))
    
    # Minimum recency: even if many days passed, don't let it go below 0.1
    recency = max(0.1, recency)

    # Base confidence: 0.2 (increased from 0.1) + 0.8 * components
    conf = 0.2 + 0.8 * evidence * stability * recency
    return float(_clamp(conf, 0.0, 1.0))


def compute_days_left(state: CycleEmaState, now: datetime, multiplier: float, cfg: PredictorConfig, inventory_days_left: Optional[float] = None) -> float:
    """
    Compute days left for a product.
    
    If inventory_days_left is provided (from user updates), use it directly.
    Otherwise, calculate from cycle_mean_days and elapsed time.
    
    multiplier > 1 means faster consumption => fewer days left.
    This is applied at prediction time only (habits temporary modifiers).
    """
    # If user has updated days_left directly (via MORE/LESS, recipe, etc.), use that value
    if inventory_days_left is not None:
        mult = max(multiplier, 1e-6)
        adjusted = inventory_days_left / mult
        return float(max(adjusted, 0.0))
    
    # Otherwise, calculate from cycle_mean_days
    if state.cycle_started_at is None:
        return 0.0

    elapsed = _days_between(now, state.cycle_started_at)
    base_left = state.cycle_mean_days - elapsed
    base_left = max(base_left, 0.0)

    mult = max(multiplier, 1e-6)
    adjusted = base_left / mult
    return float(max(adjusted, 0.0))


# ----------------------------
# Initialization (cold start)
# ----------------------------
def init_state_from_category(category_id: Optional[str], cfg: PredictorConfig, now: Optional[datetime] = None) -> CycleEmaState:
    now = now or _now_utc()
    prior = None
    if category_id is not None:
        prior = cfg.category_priors.get(str(category_id))

    if prior is None:
        prior = CategoryPrior(mean_days=7.0, mad_days=2.0)

    return CycleEmaState(
        cycle_mean_days=float(_clamp(prior.mean_days, cfg.min_cycle_days, cfg.max_cycle_days)),
        cycle_mad_days=float(max(prior.mad_days, 0.1)),
        cycle_started_at=None,
        last_purchase_at=None,
        last_update_at=now,
        n_strong_updates=0,
        n_total_updates=0,
        n_completed_cycles=0,  # Initialize n_completed_cycles
        last_pred_days_left=None,
        censored_cycles=0,
        waste_events=0,
        category_id=(str(category_id) if category_id is not None else None),
        last_feedback_at=None,  # Initialize last_feedback_at
        empty_at=None,  # Initialize empty_at
    )


# ----------------------------
# Events (update rules)
# ----------------------------
@dataclass(frozen=True)
class PurchaseEvent:
    ts: datetime
    source: InventorySource
    reliability: float = 1.0


@dataclass(frozen=True)
class FeedbackEvent:
    ts: datetime
    kind: FeedbackKind
    source: InventorySource = InventorySource.MANUAL
    reliability: float = 0.9
    note: Optional[str] = None  # Store note for WASTED reason analysis


def apply_purchase(state: CycleEmaState, ev: PurchaseEvent, cfg: PredictorConfig, current_state: Optional[InventoryState] = None) -> CycleEmaState:
    """
    Apply purchase event and update model if needed.
    
    Args:
        state: Current predictor state
        ev: Purchase event
        cfg: Predictor config
        current_state: Current inventory state (FULL/MEDIUM/LOW/EMPTY) before purchase
    """
    # Determine if we should update the mean based on empty_at or current state
    should_update_mean = False
    observed = None
    
    # Case 1: empty_at != null (product ran out)
    if state.empty_at is not None and state.cycle_started_at is not None:
        should_update_mean = True
        observed = _days_between(state.empty_at, state.cycle_started_at)
        observed = _clamp(observed, cfg.min_cycle_days, cfg.max_cycle_days)
    
    # Case 2: empty_at == null but current_state is LOW
    elif state.empty_at is None and current_state == InventoryState.LOW and state.cycle_started_at is not None:
        should_update_mean = True
        observed = _days_between(ev.ts, state.cycle_started_at)
        observed = _clamp(observed, cfg.min_cycle_days, cfg.max_cycle_days)
    
    # Update mean if needed
    if should_update_mean and observed is not None:
        old_mean = state.cycle_mean_days
        n_cycles = state.n_completed_cycles
        
        # Cumulative average: (old_mean * n_cycles + new_cycle) / (n_cycles + 1)
        if n_cycles == 0:
            # First cycle - use observed directly
            new_mean = observed
        else:
            # Cumulative average formula
            new_mean = (old_mean * n_cycles + observed) / (n_cycles + 1)
        
        new_mean = _clamp(new_mean, cfg.min_cycle_days, cfg.max_cycle_days)
        
        # Update MAD based on error (cumulative average of absolute errors)
        err = observed - old_mean
        if n_cycles == 0:
            # First cycle - use absolute error directly
            new_mad = abs(err) if abs(err) > 0 else 0.1
        else:
            # Cumulative average of absolute errors
            current_mad_sum = state.cycle_mad_days * n_cycles
            new_mad = (current_mad_sum + abs(err)) / (n_cycles + 1)
        new_mad = _clamp(new_mad, 0.1, cfg.max_cycle_days)
        
        state.cycle_mean_days = float(new_mean)
        state.cycle_mad_days = float(new_mad)
        state.n_completed_cycles += 1
        state.n_strong_updates += 1
    elif state.cycle_started_at is not None:
        # If we're not updating mean but had an active cycle, mark it as censored
        # (only if state is FULL/MEDIUM - LOW already updated mean)
        if current_state in (InventoryState.FULL, InventoryState.MEDIUM):
            state.censored_cycles += 1
    
    # Reset cycle and empty_at
    state.cycle_started_at = ev.ts
    state.last_purchase_at = ev.ts
    state.last_update_at = ev.ts
    state.empty_at = None  # Reset empty_at on purchase
    
    return state


def apply_feedback(state: CycleEmaState, ev: FeedbackEvent, cfg: PredictorConfig) -> CycleEmaState:
    state.last_update_at = ev.ts
    state.n_total_updates += 1

    if ev.kind == FeedbackKind.EMPTY:
        # Store empty_at timestamp (when product ran out)
        # Don't update mean here - it will be updated on next purchase
        if state.empty_at is None:
            state.empty_at = ev.ts
        
        # cycle_started_at stays as is (needed to calculate observed on next purchase)
        # Don't reset cycle_started_at to None - we need it for the calculation
        return state

    if ev.kind == FeedbackKind.WASTED:
        state.waste_events += 1
        
        # Check reason from note to determine if we should learn
        reason = ""
        if hasattr(ev, 'note') and ev.note:
            reason = ev.note.lower()
        elif hasattr(ev, 'source') and hasattr(ev.source, 'value'):
            # Try to get note from event if available
            pass
        
        # Parse reason from note if available (will be set in map_inventory_log_row_to_event)
        if "taste" in reason or "expired" in reason or "לא היה טעים" in reason or "פג תוקף" in reason:
            # Not a real consumption cycle - don't learn
            state.cycle_started_at = None
            state.cycle_mad_days = _clamp(state.cycle_mad_days * 1.03, 0.1, cfg.max_cycle_days)
        elif "ran out" in reason or "נגמר" in reason or "empty" in reason:
            # Might be a real cycle - learn weakly
            if state.cycle_started_at is not None:
                observed = _days_between(ev.ts, state.cycle_started_at)
                observed = _clamp(observed, cfg.min_cycle_days, cfg.max_cycle_days)
                # Very weak update (20% of alpha_strong)
                a = cfg.alpha_strong * 0.2
                old_mean = state.cycle_mean_days
                new_mean = (1 - a) * old_mean + a * observed
                new_mean = _clamp(new_mean, cfg.min_cycle_days, cfg.max_cycle_days)
                state.cycle_mean_days = float(new_mean)
                # Update MAD slightly
                err = observed - old_mean
                new_mad = (1 - a) * state.cycle_mad_days + a * abs(err) * 0.5
                state.cycle_mad_days = float(_clamp(new_mad, 0.1, cfg.max_cycle_days))
            state.cycle_started_at = None
        else:
            # Default: don't learn consumption
            state.cycle_started_at = None
            state.cycle_mad_days = _clamp(state.cycle_mad_days * 1.03, 0.1, cfg.max_cycle_days)
        
        return state

    if ev.kind == FeedbackKind.EXACT:
        a = cfg.alpha_confirm
        state.cycle_mad_days = _clamp((1 - a) * state.cycle_mad_days, 0.1, cfg.max_cycle_days)
        return state

    # MORE / LESS - DO NOT update cycle_mean_days!
    # These feedbacks only affect days_left immediately (handled in API layer)
    # cycle_mean_days will be updated during weekly update based on observed cycle length
    if ev.kind in (FeedbackKind.MORE, FeedbackKind.LESS):
        # Just track that feedback was given (for weekly processing)
        # Don't update cycle_mean_days here
        state.last_feedback_at = ev.ts
        return state

    return state


# ----------------------------
# Prediction
# ----------------------------
def predict(state: CycleEmaState, now: datetime, multiplier: float, cfg: PredictorConfig, inventory_days_left: Optional[float] = None) -> Forecast:
    """
    Predict days left for a product.
    
    Args:
        state: Current predictor state
        now: Current timestamp
        multiplier: Consumption multiplier (from habits, >1 means faster consumption)
        cfg: Predictor configuration
        inventory_days_left: Optional current inventory days_left value (from user updates).
                           If provided, this value will be used as the base and multiplier applied to it.
    
    Returns:
        Forecast object with predicted days left, state, and confidence
    """
    days_left = compute_days_left(state, now, multiplier, cfg, inventory_days_left=inventory_days_left)
    st = derive_state(days_left, state.cycle_mean_days, cfg)
    conf = compute_confidence(state, now, cfg)
    return Forecast(
        expected_days_left=float(days_left),
        predicted_state=st,
        confidence=float(conf),
        generated_at=now,
    )


def stamp_last_prediction(state: CycleEmaState, forecast: Forecast) -> CycleEmaState:
    state.last_pred_days_left = float(forecast.expected_days_left)
    return state


# ----------------------------
# Inventory log -> internal events
# ----------------------------
def parse_feedback_from_note(note: Optional[str]) -> Optional[FeedbackKind]:
    """
    Supports:
    - JSON: {"feedback_kind":"MORE"}
    - plaintext containing keywords: more/less/exact/empty/wasted
    """
    if not note:
        return None

    s = note.strip()
    # try JSON
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            k = obj.get("feedback_kind") or obj.get("kind")
            if k:
                k = str(k).upper()
                if k in FeedbackKind.__members__:
                    return FeedbackKind[k]
                # allow DB value strings
                for fk in FeedbackKind:
                    if fk.value == k:
                        return fk
    except Exception:
        pass

    low = s.lower()
    if "wasted" in low or "thrown" in low or "נזרק" in low:
        return FeedbackKind.WASTED
    if "empty" in low or "out" in low or "נגמר" in low:
        return FeedbackKind.EMPTY
    if "exact" in low or "בול" in low:
        return FeedbackKind.EXACT
    if "more" in low or "יותר" in low:
        return FeedbackKind.MORE
    if "less" in low or "פחות" in low:
        return FeedbackKind.LESS
    return None


def map_inventory_log_row_to_event(row: Dict[str, Any]) -> Tuple[Optional[PurchaseEvent], Optional[FeedbackEvent]]:
    """
    Expected row keys:
      action, delta_state, occurred_at, source, note
    """
    action = (row.get("action") or "").upper()
    source = (row.get("source") or InventorySource.SYSTEM.value).upper()
    occurred_at = row.get("occurred_at")
    if isinstance(occurred_at, str):
        try:
            # Try to parse ISO format string
            # Handle different formats: "Z" suffix, "+00:00", or already has timezone
            occurred_at_str = occurred_at.replace("Z", "+00:00")
            
            # Fix microsecond precision if needed (Supabase sometimes returns 5 digits instead of 6)
            # Format: '2025-12-27T16:45:25.52139+00:00' -> '2025-12-27T16:45:25.521390+00:00'
            import re
            # Match pattern: .DDDDD+ or .DDDDD- (5 digits before timezone)
            match = re.search(r'\.(\d{1,6})([+-]\d{2}:\d{2})$', occurred_at_str)
            if match:
                microseconds = match.group(1)
                timezone_part = match.group(2)
                # Pad to 6 digits if less than 6
                if len(microseconds) < 6:
                    microseconds = microseconds.ljust(6, '0')
                # Replace in string
                occurred_at_str = re.sub(r'\.\d{1,6}([+-]\d{2}:\d{2})$', f'.{microseconds}\\1', occurred_at_str)
            
            occurred_at = datetime.fromisoformat(occurred_at_str)
        except (ValueError, AttributeError) as e:
            # Fallback: try parsing with dateutil if available, or use current time
            try:
                from dateutil import parser
                occurred_at = parser.isoparse(occurred_at)
            except (ImportError, ValueError):
                print(f"Warning: Could not parse occurred_at '{occurred_at}', using current time. Error: {e}")
                occurred_at = _now_utc()
    elif isinstance(occurred_at, datetime):
        # Already a datetime object
        pass
    else:
        occurred_at = None
    
    if occurred_at is None:
        occurred_at = _now_utc()
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)

    try:
        src_enum = InventorySource(source)
    except Exception:
        src_enum = InventorySource.SYSTEM

    # PURCHASE/RESET -> purchase event
    if action in (InventoryAction.PURCHASE.value, InventoryAction.RESET.value):
        return PurchaseEvent(ts=occurred_at, source=src_enum), None

    # ADJUST might represent feedback; prioritize explicit note
    note = row.get("note")
    fb = parse_feedback_from_note(note)
    if fb is not None:
        return None, FeedbackEvent(ts=occurred_at, kind=fb, source=src_enum, note=note)

    # Fallback: delta_state EMPTY/FULL can be interpreted
    delta_state = (row.get("delta_state") or "").upper()
    if delta_state == InventoryState.EMPTY.value:
        return None, FeedbackEvent(ts=occurred_at, kind=FeedbackKind.EMPTY, source=src_enum)
    if delta_state == InventoryState.FULL.value:
        return PurchaseEvent(ts=occurred_at, source=src_enum), None

    return None, None
