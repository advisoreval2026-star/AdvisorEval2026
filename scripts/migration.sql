-- =============================================================
-- Map view integration — additions on top of supabase_schema.sql
-- Paste into: Supabase Dashboard → SQL Editor → New query → Run
-- =============================================================

-- 1. Advisors table (shared between board view and map view).
create table if not exists advisors (
  key         text primary key,       -- "<Name>|<University>" (same convention as comments.advisor_key)
  name        text not null,
  university  text not null,
  region      text,
  lat         double precision,
  lon         double precision,
  list_type   text not null default 'black',   -- 'black' | 'red' | 'both'
  tag         text,
  updated_at  timestamptz not null default now()
);
create index if not exists advisors_region_idx on advisors(region);
create index if not exists advisors_list_idx   on advisors(list_type);

alter table advisors enable row level security;
drop policy if exists "advisors_read" on advisors;
create policy "advisors_read" on advisors for select using (true);
-- No public write: the periodic sync job writes via service_role (bypasses RLS).

-- 2. Extend comments with fields the map view needs.
alter table comments add column if not exists source   text    not null default 'user';    -- 'user' | 'doc'
alter table comments add column if not exists nsfw     boolean not null default false;
alter table comments add column if not exists doc_hash text;   -- deterministic hash for doc-sourced comments

-- Deterministic hash makes the sync idempotent: re-running inserts nothing new.
create unique index if not exists comments_doc_hash_uidx
  on comments(doc_hash)
  where doc_hash is not null;

create index if not exists comments_source_idx on comments(source);
