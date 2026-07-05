"""Clouds-Everywhere — check satellite imagery availability by cloud cover."""

from .search import search_images
from .coverage import check_coverage
from .query import query
from .models import (
    SatelliteImage, TileResult, DateCoverage,
    TilePeriodStat, PeriodCoverage, QueryReport,
)
from .aoi import to_bbox

__version__ = "0.1.0"

__all__ = [
    "query", "search_images", "check_coverage", "to_bbox",
    "SatelliteImage", "TileResult", "DateCoverage",
    "TilePeriodStat", "PeriodCoverage", "QueryReport",
]
