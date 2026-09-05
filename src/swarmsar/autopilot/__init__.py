"""Actuation backends: how a velocity command reaches the aircraft.

``SimulatedActuator`` integrates motion in-process (the default, used by the
simulator and tests). ``MavlinkActuator`` sends the command to a real or SITL
autopilot over MAVLink, so the identical swarm logic flies actual hardware.
"""

from .actuator import Actuator, SimulatedActuator
from .mavlink import MavlinkActuator

__all__ = ["Actuator", "SimulatedActuator", "MavlinkActuator"]
