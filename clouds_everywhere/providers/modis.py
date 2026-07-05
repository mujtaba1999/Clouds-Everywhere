import requests
from ..models import SatelliteImage

# NASA CMR STAC — LP DAAC hosts MODIS land surface products
URL = "https://cmr.earthdata.nasa.gov/stac/LPDAAC_ECS/search"
COLLECTIONS = ["MOD09GA.061", "MYD09GA.061"]  # Terra + Aqua 500 m daily

def search(bbox, start_date, end_date, max_cloud):
    payload = {
        "collections": COLLECTIONS,
        "bbox": bbox,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 100,
    }
    try:
        r = requests.post(URL, json=payload, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[MODIS] API error: {e}")
        return []

    results = []
    for item in r.json().get("features", []):
        p = item["properties"]
        cloud = p.get("eo:cloud_cover", -1)
        # -1 means the field is absent; include those (cloud status unknown)
        if cloud != -1 and cloud > max_cloud:
            continue
        item_id = item.get("id", "")
        satellite = "Terra MODIS" if item_id.upper().startswith("MOD") else "Aqua MODIS"
        assets = item.get("assets", {})
        thumbnail = (
            assets.get("browse", {}).get("href", "")
            or assets.get("thumbnail", {}).get("href", "")
        )
        results.append(SatelliteImage(
            id=item_id,
            date=p.get("datetime", "")[:10],
            cloud_cover=cloud,
            satellite=satellite,
            thumbnail_url=thumbnail,
        ))
    return results
