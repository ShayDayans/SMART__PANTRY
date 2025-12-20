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
    alpha_strong: float = 0.25    # for EMPTY / observed cycles
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

    last_pred_days_left: Optional[float] = None
    censored_cycles: int = 0
    waste_events: int = 0

    # Optional for convenience
    category_id: Optional[str] = None

    def to_params_json(self) -> Dict[str, Any]:
        d = asdict(self)
        # datetimes -> iso
        for k in ["cycle_started_at", "last_purchase_at", "last_update_at"]:
            if d[k] is not None:
                d[k] = d[k].astimezone(timezone.utc).isoformat()
        return d

    @staticmethod
    def from_params_json(params: Dict[str, Any]) -> "CycleEmaState":
        def parse_dt(x: Any) -> Optional[datetime]:
            if x is None:
                return None
            if isinstance(x, datetime):
                return x
            if isinstance(x, str) and x.strip():
                # expects ISO string; timezone recommended
                return datetime.fromisoformat(x.replace("Z", "+00:00"))
            return None

        return CycleEmaState(
            cycle_mean_days=float(params.get("cycle_mean_days", 7.0)),
            cycle_mad_days=float(params.get("cycle_mad_days", 2.0)),
            cycle_started_at=parse_dt(params.get("cycle_started_at")),
            last_purchase_at=parse_dt(params.get("last_purchase_at")),
            last_update_at=parse_dt(params.get("last_update_at")) or datetime.now(timezone.utc),
            n_strong_updates=int(params.get("n_strong_updates", 0)),
            n_total_updates=int(params.get("n_total_updates", 0)),
            last_pred_days_left=(None if params.get("last_pred_days_left") is None else float(params["last_pred_days_left"])),
            censored_cycles=int(params.get("censored_cycles", 0)),
            waste_events=int(params.get("waste_events", 0)),
            category_id=(None if params.get("category_id") is None else str(params["category_id"])),
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
    if ratio >= cfg.full_ratio:
        return InventoryState.FULL
    if ratio >= cfg.medium_ratio:
        return InventoryState.MEDIUM
    return InventoryState.LOW


def compute_confidence(state: CycleEmaState, now: datetime, cfg: PredictorConfig) -> float:
    # evidence: relies mostly on strong updates ("EMPTY"/cycle observations)
    evidence = _sigmoid(state.n_strong_updates / 3.0)

    # stability: penalize large mad relative to mean
    stability = 1.0 - (state.cycle_mad_days / max(state.cycle_mean_days, 1.0))
    stability = _clamp(stability, 0.0, 1.0)

    # recency: exponential decay
    days_since = _days_between(now, state.last_update_at)
    recency = math.exp(-days_since / max(cfg.recency_tau_days, 1e-6))

    conf = 0.1 + 0.9 * evidence * stability * recency
    return float(_clamp(conf, 0.0, 1.0))


def compute_days_left(state: CycleEmaState, now: datetime, multiplier: float, cfg: PredictorConfig) -> float:
    """
    multiplier > 1 means faster consumption => fewer days left.
    This is applied at prediction time only (habits temporary modifiers).
    """
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
        last_pred_days_left=None,
        censored_cycles=0,
        waste_events=0,
        category_id=(str(category_id) if category_id is not None else None),
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


def apply_purchase(state: CycleEmaState, ev: PurchaseEvent) -> CycleEmaState:
    # If a cycle is currently active and a purchase occurs before EMPTY,
    # mark it censored and start a new cycle.
    if state.cycle_started_at is not None:
        state.censored_cycles += 1

    state.cycle_started_at = ev.ts
    state.last_purchase_at = ev.ts
    state.last_update_at = ev.ts
    # no mean/mad update
    return state


def apply_feedback(state: CycleEmaState, ev: FeedbackEvent, cfg: PredictorConfig) -> CycleEmaState:
    state.last_update_at = ev.ts
    state.n_total_updates += 1

    if ev.kind == FeedbackKind.EMPTY:
        # Strong observation: close cycle
        if state.cycle_started_at is None:
            # no active cycle; treat as noisy signal: only increase mad slightly
            state.cycle_mad_days = _clamp(state.cycle_mad_days * 1.05, 0.1, cfg.max_cycle_days)
            return state

        observed = _days_between(ev.ts, state.cycle_started_at)
        observed = _clamp(observed, cfg.min_cycle_days, cfg.max_cycle_days)

        old_mean = state.cycle_mean_days
        a = cfg.alpha_strong

        # EMA update for mean
        new_mean = (1 - a) * old_mean + a * observed
        new_mean = _clamp(new_mean, cfg.min_cycle_days, cfg.max_cycle_days)

        # Robust-ish error tracking via MAD
        err = observed - old_mean
        new_mad = (1 - a) * state.cycle_mad_days + a * abs(err)
        new_mad = _clamp(new_mad, 0.1, cfg.max_cycle_days)

        state.cycle_mean_days = float(new_mean)
        state.cycle_mad_days = float(new_mad)

        state.n_strong_updates += 1

        # no active cycle until next purchase
        state.cycle_started_at = None
        return state

    if ev.kind == FeedbackKind.WASTED:
        state.waste_events += 1
        # do not learn consumption; set empty/no active cycle
        state.cycle_started_at = None
        # slightly reduce stability
        state.cycle_mad_days = _clamp(state.cycle_mad_days * 1.03, 0.1, cfg.max_cycle_days)
        return state

    if ev.kind == FeedbackKind.EXACT:
        a = cfg.alpha_confirm
        state.cycle_mad_days = _clamp((1 - a) * state.cycle_mad_days, 0.1, cfg.max_cycle_days)
        return state

    # MORE / LESS
    if ev.kind in (FeedbackKind.MORE, FeedbackKind.LESS):
        a = cfg.alpha_weak
        base = state.last_pred_days_left
        if base is None or base <= 0:
            # fallback: fixed small step
            raw_delta = 1.0
        else:
            raw_delta = cfg.more_less_ratio * float(base)

        delta = _clamp(raw_delta, 0.0, cfg.more_less_step_cap_days)

        target_mean = state.cycle_mean_days + (delta if ev.kind == FeedbackKind.MORE else -delta)
        target_mean = _clamp(target_mean, cfg.min_cycle_days, cfg.max_cycle_days)

        # smooth towards target
        state.cycle_mean_days = float((1 - a) * state.cycle_mean_days + a * target_mean)
        state.cycle_mad_days = float(_clamp((1 - a) * state.cycle_mad_days + a * abs(delta), 0.1, cfg.max_cycle_days))
        return state

    return state


# ----------------------------
# Prediction
# ----------------------------
def predict(state: CycleEmaState, now: datetime, multiplier: float, cfg: PredictorConfig) -> Forecast:
    days_left = compute_days_left(state, now, multiplier, cfg)
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
        occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
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
    fb = parse_feedback_from_note(row.get("note"))
    if fb is not None:
        return None, FeedbackEvent(ts=occurred_at, kind=fb, source=src_enum)

    # Fallback: delta_state EMPTY/FULL can be interpreted
    delta_state = (row.get("delta_state") or "").upper()
    if delta_state == InventoryState.EMPTY.value:
        return None, FeedbackEvent(ts=occurred_at, kind=FeedbackKind.EMPTY, source=src_enum)
    if delta_state == InventoryState.FULL.value:
        return PurchaseEvent(ts=occurred_at, source=src_enum), None

    return None, None
