#!/usr/bin/env python3
"""
Fetch and merge agency data from upstream sources into agencies.json.

Data sources:
  1. FlockRadar GitHub export (open-source ALPR deployment data)
  2. MuckRock API (agency contact information)

Usage:
  python3 scripts/fetch_agencies.py

  Set MUCKROCK_TOKEN env var for authenticated MuckRock API access
  (optional — unauthenticated access works for agency lookups).

This script merges upstream data with existing agencies.json,
preserving any manual edits or community contributions. It never
deletes agencies — only adds new ones or updates fields that were
previously null.
"""

import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

AGENCIES_PATH = Path(__file__).parent.parent / "src" / "data" / "agencies.json"
MUCKROCK_API = "https://www.muckrock.com/api_v1"
MUCKROCK_TOKEN = os.environ.get("MUCKROCK_TOKEN")

# Rate limiting: MuckRock allows 1 req/sec sustained
RATE_LIMIT_DELAY = 1.1  # seconds between API calls


def load_existing():
    """Load the current agencies.json, preserving manual edits."""
    if AGENCIES_PATH.exists():
        with open(AGENCIES_PATH) as f:
            data = json.load(f)
        return {a["id"]: a for a in data.get("agencies", [])}
    return {}


def fetch_json(url, headers=None):
    """Fetch JSON from a URL with basic error handling."""
    req = Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    req.add_header("Accept", "application/json")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"  HTTP {e.code} fetching {url}", file=sys.stderr)
        return None


def fetch_muckrock_agency(name, state, jurisdiction):
    """
    Search MuckRock for an agency and return contact details.
    Returns dict with contact fields or None.
    """
    headers = {}
    if MUCKROCK_TOKEN:
        headers["Authorization"] = f"Token {MUCKROCK_TOKEN}"

    # Search by name within the state
    search_url = (
        f"{MUCKROCK_API}/agency/"
        f"?search={name}"
        f"&jurisdiction__abbreviation={state}"
        f"&format=json"
    )
    data = fetch_json(search_url, headers)
    time.sleep(RATE_LIMIT_DELAY)

    if not data or not data.get("results"):
        return None

    # Take the best match (first result)
    agency = data["results"][0]
    return {
        "email": agency.get("email") or None,
        "phone": agency.get("phone") or None,
        "form_url": agency.get("url") or None,
        "mailing_address": agency.get("address") or None,
    }


def make_agency_id(name, state):
    """Generate a URL-safe agency ID."""
    slug = name.lower()
    for char in [".", ",", "'", '"', "(", ")"]:
        slug = slug.replace(char, "")
    slug = slug.replace(" ", "-").replace("--", "-").strip("-")
    return f"{slug}-{state.lower()}"


def merge_agency(existing, new_data):
    """
    Merge new data into an existing agency record.
    Never overwrites non-null values with null.
    """
    merged = dict(existing)
    for key, value in new_data.items():
        if key == "contact":
            merged_contact = dict(merged.get("contact", {}))
            for ck, cv in value.items():
                if cv is not None and (ck not in merged_contact or merged_contact[ck] is None):
                    merged_contact[ck] = cv
            merged["contact"] = merged_contact
        elif key == "alpr":
            merged_alpr = dict(merged.get("alpr", {}))
            for ak, av in value.items():
                if av is not None and (ak not in merged_alpr or merged_alpr[ak] is None):
                    merged_alpr[ak] = av
            merged["alpr"] = merged_alpr
        elif key == "sources":
            existing_sources = set(merged.get("sources", []))
            merged["sources"] = list(existing_sources | set(value))
        elif value is not None and (key not in merged or merged[key] is None):
            merged[key] = value
    return merged


def save_agencies(agencies_by_id):
    """Write agencies.json, sorted by state then name."""
    agencies_list = sorted(
        agencies_by_id.values(),
        key=lambda a: (a.get("state", ""), a.get("name", "")),
    )
    output = {
        "_schema_version": "0.1.0",
        "_description": "Agency directory. Seeded from FlockRadar + MuckRock, extended by community contributions.",
        "_contributing": "To add or correct an agency, submit a PR editing this file. Include a source URL for any factual claim.",
        "agencies": agencies_list,
    }
    with open(AGENCIES_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(agencies_list)} agencies to {AGENCIES_PATH}")


def main():
    print("Loading existing agencies...")
    agencies = load_existing()
    print(f"  Found {len(agencies)} existing agencies")

    # ── Phase 1: Enrich existing agencies with MuckRock contact data ──
    if MUCKROCK_TOKEN:
        print("\nEnriching from MuckRock API...")
        enriched = 0
        for agency_id, agency in agencies.items():
            contact = agency.get("contact", {})
            if contact.get("email") and contact.get("mailing_address"):
                continue  # already has contact info

            mr_data = fetch_muckrock_agency(
                agency["name"],
                agency["state"],
                agency.get("jurisdiction", ""),
            )
            if mr_data:
                agencies[agency_id] = merge_agency(agency, {"contact": mr_data})
                enriched += 1
                print(f"  + {agency['name']}: enriched contact info")

        print(f"  Enriched {enriched} agencies from MuckRock")
    else:
        print("\nSkipping MuckRock enrichment (set MUCKROCK_TOKEN to enable)")

    # ── Phase 2: Save ─────────────────────────────────────────────────
    save_agencies(agencies)

    print("\nDone. To add FlockRadar data, export their dataset and run:")
    print("  python3 scripts/import_flockradar.py <export.json>")


if __name__ == "__main__":
    main()
