try:
    from models import SatelliteImage, TileResult
    from src.utils import fetch_all
except ImportError:
    from ..models import SatelliteImage, TileResult
    from .utils import fetch_all

URL = "https://earth-search.aws.element84.com/v1/search"

def search(bbox, start_date, end_date, max_cloud):
    payload = {
        "collections": ["landsat-c2-l2"],
        "bbox": bbox,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "filter-lang": "cql2-json",
        "filter": {
            "op": "<=",
            "args": [{"property": "eo:cloud_cover"}, max_cloud]
        },
        "limit": 100
    }
    results = []
    for item in fetch_all(URL, payload):
        p = item["properties"]
        results.append(SatelliteImage(
            id            = item["id"],
            date          = p.get("datetime", "")[:10],
            cloud_cover   = p.get("eo:cloud_cover", -1),
            satellite     = p.get("platform", "Landsat"),
            thumbnail_url = item["assets"].get("thumbnail", {}).get("href", "")
        ))
    return results


def search_tiles(bbox, start_date, end_date):
    """Fetch all Landsat tiles in bbox/range with no cloud filter (used for coverage analysis)."""
    payload = {
        "collections": ["landsat-c2-l2"],
        "bbox": bbox,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 100,
    }
    results = []
    for item in fetch_all(URL, payload):
        p = item["properties"]
        path = str(p.get("landsat:wrs_path", "?")).zfill(3)
        row  = str(p.get("landsat:wrs_row",  "?")).zfill(3)
        results.append(TileResult(
            tile_id       = f"P{path}R{row}",
            date          = p.get("datetime", "")[:10],
            cloud_cover   = p.get("eo:cloud_cover", -1),
            satellite     = p.get("platform", "Landsat"),
            item_id       = item["id"],
            thumbnail_url = item["assets"].get("thumbnail", {}).get("href", ""),
            geometry      = item.get("geometry"),
        ))
    return results
