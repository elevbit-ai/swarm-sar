"""Raise rescue alerts to human responders.

When a survivor estimate is both confirmed by fusion and escalated by the AI
layer, the dispatcher emits a :class:`RescueAlert` to every registered sink
(console, log, webhook, radio bridge...). It is deliberately the *only* thing
the pipeline "triggers", and what it triggers is a notification to people who
can help — a coordinate handed to a rescue team, never an action against the
person located.

Alerts are de-duplicated per survivor estimate so a standing confirmation does
not spam responders; a repeat only fires if enabled and re-confirmed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..core.vector import Vec3
from ..geo import GeoPoint, LocalFrame
from ..perception.fusion import SurvivorEstimate

AlertSink = Callable[["RescueAlert"], None]


@dataclass(frozen=True)
class RescueAlert:
    """A dispatched notification that a person likely needs help here."""

    estimate_id: int
    position: Vec3
    confidence: float
    corroborating_drones: int
    sim_time: float
    message: str
    geo: GeoPoint | None = None  # WGS-84 fix, when a LocalFrame is configured

    def as_dict(self) -> dict:
        data = {
            "estimate_id": self.estimate_id,
            "local_x": round(self.position.x, 2),
            "local_y": round(self.position.y, 2),
            "altitude": round(self.position.z, 2),
            "confidence": round(self.confidence, 3),
            "corroborating_drones": self.corroborating_drones,
            "sim_time": round(self.sim_time, 2),
            "message": self.message,
        }
        if self.geo is not None:
            data["geo"] = self.geo.as_dict()
        return data


@dataclass
class AlertDispatcher:
    """Fan out rescue alerts to sinks, once per confirmed survivor."""

    sinks: list[AlertSink] = field(default_factory=list)
    allow_repeat: bool = False
    frame: LocalFrame | None = None  # set to attach WGS-84 coordinates to alerts
    _fired: set[int] = field(default_factory=set)
    history: list[RescueAlert] = field(default_factory=list)

    def add_sink(self, sink: AlertSink) -> None:
        self.sinks.append(sink)

    def dispatch(self, estimate: SurvivorEstimate, sim_time: float) -> RescueAlert | None:
        """Emit an alert for a confirmed estimate, respecting de-duplication."""
        if not estimate.confirmed:
            return None
        if estimate.id in self._fired and not self.allow_repeat:
            return None
        geo = self.frame.to_geo(estimate.position) if self.frame is not None else None
        where = (
            f"{geo.lat:.5f}, {geo.lon:.5f}"
            if geo is not None
            else f"({estimate.position.x:.0f}, {estimate.position.y:.0f})"
        )
        alert = RescueAlert(
            estimate_id=estimate.id,
            position=estimate.position,
            confidence=estimate.confidence,
            corroborating_drones=estimate.corroborated_by,
            sim_time=sim_time,
            geo=geo,
            message=(
                f"Suspected survivor #{estimate.id} confirmed at "
                f"{where} — dispatch rescue team."
            ),
        )
        self._fired.add(estimate.id)
        self.history.append(alert)
        for sink in self.sinks:
            sink(alert)
        return alert


def console_sink(alert: RescueAlert) -> None:
    """A ready-made sink that prints a formatted rescue alert."""
    print(f"  [RESCUE ALERT] {alert.message} (p={alert.confidence:.2f})")
