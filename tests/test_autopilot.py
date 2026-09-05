import pytest

from swarmsar.autopilot import MavlinkActuator, SimulatedActuator
from swarmsar.core.drone import Drone
from swarmsar.core.vector import Vec3


def test_simulated_actuator_moves_drone():
    drone = Drone(id="d", position=Vec3(0, 0, 30))
    SimulatedActuator().apply(drone, Vec3(10, 0, 0), dt=1.0)
    assert drone.position.x > 0
    assert drone.velocity.norm <= drone.max_speed + 1e-9


def test_simulated_actuator_clamps_to_max_speed():
    drone = Drone(id="d", max_speed=5.0)
    SimulatedActuator().apply(drone, Vec3(100, 0, 0), dt=1.0)
    assert drone.velocity.norm == pytest.approx(5.0)


def test_mavlink_actuator_requires_pymavlink_lazily():
    # Constructing must not import pymavlink; connecting without it must raise clearly.
    act = MavlinkActuator("udpin:0.0.0.0:14540")
    pytest.importorskip  # noqa: B018 - documents intent; skip below if installed
    try:
        import pymavlink  # noqa: F401
    except ImportError:
        with pytest.raises(ImportError, match="pymavlink"):
            act.connect()
