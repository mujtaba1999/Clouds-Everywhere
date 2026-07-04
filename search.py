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

    # Each satellite is fetched independently — one being down or empty must
    # not abort the whole search.
    providers = [
        ("sentinel2", sentinel2.search),
        ("landsat",   landsat.search),
        ("modis",     modis.search),
    ]
    for name, fetch in providers:
        if name not in satellites:
            continue
        try:
            results += fetch(bbox, start_date, end_date, max_cloud)
        except Exception as e:
            print(f"[search] '{name}' unavailable for this request — skipping ({e})")

    return sorted(results, key=lambda x: x.date)