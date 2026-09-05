"""The human-presence detector interface.

**Scope and intent.** A ``HumanDetector`` reports *where people appear to be*
so a rescue team can reach them. It is the sensing front-end of a
search-and-rescue system — thermal/RGB/acoustic in the field — and nothing
downstream of it in this project does anything but map, rank and alert humans
for assistance. Implementations must not be wired to any mechanism that harms
the people they detect.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..core.drone import Drone
from ..core.vector import Vec3


@dataclass(frozen=True)
class Detection:
    """A single sensor hit suggesting a person, in world coordinates."""

    source_drone: str
    position: Vec3
    confidence: float          # 0..1
    timestamp: float
    modality: str = "thermal"  # thermal | rgb | acoustic | rf ...

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")


class HumanDetector(ABC):
    """Strategy interface for turning a drone's field of view into detections.

    Swap in a real perception model (e.g. a thermal person-detector) by
    subclassing this and implementing :meth:`detect`. The swarm code depends
    only on this contract, never on a specific model.
    """

    @abstractmethod
    def detect(self, drone: Drone, now: float) -> list[Detection]:
        """Return the detections visible to ``drone`` at time ``now``."""
        raise NotImplementedError
