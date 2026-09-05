from swarmsar.alerting.dispatcher import AlertDispatcher
from swarmsar.core.vector import Vec3
from swarmsar.geo import GeoPoint, LocalFrame
from swarmsar.perception.fusion import SurvivorEstimate


def _confirmed(eid=1, pos=None):
    pos = pos if pos is not None else Vec3(100, 50, 0)
    return SurvivorEstimate(
        id=eid, position=pos, confidence=0.95, observations=3,
        contributors={"a", "b"}, confirmed=True,
    )


def test_alert_dedup():
    d = AlertDispatcher()
    est = _confirmed()
    assert d.dispatch(est, 1.0) is not None
    assert d.dispatch(est, 2.0) is None  # same estimate, suppressed
    assert len(d.history) == 1


def test_unconfirmed_never_alerts():
    d = AlertDispatcher()
    est = _confirmed()
    est.confirmed = False
    assert d.dispatch(est, 1.0) is None


def test_alert_carries_geo_when_frame_set():
    frame = LocalFrame(GeoPoint(lat=-3.1, lon=-60.0, alt=90.0))
    d = AlertDispatcher(frame=frame)
    alert = d.dispatch(_confirmed(pos=Vec3(500, 500, 0)), 1.0)
    assert alert.geo is not None
    assert alert.as_dict()["geo"]["lat"] != frame.origin.lat  # moved north
    assert "lat" in alert.as_dict()["geo"]


def test_alert_without_frame_has_no_geo():
    d = AlertDispatcher()
    alert = d.dispatch(_confirmed(), 1.0)
    assert alert.geo is None
    assert "geo" not in alert.as_dict()
