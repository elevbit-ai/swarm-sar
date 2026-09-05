"""A simulated detector for demos, tests and CI — no hardware required.

It reads the ground-truth survivors from a :class:`~swarmsar.sim.world.World`
and returns noisy, range-attenuated detections, so the rest of the pipeline
can be exercised deterministically.
"""

from __future__ import annotations

import random

from ..core.drone import Drone
from ..core.vector import Vec3
from .detector import Detection, HumanDetector


class SimulatedDetector(HumanDetector):
    """Emits detections for ground-truth survivors within a drone's sensor cone.

    Confidence falls off with range and each hit carries positional noise, so
    fusion across several drones is what produces a reliable fix — exactly as
    in the field.
    """

    def __init__(self, world, seed: int | None = None, noise_m: float = 4.0) -> None:
        self.world = world
        self.noise_m = noise_m
        self._rng = random.Random(seed)

    def detect(self, drone: Drone, now: float) -> list[Detection]:
        hits: list[Detection] = []
        for survivor in self.world.survivors:
            # Compare on the ground plane; drones fly above the survivors.
            ground = Vec3(drone.position.x, drone.position.y, survivor.z)
            dist = ground.distance_to(survivor)
            if dist > drone.sensor_range:
                continue
            # Detection probability and confidence both decay with range.
            p_detect = max(0.05, 1.0 - dist / drone.sensor_range)
            if self._rng.random() > p_detect:
                continue
            noisy = Vec3(
                survivor.x + self._rng.gauss(0, self.noise_m),
                survivor.y + self._rng.gauss(0, self.noise_m),
                survivor.z,
            )
            confidence = round(min(1.0, p_detect * self._rng.uniform(0.75, 1.0)), 4)
            hits.append(
                Detection(
                    source_drone=drone.id,
                    position=noisy,
                    confidence=confidence,
                    timestamp=now,
                    modality="thermal",
                )
            )
        return hits
