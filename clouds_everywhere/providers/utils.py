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
    the next page via a ``links[rel=next].body`` object containing a ``next``
    cursor token.  Crucially, that body omits any ``filter`` / ``filter-lang``
    fields from the original request, so we must NOT replace the payload
    wholesale — we only inject the cursor token into the original payload.
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
        # Only carry the cursor forward — keep the original filter intact.
        cursor = next_link["body"].get("next")
        current_payload = {**payload, "next": cursor}
    return features


def get_with_retry(url, params=None, retries=3, backoff=2, timeout=30):
    """GET with automatic retry on 5xx errors (exponential backoff: 1 s, 2 s, 4 s)."""
    for attempt in range(retries):
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code < 500:
            r.raise_for_status()   # raises on 4xx, returns cleanly on 2xx
            return r
        if attempt < retries - 1:
            time.sleep(backoff ** attempt)
    r.raise_for_status()
    return r


def fetch_all_get(url, params, retries=3, backoff=2, timeout=30):
    """Collect every feature across all pages of a GET-based STAC search.

    Unlike the Element84 API (POST + cursor token in the response body), the
    Copernicus Data Space Ecosystem STAC API returns a fully-formed
    ``links[rel=next].href`` GET URL for the next page — no payload surgery
    needed, just follow it.
    """
    features = []
    next_url, next_params = url, params
    while True:
        r = get_with_retry(next_url, params=next_params, retries=retries, backoff=backoff, timeout=timeout)
        data = r.json()
        page = data.get("features", [])
        features.extend(page)
        next_link = next(
            (lnk for lnk in data.get("links", []) if lnk.get("rel") == "next"),
            None,
        )
        if not next_link or not page:
            break
        next_url, next_params = next_link["href"], None
    return features
