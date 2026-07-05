from collections import defaultdict

from .providers import sentinel2, landsat
from .models import DateCoverage
from .aoi import to_bbox


def check_coverage(aoi, start_date, end_date, max_cloud=20, satellites=("sentinel2", "landsat")):
    """
    For each date in the range, determine whether all tiles covering the bbox
    are available and below the cloud threshold.

    Returns a list of DateCoverage objects sorted by date, each flagged as:
      "full"    — every required tile passes the cloud threshold
      "partial" — some tiles pass, some are missing or too cloudy
      "missing" — no tiles pass at all for that date
    """
    bbox = to_bbox(aoi)

    fetchers = []
    if "sentinel2" in satellites:
        fetchers.append(("sentinel2", sentinel2.search_tiles))
    if "landsat" in satellites:
        fetchers.append(("landsat", landsat.search_tiles))

    # One satellite failing (API down, no passes) must not abort coverage.
    all_tile_results = []
    for name, fetch in fetchers:
        try:
            all_tile_results += fetch(bbox, start_date, end_date)
        except Exception as e:
            print(f"[coverage] '{name}' unavailable for this request — skipping ({e})")

    if not all_tile_results:
        return []

    # Analyse each satellite independently so Sentinel-2 and Landsat tile
    # grids don't interfere with each other.
    by_satellite = defaultdict(list)
    for tr in all_tile_results:
        by_satellite[tr.satellite].append(tr)

    coverage_results = []

    for satellite, tile_results in by_satellite.items():
        required_tiles = set(tr.tile_id for tr in tile_results)

        by_date = defaultdict(list)
        for tr in tile_results:
            by_date[tr.date].append(tr)

        for date, date_tiles in sorted(by_date.items()):
            tile_cloud = {tr.tile_id: tr.cloud_cover for tr in date_tiles}

            covered = {
                t: c for t, c in tile_cloud.items()
                if c == -1 or c <= max_cloud          # -1 = cloud unknown, include it
            }
            failed  = {
                t: c for t, c in tile_cloud.items()
                if c != -1 and c > max_cloud
            }
            absent  = required_tiles - set(tile_cloud.keys())

            covered_tiles = sorted(covered.keys())
            missing_tiles = sorted(failed.keys()) + sorted(absent)

            if not missing_tiles:
                status = "full"
            elif covered_tiles:
                status = "partial"
            else:
                status = "missing"

            valid_clouds = [c for c in covered.values() if c != -1]
            avg_cloud = sum(valid_clouds) / len(valid_clouds) if valid_clouds else -1

            coverage_results.append(DateCoverage(
                date           = date,
                satellite      = satellite,
                status         = status,
                required_tiles = sorted(required_tiles),
                covered_tiles  = covered_tiles,
                missing_tiles  = missing_tiles,
                avg_cloud      = avg_cloud,
                tile_details   = date_tiles,
            ))

    return sorted(coverage_results, key=lambda x: (x.date, x.satellite))
