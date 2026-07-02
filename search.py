try:
    from src import sentinel2, landsat, modis        # notebook / script context
    from aoi import to_bbox
except ImportError:
    from .src import sentinel2, landsat, modis       # installed package context
    from .aoi import to_bbox

def search_images(aoi, start_date, end_date, max_cloud=20, satellites=["sentinel2", "landsat", "modis"]):
    """
    aoi         : any of —
                    [minX, minY, maxX, maxY] bbox,
                    [[lon, lat], ...] polygon coords,
                    GeoJSON dict (Feature / FeatureCollection / geometry),
                    path to .geojson, .json, .shp, or .zip shapefile
                  Any CRS is automatically reprojected to WGS84.
    start_date  : "YYYY-MM-DD"
    end_date    : "YYYY-MM-DD"
    max_cloud   : 0-100 (default 20%)
    satellites  : ["sentinel2", "landsat", "modis"] or a subset
    """
    bbox = to_bbox(aoi)
    results = []

    if "sentinel2" in satellites:
        results += sentinel2.search(bbox, start_date, end_date, max_cloud)

    if "landsat" in satellites:
        results += landsat.search(bbox, start_date, end_date, max_cloud)

    if "modis" in satellites:
        results += modis.search(bbox, start_date, end_date, max_cloud)

    return sorted(results, key=lambda x: x.date)