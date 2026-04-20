# Project notes

## Purpose
Static visualization (map + threaded comments) of an anonymous crowdsourced
advisor-evaluation Google Doc.

## Layout
- `index.html`, `style.css`, `app.js` — static frontend, served by GitHub Pages from repo root.
- `advisors.json` — parsed data loaded by `app.js` at runtime.
- `scripts/parse.py` — parser turning `scripts/raw.txt` → `advisors.json`.
- `scripts/raw.txt` — plain-text export of the source Google Doc (snapshot).

## Regenerating data
```
cd scripts && python3 parse.py   # writes advisors.json in scripts/
cp scripts/advisors.json ../advisors.json
```
Re-fetch the source with:
```
curl -sL "https://docs.google.com/document/d/1-AtKUh-xE1CPRRDVlfPx1d42Trhr7F8qQIw69hP85Ds/export?format=txt" -o scripts/raw.txt
```

## Deploy
Enable GitHub Pages in repo **Settings → Pages**: Source = "Deploy from a branch",
Branch = `main`, Folder = `/` (root). URL becomes
`https://advisoreval2026-star.github.io/AdvisorEval2026/`.

## Safety
- `noindex` meta on all pages to keep the site out of search engines.
- Unverified-content banner + per-entry badge.
- NSFW content default-folded (blurred).
- Content is republished from a public Google Doc — the owner of this repo should monitor
  and take it offline if there are abuse reports.
