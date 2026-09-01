#!/usr/bin/env python3
"""
Import ALPR camera locations from OpenStreetMap via the Overpass API.

Data comes from community-mapped nodes tagged surveillance:type=ALPR,
primarily contributed through the DeFlock project. Licensed under ODbL.

Usage:
  python3 scripts/import_osm_cameras.py [--state XX] [--dry-run]

Without --state, processes all 50 states + DC.
"""

import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

AGENCIES_PATH = Path(__file__).parent.parent / "src" / "data" / "agencies.json"
CAMERA_COUNTS_PATH = Path(__file__).parent.parent / "src" / "data" / "state_camera_counts.json"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# US state bounding boxes (south, west, north, east)
STATE_BOUNDS = {
    "AL": (30.22, -88.47, 35.01, -84.89),
    "AK": (51.21, -179.15, 71.39, -129.98),
    "AZ": (31.33, -114.81, 37.00, -109.04),
    "AR": (33.00, -94.62, 36.50, -89.64),
    "CA": (32.53, -124.48, 42.01, -114.13),
    "CO": (36.99, -109.06, 41.00, -102.04),
    "CT": (40.95, -73.73, 42.05, -71.79),
    "DE": (38.45, -75.79, 39.84, -75.05),
    "DC": (38.79, -77.12, 38.99, -76.91),
    "FL": (24.40, -87.63, 31.00, -80.03),
    "GA": (30.36, -85.61, 35.00, -80.84),
    "HI": (18.91, -160.24, 22.24, -154.81),
    "ID": (41.99, -117.24, 49.00, -111.04),
    "IL": (36.97, -91.51, 42.51, -87.02),
    "IN": (37.77, -88.10, 41.76, -84.78),
    "IA": (40.38, -96.64, 43.50, -90.14),
    "KS": (36.99, -102.05, 40.00, -94.59),
    "KY": (36.50, -89.57, 39.15, -81.96),
    "LA": (28.93, -94.04, 33.02, -88.82),
    "ME": (43.06, -71.08, 47.46, -66.95),
    "MD": (37.91, -79.49, 39.72, -75.05),
    "MA": (41.24, -73.51, 42.89, -69.93),
    "MI": (41.70, -90.42, 48.26, -82.12),
    "MN": (43.50, -97.24, 49.38, -89.49),
    "MS": (30.17, -91.66, 34.99, -88.10),
    "MO": (35.99, -95.77, 40.61, -89.10),
    "MT": (44.36, -116.05, 49.00, -104.04),
    "NE": (39.99, -104.05, 43.00, -95.31),
    "NV": (35.00, -120.01, 42.00, -114.04),
    "NH": (42.70, -72.56, 45.31, -70.70),
    "NJ": (38.93, -75.56, 41.36, -73.89),
    "NM": (31.33, -109.05, 37.00, -103.00),
    "NY": (40.50, -79.76, 45.02, -71.86),
    "NC": (33.84, -84.32, 36.59, -75.46),
    "ND": (45.94, -104.05, 49.00, -96.55),
    "OH": (38.40, -84.82, 41.98, -80.52),
    "OK": (33.62, -103.00, 37.00, -94.43),
    "OR": (41.99, -124.57, 46.29, -116.46),
    "PA": (39.72, -80.52, 42.27, -74.69),
    "RI": (41.15, -71.86, 42.02, -71.12),
    "SC": (32.03, -83.35, 35.21, -78.54),
    "SD": (42.48, -104.06, 45.95, -96.44),
    "TN": (34.98, -90.31, 36.68, -81.65),
    "TX": (25.84, -106.65, 36.50, -93.51),
    "UT": (36.99, -114.05, 42.00, -109.04),
    "VT": (42.73, -73.44, 45.02, -71.46),
    "VA": (36.54, -83.68, 39.47, -75.24),
    "WA": (45.54, -124.85, 49.00, -116.92),
    "WV": (37.20, -82.64, 40.64, -77.72),
    "WI": (42.49, -92.89, 47.08, -86.25),
    "WY": (40.99, -111.06, 45.01, -104.05),
}


def query_overpass(state_abbrev):
    """Query Overpass API for ALPR nodes in a state's bounding box."""
    bounds = STATE_BOUNDS.get(state_abbrev)
    if not bounds:
        return []

    s, w, n, e = bounds
    query = f"""[out:json][timeout:60];
node["man_made"="surveillance"]["surveillance:type"="ALPR"]({s},{w},{n},{e});
out body;"""

    data = urlencode({"data": query}).encode()
    req = Request(OVERPASS_URL, data=data)
    req.add_header("User-Agent", "FoilFlock/1.0 (+https://github.com/Foil-Flock)")

    try:
        with urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
        return result.get("elements", [])
    except Exception as exc:
        print(f"    Error querying {state_abbrev}: {exc}")
        return []


def normalize_operator(name):
    """Normalize an operator name for fuzzy matching."""
    name = name.strip().lower()
    for suffix in [" department", " dept", " dept."]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


def match_cameras_to_agencies(cameras, agencies_in_state):
    """Match OSM camera nodes to agencies by operator tag."""
    # Build lookup: normalized name -> agency id
    agency_lookup = {}
    for a in agencies_in_state:
        agency_lookup[normalize_operator(a["name"])] = a["id"]
        # Also try without "police" for broader matching
        short = normalize_operator(a["name"]).replace(" police", "")
        if short not in agency_lookup:
            agency_lookup[short] = a["id"]

    matched = {}  # agency_id -> count
    unmatched_operators = {}  # operator -> count

    for cam in cameras:
        tags = cam.get("tags", {})
        operator = tags.get("operator", "").strip()
        if not operator:
            unmatched_operators["(no operator tag)"] = unmatched_operators.get("(no operator tag)", 0) + 1
            continue

        norm = normalize_operator(operator)
        agency_id = agency_lookup.get(norm)

        if not agency_id:
            # Try without "police"
            short = norm.replace(" police", "")
            agency_id = agency_lookup.get(short)

        if agency_id:
            matched[agency_id] = matched.get(agency_id, 0) + 1
        else:
            unmatched_operators[operator] = unmatched_operators.get(operator, 0) + 1

    return matched, unmatched_operators


def main():
    parser = argparse.ArgumentParser(description="Import ALPR cameras from OpenStreetMap")
    parser.add_argument("--state", type=str, help="Process only this state (e.g., MA)")
    parser.add_argument("--dry-run", action="store_true", help="Show results without writing files")
    args = parser.parse_args()

    # Load agencies
    with open(AGENCIES_PATH) as f:
        data = json.load(f)
    agencies_by_id = {a["id"]: a for a in data["agencies"]}

    # Load existing camera counts
    if CAMERA_COUNTS_PATH.exists():
        with open(CAMERA_COUNTS_PATH) as f:
            camera_counts = json.load(f)
    else:
        camera_counts = {"counts": {}}

    states = [args.state.upper()] if args.state else sorted(STATE_BOUNDS.keys())

    total_cameras = 0
    total_matched = 0
    total_new_agencies = 0
    all_unmatched = {}

    for state in states:
        state_agencies = [a for a in data["agencies"] if a["state"] == state]
        print(f"\n{state}: {len(state_agencies)} agencies in directory")

        cameras = query_overpass(state)
        print(f"  OSM: {len(cameras)} ALPR nodes")
        total_cameras += len(cameras)

        if not cameras:
            time.sleep(2)
            continue

        # Update state camera count
        camera_counts["counts"][state] = len(cameras)

        matched, unmatched = match_cameras_to_agencies(cameras, state_agencies)

        if matched:
            total_matched += sum(matched.values())
            print(f"  Matched: {sum(matched.values())} cameras -> {len(matched)} agencies")
            for agency_id, count in sorted(matched.items(), key=lambda x: -x[1]):
                agency = agencies_by_id[agency_id]
                old_count = agency.get("alpr", {}).get("camera_count")
                if old_count is None or count > old_count:
                    if not args.dry_run:
                        agency.setdefault("alpr", {})["camera_count_osm"] = count
                        if "openstreetmap.org" not in " ".join(agency.get("sources", [])):
                            agency.setdefault("sources", []).append(
                                "https://www.openstreetmap.org"
                            )
                    action = "NEW" if old_count is None else f"updated {old_count}->{count}"
                    print(f"    {agency['name']}: {count} cameras ({action})")
                    total_new_agencies += 1

        if unmatched:
            for op, count in sorted(unmatched.items(), key=lambda x: -x[1]):
                all_unmatched[f"{op} ({state})"] = count

        # Courtesy delay between state queries
        time.sleep(5)

    # Summary
    print(f"\n{'='*60}")
    print(f"Total ALPR nodes: {total_cameras}")
    print(f"Matched to agencies: {total_matched}")
    print(f"Agencies updated: {total_new_agencies}")

    if all_unmatched:
        print(f"\nTop unmatched operators ({len(all_unmatched)} total):")
        for op, count in sorted(all_unmatched.items(), key=lambda x: -x[1])[:25]:
            print(f"  {count:4d}  {op}")

    if not args.dry_run:
        # Save updated agencies
        data["agencies"] = sorted(
            agencies_by_id.values(),
            key=lambda a: (a.get("state", ""), a.get("name", "")),
        )
        with open(AGENCIES_PATH, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"\nWrote {len(data['agencies'])} agencies to {AGENCIES_PATH}")

        # Save camera counts
        with open(CAMERA_COUNTS_PATH, "w") as f:
            json.dump(camera_counts, f, indent=2)
            f.write("\n")
        print(f"Wrote camera counts to {CAMERA_COUNTS_PATH}")
    else:
        print("\n(dry run — no files written)")


if __name__ == "__main__":
    main()
