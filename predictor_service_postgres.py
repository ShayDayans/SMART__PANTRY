from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# You need a DB-API connection (psycopg3 / psycopg2).
# This module is written to be simple and explicit.
# Example with psycopg3:
#   import psycopg
#   conn = psycopg.connect(dsn)

from ema_cycle_predictor import (
    PredictorConfig, CycleEmaState, Forecast,
    init_state_from_category, apply_purchase, apply_feedback,
    predict, stamp_last_prediction, map_inventory_log_row_to_event,
    InventoryState, InventorySource
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ActiveProfile:
    predictor_profile_id: str
    user_id: str
    method: str
    config: Dict[str, Any]


class PantryRepository:
    """
    Minimal repository targeting your schema:
      predictor_profiles, product_predictor_state, inventory, inventory_log,
      products, inventory_forecasts, habits (optional)
    """

    def __init__(self, conn):
        self.conn = conn

    # ---------- profiles ----------
    def get_active_predictor_profile(self, user_id: str) -> ActiveProfile:
        q = """
        select predictor_profile_id::text, user_id::text, method::text, config
        from predictor_profiles
        where user_id = %s and is_active = true
        limit 1;
        """
        with self.conn.cursor() as cur:
            cur.execute(q, (user_id,))
            row = cur.fetchone()
        if not row:
            raise RuntimeError("No active predictor_profile for this user. Set predictor_profiles.is_active=true for one profile.")
        return ActiveProfile(
            predictor_profile_id=row[0],
            user_id=row[1],
            method=row[2],
            config=row[3] or {},
        )

    # ---------- products ----------
    def get_user_inventory_products(self, user_id: str) -> List[Tuple[str, Optional[str]]]:
        """
        Returns list of (product_id, category_id) for products currently in inventory table.
        category_id is derived from products.category_id.
        """
        q = """
        select i.product_id::text, p.category_id::text
        from inventory i
        join products p on p.product_id = i.product_id
        where i.user_id = %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(q, (user_id,))
            rows = cur.fetchall()
        return [(r[0], r[1]) for r in rows]

    # ---------- state ----------
    def get_predictor_state(self, user_id: str, product_id: str) -> Optional[Tuple[Dict[str, Any], float, datetime, str]]:
        """
        Returns (params_json, confidence, updated_at, predictor_profile_id)
        """
        q = """
        select params, confidence, updated_at, predictor_profile_id::text
        from product_predictor_state
        where user_id = %s and product_id = %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(q, (user_id, product_id))
            row = cur.fetchone()
        if not row:
            return None
        return row[0] or {}, float(row[1]), row[2], row[3]

    def upsert_predictor_state(
        self,
        user_id: str,
        product_id: str,
        predictor_profile_id: str,
        params: Dict[str, Any],
        confidence: float,
        updated_at: datetime,
    ) -> None:
        q = """
        insert into product_predictor_state
          (user_id, product_id, predictor_profile_id, params, confidence, updated_at)
        values
          (%s, %s, %s, %s::jsonb, %s, %s)
        on conflict (user_id, product_id)
        do update set
          predictor_profile_id = excluded.predictor_profile_id,
          params = excluded.params,
          confidence = excluded.confidence,
          updated_at = excluded.updated_at;
        """
        with self.conn.cursor() as cur:
            cur.execute(q, (user_id, product_id, predictor_profile_id, params, confidence, updated_at))

    # ---------- inventory ----------
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
        q = """
        insert into inventory
          (user_id, product_id, state, estimated_qty, qty_unit, confidence, last_updated_at, last_source, displayed_name)
        values
          (%s, %s, %s, %s, 'days', %s, now(), %s, coalesce(%s, displayed_name))
        on conflict (user_id, product_id)
        do update set
          state = excluded.state,
          estimated_qty = excluded.estimated_qty,
          qty_unit = excluded.qty_unit,
          confidence = excluded.confidence,
          last_updated_at = excluded.last_updated_at,
          last_source = excluded.last_source,
          displayed_name = coalesce(excluded.displayed_name, inventory.displayed_name);
        """
        with self.conn.cursor() as cur:
            cur.execute(q, (user_id, product_id, state.value, days_left, confidence, source.value, displayed_name))

    # ---------- forecasts ----------
    def insert_forecast(
        self,
        user_id: str,
        product_id: str,
        forecast: Forecast,
        trigger_log_id: Optional[str],
    ) -> None:
        q = """
        insert into inventory_forecasts
          (user_id, product_id, generated_at, expected_days_left, predicted_state, confidence, trigger_log_id)
        values
          (%s, %s, %s, %s, %s, %s, %s);
        """
        with self.conn.cursor() as cur:
            cur.execute(
                q,
                (
                    user_id,
                    product_id,
                    forecast.generated_at,
                    forecast.expected_days_left,
                    forecast.predicted_state.value,
                    forecast.confidence,
                    trigger_log_id,
                ),
            )

    # ---------- inventory log ----------
    def get_inventory_log_row(self, log_id: str) -> Dict[str, Any]:
        q = """
        select
          log_id::text, user_id::text, product_id::text,
          action::text, delta_state::text, action_confidence,
          occurred_at, source::text, note
        from inventory_log
        where log_id = %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(q, (log_id,))
            row = cur.fetchone()
        if not row:
            raise RuntimeError(f"inventory_log row not found for log_id={log_id}")
        return {
            "log_id": row[0],
            "user_id": row[1],
            "product_id": row[2],
            "action": row[3],
            "delta_state": row[4],
            "action_confidence": float(row[5]),
            "occurred_at": row[6],
            "source": row[7],
            "note": row[8],
        }

    # ---------- habits (optional) ----------
    def get_active_habit_multiplier(self, user_id: str, product_id: str, category_id: Optional[str], now: datetime) -> float:
        """
        Reads habits.effects JSON and returns a multiplier >= 1e-6.
        Suggested effects JSON (examples):
          {"product_multipliers":{"<product_id>":1.2}}
          {"category_multipliers":{"<category_id>":1.3}}
          {"global_multiplier":1.1}
        """
        q = """
        select effects
        from habits
        where user_id = %s
          and status = 'ACTIVE'
          and (start_date is null or start_date <= %s)
          and (end_date is null or end_date >= %s);
        """
        effects_list: List[Dict[str, Any]] = []
        with self.conn.cursor() as cur:
            cur.execute(q, (user_id, now, now))
            rows = cur.fetchall()
        for (effects,) in rows:
            if isinstance(effects, dict):
                effects_list.append(effects)

        mult = 1.0
        pid = str(product_id)
        cid = str(category_id) if category_id else None

        for eff in effects_list:
            try:
                gm = eff.get("global_multiplier")
                if gm is not None:
                    mult *= float(gm)

                pm = eff.get("product_multipliers") or {}
                if pid in pm:
                    mult *= float(pm[pid])

                if cid:
                    cm = eff.get("category_multipliers") or {}
                    if cid in cm:
                        mult *= float(cm[cid])
            except Exception:
                continue

        return float(max(mult, 1e-6))

    # ---------- transaction ----------
    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()


class PantryPredictorService:
    def __init__(self, repo: PantryRepository):
        self.repo = repo

    def _load_cfg_and_profile(self, user_id: str) -> Tuple[str, PredictorConfig]:
        prof = self.repo.get_active_predictor_profile(user_id)
        cfg = PredictorConfig.from_profile_config_json(prof.config or {})
        return prof.predictor_profile_id, cfg

    def _load_or_init_state(
        self,
        user_id: str,
        product_id: str,
        predictor_profile_id: str,
        cfg: PredictorConfig,
        category_id: Optional[str],
        now: datetime,
    ) -> CycleEmaState:
        row = self.repo.get_predictor_state(user_id, product_id)
        if row is None:
            st = init_state_from_category(category_id, cfg, now=now)
            # keep category in state for future
            st.category_id = str(category_id) if category_id else None
            return st

        params_json, _conf, _updated_at, _ppid = row
        st = CycleEmaState.from_params_json(params_json)
        # ensure category_id is present (optional)
        if st.category_id is None and category_id is not None:
            st.category_id = str(category_id)
        return st

    def process_inventory_log(self, log_id: str) -> None:
        """
        Trigger-style: call this whenever you insert inventory_log.
        It will update predictor_state + inventory + insert a forecast snapshot.
        """
        row = self.repo.get_inventory_log_row(log_id)
        user_id = row["user_id"]
        product_id = row["product_id"]
        now = _now_utc()

        predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)

        # get category_id via inventory join products
        # (fast route: reuse get_user_inventory_products for the one product)
        products = dict(self.repo.get_user_inventory_products(user_id))
        category_id = products.get(product_id)

        state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)

        purchase_ev, feedback_ev = map_inventory_log_row_to_event(row)

        if purchase_ev is not None:
            state = apply_purchase(state, purchase_ev)

        if feedback_ev is not None:
            state = apply_feedback(state, feedback_ev, cfg)

        # prediction (apply habits multiplier)
        mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
        fc = predict(state, now, mult, cfg)

        # stamp last prediction for future MORE/LESS/EXACT
        state = stamp_last_prediction(state, fc)

        # persist
        self.repo.upsert_predictor_state(
            user_id=user_id,
            product_id=product_id,
            predictor_profile_id=predictor_profile_id,
            params=state.to_params_json(),
            confidence=fc.confidence,
            updated_at=now,
        )

        self.repo.upsert_inventory_days_estimate(
            user_id=user_id,
            product_id=product_id,
            days_left=fc.expected_days_left,
            state=fc.predicted_state,
            confidence=fc.confidence,
            source=InventorySource.SYSTEM,
        )

        # optional history/debug snapshot
        self.repo.insert_forecast(user_id, product_id, fc, trigger_log_id=row["log_id"])

        self.repo.commit()

    def refresh_user_inventory_forecasts(self, user_id: str) -> None:
        """
        On-demand refresh: recompute for all products in inventory.
        Useful on login / inventory screen.
        """
        now = _now_utc()
        predictor_profile_id, cfg = self._load_cfg_and_profile(user_id)

        items = self.repo.get_user_inventory_products(user_id)  # [(product_id, category_id)]
        for product_id, category_id in items:
            state = self._load_or_init_state(user_id, product_id, predictor_profile_id, cfg, category_id, now)
            mult = self.repo.get_active_habit_multiplier(user_id, product_id, category_id, now)
            fc = predict(state, now, mult, cfg)
            state = stamp_last_prediction(state, fc)

            self.repo.upsert_predictor_state(
                user_id=user_id,
                product_id=product_id,
                predictor_profile_id=predictor_profile_id,
                params=state.to_params_json(),
                confidence=fc.confidence,
                updated_at=now,
            )
            self.repo.upsert_inventory_days_estimate(
                user_id=user_id,
                product_id=product_id,
                days_left=fc.expected_days_left,
                state=fc.predicted_state,
                confidence=fc.confidence,
                source=InventorySource.SYSTEM,
            )
            # forecast row is optional here; you can skip to reduce writes:
            self.repo.insert_forecast(user_id, product_id, fc, trigger_log_id=None)

        self.repo.commit()
