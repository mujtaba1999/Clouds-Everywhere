"""Tests for aoi.to_bbox — AOI normalization and error handling."""
import pytest

from clouds_everywhere.aoi import to_bbox


# ── valid inputs — all should give the same WGS84 bbox ────────────────────────

MADRID = [-4.5, 39.5, -2.5, 41.0]


def test_plain_bbox_passthrough():
    assert to_bbox([-4.5, 39.5, -2.5, 41.0]) == MADRID


def test_bbox_tuple():
    assert to_bbox((-4.5, 39.5, -2.5, 41.0)) == MADRID


def test_polygon_ring():
    ring = [[-4.5, 39.5], [-2.5, 39.5], [-2.5, 41.0], [-4.5, 41.0], [-4.5, 39.5]]
    assert to_bbox(ring) == MADRID


def test_geojson_feature():
    gj = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-4.5, 39.5], [-2.5, 39.5], [-2.5, 41.0], [-4.5, 41.0], [-4.5, 39.5],
            ]],
        },
    }
    assert to_bbox(gj) == MADRID


def test_geojson_feature_collection():
    gj = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-4.5, 39.5], [-2.5, 39.5], [-2.5, 41.0], [-4.5, 41.0], [-4.5, 39.5],
                ]],
            },
        }],
    }
    assert to_bbox(gj) == MADRID


def test_lat_lon_axis_swap_detected():
    # coords given as (lat, lon) with lon > 90 → should be swapped to (lon, lat)
    swapped = [[30.0, 120.0], [31.0, 120.0], [31.0, 122.0], [30.0, 122.0], [30.0, 120.0]]
    bbox = to_bbox(swapped)
    # after swap, x = 120..122 (lon), y = 30..31 (lat)
    assert bbox == [120.0, 30.0, 122.0, 31.0]


# ── error handling — these are the "AOI can cause problems" cases ──────────────

def test_empty_list_raises_clear_error():
    with pytest.raises(ValueError, match="empty"):
        to_bbox([])


def test_empty_tuple_raises_clear_error():
    with pytest.raises(ValueError, match="empty"):
        to_bbox(())


def test_too_few_polygon_points():
    with pytest.raises(ValueError, match="at least 3"):
        to_bbox([[0.0, 0.0], [1.0, 1.0]])


def test_unsupported_type():
    with pytest.raises(TypeError):
        to_bbox(12345)


def test_unsupported_file_format(tmp_path):
    bad = tmp_path / "area.kml"
    bad.write_text("not really kml")
    with pytest.raises(ValueError, match="Unsupported file format"):
        to_bbox(str(bad))


def test_longitude_out_of_range():
    with pytest.raises(ValueError, match="Longitude"):
        to_bbox([-400.0, 10.0, -390.0, 20.0])


def test_latitude_out_of_range():
    with pytest.raises(ValueError, match="Latitude"):
        to_bbox([10.0, -100.0, 20.0, -95.0])


def test_degenerate_bbox_min_equals_max():
    with pytest.raises(ValueError, match="Degenerate|invalid|empty"):
        to_bbox([10.0, 10.0, 10.0, 10.0])
