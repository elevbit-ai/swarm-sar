"""Record a mission to JSON for the web dashboard.

The recorder is an ``on_tick`` callback for :meth:`SwarmCoordinator.run`. Each
tick it captures a compact frame — drone poses and status, the live mesh edges,
the survivor estimates, and any alerts so far — and :meth:`save` writes a single
JSON document the dashboard replays. Coordinates are rounded to keep the file
small; ground-truth survivors and the area are stored once in the header so the
viewer can score coverage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..swarm.coordinator import SwarmCoordinator, TickReport


def _round_vec(v, nd: int = 1) -> list[float]:
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


@dataclass
class DashboardRecorder:
    """Collect per-tick frames from a running coordinator."""

    coordinator: SwarmCoordinator
    world: object | None = None
    every: int = 1
    frames: list[dict] = field(default_factory=list)

    def __call__(self, report: TickReport) -> None:
        if report.tick % self.every != 0:
            return
        c = self.coordinator
        self.frames.append(
            {
                "t": round(c.sim_time, 2),
                "drones": [
                    {
                        "id": d.id,
                        "p": _round_vec(d.position),
                        "batt": round(d.battery, 3),
                        "status": d.status.value,
                        "sensor": d.sensor_range,
                    }
                    for d in c.drones
                ],
                "edges": [sorted(link) for link in c.mesh.edges],
                "estimates": [
                    {
                        "id": e.id,
                        "p": _round_vec(e.position),
                        "conf": round(e.confidence, 3),
                        "drones": e.corroborated_by,
                        "confirmed": e.confirmed,
                    }
                    for e in c.detection_map.estimates
                ],
                "alerts": [a.estimate_id for a in c.dispatcher.history],
                "rationale": report.rationale,
            }
        )

    def document(self) -> dict:
        c = self.coordinator
        survivors = []
        if self.world is not None and getattr(self.world, "survivors", None):
            survivors = [_round_vec(s) for s in self.world.survivors]
        return {
            "meta": {
                "generator": "swarmsar.telemetry.DashboardRecorder",
                "area": {
                    "min_x": c.area.min_x,
                    "min_y": c.area.min_y,
                    "max_x": c.area.max_x,
                    "max_y": c.area.max_y,
                    "altitude": c.area.altitude,
                },
                "drone_count": len(c.drones),
                "survivors": survivors,
                "frame_count": len(self.frames),
            },
            "frames": self.frames,
        }

    def save(self, path: str, *, indent: int | None = None) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.document(), fh, indent=indent)

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.document(), indent=indent)
