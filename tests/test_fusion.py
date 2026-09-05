from swarmsar.core.vector import Vec3
from swarmsar.perception.detector import Detection
from swarmsar.perception.fusion import DetectionMap


def _det(drone, x, y, conf, t=0.0):
    return Detection(source_drone=drone, position=Vec3(x, y, 0), confidence=conf, timestamp=t)


def test_nearby_detections_merge():
    m = DetectionMap(merge_radius=12)
    m.ingest([_det("a", 100, 100, 0.5)], now=0)
    m.ingest([_det("b", 104, 103, 0.5)], now=0)
    assert len(m.estimates) == 1


def test_distant_detections_stay_separate():
    m = DetectionMap(merge_radius=12)
    m.ingest([_det("a", 0, 0, 0.5), _det("a", 80, 80, 0.5)], now=0)
    assert len(m.estimates) == 2


def test_confirmation_requires_two_drones():
    m = DetectionMap(confirm_threshold=0.8, confirm_min_drones=2)
    # Two hits from the SAME drone: high belief but not corroborated.
    m.ingest([_det("a", 50, 50, 0.9), _det("a", 51, 50, 0.9)], now=0)
    assert m.confirmed() == []
    # A second drone corroborates -> confirmed.
    m.ingest([_det("b", 50, 51, 0.9)], now=0)
    assert len(m.confirmed()) == 1


def test_belief_accumulates_across_observations():
    m = DetectionMap()
    m.ingest([_det("a", 10, 10, 0.6)], now=0)
    first = m.estimates[0].confidence
    m.ingest([_det("b", 11, 10, 0.6)], now=0)
    assert m.estimates[0].confidence > first


def test_decay_removes_stale_unconfirmed():
    m = DetectionMap(decay_half_life=1.0)
    m.ingest([_det("a", 10, 10, 0.3)], now=0)
    m.decay(now=20)  # many half-lives later
    assert m.estimates == []
