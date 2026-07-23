from ..models import SatelliteImage, TileResult
from .utils import fetch_all_get

URL = "https://stac.dataspace.copernicus.eu/v1/search"
COLLECTION = "sentinel-3-olci-2-lfr-ntc"  # OLCI Level-2 Land Full Resolution


def _params(bbox, start_date, end_date):
    return {
        "collections": COLLECTION,
        "bbox": ",".join(str(b) for b in bbox),
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 100,
    }


def search(bbox, start_date, end_date, max_cloud):
    results = []
    for item in fetch_all_get(URL, _params(bbox, start_date, end_date)):
        p = item["properties"]
        cloud = p.get("eo:cloud_cover", -1)
        if cloud != -1 and cloud > max_cloud:
            continue
        results.append(SatelliteImage(
            id            = item["id"],
            date          = p.get("datetime", "")[:10],
            cloud_cover   = cloud,
            satellite     = p.get("platform", "sentinel-3"),
            thumbnail_url = item.get("assets", {}).get("thumbnail", {}).get("href", "")
        ))
    return results


def search_tiles(bbox, start_date, end_date):
    """Fetch all Sentinel-3 passes in bbox/range with no cloud filter (used for coverage analysis).

    Sentinel-3 has no MGRS/WRS tile grid — OLCI's swath is ~1270 km wide,
    far larger than a typical study area, so any single pass that intersects
    the AOI already images it in full (unlike Sentinel-2/Landsat, where a
    small AOI can straddle more than one tile). There is nothing analogous
    to "multiple tiles needed to fully cover the area" here, so every match
    is reported under one constant tile id — coverage for a period just
    means "at least one usable pass occurred".
    """
    results = []
    for item in fetch_all_get(URL, _params(bbox, start_date, end_date)):
        p = item["properties"]
        results.append(TileResult(
            tile_id       = "swath",
            date          = p.get("datetime", "")[:10],
            cloud_cover   = p.get("eo:cloud_cover", -1),
            satellite     = p.get("platform", "sentinel-3"),
            item_id       = item["id"],
            thumbnail_url = item.get("assets", {}).get("thumbnail", {}).get("href", ""),
            geometry      = item.get("geometry"),
        ))
    return results
