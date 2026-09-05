"""The drone node model: state, telemetry, and simple flight integration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from enum import Enum

from .vector import Vec3


class DroneStatus(str, Enum):
    """Lifecycle state of a single drone within the swarm."""

    IDLE = "idle"
    SEARCHING = "searching"
    TRACKING = "tracking"          # holding station over a suspected survivor
    RETURNING = "returning"        # low battery / recall
    LOST = "lost"                  # dropped off the mesh


@dataclass(frozen=True)
class Telemetry:
    """An immutable snapshot a drone shares with its neighbours over the mesh."""

    drone_id: str
    position: Vec3
    velocity: Vec3
    battery: float                 # 0.0 .. 1.0
    status: DroneStatus
    timestamp: float

    @property
    def is_healthy(self) -> bool:
        return self.status is not DroneStatus.LOST and self.battery > 0.0


@dataclass
class Drone:
    """A single autonomous node.

    The drone integrates its own motion each tick from a commanded velocity.
    Real deployments would replace :meth:`step` with an autopilot bridge
    (e.g. MAVLink), but the swarm logic above it stays identical.
    """

    id: str
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    battery: float = 1.0
    status: DroneStatus = DroneStatus.IDLE
    max_speed: float = 12.0        # m/s
    comm_range: float = 120.0      # m — radius of the mesh link
    sensor_range: float = 45.0     # m — radius of the human-presence sensor
    drain_per_metre: float = 6.0e-5
    idle_drain_per_s: float = 3.0e-4

    def command_velocity(self, desired: Vec3) -> None:
        """Set the target velocity, clamped to the drone's flight envelope."""
        self.velocity = desired.clamped(self.max_speed)

    def step(self, dt: float) -> None:
        """Advance position and drain the battery by ``dt`` seconds."""
        if self.status is DroneStatus.LOST or self.battery <= 0.0:
            self.status = DroneStatus.LOST
            self.velocity = Vec3()
            return
        travelled = self.velocity * dt
        self.position = self.position + travelled
        self.battery = max(
            0.0,
            self.battery
            - travelled.norm * self.drain_per_metre
            - self.idle_drain_per_s * dt,
        )
        if self.battery <= 0.0:
            self.status = DroneStatus.LOST
            self.velocity = Vec3()

    def telemetry(self, now: float | None = None) -> Telemetry:
        return Telemetry(
            drone_id=self.id,
            position=self.position,
            velocity=self.velocity,
            battery=self.battery,
            status=self.status,
            timestamp=time.time() if now is None else now,
        )

    def snapshot(self) -> Drone:
        """A detached copy, handy for logging without aliasing live state."""
        return replace(self)
