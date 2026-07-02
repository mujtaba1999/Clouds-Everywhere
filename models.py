from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SatelliteImage:
    id: str
    date: str
    cloud_cover: float
    satellite: str
    thumbnail_url: str

    def __repr__(self):
        return f"{self.date} | {self.satellite} | Cloud: {self.cloud_cover}%"


@dataclass
class TileResult:
    tile_id: str
    date: str
    cloud_cover: float        # -1 means unknown
    satellite: str
    item_id: str
    thumbnail_url: str
    geometry: dict | None = None      # GeoJSON geometry from the STAC item

    def __repr__(self):
        cloud = f"{self.cloud_cover:.1f}%" if self.cloud_cover != -1 else "N/A"
        return f"{self.date} | {self.satellite} | Tile {self.tile_id} | Cloud: {cloud}"


@dataclass
class DateCoverage:
    date: str
    satellite: str
    status: str                          # "full" | "partial" | "missing"
    required_tiles: List[str]
    covered_tiles: List[str]             # tiles that pass the cloud threshold
    missing_tiles: List[str]             # absent or too cloudy
    avg_cloud: float                     # average over covered_tiles; -1 if unknown
    tile_details: List[TileResult] = field(default_factory=list)

    def __repr__(self):
        cloud = f"{self.avg_cloud:.1f}%" if self.avg_cloud != -1 else "N/A"
        return (
            f"{self.date} | {self.satellite} | {self.status.upper()} "
            f"({len(self.covered_tiles)}/{len(self.required_tiles)} tiles) "
            f"avg cloud: {cloud}"
        )


# ── Period-based availability report ──────────────────────────────────────────

@dataclass
class TilePeriodStat:
    """How much usable imagery exists for a single tile within one time period."""
    tile_id: str
    usable_images: int          # scenes at or below the cloud threshold
    total_images: int           # all scenes acquired, regardless of cloud
    best_cloud: float           # lowest cloud % seen; -1 if none acquired

    @property
    def covered(self) -> bool:
        return self.usable_images > 0

    def __repr__(self):
        best = f"{self.best_cloud:.1f}%" if self.best_cloud != -1 else "N/A"
        return f"{self.tile_id}: {self.usable_images} usable / {self.total_images} total (best {best})"


@dataclass
class PeriodCoverage:
    """Availability of one satellite over the AOI for one time period (day/week/month)."""
    label: str                  # friendly label, e.g. "13-19 Jan 2024"
    period_start: str           # "YYYY-MM-DD"
    period_end: str             # "YYYY-MM-DD"
    satellite: str
    status: str                 # "available" | "gap" | "missing"
    required_tiles: List[str]
    covered_tiles: List[str]    # tiles with >=1 usable image this period
    missing_tiles: List[str]    # tiles with zero usable images (the holes)
    tile_stats: List[TilePeriodStat] = field(default_factory=list)

    @property
    def n_required(self) -> int:
        return len(self.required_tiles)

    @property
    def n_covered(self) -> int:
        return len(self.covered_tiles)

    @property
    def total_usable_images(self) -> int:
        return sum(t.usable_images for t in self.tile_stats)

    def __repr__(self):
        return (
            f"{self.label} | {self.satellite} | {self.status.upper()} "
            f"({self.n_covered}/{self.n_required} tiles, {self.total_usable_images} images)"
        )


@dataclass
class QueryReport:
    """
    Full result of a user query, grouped by time period.

    Use ``print(report)`` or ``report.summary()`` for a friendly, plain-language
    breakdown, or ``report.to_dataframe()`` for a tabular view.
    """
    aoi_bbox: List[float]
    start_date: str
    end_date: str
    max_cloud: float
    group_by: str                       # "day" | "week" | "month"
    satellites: List[str]
    periods: List[PeriodCoverage] = field(default_factory=list)

    # ── convenience views ────────────────────────────────────────────────────
    def by_satellite(self) -> Dict[str, List[PeriodCoverage]]:
        out: Dict[str, List[PeriodCoverage]] = {}
        for p in self.periods:
            out.setdefault(p.satellite, []).append(p)
        return out

    def available_periods(self, satellite=None) -> List[PeriodCoverage]:
        return [p for p in self.periods
                if p.status == "available" and (satellite is None or p.satellite == satellite)]

    def gap_periods(self, satellite=None) -> List[PeriodCoverage]:
        return [p for p in self.periods
                if p.status == "gap" and (satellite is None or p.satellite == satellite)]

    def required_tiles(self, satellite) -> List[str]:
        for p in self.periods:
            if p.satellite == satellite:
                return p.required_tiles
        return []

    def __repr__(self):
        return self.summary()

    # ── tabular views ────────────────────────────────────────────────────────
    def to_dataframe(self):
        """One row per period × satellite (requires pandas)."""
        import pandas as pd
        return pd.DataFrame([
            {
                "Period":       p.label,
                "Start":        p.period_start,
                "Satellite":    p.satellite,
                "Status":       p.status,
                "Tiles needed": p.n_required,
                "Tiles covered": p.n_covered,
                "Images":       p.total_usable_images,
                "Missing tiles": ", ".join(p.missing_tiles) if p.missing_tiles else "-",
            }
            for p in self.periods
        ])

    def tile_dataframe(self):
        """One row per period × satellite × tile (requires pandas)."""
        import pandas as pd
        rows = []
        for p in self.periods:
            for t in p.tile_stats:
                rows.append({
                    "Period":    p.label,
                    "Start":     p.period_start,
                    "Satellite": p.satellite,
                    "Tile":      t.tile_id,
                    "Usable":    t.usable_images,
                    "Total":     t.total_images,
                    "Best cloud %": round(t.best_cloud, 1) if t.best_cloud != -1 else None,
                })
        return pd.DataFrame(rows)

    # ── friendly text summary ────────────────────────────────────────────────
    def summary(self) -> str:
        icon = {"available": "[OK] ", "gap": "[GAP]", "missing": "[--] "}
        word = {
            "available": "All tiles have usable imagery",
            "gap":       "Data gap - some tiles missing",
            "missing":   "No usable imagery",
        }
        unit = {"day": "day", "week": "week", "month": "month"}[self.group_by]

        lines = []
        lines.append("=" * 68)
        lines.append("  SATELLITE DATA AVAILABILITY REPORT")
        lines.append("=" * 68)
        lines.append(f"  Study area (bbox) : {self.aoi_bbox}")
        lines.append(f"  Date range        : {self.start_date}  ->  {self.end_date}")
        lines.append(f"  Cloud threshold   : <= {self.max_cloud:.0f}%")
        lines.append(f"  Grouped by        : {unit}")
        lines.append("")

        for satellite, periods in self.by_satellite().items():
            n_req = periods[0].n_required if periods else 0
            n_ok  = sum(1 for p in periods if p.status == "available")
            n_gap = sum(1 for p in periods if p.status == "gap")
            n_no  = sum(1 for p in periods if p.status == "missing")

            lines.append("-" * 68)
            lines.append(f"  {satellite}  -  needs {n_req} tiles to fully cover your area")
            lines.append("-" * 68)

            for p in periods:
                detail = ""
                if p.status == "gap":
                    holes = ", ".join(p.missing_tiles[:6])
                    if len(p.missing_tiles) > 6:
                        holes += f", +{len(p.missing_tiles) - 6} more"
                    detail = f"  ({p.n_covered}/{p.n_required} tiles; missing: {holes})"
                elif p.status == "available":
                    detail = f"  ({p.total_usable_images} images across {p.n_required} tiles)"
                lines.append(f"    {icon[p.status]} {p.label:<22} {word[p.status]}{detail}")

            lines.append("")
            lines.append(f"    Summary: {n_ok} fully-covered {unit}s, "
                         f"{n_gap} with gaps, {n_no} empty  (of {len(periods)} {unit}s)")
            lines.append("")

        lines.append("=" * 68)
        return "\n".join(lines)