"""Resilience tests for search_images() and check_coverage() when a satellite fails."""
import pytest

import search as search_mod
import coverage as coverage_mod
from models import SatelliteImage, TileResult

AOI = [-4.5, 39.5, -2.5, 41.0]


def img(date, cloud, sat="Sentinel-2"):
    return SatelliteImage(id=f"{sat}_{date}", date=date, cloud_cover=cloud,
                          satellite=sat, thumbnail_url="")


def tile(tile_id, date, cloud, sat="Sentinel-2"):
    return TileResult(tile_id=tile_id, date=date, cloud_cover=cloud, satellite=sat,
                      item_id=f"{tile_id}_{date}", thumbnail_url="", geometry=None)


# ── search_images ─────────────────────────────────────────────────────────────

def test_search_one_satellite_down_does_not_raise(monkeypatch, capsys):
    def boom(*a, **k):
        raise ConnectionError("503")

    monkeypatch.setattr(search_mod.sentinel2, "search", boom)
    monkeypatch.setattr(search_mod.landsat, "search",
                        lambda *a, **k: [img("2024-01-05", 5.0, "landsat-9")])
    monkeypatch.setattr(search_mod.modis, "search", lambda *a, **k: [])

    results = search_mod.search_images(AOI, "2024-01-01", "2024-01-31",
                                       satellites=["sentinel2", "landsat"])
    assert [r.satellite for r in results] == ["landsat-9"]
    assert "unavailable" in capsys.readouterr().out


def test_search_results_sorted_by_date(monkeypatch):
    monkeypatch.setattr(search_mod.sentinel2, "search",
                        lambda *a, **k: [img("2024-01-20", 5.0), img("2024-01-02", 5.0)])
    monkeypatch.setattr(search_mod.landsat, "search", lambda *a, **k: [])
    monkeypatch.setattr(search_mod.modis, "search", lambda *a, **k: [])
    results = search_mod.search_images(AOI, "2024-01-01", "2024-01-31",
                                       satellites=["sentinel2"])
    assert [r.date for r in results] == ["2024-01-02", "2024-01-20"]


# ── check_coverage ────────────────────────────────────────────────────────────

def test_coverage_one_satellite_down_does_not_raise(monkeypatch, capsys):
    def boom(*a, **k):
        raise TimeoutError("timeout")

    monkeypatch.setattr(coverage_mod.sentinel2, "search_tiles", boom)
    monkeypatch.setattr(coverage_mod.landsat, "search_tiles",
                        lambda *a, **k: [tile("P1", "2024-01-05", 5.0, "landsat-9")])

    cov = coverage_mod.check_coverage(AOI, "2024-01-01", "2024-01-31",
                                      satellites=["sentinel2", "landsat"])
    assert all(c.satellite == "landsat-9" for c in cov)
    assert "unavailable" in capsys.readouterr().out


def test_coverage_empty_when_all_fail(monkeypatch):
    monkeypatch.setattr(coverage_mod.sentinel2, "search_tiles", lambda *a, **k: [])
    monkeypatch.setattr(coverage_mod.landsat, "search_tiles", lambda *a, **k: [])
    cov = coverage_mod.check_coverage(AOI, "2024-01-01", "2024-01-31",
                                      satellites=["sentinel2", "landsat"])
    assert cov == []
