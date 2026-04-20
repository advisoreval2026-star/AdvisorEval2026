# Changelog

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
