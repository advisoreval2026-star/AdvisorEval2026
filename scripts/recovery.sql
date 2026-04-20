-- =============================================================
-- Full schema recovery: base + map-view migration.
-- Safe to run multiple times (all statements are idempotent).
-- Paste the whole thing into Supabase → SQL Editor → Run.
-- =============================================================

-- ---------- Base schema (from rankmyadvisors/supabase_schema.sql) ----------

create table if not exists comments (
  id          uuid primary key default gen_random_uuid(),
  advisor_key text not null,
  parent_id   uuid references comments(id) on delete cascade,
  author      text not null default '匿名',
  body        text not null,
  op          boolean not null default false,
  score       int not null default 0,
  created_at  timestamptz not null default now()
);
create index if not exists comments_advisor_idx on comments(advisor_key);
create index if not exists comments_parent_idx  on comments(parent_id);
create index if not exists comments_created_idx on comments(created_at);

create table if not exists votes (
  voter_id   text not null,
  comment_id uuid not null references comments(id) on delete cascade,
  dir        smallint not null check (dir in (-1, 1)),
  primary key (voter_id, comment_id)
);

create or replace function cast_vote(p_comment uuid, p_voter text, p_dir smallint)
returns int language plpgsql security definer as $$
declare old_dir smallint; new_score int;
begin
  if p_dir not in (-1, 1) then raise exception 'dir must be -1 or 1'; end if;
  select dir into old_dir from votes where comment_id = p_comment and voter_id = p_voter;
  if old_dir is null then
    insert into votes(comment_id, voter_id, dir) values (p_comment, p_voter, p_dir);
    update comments set score = score + p_dir where id = p_comment returning score into new_score;
  elsif old_dir = p_dir then
    delete from votes where comment_id = p_comment and voter_id = p_voter;
    update comments set score = score - old_dir where id = p_comment returning score into new_score;
  else
    update votes set dir = p_dir where comment_id = p_comment and voter_id = p_voter;
    update comments set score = score - old_dir + p_dir where id = p_comment returning score into new_score;
  end if;
  return new_score;
end $$;

alter table comments enable row level security;
alter table votes    enable row level security;

drop policy if exists "comments_read"  on comments;
drop policy if exists "comments_write" on comments;
drop policy if exists "votes_read"     on votes;

create policy "comments_read"  on comments for select using (true);
create policy "comments_write" on comments for insert with check (
  length(body) between 1 and 5000 and
  length(author) between 1 and 80 and
  length(advisor_key) between 1 and 200
);
create policy "votes_read" on votes for select using (true);

create table if not exists reports (
  id         uuid primary key default gen_random_uuid(),
  comment_id uuid references comments(id) on delete cascade,
  reason     text,
  reporter   text,
  created_at timestamptz not null default now()
);
alter table reports enable row level security;
drop policy if exists "reports_write" on reports;
create policy "reports_write" on reports for insert with check (length(coalesce(reason,'')) <= 1000);

-- ---------- Map-view additions ----------

create table if not exists advisors (
  key         text primary key,
  name        text not null,
  university  text not null,
  region      text,
  lat         double precision,
  lon         double precision,
  list_type   text not null default 'black',
  tag         text,
  updated_at  timestamptz not null default now()
);
create index if not exists advisors_region_idx on advisors(region);
create index if not exists advisors_list_idx   on advisors(list_type);

alter table advisors enable row level security;
drop policy if exists "advisors_read" on advisors;
create policy "advisors_read" on advisors for select using (true);

alter table comments add column if not exists source   text    not null default 'user';
alter table comments add column if not exists nsfw     boolean not null default false;
alter table comments add column if not exists doc_hash text;

-- Non-partial unique index so PostgREST can use it as ON CONFLICT arbiter.
-- Postgres treats each NULL as distinct, so user comments with null doc_hash
-- still coexist.
create unique index if not exists comments_doc_hash_uidx
  on comments(doc_hash);
create index if not exists comments_source_idx on comments(source);

-- ---------- Force PostgREST to re-read the schema ----------
notify pgrst, 'reload schema';
