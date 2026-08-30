#!/usr/bin/env python3
"""
Import camera location data from the flock-finder WiFi detection dataset
and aggregate into agency-level records for agencies.json.

Data source: github.com/simeononsecurity/flock-finder
Method: WiFi OUI fingerprinting of Flock Safety devices via WiGLE.

Usage:
    python3 scripts/import_camera_data.py [--min-cameras 3] [--dry-run]

This script:
  1. Reads the flock-finder CSV (individual camera coordinates)
  2. Filters to US-only locations
  3. Aggregates by state + city
  4. Creates agency entries for jurisdictions with sufficient cameras
  5. Merges with existing agencies.json (never overwrites manual data)
  6. Writes enriched agencies.json sorted by state then name
"""

import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
AGENCIES_PATH = PROJECT_ROOT / "src" / "data" / "agencies.json"
CAMERA_CSV = SCRIPT_DIR / "flock_finder_raw.csv"

# US state abbreviations (for filtering)
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY",
}

# Cities that should map to county-level agencies instead of city PDs
# (unincorporated areas, townships, etc.)
COUNTY_OVERRIDE = set()  # populated dynamically

# Minimum cameras in a city to create an agency entry
DEFAULT_MIN_CAMERAS = 3

TODAY = date.today().isoformat()


def slugify(text):
    """Convert text to URL-safe slug."""
    slug = text.lower()
    for ch in [".", ",", "'", '"', "(", ")", "/", "\\", "&"]:
        slug = slug.replace(ch, "")
    slug = re.sub(r"\s+", "-", slug).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug


def make_agency_id(name, state):
    """Generate a unique agency ID from name and state."""
    return f"{slugify(name)}-{state.lower()}"


def load_existing_agencies():
    """Load current agencies.json into a dict keyed by ID."""
    if AGENCIES_PATH.exists():
        with open(AGENCIES_PATH) as f:
            data = json.load(f)
        return {a["id"]: a for a in data.get("agencies", [])}
    return {}


def parse_camera_csv(csv_path):
    """
    Parse the flock-finder CSV and return US camera counts by (state, city).

    Returns:
        dict: {(state, city): camera_count}
        dict: {state: total_cameras}
    """
    city_counts = Counter()
    state_totals = Counter()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            country = (row.get("country") or "").strip()
            state = (row.get("region") or "").strip()
            city = (row.get("city") or "").strip()

            # US only
            if country != "US" or state not in US_STATES:
                continue

            state_totals[state] += 1

            if city:
                # Normalize city names
                city = normalize_city(city)
                city_counts[(state, city)] += 1

    return city_counts, state_totals


def normalize_city(city):
    """Normalize city name for consistent grouping."""
    # Remove common suffixes/prefixes that vary in data
    city = city.strip()
    # "City of New York" -> "New York"
    if city.startswith("City of "):
        city = city[8:]
    # "Town of X" -> "X"
    if city.startswith("Town of "):
        city = city[8:]
    # "Village of X" -> "X"
    if city.startswith("Village of "):
        city = city[11:]
    return city


def infer_agency_name(city, state):
    """
    Infer the most likely agency operating ALPR cameras in a city.
    Returns (name, type, jurisdiction, jurisdiction_type).
    """
    # Major cities with known non-standard department names
    known_names = {
        ("New York", "NY"): ("New York City Police Department", "police", "New York City", "city"),
        ("Las Vegas", "NV"): ("Las Vegas Metropolitan Police Department", "police", "Las Vegas", "city"),
        ("Washington", "DC"): ("Metropolitan Police Department of the District of Columbia", "police", "Washington, D.C.", "district"),
        ("Indianapolis", "IN"): ("Indianapolis Metropolitan Police Department", "police", "Indianapolis", "city"),
        ("Nashville", "TN"): ("Metropolitan Nashville Police Department", "police", "Nashville", "city"),
        ("Louisville", "KY"): ("Louisville Metro Police Department", "police", "Louisville", "city"),
        ("Honolulu", "HI"): ("Honolulu Police Department", "police", "Honolulu", "city"),
        ("Jacksonville", "FL"): ("Jacksonville Sheriff's Office", "sheriff", "Jacksonville", "city"),
        ("Saint Paul", "MN"): ("Saint Paul Police Department", "police", "Saint Paul", "city"),
    }

    if (city, state) in known_names:
        return known_names[(city, state)]

    return (f"{city} Police Department", "police", city, "city")


def create_agency_entry(city, state, camera_count):
    """Create a new agency entry for a city."""
    name, agency_type, jurisdiction, jurisdiction_type = infer_agency_name(city, state)
    agency_id = make_agency_id(name, state)

    return {
        "id": agency_id,
        "name": name,
        "type": agency_type,
        "jurisdiction": jurisdiction,
        "jurisdiction_type": jurisdiction_type,
        "state": state,
        "contact": {
            "records_access_officer": None,
            "email": None,
            "phone": None,
            "form_url": None,
            "mailing_address": None,
            "submission_methods": ["mail"],
        },
        "alpr": {
            "vendor": "flock",
            "camera_count": camera_count,
            "retention_period": None,
            "contract_status": "unknown",
            "transparency_portal_url": None,
        },
        "sources": [
            "https://github.com/simeononsecurity/flock-finder",
        ],
        "last_verified": TODAY,
    }


def merge_agency(existing, new_data):
    """
    Merge new data into an existing agency record.
    Never overwrites non-null values with null.
    Updates camera_count if the new count is higher.
    """
    merged = dict(existing)

    # Update camera count if we have a higher number
    if new_data.get("alpr", {}).get("camera_count"):
        existing_count = merged.get("alpr", {}).get("camera_count") or 0
        new_count = new_data["alpr"]["camera_count"]
        if new_count > existing_count:
            if "alpr" not in merged:
                merged["alpr"] = {}
            merged["alpr"]["camera_count"] = new_count

    # Add sources without duplicating
    if "sources" in new_data:
        existing_sources = set(merged.get("sources", []))
        new_sources = set(new_data.get("sources", []))
        merged["sources"] = sorted(existing_sources | new_sources)

    # Update last_verified
    merged["last_verified"] = TODAY

    return merged


def save_agencies(agencies_by_id):
    """Write agencies.json sorted by state then name."""
    agencies_list = sorted(
        agencies_by_id.values(),
        key=lambda a: (a.get("state", ""), a.get("name", "")),
    )

    output = {
        "_schema_version": "0.2.0",
        "_description": (
            "Agency directory. Seeded from flock-finder WiFi detection data + "
            "MuckRock, extended by community contributions. Each entry represents "
            "one government agency with known or suspected ALPR deployments."
        ),
        "_contributing": (
            "To add or correct an agency, submit a PR editing this file. "
            "Include a source URL for any factual claim."
        ),
        "_camera_data_source": (
            "Camera counts derived from WiFi OUI fingerprinting via "
            "github.com/simeononsecurity/flock-finder. Counts represent "
            "detected devices, not confirmed installations."
        ),
        "agencies": agencies_list,
    }

    with open(AGENCIES_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return len(agencies_list)


def build_state_camera_counts(state_totals):
    """Write per-state camera count data for the stat grid."""
    counts_path = PROJECT_ROOT / "src" / "data" / "state_camera_counts.json"
    with open(counts_path, "w") as f:
        json.dump(
            {
                "_description": (
                    "Per-state camera counts from flock-finder WiFi detection. "
                    "These are detected devices, not confirmed installations."
                ),
                "_source": "github.com/simeononsecurity/flock-finder",
                "_updated": TODAY,
                "counts": dict(sorted(state_totals.items())),
            },
            f,
            indent=2,
        )
        f.write("\n")
    print(f"Wrote state camera counts to {counts_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Import flock-finder camera data")
    parser.add_argument(
        "--min-cameras",
        type=int,
        default=DEFAULT_MIN_CAMERAS,
        help=f"Minimum cameras to create agency entry (default: {DEFAULT_MIN_CAMERAS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be added without writing",
    )
    args = parser.parse_args()

    if not CAMERA_CSV.exists():
        print(f"Error: Camera CSV not found at {CAMERA_CSV}")
        print("Download it first:")
        print("  curl -sL https://raw.githubusercontent.com/simeononsecurity/flock-finder/main/data/flock_cameras.csv -o scripts/flock_finder_raw.csv")
        sys.exit(1)

    print("Parsing camera CSV...")
    city_counts, state_totals = parse_camera_csv(CAMERA_CSV)
    us_total = sum(state_totals.values())
    print(f"  {us_total:,} US cameras across {len(state_totals)} states")
    print(f"  {len(city_counts):,} distinct city+state combinations")

    # Filter to cities meeting the threshold
    qualified = {
        k: v for k, v in city_counts.items() if v >= args.min_cameras
    }
    print(f"  {len(qualified):,} cities with >= {args.min_cameras} cameras")

    # Load existing agencies
    print("\nLoading existing agencies...")
    agencies = load_existing_agencies()
    print(f"  {len(agencies)} existing agencies")

    # Track what we do
    added = 0
    updated = 0
    skipped = 0

    for (state, city), count in sorted(qualified.items(), key=lambda x: -x[1]):
        new_entry = create_agency_entry(city, state, count)
        agency_id = new_entry["id"]

        # Check for existing entry by ID or by matching name+state
        existing = agencies.get(agency_id)

        # Also check for fuzzy match on existing agencies in same state
        if not existing:
            for eid, eagency in agencies.items():
                if (
                    eagency.get("state") == state
                    and eagency.get("jurisdiction", "").lower() == city.lower()
                ):
                    existing = eagency
                    agency_id = eid
                    break

        if existing:
            merged = merge_agency(existing, new_entry)
            if merged != existing:
                agencies[agency_id] = merged
                updated += 1
            else:
                skipped += 1
        else:
            agencies[agency_id] = new_entry
            added += 1

    print(f"\nResults: +{added} new, ~{updated} updated, ={skipped} unchanged")

    if args.dry_run:
        print("\n[DRY RUN] Would write the following new agencies:")
        for aid, agency in sorted(agencies.items()):
            if aid not in load_existing_agencies():
                print(
                    f"  {agency['state']:2s} | {agency['name']:50s} | "
                    f"{agency['alpr'].get('camera_count', '?'):>4} cameras"
                )
        return

    # Save enriched agencies
    total = save_agencies(agencies)
    print(f"Wrote {total} agencies to {AGENCIES_PATH}")

    # Save per-state camera counts
    build_state_camera_counts(state_totals)

    # Summary by state
    print("\nAgencies per state:")
    state_agency_counts = Counter()
    for a in agencies.values():
        state_agency_counts[a.get("state", "??")] += 1
    for st, ct in sorted(state_agency_counts.items()):
        print(f"  {st}: {ct}")


if __name__ == "__main__":
    main()
