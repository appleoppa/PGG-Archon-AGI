---
name: maps
description: 地理编码、POI、路线、时区查询
version: 1.2.0
author: Mibayy
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [maps, geocoding, places, routing, distance, directions, nearby, location, openstreetmap, nominatim, overpass, osrm]
    category: productivity
    requires_toolsets: [terminal]
    supersedes: [find-nearby]
---

# Maps — Compact

## Trigger

Use for geocoding, POI search, routes, distance/time, timezone, address normalization and location-based lookup.

## Workflow

1. Clarify origin/destination/place and geography if ambiguous.
2. Use maps/geocoder tool or API; do not guess current data.
3. Return coordinates, address, route/duration, timezone and source timestamp as needed.
4. For legal/business use, mark location uncertainty and verify with official records where material.

## Reference

Full API examples archived at `references/full-skill-archive-20260601.md`.
