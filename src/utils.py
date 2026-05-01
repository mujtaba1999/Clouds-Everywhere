import time
import requests


def post_with_retry(url, payload, retries=3, backoff=2, timeout=30):
    """POST with automatic retry on 5xx errors (exponential backoff: 1 s, 2 s, 4 s)."""
    for attempt in range(retries):
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code < 500:
            r.raise_for_status()   # raises on 4xx, returns cleanly on 2xx
            return r
        if attempt < retries - 1:
            time.sleep(backoff ** attempt)
    r.raise_for_status()
    return r


def fetch_all(url, payload, retries=3, backoff=2, timeout=30):
    """Collect every feature across all pages of a STAC search.

    The Element84 STAC API caps responses at 100 items per page and signals
    the next page via a ``links[rel=next].body`` object that is POSTed as-is.
    """
    features = []
    current_payload = payload.copy()
    while True:
        r = post_with_retry(url, current_payload, retries=retries, backoff=backoff, timeout=timeout)
        data = r.json()
        page = data.get("features", [])
        features.extend(page)
        next_link = next(
            (lnk for lnk in data.get("links", []) if lnk.get("rel") == "next"),
            None,
        )
        if not next_link or not page:
            break
        current_payload = next_link["body"]   # cursor already embedded by the API
    return features
