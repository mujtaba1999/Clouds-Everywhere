try:
    from models import SatelliteImage, TileResult
    from src.utils import fetch_all
except ImportError:
    from ..models import SatelliteImage, TileResult
    from .utils import fetch_all

URL = "https://earth-search.aws.element84.com/v1/search"

def search(bbox, start_date, end_date, max_cloud):
    payload = {
        "collections": ["sentinel-2-l2a"],
        "bbox": bbox,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 100,
    }
    results = []
    for item in fetch_all(URL, payload):
        p = item["properties"]
        cloud = p.get("eo:cloud_cover", -1)
        if cloud != -1 and cloud > max_cloud:
            continue
        results.append(SatelliteImage(
            id            = item["id"],
            date          = p.get("datetime", "")[:10],
            cloud_cover   = cloud,
            satellite     = "Sentinel-2",
            thumbnail_url = item["assets"].get("thumbnail", {}).get("href", "")
        ))
    return results


def search_tiles(bbox, start_date, end_date):
    """Fetch all Sentinel-2 tiles in bbox/range with no cloud filter (used for coverage analysis)."""
    payload = {
        "collections": ["sentinel-2-l2a"],
        "bbox": bbox,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 100,
    }
    results = []
    for item in fetch_all(URL, payload):
        p = item["properties"]
        tile_id = p.get("s2:mgrs_tile") or item["id"].split("_")[1]
        results.append(TileResult(
            tile_id       = tile_id,
            date          = p.get("datetime", "")[:10],
            cloud_cover   = p.get("eo:cloud_cover", -1),
            satellite     = "Sentinel-2",
            item_id       = item["id"],
            thumbnail_url = item["assets"].get("thumbnail", {}).get("href", ""),
            geometry      = item.get("geometry"),
        ))
    return results
