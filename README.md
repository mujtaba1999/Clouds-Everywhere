<p align="center">
  <img src="https://raw.githubusercontent.com/mohammadanwarx/Clouds-Everywhere/main/assets/logo.png" alt="Clouds-Everywhere logo" width="260">
</p>

# Clouds-Everywhere

<p align="center">
  <a href="https://pypi.org/project/clouds-everywhere/"><img src="https://img.shields.io/pypi/v/clouds-everywhere.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/clouds-everywhere/"><img src="https://img.shields.io/pypi/pyversions/clouds-everywhere.svg" alt="Python versions"></a>
  <a href="https://github.com/mohammadanwarx/Clouds-Everywhere/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/clouds-everywhere.svg" alt="License"></a>
</p>

Find out when cloud-free satellite imagery is available over your study area —
and where the data gaps are.

You give it an area, a date range, and a cloud limit. It answers in plain
language: which days, weeks, or months have usable imagery, and which tiles
are missing.

## Install
https://pypi.org/project/clouds-everywhere/
```bash
pip install clouds-everywhere
```

Or from source:

```bash
git clone https://github.com/mohammadanwarx/Clouds-Everywhere.git
cd Clouds-Everywhere
pip install -e .
```

## Quick start

```python
from clouds_everywhere import query

report = query(
    aoi        = "my_area.geojson",   # bbox, polygon, GeoJSON, or shapefile
    start_date = "2024-01-01",
    end_date   = "2024-02-29",
    max_cloud  = 20,                  # max cloud cover in %
    group_by   = "week",              # "day" | "week" | "month"
    satellites = ["sentinel2", "landsat"],
)

print(report)
```

```
  Sentinel-2  -  needs 9 tiles to fully cover your area
    [OK]  8-14 Jan 2024      All tiles have usable imagery  (15 images across 9 tiles)
    [GAP] 15-21 Jan 2024     Data gap - some tiles missing  (3/9 tiles; missing: 30SVJ, ...)
    [--]  5-11 Feb 2024      No usable imagery

    Summary: 3 fully-covered weeks, 5 with gaps, 1 empty  (of 9 weeks)
```

Each period gets one of three statuses:

| Status | Meaning |
|---|---|
| **available** | every tile has at least one usable image |
| **gap** | some tiles have imagery, but at least one is missing |
| **missing** | no usable imagery at all |

*Usable* means cloud cover is at or below your threshold.

## Your area, any format

The AOI can be any of these — the CRS is handled for you (everything is
reprojected to WGS84 automatically):

- a bbox: `[minX, minY, maxX, maxY]`
- polygon coordinates: `[[lon, lat], ...]`
- a GeoJSON dict (`Feature`, `FeatureCollection`, or geometry)
- a file: `.geojson`, `.json`, `.shp`, or `.zip` (zipped shapefile)

## Tables and plots

```python
report.to_dataframe()        # one row per period per satellite
report.tile_dataframe()      # one row per tile per period
report.available_periods()   # fully covered periods
report.gap_periods()         # periods with holes

from clouds_everywhere.viz import plot_availability_calendar
plot_availability_calendar(report)   # green / amber / red calendar
```

## Lower-level functions

- `search_images(...)` — flat list of matching scenes
- `check_coverage(...)` — tile coverage per date
- `viz.plot_coverage_heatmap`, `plot_cloud_timeline`, `plot_satellite_comparison`

## Demos

- [`demo.ipynb`](demo.ipynb) — search and coverage basics
- [`demo2.ipynb`](demo2.ipynb) — the `query()` workflow and all plots

## Tests

```bash
pytest
```

Fast and offline — all API calls are mocked.

## Data sources

Sentinel-2 and Landsat from the [Element84 Earth Search](https://earth-search.aws.element84.com)
STAC API. MODIS from NASA CMR STAC.
