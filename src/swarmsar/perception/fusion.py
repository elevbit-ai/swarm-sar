"""Fuse detections from many drones into a shared survivor map.

Detections arrive noisy and duplicated — several drones may see the same
person from different angles. The :class:`DetectionMap` clusters nearby hits,
maintains a confidence-weighted position estimate per cluster, and lets
confidence decay over time so stale ghosts fade. This is the swarm's shared
picture of "who is out there and how sure are we".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count

from ..core.vector import Vec3
from .detector import Detection


@dataclass
class SurvivorEstimate:
    """A fused, running estimate of one suspected survivor's location."""

    id: int
    position: Vec3
    confidence: float
    observations: int
    contributors: set[str] = field(default_factory=set)
    first_seen: float = 0.0
    last_seen: float = 0.0
    confirmed: bool = False

    @property
    def corroborated_by(self) -> int:
        """Number of distinct drones that have contributed to this estimate."""
        return len(self.contributors)


class DetectionMap:
    """Online clustering + confidence fusion for survivor detections.

    Parameters
    ----------
    merge_radius:
        Detections within this distance of an estimate update it; otherwise a
        new estimate is created.
    decay_half_life:
        Seconds over which an unrefreshed estimate loses half its confidence.
    confirm_threshold / confirm_min_drones:
        An estimate is *confirmed* once its confidence and the number of
        distinct contributing drones both clear these bars — the guard against
        a single false positive escalating.
    """

    def __init__(
        self,
        merge_radius: float = 18.0,
        decay_half_life: float = 20.0,
        confirm_threshold: float = 0.8,
        confirm_min_drones: int = 2,
    ) -> None:
        self.merge_radius = merge_radius
        self.decay_half_life = decay_half_life
        self.confirm_threshold = confirm_threshold
        self.confirm_min_drones = confirm_min_drones
        self._estimates: dict[int, SurvivorEstimate] = {}
        self._ids = count(1)

    @property
    def estimates(self) -> list[SurvivorEstimate]:
        return list(self._estimates.values())

    def confirmed(self) -> list[SurvivorEstimate]:
        return [e for e in self._estimates.values() if e.confirmed]

    def ingest(self, detections: list[Detection], now: float) -> None:
        """Fold a batch of detections into the map."""
        for det in detections:
            match = self._nearest(det.position)
            if match is None:
                self._create(det)
            else:
                self._update(match, det)

    def decay(self, now: float) -> None:
        """Age out estimates that have not been refreshed recently."""
        if self.decay_half_life <= 0:
            return
        drop: list[int] = []
        for est in self._estimates.values():
            elapsed = now - est.last_seen
            if elapsed <= 0:
                continue
            est.confidence *= 0.5 ** (elapsed / self.decay_half_life)
            est.last_seen = now
            if est.confidence < 0.05 and not est.confirmed:
                drop.append(est.id)
        for eid in drop:
            del self._estimates[eid]

    # -- internals ---------------------------------------------------------

    def _nearest(self, position: Vec3) -> SurvivorEstimate | None:
        best: SurvivorEstimate | None = None
        best_dist = self.merge_radius
        for est in self._estimates.values():
            d = est.position.distance_to(position)
            if d <= best_dist:
                best, best_dist = est, d
        return best

    def _create(self, det: Detection) -> None:
        eid = next(self._ids)
        self._estimates[eid] = SurvivorEstimate(
            id=eid,
            position=det.position,
            confidence=det.confidence,
            observations=1,
            contributors={det.source_drone},
            first_seen=det.timestamp,
            last_seen=det.timestamp,
        )
        self._reassess(self._estimates[eid])

    def _update(self, est: SurvivorEstimate, det: Detection) -> None:
        # Confidence-weighted position blend, then Bayesian-style OR on belief.
        w_old, w_new = est.confidence, det.confidence
        total = w_old + w_new
        if total > 0:
            est.position = (est.position * w_old + det.position * w_new) / total
        est.confidence = 1.0 - (1.0 - est.confidence) * (1.0 - det.confidence)
        est.observations += 1
        est.contributors.add(det.source_drone)
        est.last_seen = det.timestamp
        self._reassess(est)

    def _reassess(self, est: SurvivorEstimate) -> None:
        est.confidence = min(1.0, est.confidence)
        if (
            est.confidence >= self.confirm_threshold
            and est.corroborated_by >= self.confirm_min_drones
        ):
            est.confirmed = True
