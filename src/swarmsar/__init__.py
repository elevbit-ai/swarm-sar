"""SwarmSAR — graph-coordinated drone swarm for search-and-rescue.

Author: Joaquim Pedro de Morais Filho.

This framework is built strictly for humanitarian search-and-rescue,
inspection and mapping. It locates people in order to *help* them; it
contains no targeting or weapons functionality and must not be adapted
for any use that harms people. See the project README and LICENSE.
"""

from .__about__ import (
    __author__,
    __copyright__,
    __license__,
    __summary__,
    __title__,
    __url__,
    __version__,
)
from .ai.provider import AIProvider, Decision, SituationContext
from .ai.registry import AIRegistry
from .alerting.dispatcher import AlertDispatcher, RescueAlert
from .autopilot.actuator import Actuator, SimulatedActuator
from .core.drone import Drone, DroneStatus, Telemetry
from .core.mesh import GraphMesh
from .core.vector import Vec3
from .geo import GeoPoint, LocalFrame
from .perception.detector import Detection, HumanDetector
from .perception.fusion import DetectionMap, SurvivorEstimate
from .swarm.coordinator import MissionConfig, SwarmCoordinator
from .telemetry import DashboardRecorder

__all__ = [
    "Vec3",
    "Drone",
    "DroneStatus",
    "Telemetry",
    "GraphMesh",
    "SwarmCoordinator",
    "MissionConfig",
    "Detection",
    "HumanDetector",
    "DetectionMap",
    "SurvivorEstimate",
    "AIRegistry",
    "AIProvider",
    "Decision",
    "SituationContext",
    "AlertDispatcher",
    "RescueAlert",
    "Actuator",
    "SimulatedActuator",
    "GeoPoint",
    "LocalFrame",
    "DashboardRecorder",
    "__version__",
    "__author__",
    "__license__",
    "__copyright__",
    "__summary__",
    "__title__",
    "__url__",
]
