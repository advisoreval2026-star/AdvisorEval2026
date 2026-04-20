# TODO

## Done
- [x] Pull Google Doc text export
- [x] Parse into advisors + threaded comments with NSFW flag
- [x] Static Leaflet map + per-advisor cards with default-folded NSFW
- [x] Push to `advisoreval2026-star/AdvisorEval2026`
- [x] Enable GitHub Pages on `main` (manual step in repo Settings → Pages)
- [x] Supabase migration: `advisors` table + `source`/`nsfw`/`doc_hash` on `comments`
- [x] Sync script (`scripts/sync_supabase.py`) — idempotent upsert via `doc_hash`
- [x] Frontend reads live from Supabase (no more static `advisors.json` on root)
- [x] Daily CI sync (`.github/workflows/sync.yml`)

## Remaining one-time manual steps
- [ ] **Apply `scripts/migration.sql` in Supabase Dashboard → SQL Editor.**
- [ ] **Add repo secrets `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`** in
      `Settings → Secrets and variables → Actions`. The service-role key is under
      Supabase Project Settings → API.
- [ ] **First run**: trigger the sync workflow manually from the Actions tab
      (`workflow_dispatch`) to seed the DB with the current doc snapshot.

## Open
- [ ] Improve advisor-name extraction for edge cases (compound headings like `A / pre B Name`,
      name-first headings like `Name INST -> INST2`). A few entries still keep a fragment.
- [ ] Better threading for long in-line rebuttal chains (some collapse into walls of text).
- [ ] Add a small "add comment" form that POSTs to Supabase (using the anon key + RLS insert
      policy already in the base schema).
- [ ] Consider a password gate if the URL spreads wider than intended.
- [ ] Optional: delete doc comments from DB when they disappear from the doc (current
      default: keep forever).
