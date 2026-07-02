# Clouds-Everywhere

Check whether usable satellite imagery is available over your area of interest —
filtered by cloud cover, grouped by day, week, or month.

Point it at a region and a time window and it tells you, in plain language,
**when clean imagery exists and where the data gaps are.**

## Install

```bash
pip install -e .
```

Depends on `requests`, `pandas`, `matplotlib`, `seaborn`, `folium`,
`geopandas`, and `pyproj`.

## Quick start

```python
from query import query

report = query(
    aoi        = "my_area.geojson",   # bbox, polygon, GeoJSON, or shapefile
    start_date = "2024-01-01",
    end_date   = "2024-02-29",
    max_cloud  = 20,                  # % cloud threshold
    group_by   = "week",             # "day" | "week" | "month"
    satellites = ["sentinel2", "landsat"],
)

print(report)   # friendly, plain-language summary
```

```
  Sentinel-2  -  needs 9 tiles to fully cover your area
    [OK]  8-14 Jan 2024      All tiles have usable imagery  (15 images across 9 tiles)
    [GAP] 15-21 Jan 2024     Data gap - some tiles missing  (3/9 tiles; missing: 30SVJ, ...)
    [--]  5-11 Feb 2024      No usable imagery

    Summary: 3 fully-covered weeks, 5 with gaps, 1 empty  (of 9 weeks)
```

Each period is flagged as:

| Status | Meaning |
|---|---|
| **available** | every tile covering the AOI has ≥1 usable image |
| **gap** | some tiles are covered but at least one is a hole |
| **missing** | no tile has any usable imagery |

*Usable* = cloud cover at or below your threshold.

## Any AOI format

`to_bbox()` (called automatically inside `query`) accepts and reprojects to WGS84:

- plain bbox `[minX, minY, maxX, maxY]`
- polygon coordinate ring `[[lon, lat], ...]`
- GeoJSON dict (`Feature`, `FeatureCollection`, or geometry)
- file path: `.geojson`, `.json`, `.shp`, `.zip` (zipped shapefile)

Non-WGS84 CRS are reprojected with `pyproj`, so you never worry about the
coordinate reference system.

## Structured output & plots

```python
report.to_dataframe()      # one row per period × satellite
report.tile_dataframe()    # one row per period × satellite × tile
report.available_periods() # list of fully-covered periods
report.gap_periods()       # periods with holes

from viz import plot_availability_calendar
plot_availability_calendar(report)   # green / amber / red calendar strip
```

## Lower-level API

- `search_images(aoi, start, end, max_cloud, satellites)` — flat list of scenes
- `check_coverage(aoi, start, end, max_cloud, satellites)` — per-date tile coverage
- `viz.plot_coverage_heatmap`, `plot_cloud_timeline`, `plot_satellite_comparison`

## Notebooks

- [`demo.ipynb`](demo.ipynb) — basic search & coverage walkthrough
- [`demo2.ipynb`](demo2.ipynb) — the `query()` workflow plus expert views

## Data sources

Sentinel-2 and Landsat via the [Element84 Earth Search](https://earth-search.aws.element84.com)
STAC API; MODIS via NASA CMR STAC.
