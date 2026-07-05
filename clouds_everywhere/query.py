"""
query.py — user-facing availability query.

Answers the practical question:

    "For my study area, my dates, and my cloud limit — grouped by day / week /
     month — is satellite imagery available, and where are the data gaps?"

A period is:
    available  → every tile covering the AOI has >= 1 usable image
    gap        → some tiles are covered but at least one is missing (a hole)
    missing    → no tile has any usable image at all

"Usable" means the scene's cloud cover is at or below the user's threshold.
Cloud-unknown scenes (cloud == -1) are treated as usable, since we can't rule
them out.
"""

from collections import defaultdict

import pandas as pd

from .providers import sentinel2, landsat
from .models import TilePeriodStat, PeriodCoverage, QueryReport
from .aoi import to_bbox


_FETCHERS = {
    "sentinel2": sentinel2.search_tiles,
    "landsat":   landsat.search_tiles,
}


def query(aoi, start_date, end_date, max_cloud=20, group_by="week",
          satellites=("sentinel2", "landsat")):
    """
    Parameters
    ----------
    aoi         : bbox / polygon coords / GeoJSON / shapefile path (any CRS)
    start_date  : "YYYY-MM-DD"
    end_date    : "YYYY-MM-DD"
    max_cloud   : cloud-cover threshold in percent (default 20)
    group_by    : "day" | "week" | "month"  (default "week")
    satellites  : subset of ("sentinel2", "landsat")

    Returns
    -------
    QueryReport — print it for a friendly summary, or use .to_dataframe() /
    .periods for structured access.
    """
    if group_by not in ("day", "week", "month"):
        raise ValueError("group_by must be 'day', 'week', or 'month'")

    bbox = to_bbox(aoi)

    # ── fetch every tile in range (no cloud filter — we bucket ourselves) ────
    # A single satellite being down or returning nothing must not abort the
    # whole query — we skip it and carry on with the others.
    all_tiles = []
    for sat in satellites:
        fetch = _FETCHERS.get(sat)
        if fetch is None:
            print(f"[query] Unknown satellite '{sat}' — skipping")
            continue
        try:
            all_tiles += fetch(bbox, start_date, end_date)
        except Exception as e:
            print(f"[query] '{sat}' unavailable for this request — skipping ({e})")

    periods = []
    by_sat = defaultdict(list)
    for tr in all_tiles:
        by_sat[tr.satellite].append(tr)

    for satellite, tiles in by_sat.items():
        # Required tiles = every tile that ever intersects the AOI in the range
        required = sorted({t.tile_id for t in tiles})

        # Bucket tiles into periods
        buckets = defaultdict(list)     # period_key -> list[TileResult]
        for t in tiles:
            key = _period_key(t.date, group_by)
            buckets[key].append(t)

        for key in sorted(buckets):
            period_tiles = buckets[key]
            label, p_start, p_end = _period_label(key, group_by)

            # per-tile stats within this period
            per_tile = defaultdict(lambda: {"usable": 0, "total": 0, "best": -1.0})
            for t in period_tiles:
                s = per_tile[t.tile_id]
                s["total"] += 1
                usable = (t.cloud_cover == -1) or (t.cloud_cover <= max_cloud)
                if usable:
                    s["usable"] += 1
                if t.cloud_cover != -1:
                    s["best"] = t.cloud_cover if s["best"] == -1 else min(s["best"], t.cloud_cover)

            tile_stats = [
                TilePeriodStat(
                    tile_id       = tid,
                    usable_images = s["usable"],
                    total_images  = s["total"],
                    best_cloud    = s["best"],
                )
                for tid, s in sorted(per_tile.items())
            ]

            covered = sorted(tid for tid, s in per_tile.items() if s["usable"] > 0)
            missing = sorted(set(required) - set(covered))

            if not missing:
                status = "available"
            elif covered:
                status = "gap"
            else:
                status = "missing"

            periods.append(PeriodCoverage(
                label          = label,
                period_start   = p_start,
                period_end     = p_end,
                satellite      = satellite,
                status         = status,
                required_tiles = required,
                covered_tiles  = covered,
                missing_tiles  = missing,
                tile_stats     = tile_stats,
            ))

    periods.sort(key=lambda p: (p.period_start, p.satellite))

    return QueryReport(
        aoi_bbox   = bbox,
        start_date = start_date,
        end_date   = end_date,
        max_cloud  = max_cloud,
        group_by   = group_by,
        satellites = list(satellites),
        periods    = periods,
    )


# ── period helpers ────────────────────────────────────────────────────────────

def _period_key(date_str, group_by):
    """Return a stable, sortable key identifying the period a date falls in."""
    ts = pd.Timestamp(date_str)
    if group_by == "day":
        return ts.strftime("%Y-%m-%d")
    if group_by == "week":
        iso = ts.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    # month
    return ts.strftime("%Y-%m")


def _period_label(key, group_by):
    """Return (friendly_label, period_start_iso, period_end_iso) for a period key."""
    if group_by == "day":
        ts = pd.Timestamp(key)
        return ts.strftime("%a %d %b %Y"), key, key

    if group_by == "week":
        year, week = key.split("-W")
        # Monday of that ISO week
        monday = pd.Timestamp.fromisocalendar(int(year), int(week), 1)
        sunday = monday + pd.Timedelta(days=6)
        if monday.month == sunday.month:
            label = f"{monday.day}-{sunday.day} {monday.strftime('%b %Y')}"
        else:
            label = f"{monday.strftime('%d %b')}-{sunday.strftime('%d %b %Y')}"
        return label, monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")

    # month
    ts = pd.Timestamp(key + "-01")
    p_end = (ts + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
    return ts.strftime("%B %Y"), ts.strftime("%Y-%m-%d"), p_end
