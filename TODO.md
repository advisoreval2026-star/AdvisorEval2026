# TODO

## Done
- [x] Pull Google Doc text export
- [x] Parse into `advisors.json` with institution / advisor / region / list_type / threaded comments
- [x] NSFW flag + default fold
- [x] Static Leaflet map + per-advisor cards
- [x] Push to `advisoreval2026-star/AdvisorEval2026`
- [x] Enable GitHub Pages on `main` (manual step in repo Settings → Pages)

## Open
- [ ] Improve advisor-name extraction for edge cases (compound headings like `A / pre B Name`,
      name-first headings like `Name INST -> INST2`). Some names still keep a fragment.
- [ ] Better threading: currently every parenthetical becomes a reply. Multi-reply siblings
      within a single bullet are correctly separated, but chains of in-line rebuttals
      sometimes collapse into one wall of text (the doc's formatting is ambiguous).
- [ ] Add a "refresh data" script that re-pulls the doc and re-runs `parse.py` on CI.
- [ ] Consider adding a simple password gate if the URL spreads wider than intended.
