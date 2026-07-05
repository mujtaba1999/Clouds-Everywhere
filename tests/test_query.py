"""
Tests for query() — grouping, status classification, and resilience.

All network access is mocked: we patch query._FETCHERS with functions that
return synthetic TileResult lists, so these tests are fast and deterministic.
"""
import importlib

import pytest

# NB: "clouds_everywhere.query" the *module* is shadowed by the query()
# *function* re-exported in the package __init__, so fetch it via importlib.
query_mod = importlib.import_module("clouds_everywhere.query")
query = query_mod.query
from clouds_everywhere.models import TileResult, QueryReport


# ── helpers ───────────────────────────────────────────────────────────────────

def tile(tile_id, date, cloud, sat="Sentinel-2"):
    return TileResult(
        tile_id=tile_id, date=date, cloud_cover=cloud,
        satellite=sat, item_id=f"{tile_id}_{date}", thumbnail_url="",
        geometry=None,
    )


# A two-tile AOI over three weeks:
#   week1: both tiles usable          -> available
#   week2: only T1 usable, T2 absent  -> gap
#   week3: both present but too cloudy -> missing
SCENE_DATA = [
    tile("T1", "2024-01-02", 10.0),
    tile("T2", "2024-01-03", 12.0),
    tile("T1", "2024-01-09", 8.0),
    tile("T1", "2024-01-16", 90.0),
    tile("T2", "2024-01-17", 95.0),
]


@pytest.fixture
def patch_sentinel(monkeypatch):
    """Patch the sentinel2 fetcher to return SCENE_DATA; landsat returns nothing."""
    monkeypatch.setitem(query_mod._FETCHERS, "sentinel2",
                        lambda bbox, s, e: list(SCENE_DATA))
    monkeypatch.setitem(query_mod._FETCHERS, "landsat",
                        lambda bbox, s, e: [])
    return monkeypatch


AOI = [-4.5, 39.5, -2.5, 41.0]


# ── basic contract ────────────────────────────────────────────────────────────

def test_returns_query_report(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="week", satellites=["sentinel2"])
    assert isinstance(r, QueryReport)


def test_required_tiles_is_union_over_range(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="week", satellites=["sentinel2"])
    assert r.required_tiles("Sentinel-2") == ["T1", "T2"]


# ── status classification (the core "gap / hole" logic) ───────────────────────

def test_week_statuses(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="week", satellites=["sentinel2"])
    statuses = [p.status for p in r.periods]
    assert statuses == ["available", "gap", "missing"]


def test_gap_reports_the_missing_tile(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="week", satellites=["sentinel2"])
    gap = r.gap_periods()[0]
    assert gap.missing_tiles == ["T2"]
    assert gap.covered_tiles == ["T1"]


def test_available_counts_usable_images(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="week", satellites=["sentinel2"])
    avail = r.available_periods()[0]
    assert avail.total_usable_images == 2


def test_threshold_changes_classification(patch_sentinel):
    # Raising the threshold fixes CLOUD problems (week 3: both tiles present but
    # cloudy) but NOT true data gaps (week 2: T2 was never acquired).
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=100,
              group_by="week", satellites=["sentinel2"])
    statuses = [p.status for p in r.periods]
    assert statuses == ["available", "gap", "available"]
    # week 2 is still a gap because T2 had no pass that week — a hole, not clouds
    assert r.gap_periods()[0].missing_tiles == ["T2"]


# ── grouping granularity ──────────────────────────────────────────────────────

def test_group_by_month_collapses_to_one_period(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="month", satellites=["sentinel2"])
    assert len(r.periods) == 1
    # both tiles appear somewhere usable in the month -> available
    assert r.periods[0].status == "available"


def test_group_by_day(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="day", satellites=["sentinel2"])
    # 5 distinct acquisition dates in the scene data
    assert len({p.period_start for p in r.periods}) == 5


def test_invalid_group_by():
    with pytest.raises(ValueError, match="group_by"):
        query(AOI, "2024-01-01", "2024-01-31", group_by="fortnight")


# ── resilience: a satellite not functioning must NOT raise ────────────────────

def test_failing_satellite_is_skipped(monkeypatch, capsys):
    def boom(bbox, s, e):
        raise ConnectionError("API 503")

    monkeypatch.setitem(query_mod._FETCHERS, "sentinel2", boom)
    monkeypatch.setitem(query_mod._FETCHERS, "landsat",
                        lambda bbox, s, e: [tile("P1", "2024-01-05", 5.0, sat="landsat-9")])

    # should not raise despite sentinel2 blowing up
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="week", satellites=["sentinel2", "landsat"])

    sats = {p.satellite for p in r.periods}
    assert sats == {"landsat-9"}                 # only the working satellite
    assert "unavailable" in capsys.readouterr().out


def test_all_satellites_empty_gives_empty_report(monkeypatch):
    monkeypatch.setitem(query_mod._FETCHERS, "sentinel2", lambda b, s, e: [])
    monkeypatch.setitem(query_mod._FETCHERS, "landsat", lambda b, s, e: [])
    r = query(AOI, "2024-01-01", "2024-01-31", satellites=["sentinel2", "landsat"])
    assert r.periods == []
    # summary must still render without error
    assert "AVAILABILITY REPORT" in r.summary()


def test_unknown_satellite_is_skipped(monkeypatch, capsys):
    monkeypatch.setitem(query_mod._FETCHERS, "sentinel2", lambda b, s, e: list(SCENE_DATA))
    r = query(AOI, "2024-01-01", "2024-01-31", satellites=["sentinel2", "modis"])
    # modis isn't a query fetcher -> skipped with a notice, sentinel2 still works
    assert r.required_tiles("Sentinel-2") == ["T1", "T2"]
    assert "Unknown satellite" in capsys.readouterr().out


# ── bad AOI propagates a clear error before any network work ──────────────────

def test_bad_aoi_raises_before_fetch():
    with pytest.raises((ValueError, TypeError)):
        query([], "2024-01-01", "2024-01-31")


# ── report views work on real objects ─────────────────────────────────────────

def test_to_dataframe_shape(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="week", satellites=["sentinel2"])
    df = r.to_dataframe()
    assert len(df) == 3
    assert {"Period", "Status", "Missing tiles"}.issubset(df.columns)


def test_tile_dataframe_has_per_tile_rows(patch_sentinel):
    r = query(AOI, "2024-01-01", "2024-01-31", max_cloud=20,
              group_by="week", satellites=["sentinel2"])
    tdf = r.tile_dataframe()
    assert set(tdf["Tile"].unique()) == {"T1", "T2"}
