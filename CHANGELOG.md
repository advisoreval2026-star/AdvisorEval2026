# Changelog

## 2026-04-20 — Supabase integration

- New schema migration `scripts/migration.sql`:
  - Creates `advisors` table (key, name, university, region, lat, lon, list_type, tag).
  - Adds `source`, `nsfw`, `doc_hash` columns to existing `comments` table.
  - Unique index on `comments.doc_hash` so doc sync is idempotent.
- New `scripts/sync_supabase.py`: refreshes `raw.txt` from the Google Doc, re-runs the
  parser, upserts advisors, and walks each advisor's threaded comments, inserting any
  with a new deterministic hash.
- New GitHub Actions workflow `.github/workflows/sync.yml`: daily cron (06:00 UTC) that
  runs the sync and (if the doc snapshot changed) commits the updated `raw.txt` /
  `advisors.json` back to `main`.
- Frontend rewrite: `app.js` no longer reads `advisors.json`. It creates a Supabase
  client, pulls `advisors` at load, then fetches all comments in one background pass
  and builds threads client-side. `config.js` re-uses the same Supabase project as the
  board-view (`rankmyadvisors`) — one DB, two frontends.
- Removed stale `advisors.json` from repo root (source of truth is now Supabase).
- Added a per-comment `user` badge to distinguish user-added rebuttals from doc content.

## 2026-04-20 — Initial build

- Added `scripts/parse.py`: parses `scripts/raw.txt` (Google Doc export) into `advisors.json`.
  Heuristic heading detection by known-institution prefix match; name cleanup strips leading
  dept qualifiers, arrow markers, and institution word fragments.
- Threaded-comment parser recursively splits `()`, `（）`, `[]`, `【】` into reply trees.
- NSFW bubble-up: a comment is flagged if itself or any descendant matches NSFW patterns.
- Static frontend (`index.html` + `style.css` + `app.js`) uses Leaflet + MarkerCluster on a CARTO
  dark basemap; one circle-marker per institution, sized by advisor count and colored by
  black/red/both dominance.
- Filters: list-type toggles, free-text search, institution filter (click marker).
- NSFW content is default-folded (blurred); per-comment or global reveal.
- `<meta name="robots" content="noindex, nofollow, noarchive">` on all pages.
- Top-of-page disclaimer labels all entries **unverified**.
