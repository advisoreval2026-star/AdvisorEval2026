#!/usr/bin/env python3
"""Sync Google Doc → Supabase.

Steps:
  1. Download the Google Doc as plain text (or reuse the local scripts/raw.txt).
  2. Run parse.py's machinery in-process → list of advisors with threaded comments.
  3. Upsert each advisor into `advisors`.
  4. Walk each advisor's comment tree and upsert comments with source='doc'.
     Each doc comment has a deterministic `doc_hash` so re-running is idempotent.

Env vars:
  SUPABASE_URL          e.g. https://xxxxx.supabase.co
  SUPABASE_SERVICE_KEY  service_role key (bypasses RLS, can write)
  DOC_URL               (optional) plain-text export URL; default is the hard-coded doc.

Requires: requests  (supabase-py would work too but `requests` keeps deps minimal).
"""
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import parse  # noqa: E402  — reuse parsing logic

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
DOC_URL = os.environ.get(
    "DOC_URL",
    "https://docs.google.com/document/d/1-AtKUh-xE1CPRRDVlfPx1d42Trhr7F8qQIw69hP85Ds/export?format=txt",
)

BASE_HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}


def sb_request(method, path, body=None, params=None, prefer="return=representation"):
    import urllib.parse
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    headers = dict(BASE_HEADERS)
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def upsert_advisor(row):
    return sb_request(
        "POST",
        "advisors",
        body=[row],
        params={"on_conflict": "key"},
        prefer="return=representation,resolution=merge-duplicates",
    ) or []


def doc_hash(advisor_key, parent_hash, body):
    h = hashlib.sha1()
    h.update(advisor_key.encode())
    h.update(b"::")
    h.update((parent_hash or "").encode())
    h.update(b"::")
    h.update(body.encode())
    return h.hexdigest()


def find_comment_by_hash(hsh):
    rows = sb_request(
        "GET",
        "comments",
        params={"doc_hash": f"eq.{hsh}", "select": "id"},
    ) or []
    return rows[0]["id"] if rows else None


def insert_doc_comment(advisor_key, body, parent_uuid, hsh, nsfw):
    row = {
        "advisor_key": advisor_key,
        "parent_id": parent_uuid,
        "author": "doc",
        "body": body[:5000],
        "op": False,
        "source": "doc",
        "nsfw": nsfw,
        "doc_hash": hsh,
    }
    rows = sb_request(
        "POST",
        "comments",
        body=[row],
        params={"on_conflict": "doc_hash"},
        prefer="return=representation,resolution=ignore-duplicates",
    ) or []
    if rows:
        return rows[0]["id"]
    return find_comment_by_hash(hsh)


def walk_comments(nodes, advisor_key, parent_hash=None, parent_uuid=None):
    for node in nodes:
        body = (node.get("text") or "").strip()
        if not body:
            # Skip empty wrappers; continue into replies as siblings of the parent
            walk_comments(node.get("replies", []), advisor_key, parent_hash, parent_uuid)
            continue
        hsh = doc_hash(advisor_key, parent_hash, body)
        existing = find_comment_by_hash(hsh)
        if existing:
            uuid = existing
        else:
            uuid = insert_doc_comment(
                advisor_key,
                body,
                parent_uuid,
                hsh,
                bool(node.get("nsfw")),
            )
            if not uuid:
                # Should not happen; abort to avoid cascading corrupt tree
                print(f"WARN: insert returned no id for {advisor_key}: {body[:40]}")
                continue
        walk_comments(node.get("replies", []), advisor_key, hsh, uuid)


def fetch_doc(local_path):
    """Refresh local raw.txt from the doc URL.

    Retries a few times with backoff on rate-limit (429). If the doc refuses
    to cooperate, we fall back to whatever raw.txt is already checked into
    the repo so the sync can still run.
    """
    import time
    print(f"fetching {DOC_URL}", flush=True)
    delays = [0, 10, 30, 60]
    last_err = None
    for i, wait in enumerate(delays):
        if wait:
            print(f"  retry in {wait}s…", flush=True)
            time.sleep(wait)
        try:
            req = urllib.request.Request(
                DOC_URL,
                headers={"User-Agent": "Mozilla/5.0 (advisor-eval-sync)"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            Path(local_path).write_text(text, encoding="utf-8")
            print(f"  fetched {len(text)} chars", flush=True)
            return
        except urllib.error.HTTPError as e:
            last_err = e
            print(f"  attempt {i + 1}: HTTP {e.code}", flush=True)
            if e.code != 429:
                break  # only retry rate-limits
        except Exception as e:
            last_err = e
            print(f"  attempt {i + 1}: {e}", flush=True)
    # Fallback: use whatever raw.txt already exists.
    if Path(local_path).exists():
        print(f"WARN: using existing raw.txt ({Path(local_path).stat().st_size} bytes); "
              f"last fetch error: {last_err}", flush=True)
        return
    raise RuntimeError(f"Could not fetch doc and no local raw.txt fallback: {last_err}")


def main():
    if os.environ.get("SKIP_FETCH") != "1":
        fetch_doc(Path(__file__).parent / "raw.txt")
    # Re-run parse.py's main() to regenerate advisors.json (used as the intermediate).
    parse.main()
    advisors = json.loads(
        (Path(__file__).parent / "advisors.json").read_text(encoding="utf-8")
    )
    print(f"loaded {len(advisors)} advisors to sync")
    for a in advisors:
        key = f"{a['advisor']}|{a['institution']}"
        advisor_row = {
            "key": key,
            "name": a["advisor"],
            "university": a["institution"],
            "region": a.get("region"),
            "lat": a.get("lat"),
            "lon": a.get("lon"),
            "list_type": a.get("list_type") or "black",
            "tag": (a.get("tag") or "")[:500] or None,
        }
        upsert_advisor(advisor_row)
        walk_comments(a.get("comments", []), key)
    print("sync complete")


if __name__ == "__main__":
    main()
