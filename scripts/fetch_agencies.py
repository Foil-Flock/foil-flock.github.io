#!/usr/bin/env python3
"""
Fetch and merge agency data from upstream sources into agencies.json.

Data sources:
  1. FlockRadar GitHub export (open-source ALPR deployment data)
  2. MuckRock API (agency contact information)

Usage:
  python3 scripts/fetch_agencies.py

  Authentication (required — MuckRock API requires login):

  Set SQ_USERNAME and SQ_PASSWORD env vars (your MuckRock account).
  Requires: pip install python-muckrock

This script merges upstream data with existing agencies.json,
preserving any manual edits or community contributions. It never
deletes agencies — only adds new ones or updates fields that were
previously null.
"""

import json
import os
from pathlib import Path

AGENCIES_PATH = Path(__file__).parent.parent / "src" / "data" / "agencies.json"


def load_existing():
    """Load the current agencies.json, preserving manual edits."""
    if AGENCIES_PATH.exists():
        with open(AGENCIES_PATH) as f:
            data = json.load(f)
        return {a["id"]: a for a in data.get("agencies", [])}
    return {}


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


def enrich_from_muckrock(agencies):
    """Enrich agencies with contact info from MuckRock's v2 API."""
    import time

    try:
        from muckrock import MuckRock
    except ImportError:
        print("python-muckrock not installed. Run: pip install python-muckrock")
        return agencies

    username = os.environ.get("SQ_USERNAME", "")
    password = os.environ.get("SQ_PASSWORD", "")
    if not username:
        print("Set SQ_USERNAME and SQ_PASSWORD env vars for MuckRock auth")
        return agencies

    try:
        client = MuckRock(username=username, password=password)
        print(f"Authenticated as {username}")
    except Exception as e:
        print(f"MuckRock auth failed: {e}")
        return agencies

    enriched = 0
    skipped = 0
    not_found = 0

    for agency_id, agency in agencies.items():
        contact = agency.get("contact", {})
        if contact.get("email") and contact.get("mailing_address"):
            skipped += 1
            continue

        for attempt in range(3):
            try:
                results = client.agencies.list(search=agency["name"])
                match = None
                for result in results:
                    result_data = vars(result)
                    jurisdiction = result_data.get("jurisdiction", {})
                    if isinstance(jurisdiction, dict):
                        abbrev = jurisdiction.get("abbreviation", "")
                    else:
                        abbrev = ""
                    if abbrev.upper() == agency["state"].upper():
                        match = result_data
                        break

                if not match:
                    not_found += 1
                else:
                    mr_contact = {
                        "email": match.get("email") or None,
                        "phone": match.get("phone") or None,
                        "form_url": match.get("url") or None,
                        "mailing_address": match.get("address") or None,
                    }
                    if any(v is not None for v in mr_contact.values()):
                        agencies[agency_id] = merge_agency(
                            agency, {"contact": mr_contact}
                        )
                        enriched += 1
                        print(f"  + {agency['name']}: enriched contact info")
                break

            except Exception as e:
                if "503" in str(e) and attempt < 2:
                    wait = 5 * (attempt + 1)
                    print(f"  ~ {agency['name']}: 503, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"  ! {agency['name']}: {e}")
                break

        time.sleep(1.5)

    print(
        f"  Enriched {enriched}, skipped {skipped} (already complete),"
        f" {not_found} not found"
    )
    return agencies


def main():
    print("Loading existing agencies...")
    agencies = load_existing()
    print(f"  Found {len(agencies)} existing agencies")

    print("\nEnriching from MuckRock API...")
    agencies = enrich_from_muckrock(agencies)

    save_agencies(agencies)
    print("\nDone.")


if __name__ == "__main__":
    main()
