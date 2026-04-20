# Project notes

## Purpose
Static frontend (Leaflet map + threaded comments) backed by a shared Supabase
database. Periodically synced from an anonymous crowdsourced advisor-evaluation
Google Doc.

## Repo layout
- `index.html`, `style.css`, `app.js`, `config.js` — static frontend, served by
  GitHub Pages from repo root. `app.js` uses `supabase-js` at runtime to read
  `advisors` and `comments`.
- `scripts/parse.py` — Google Doc → `advisors.json` (parser).
- `scripts/sync_supabase.py` — runs parser, upserts everything into Supabase.
  Idempotent via `comments.doc_hash`.
- `scripts/migration.sql` — additive schema: creates `advisors`, extends `comments`.
- `scripts/raw.txt` — most recent plaintext snapshot of the Google Doc.
- `.github/workflows/sync.yml` — daily cron (06:00 UTC) that runs the sync and
  commits back any doc-snapshot diff.

## Supabase project (shared)
- Same project as the sibling board-view app (`AdvisorEval/rankmyadvisors`).
- Tables: `advisors` (map/list source), `comments` (both doc-sourced and user-added;
  distinguished by `source` column), `votes`, `reports`.
- Anon key is in `config.js` (public by design, RLS-limited).
- Service-role key lives **only** as a GitHub Actions secret.

## Sync model
- Advisors: upsert on `key = "<Name>|<University>"`. Re-runs update fields in place.
- Doc comments: each gets a deterministic `doc_hash = sha1(advisor_key ||
  parent_hash || body)`. Unique index → re-syncing is a no-op for unchanged rows.
- **Deletions are NOT propagated** — if a comment disappears from the doc later,
  it stays in the DB. This preserves the record; toggle later if needed.
- User comments are keyed by the same `advisor_key` with `source='user'`.

## Deploy
Enable GitHub Pages in repo **Settings → Pages**: Source = "Deploy from a branch",
Branch = `main`, Folder = `/` (root). URL:
`https://advisoreval2026-star.github.io/AdvisorEval2026/`

## Safety
- `noindex` meta on all pages.
- Unverified-content banner + per-entry badge.
- NSFW content default-folded (blurred), surfaced by per-comment reveal.
- Site is republishing an anonymous doc — repo owner should monitor and take it
  offline if there are abuse reports.
