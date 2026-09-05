import math

import pytest

from swarmsar.core.vector import Vec3


def test_add_sub_scale():
    a, b = Vec3(1, 2, 3), Vec3(4, 5, 6)
    assert a + b == Vec3(5, 7, 9)
    assert b - a == Vec3(3, 3, 3)
    assert a * 2 == Vec3(2, 4, 6)
    assert 2 * a == Vec3(2, 4, 6)


def test_norm_and_distance():
    assert Vec3(3, 4, 0).norm == 5
    assert Vec3(0, 0, 0).distance_to(Vec3(0, 0, 2)) == 2


def test_normalized_unit_length():
    n = Vec3(0, 3, 4).normalized()
    assert math.isclose(n.norm, 1.0)


def test_normalized_zero_is_stable():
    assert Vec3().normalized() == Vec3()


def test_clamped():
    v = Vec3(10, 0, 0).clamped(4)
    assert math.isclose(v.norm, 4.0)
    assert Vec3(1, 0, 0).clamped(4) == Vec3(1, 0, 0)


def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        _ = Vec3(1, 1, 1) / 0
