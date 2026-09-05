import pytest

from swarmsar.core.vector import Vec3
from swarmsar.geo import GeoPoint, LocalFrame


def test_round_trip_local_geo_local():
    frame = LocalFrame(GeoPoint(lat=-23.5505, lon=-46.6333, alt=760.0))  # São Paulo
    local = Vec3(1234.0, -567.0, 42.0)
    back = frame.to_local(frame.to_geo(local))
    assert back.x == pytest.approx(local.x, abs=1e-3)
    assert back.y == pytest.approx(local.y, abs=1e-3)
    assert back.z == pytest.approx(local.z, abs=1e-6)


def test_north_increases_latitude():
    frame = LocalFrame(GeoPoint(lat=0.0, lon=0.0))
    north_1km = frame.to_geo(Vec3(0, 1000, 0))
    assert north_1km.lat > 0
    # ~1 km north near the equator is close to 0.009 degrees of latitude.
    assert north_1km.lat == pytest.approx(0.00899, abs=1e-4)


def test_east_scales_with_latitude():
    equator = LocalFrame(GeoPoint(lat=0.0, lon=0.0))
    high = LocalFrame(GeoPoint(lat=60.0, lon=0.0))
    d_equator = equator.to_geo(Vec3(1000, 0, 0)).lon
    d_high = high.to_geo(Vec3(1000, 0, 0)).lon
    # cos(60°) = 0.5, so the same easting spans ~twice the longitude at lat 60.
    assert d_high == pytest.approx(2 * d_equator, rel=1e-3)


def test_invalid_latitude_rejected():
    with pytest.raises(ValueError):
        GeoPoint(lat=91.0, lon=0.0)


def test_origin_maps_to_zero():
    origin = GeoPoint(lat=10.0, lon=20.0, alt=5.0)
    frame = LocalFrame(origin)
    v = frame.to_local(origin)
    assert v.norm == pytest.approx(0.0, abs=1e-9)
