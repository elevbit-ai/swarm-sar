"""Minimal, dependency-free 3D vector used across the framework.

Coordinates are metres in a local East-North-Up (ENU) frame:
``x`` east, ``y`` north, ``z`` up (altitude).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vec3:
    """An immutable 3D vector with the arithmetic the swarm math needs."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> Vec3:
        if scalar == 0:
            raise ZeroDivisionError("cannot divide a Vec3 by zero")
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    @property
    def norm(self) -> float:
        """Euclidean length of the vector."""
        return math.sqrt(self.dot(self))

    def distance_to(self, other: Vec3) -> float:
        return (self - other).norm

    def normalized(self) -> Vec3:
        """Unit vector in the same direction; the zero vector maps to itself."""
        n = self.norm
        return self if n == 0 else self / n

    def clamped(self, max_norm: float) -> Vec3:
        """Return the vector scaled down so its length never exceeds ``max_norm``."""
        if max_norm < 0:
            raise ValueError("max_norm must be non-negative")
        n = self.norm
        return self if n <= max_norm or n == 0 else self * (max_norm / n)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


ORIGIN = Vec3(0.0, 0.0, 0.0)
