"""Decentralised coverage control with anti-collision.

Each drone computes its own velocity from local drives, using only the
telemetry it heard over the mesh — never a global controller:

* **separation** — push away from neighbours that are too close (safety);
* **spread**     — fan out horizontally so drones sensor-cover distinct lanes;
* **patrol**     — sweep north-south across the full height of the area, so the
  fleet actually traverses the region instead of hovering; each drone keeps its
  own sweep direction and reverses at the boundary;
* **boundary**   — stay inside the rectangle and hold search altitude.

A drone that is *tracking* a suspected survivor ignores patrol and holds
station instead, so confirmations stay put while the rest keep searching.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.drone import Drone, DroneStatus, Telemetry
from ..core.vector import Vec3


@dataclass
class SearchArea:
    """Axis-aligned rectangle to be covered, at a fixed search altitude."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float
    altitude: float = 30.0

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def center(self) -> Vec3:
        return Vec3((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2, self.altitude)

    def contains(self, p: Vec3) -> bool:
        return self.min_x <= p.x <= self.max_x and self.min_y <= p.y <= self.max_y

    def clamp(self, p: Vec3) -> Vec3:
        return Vec3(
            min(max(p.x, self.min_x), self.max_x),
            min(max(p.y, self.min_y), self.max_y),
            self.altitude,
        )


@dataclass
class FormationParams:
    separation_radius: float = 25.0
    separation_gain: float = 2.4
    spread_gain: float = 1.1
    patrol_gain: float = 2.2
    boundary_gain: float = 3.0
    hold_gain: float = 1.6
    boundary_margin: float = 8.0


class CoverageController:
    """Turns local mesh knowledge into a velocity command for one drone.

    The controller is stateful only in a small way: it remembers each drone's
    current vertical sweep direction so the fleet lawnmowers the area. That
    state is keyed by drone id and never leaks between drones.
    """

    def __init__(self, area: SearchArea, params: FormationParams | None = None) -> None:
        self.area = area
        self.p = params or FormationParams()
        self._sweep_dir: dict[str, float] = {}

    def command(
        self,
        drone: Drone,
        neighbors: dict[str, Telemetry],
        target: Vec3 | None = None,
    ) -> Vec3:
        """Compute the desired velocity for ``drone`` this tick.

        ``target`` is an optional point of interest (e.g. a survivor estimate
        this drone was assigned to confirm). When set, the drone holds over it.
        """
        if drone.status is DroneStatus.TRACKING and target is not None:
            return self._hold(drone, target)

        sep = self._separation(drone, neighbors)
        spread = self._spread(drone, neighbors)
        patrol = self._patrol(drone)
        bnd = self._boundary(drone)
        desired = (
            sep * self.p.separation_gain
            + spread * self.p.spread_gain
            + patrol * self.p.patrol_gain
            + bnd * self.p.boundary_gain
        )
        return desired.clamped(drone.max_speed)

    # -- individual drives -------------------------------------------------

    def _separation(self, drone: Drone, neighbors: dict[str, Telemetry]) -> Vec3:
        push = Vec3()
        for tel in neighbors.values():
            if tel.drone_id == drone.id:
                continue
            offset = drone.position - tel.position
            dist = offset.norm
            if 0 < dist < self.p.separation_radius:
                # Inverse-distance repulsion, strongest when almost touching.
                strength = (self.p.separation_radius - dist) / self.p.separation_radius
                push = push + offset.normalized() * strength
        return push

    def _spread(self, drone: Drone, neighbors: dict[str, Telemetry]) -> Vec3:
        """Fan out horizontally: drift away from the mean x of nearby drones."""
        xs = [t.position.x for t in neighbors.values() if t.drone_id != drone.id]
        if not xs:
            return Vec3()
        mean_x = sum(xs) / len(xs)
        dx = drone.position.x - mean_x
        direction = math.copysign(1.0, dx) if dx != 0 else 0.0
        return Vec3(direction, 0.0, 0.0)

    def _patrol(self, drone: Drone) -> Vec3:
        """North-south lawnmower sweep; reverse when near the y boundary."""
        d = self._sweep_dir.get(drone.id, 1.0)
        margin = self.p.boundary_margin
        if drone.position.y >= self.area.max_y - margin:
            d = -1.0
        elif drone.position.y <= self.area.min_y + margin:
            d = 1.0
        self._sweep_dir[drone.id] = d
        return Vec3(0.0, d, 0.0)

    def _boundary(self, drone: Drone) -> Vec3:
        """Keep the drone inside the search rectangle and at search altitude."""
        pull = Vec3()
        if drone.position.x < self.area.min_x:
            pull = pull + Vec3(1, 0, 0)
        elif drone.position.x > self.area.max_x:
            pull = pull + Vec3(-1, 0, 0)
        if drone.position.y < self.area.min_y:
            pull = pull + Vec3(0, 1, 0)
        elif drone.position.y > self.area.max_y:
            pull = pull + Vec3(0, -1, 0)
        dz = self.area.altitude - drone.position.z
        if abs(dz) > 0.5:
            pull = pull + Vec3(0, 0, math.copysign(1.0, dz))
        return pull

    def _hold(self, drone: Drone, target: Vec3) -> Vec3:
        offset = self.area.clamp(target) - drone.position
        return (offset * self.p.hold_gain).clamped(drone.max_speed)
