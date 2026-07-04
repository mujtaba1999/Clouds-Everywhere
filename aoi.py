"""
aoi.py — normalize any AOI input to a WGS84 bbox [minX, minY, maxX, maxY].

Accepted inputs
---------------
* Plain bbox list/tuple  : [minX, minY, maxX, maxY]
* Polygon coords         : [[lon, lat], ...]  or  shapely Polygon
* GeoJSON dict           : FeatureCollection, Feature, or geometry
* File path (str/Path)   : .geojson, .json, .shp, .zip (zipped shapefile)

Every spatial input is reprojected to WGS84 (EPSG:4326) before the bbox is
returned, so callers never need to think about CRS.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pyproj
from shapely.geometry import shape, Polygon
from shapely.ops import transform, unary_union


WGS84 = pyproj.CRS("EPSG:4326")


# ── public entry point ────────────────────────────────────────────────────────

def to_bbox(aoi) -> list[float]:
    """Return [minX, minY, maxX, maxY] in WGS84 for any supported AOI input."""
    geom, crs = _parse(aoi)
    geom = _ensure_wgs84(geom, crs)
    _validate_wgs84_bbox(geom.bounds)
    minx, miny, maxx, maxy = geom.bounds
    return [minx, miny, maxx, maxy]


# ── parsers — all return (shapely_geom, pyproj.CRS | None) ───────────────────

def _parse(aoi):
    # shapely geometry passed directly — assume WGS84
    if hasattr(aoi, "geom_type"):
        return aoi, None

    # file path
    if isinstance(aoi, (str, Path)):
        return _from_file(Path(aoi))

    # empty containers are never a valid AOI
    if isinstance(aoi, (list, tuple)) and len(aoi) == 0:
        raise ValueError("AOI is empty - provide a bbox, polygon coords, or GeoJSON")

    # plain bbox [minX, minY, maxX, maxY]
    if (isinstance(aoi, (list, tuple))
            and len(aoi) == 4
            and all(isinstance(v, (int, float)) for v in aoi)):
        return _bbox_to_polygon(aoi), None

    # polygon as list of coordinate pairs [[x, y], ...]
    if (isinstance(aoi, (list, tuple))
            and all(isinstance(v, (list, tuple)) and len(v) == 2 for v in aoi)):
        if len(aoi) < 3:
            raise ValueError(
                f"Polygon needs at least 3 coordinate pairs, got {len(aoi)}"
            )
        return _coords_to_polygon(aoi), None

    # GeoJSON dict
    if isinstance(aoi, dict):
        return _from_geojson(aoi)

    raise TypeError(f"Unsupported AOI type: {type(aoi)}")


def _from_file(path: Path):
    suffix = path.suffix.lower()

    if suffix in (".geojson", ".json"):
        gdf = gpd.read_file(path)
    elif suffix == ".shp":
        gdf = gpd.read_file(path)
    elif suffix == ".zip":
        gdf = gpd.read_file(f"zip://{path}")
    else:
        raise ValueError(f"Unsupported file format: {suffix!r}. Use .geojson, .json, .shp, or .zip")

    geom = unary_union(gdf.geometry)
    crs = gdf.crs  # pyproj.CRS or None
    return geom, crs


def _from_geojson(d: dict):
    typ = d.get("type")

    if typ == "FeatureCollection":
        geoms = [shape(f["geometry"]) for f in d["features"] if f.get("geometry")]
        geom = unary_union(geoms)
    elif typ == "Feature":
        geom = shape(d["geometry"])
    elif typ in ("Polygon", "MultiPolygon", "Point", "LineString",
                 "MultiPoint", "MultiLineString", "GeometryCollection"):
        geom = shape(d)
    else:
        raise ValueError(f"Unrecognised GeoJSON type: {typ!r}")

    # Some tools embed a CRS object (older GeoJSON / ArcGIS exports)
    crs = None
    crs_obj = d.get("crs")
    if crs_obj:
        epsg_name = crs_obj.get("properties", {}).get("name", "")
        try:
            crs = pyproj.CRS.from_user_input(epsg_name)
        except Exception:
            pass  # can't parse it; fall back to WGS84 assumption

    return geom, crs


def _bbox_to_polygon(bbox) -> Polygon:
    minx, miny, maxx, maxy = bbox
    return Polygon([
        (minx, miny), (maxx, miny),
        (maxx, maxy), (minx, maxy),
        (minx, miny),
    ])


def _coords_to_polygon(coords) -> Polygon:
    """Accept [[lon, lat], ...] or [[lat, lon], ...] and fix axis order."""
    coords = [tuple(c) for c in coords]

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]

    # If xs fit in [-90, 90] but ys don't → coords are (lat, lon), swap them
    if all(-90 <= v <= 90 for v in xs) and any(abs(v) > 90 for v in ys):
        coords = [(y, x) for x, y in coords]

    return Polygon(coords)


# ── CRS reprojection ──────────────────────────────────────────────────────────

def _ensure_wgs84(geom, crs):
    if crs is None or crs.equals(WGS84):
        return geom
    transformer = pyproj.Transformer.from_crs(crs, WGS84, always_xy=True)
    return transform(transformer.transform, geom)


def _validate_wgs84_bbox(bounds):
    minx, miny, maxx, maxy = bounds
    if any(v != v for v in bounds):        # NaN check (NaN != NaN)
        raise ValueError("AOI produced an empty or invalid geometry")
    if not (-180 <= minx <= 180 and -180 <= maxx <= 180):
        raise ValueError(f"Longitude out of WGS84 range: minX={minx}, maxX={maxx}")
    if not (-90 <= miny <= 90 and -90 <= maxy <= 90):
        raise ValueError(f"Latitude out of WGS84 range: minY={miny}, maxY={maxy}")
    if minx >= maxx or miny >= maxy:
        raise ValueError(f"Degenerate bbox (min >= max): {list(bounds)}")
