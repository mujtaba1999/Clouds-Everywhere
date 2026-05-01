try:
    from src import sentinel2, landsat, modis        # notebook / script context
except ImportError:
    from .src import sentinel2, landsat, modis       # installed package context

def search_images(bbox, start_date, end_date, max_cloud=20, satellites=["sentinel2", "landsat", "modis"]):
    """
    bbox        : [minX, minY, maxX, maxY] in WGS84
    start_date  : "YYYY-MM-DD"
    end_date    : "YYYY-MM-DD"
    max_cloud   : 0-100 (default 20%)
    satellites  : ["sentinel2", "landsat"] or just one
    """
    results = []

    if "sentinel2" in satellites:
        results += sentinel2.search(bbox, start_date, end_date, max_cloud)

    if "landsat" in satellites:
        results += landsat.search(bbox, start_date, end_date, max_cloud)

    if "modis" in satellites:
        results += modis.search(bbox, start_date, end_date, max_cloud)

    return sorted(results, key=lambda x: x.date)