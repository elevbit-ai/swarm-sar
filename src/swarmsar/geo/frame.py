"""Local ENU <-> WGS-84 conversion for real-world rescue coordinates.

Search-and-rescue areas are small (a few kilometres at most), so an
equirectangular ("flat-earth") projection about a fixed origin is accurate to
well under a metre here while staying dependency-free. Pick an origin near the
operation, and every local ``Vec3`` maps to a latitude/longitude a rescue team
can navigate to.

For continental-scale work, swap this for a proper geodesic library; the rest
of the framework only depends on :class:`LocalFrame`'s two methods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.vector import Vec3

# Mean Earth radius (WGS-84 authalic sphere), metres.
_EARTH_RADIUS_M = 6_371_008.8
_M_PER_DEG_LAT = math.pi * _EARTH_RADIUS_M / 180.0


@dataclass(frozen=True)
class GeoPoint:
    """A WGS-84 geographic coordinate."""

    lat: float
    lon: float
    alt: float = 0.0

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError("lat must be within [-90, 90]")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError("lon must be within [-180, 180]")

    def as_dict(self) -> dict[str, float]:
        return {"lat": round(self.lat, 7), "lon": round(self.lon, 7), "alt": round(self.alt, 2)}


@dataclass(frozen=True)
class LocalFrame:
    """An East-North-Up tangent plane anchored at a geographic ``origin``."""

    origin: GeoPoint

    @property
    def _m_per_deg_lon(self) -> float:
        return _M_PER_DEG_LAT * math.cos(math.radians(self.origin.lat))

    def to_geo(self, local: Vec3) -> GeoPoint:
        """Local ENU metres (x=east, y=north, z=up) -> WGS-84."""
        lat = self.origin.lat + local.y / _M_PER_DEG_LAT
        lon = self.origin.lon + local.x / self._m_per_deg_lon
        return GeoPoint(lat=lat, lon=lon, alt=self.origin.alt + local.z)

    def to_local(self, geo: GeoPoint) -> Vec3:
        """WGS-84 -> local ENU metres about the origin."""
        x = (geo.lon - self.origin.lon) * self._m_per_deg_lon
        y = (geo.lat - self.origin.lat) * _M_PER_DEG_LAT
        return Vec3(x, y, geo.alt - self.origin.alt)
