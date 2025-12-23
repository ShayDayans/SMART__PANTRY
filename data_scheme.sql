-- =========================================================
-- Smart Pantry (Demo) Schema — PostgreSQL / Supabase Auth
-- - IDs are UUID
-- - Household = one auth user (auth.users)
-- - Products & categories are GLOBAL (no user_id)
-- =========================================================

-- Supabase typically has this already, but safe to include:
create extension if not exists pgcrypto;

-- -------------------------
-- Enums (minimal, demo-safe)
-- -------------------------
do $$ begin
  create type inventory_state as enum ('EMPTY','LOW','MEDIUM','FULL','UNKNOWN');
exception when duplicate_object then null; end $$;

do $$ begin
  create type inventory_source as enum ('RECEIPT','SHOPPING_LIST','MANUAL','SYSTEM');
exception when duplicate_object then null; end $$;

do $$ begin
  create type inventory_action as enum ('PURCHASE','ADJUST','TRASH','EMPTY','REPURCHASE');
exception when duplicate_object then null; end $$;

-- Add REPURCHASE to existing enum if it doesn't exist
do $$ begin
  alter type inventory_action add value if not exists 'REPURCHASE';
exception when duplicate_object then null; end $$;

do $$ begin
  create type shopping_list_status as enum ('ACTIVE','COMPLETED','ARCHIVED');
exception when duplicate_object then null; end $$;

do $$ begin
  create type shopping_item_status as enum ('PLANNED','BOUGHT','NOT_FOUND','SKIPPED');
exception when duplicate_object then null; end $$;

do $$ begin
  create type item_added_by as enum ('USER','SYSTEM');
exception when duplicate_object then null; end $$;

do $$ begin
  create type habit_status as enum ('ACTIVE','INACTIVE','EXPIRED');
exception when duplicate_object then null; end $$;

do $$ begin
  create type habit_type as enum ('DIET','HOUSEHOLD','SHOPPING_SCHEDULE','OTHER');
exception when duplicate_object then null; end $$;

do $$ begin
  create type habit_input_source as enum ('CHAT','FORM','SYSTEM');
exception when duplicate_object then null; end $$;

do $$ begin
  create type predictor_method as enum ('RULES','EMA','BAYES_FILTER');
exception when duplicate_object then null; end $$;

-- -------------------------
-- Household Profile (using custom users table)
-- -------------------------
create table if not exists profiles (
  user_id        uuid primary key references users(user_id) on delete cascade,
  username       text,
  email          text, -- optional mirror; users is the source of truth
  created_at     timestamptz not null default now()
);

-- -------------------------
-- Global catalog
-- -------------------------
create table if not exists product_categories (
  category_id    uuid primary key default gen_random_uuid(),
  category_name  text not null unique
);

create table if not exists products (
  product_id     uuid primary key default gen_random_uuid(),
  product_name   text not null,
  category_id    uuid references product_categories(category_id) on delete set null,
  default_unit   text, -- keep flexible for demo: 'unit', 'g', 'ml', 'days', etc.
  unique (product_name)
);

-- -------------------------
-- Inventory snapshot (current belief per product per household)
-- -------------------------
create table if not exists inventory (
  user_id        uuid not null references users(user_id) on delete cascade,
  product_id     uuid not null references products(product_id) on delete cascade,
  state          inventory_state not null default 'UNKNOWN',

  -- Optional numeric estimate (could be qty, or "days left" if you set qty_unit='days')
  estimated_qty  numeric,
  qty_unit       text,

  confidence     real not null default 0.0,

  last_updated_at timestamptz not null default now(),
  last_source     inventory_source not null default 'SYSTEM',

  displayed_name text, -- optional per-user label for UI

  primary key (user_id, product_id)
);

-- -------------------------
-- Receipts + receipt items (OCR / parse output)
-- -------------------------
create table if not exists receipts (
  receipt_id     uuid primary key default gen_random_uuid(),
  user_id        uuid not null references users(user_id) on delete cascade,

  store_name     text,
  purchased_at   timestamptz,
  total_amount   numeric(12,2),

  raw_text       text, -- OCR output
  created_at     timestamptz not null default now()
);

create table if not exists receipt_items (
  receipt_item_id uuid primary key default gen_random_uuid(),
  receipt_id      uuid not null references receipts(receipt_id) on delete cascade,

  line_index      integer, -- preserves order; optional
  raw_label       text not null, -- REQUIRED per your note
  normalized_label text,

  product_id      uuid references products(product_id) on delete set null, -- nullable until confirmed
  match_confidence real,

  quantity        numeric,
  unit            text,
  unit_price      numeric(12,4),
  total_price     numeric(12,2),

  created_at      timestamptz not null default now(),

  unique (receipt_id, line_index)
);

-- -------------------------
-- Shopping lists
-- -------------------------
create table if not exists shopping_list (
  shopping_list_id uuid primary key default gen_random_uuid(),
  user_id          uuid not null references users(user_id) on delete cascade,

  title            text,
  status           shopping_list_status not null default 'ACTIVE',
  created_at       timestamptz not null default now(),
  notes            text
);

create table if not exists shopping_list_items (
  shopping_list_item_id uuid primary key default gen_random_uuid(),
  shopping_list_id      uuid not null references shopping_list(shopping_list_id) on delete cascade,

  product_id            uuid references products(product_id) on delete set null,
  free_text_name        text,

  recommended_qty       numeric,
  unit                  text,

  user_qty_override     numeric,

  status                shopping_item_status not null default 'PLANNED',
  priority              integer,
  added_by              item_added_by not null default 'USER',

  -- Feedback fields for model learning
  sufficiency_marked    boolean,
  actual_qty_purchased  numeric,
  qty_feedback          text,  -- 'LESS', 'MORE', 'EXACT', 'NOT_ENOUGH'

  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),

  -- enforce: either linked product OR free text
  constraint shopping_item_name_chk
    check (
      (product_id is not null and free_text_name is null)
      or
      (product_id is null and free_text_name is not null)
    )
);

-- -------------------------
-- Inventory log (event stream)
-- -------------------------
create table if not exists inventory_log (
  log_id           uuid primary key default gen_random_uuid(),
  user_id          uuid not null references users(user_id) on delete cascade,
  product_id       uuid not null references products(product_id) on delete cascade,

  action           inventory_action not null,
  delta_state      inventory_state,
  action_confidence real not null default 1.0,

  occurred_at      timestamptz not null default now(),
  source           inventory_source not null default 'SYSTEM',

  receipt_item_id  uuid references receipt_items(receipt_item_id) on delete set null,
  shopping_list_item_id uuid references shopping_list_items(shopping_list_item_id) on delete set null,

  note             text
);

-- -------------------------
-- Habits + habit inputs (structured + raw intake)
-- -------------------------
create table if not exists habits (
  habit_id        uuid primary key default gen_random_uuid(),
  user_id         uuid not null references users(user_id) on delete cascade,

  type            habit_type not null default 'OTHER',
  status          habit_status not null default 'ACTIVE',

  start_date      timestamptz,
  end_date        timestamptz,

  explanation     text,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  params          jsonb,
  effects         jsonb
);

create table if not exists habit_inputs (
  habit_input_id  uuid primary key default gen_random_uuid(),
  user_id         uuid not null references users(user_id) on delete cascade,
  habit_id        uuid references habits(habit_id) on delete set null,

  source          habit_input_source not null default 'CHAT',

  raw_text        text,
  extracted_json  jsonb,

  confirmed_at    timestamptz,
  created_at      timestamptz not null default now()
);

-- -------------------------
-- Predictor configuration + per-product predictor state (Path A)
-- -------------------------
create table if not exists predictor_profiles (
  predictor_profile_id uuid primary key default gen_random_uuid(),
  user_id              uuid not null references users(user_id) on delete cascade,

  name                 text not null,
  method               predictor_method not null default 'EMA',
  config               jsonb not null default '{}'::jsonb,

  is_active            boolean not null default false,
  created_at           timestamptz not null default now()
);

-- Ensure at most one active profile per user (demo-friendly)
create unique index if not exists uq_predictor_profiles_one_active
on predictor_profiles(user_id)
where is_active;

create table if not exists product_predictor_state (
  user_id              uuid not null references users(user_id) on delete cascade,
  product_id           uuid not null references products(product_id) on delete cascade,

  predictor_profile_id uuid not null references predictor_profiles(predictor_profile_id) on delete cascade,
  params               jsonb not null default '{}'::jsonb,

  confidence           real not null default 0.0,
  updated_at           timestamptz not null default now(),

  primary key (user_id, product_id)
);

-- -------------------------
-- Optional: persisted forecast snapshots (not required, but useful)
-- -------------------------
create table if not exists inventory_forecasts (
  forecast_id       uuid primary key default gen_random_uuid(),
  user_id           uuid not null references users(user_id) on delete cascade,
  product_id        uuid not null references products(product_id) on delete cascade,

  generated_at      timestamptz not null default now(),
  expected_days_left numeric,
  predicted_state   inventory_state not null default 'UNKNOWN',
  confidence        real not null default 0.0,

  trigger_log_id    uuid references inventory_log(log_id) on delete set null
);

-- -------------------------
-- Performance indexes (minimal)
-- -------------------------
create index if not exists idx_inventory_log_user_product_time
  on inventory_log(user_id, product_id, occurred_at desc);

create index if not exists idx_receipts_user_time
  on receipts(user_id, purchased_at desc);

create index if not exists idx_receipt_items_receipt
  on receipt_items(receipt_id);

create index if not exists idx_shopping_list_user_status
  on shopping_list(user_id, status);

create index if not exists idx_shopping_list_items_list
  on shopping_list_items(shopping_list_id);

create index if not exists idx_product_predictor_state_profile
  on product_predictor_state(predictor_profile_id);

create index if not exists idx_inventory_forecasts_user_product_time
  on inventory_forecasts(user_id, product_id, generated_at desc);
