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


def build_state_abbrev_cache(client):
    """Build a mapping of jurisdiction ID -> state abbreviation by fetching all state-level jurisdictions."""
    parent_to_abbrev = {}
    api_results = client.jurisdictions.list(level="s")
    for j in api_results.results:
        jd = vars(j)
        abbrev = jd.get("abbrev", "")
        if abbrev:
            parent_to_abbrev[jd["id"]] = abbrev.upper()
    print(f"  Cached {len(parent_to_abbrev)} state jurisdictions")
    return parent_to_abbrev


def resolve_state(client, jurisdiction_id, state_cache, jurisdiction_parents):
    """Resolve a local jurisdiction ID to a state abbreviation, caching parent lookups."""
    if jurisdiction_id in state_cache:
        return state_cache[jurisdiction_id]

    if jurisdiction_id in jurisdiction_parents:
        parent_id = jurisdiction_parents[jurisdiction_id]
    else:
        j = client.jurisdictions.get(jurisdiction_id)
        jd = vars(j)
        parent_id = jd.get("parent")
        jurisdiction_parents[jurisdiction_id] = parent_id

    if parent_id and parent_id in state_cache:
        abbrev = state_cache[parent_id]
        state_cache[jurisdiction_id] = abbrev
        return abbrev

    return None


def enrich_from_muckrock(agencies):
    """Enrich agencies with data from MuckRock's v2 API."""
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
        client.session.headers["User-Agent"] = (
            "Mozilla/5.0 (compatible; FoilFlock/1.0; +https://github.com/Foil-Flock)"
        )
        print(f"Authenticated as {username}")
    except Exception as e:
        print(f"MuckRock auth failed: {e}")
        return agencies

    print("  Building jurisdiction cache...")
    state_cache = build_state_abbrev_cache(client)
    jurisdiction_parents = {}

    matched = 0
    not_found = 0
    errors = 0
    total = len(agencies)

    for i, (agency_id, agency) in enumerate(agencies.items(), 1):
        if i % 50 == 0 or i == total:
            print(f"  Progress: {i}/{total} (matched={matched}, not_found={not_found}, errors={errors})")

        try:
            api_results = client.agencies.list(search=agency["name"])
            match = None
            for result in api_results.results:
                result_data = vars(result)
                jid = result_data.get("jurisdiction")
                if jid is None:
                    continue
                state_abbrev = resolve_state(client, jid, state_cache, jurisdiction_parents)
                if state_abbrev and state_abbrev == agency["state"].upper():
                    match = result_data
                    break

            if match:
                matched += 1
                mr_data = {
                    "muckrock_id": match.get("id"),
                }
                types = match.get("types")
                if types:
                    mr_data["agency_types"] = types
                agencies[agency_id] = merge_agency(agency, mr_data)
            else:
                not_found += 1

        except Exception as e:
            errors += 1
            print(f"  ! {agency['name']}: {e}")

    print(
        f"  Done: {matched} matched, {not_found} not found, {errors} errors"
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
