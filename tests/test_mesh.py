from swarmsar.core.drone import Drone
from swarmsar.core.mesh import GraphMesh
from swarmsar.core.vector import Vec3


def _line(spacing: float, n: int = 3, comm_range: float = 60.0):
    return [
        Drone(id=f"d{i}", position=Vec3(i * spacing, 0, 30), comm_range=comm_range)
        for i in range(n)
    ]


def test_edges_form_within_range():
    mesh = GraphMesh()
    mesh.rebuild(_line(spacing=50), now=0.0)
    # 0-1 and 1-2 are within 60 m; 0-2 (100 m) is not.
    assert mesh.neighbors("d0") == {"d1"}
    assert mesh.neighbors("d1") == {"d0", "d2"}
    assert mesh.is_connected


def test_partition_creates_two_components():
    mesh = GraphMesh()
    mesh.rebuild(_line(spacing=200), now=0.0)  # all out of range
    assert not mesh.is_connected
    assert len(mesh.components()) == 3


def test_gossip_hops_limit_visibility():
    mesh = GraphMesh()
    mesh.rebuild(_line(spacing=50, n=4), now=0.0)  # chain d0-d1-d2-d3
    one_hop = mesh.reachable_telemetry("d0", max_hops=1)
    assert set(one_hop) == {"d0", "d1"}
    all_hops = mesh.reachable_telemetry("d0", max_hops=5)
    assert set(all_hops) == {"d0", "d1", "d2", "d3"}


def test_lost_drone_excluded():
    drones = _line(spacing=50)
    drones[1].battery = 0.0
    drones[1].step(1.0)  # marks it LOST
    mesh = GraphMesh()
    mesh.rebuild(drones, now=1.0)
    assert "d1" not in mesh.neighbors("d0")
