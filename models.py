from dataclasses import dataclass, field
from typing import List

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