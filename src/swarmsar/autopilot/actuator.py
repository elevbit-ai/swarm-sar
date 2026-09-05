"""The actuation seam between swarm decisions and the aircraft.

The coordinator computes a *desired velocity* for each drone and hands it to an
:class:`Actuator`. In simulation the actuator integrates motion; on hardware it
would push the command to an autopilot and refresh the drone's state from
telemetry. Keeping this behind one interface is what lets the same swarm logic
run in the simulator and on a real vehicle unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.drone import Drone
from ..core.vector import Vec3


class Actuator(ABC):
    """Applies a desired velocity to a drone for one time step."""

    @abstractmethod
    def apply(self, drone: Drone, desired_velocity: Vec3, dt: float) -> None:
        raise NotImplementedError


class SimulatedActuator(Actuator):
    """Default backend: clamp the command and integrate motion in-process."""

    def apply(self, drone: Drone, desired_velocity: Vec3, dt: float) -> None:
        drone.command_velocity(desired_velocity)
        drone.step(dt)
