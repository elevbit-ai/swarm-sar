"""Ground-truth world for the simulator: where the survivors actually are.

Only the simulated detector may read the survivor list; the swarm itself must
discover them through sensing and fusion, which is what makes the demo a fair
test of the pipeline.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..core.vector import Vec3


@dataclass
class World:
    """A rectangular search region seeded with hidden survivors."""

    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 400.0
    max_y: float = 300.0
    survivors: list[Vec3] = field(default_factory=list)

    @classmethod
    def random(
        cls,
        n_survivors: int = 5,
        width: float = 400.0,
        height: float = 300.0,
        seed: int | None = None,
    ) -> World:
        rng = random.Random(seed)
        survivors = [
            Vec3(rng.uniform(0, width), rng.uniform(0, height), 0.0)
            for _ in range(n_survivors)
        ]
        return cls(0.0, 0.0, width, height, survivors)

    def found_count(self, estimates_positions: list[Vec3], radius: float = 15.0) -> int:
        """How many true survivors have an estimate within ``radius`` (for scoring)."""
        found = 0
        for truth in self.survivors:
            if any(truth.distance_to(p) <= radius for p in estimates_positions):
                found += 1
        return found
