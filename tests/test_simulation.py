"""Integration test: the full pipeline locates survivors and alerts, deterministically."""

from swarmsar import AIRegistry, AlertDispatcher, Drone, SwarmCoordinator, Vec3
from swarmsar.ai.providers import HeuristicProvider
from swarmsar.perception.simulated import SimulatedDetector
from swarmsar.sim import World
from swarmsar.swarm.formation import SearchArea


def _coordinator():
    world = World.random(n_survivors=5, width=300, height=200, seed=3)
    area = SearchArea(0, 0, 300, 200, altitude=30.0)
    drones = [
        Drone(id=f"uav-{i}", position=Vec3(40 + i * 40, 10, 30))
        for i in range(6)
    ]
    ai = AIRegistry()
    ai.register(HeuristicProvider())
    dispatcher = AlertDispatcher()
    coord = SwarmCoordinator(
        drones=drones,
        detector=SimulatedDetector(world, seed=3),
        area=area,
        ai=ai,
        dispatcher=dispatcher,
    )
    return coord, world, dispatcher


def test_mission_locates_and_alerts():
    coord, world, dispatcher = _coordinator()
    coord.run(ticks=300)
    positions = [e.position for e in coord.detection_map.confirmed()]
    assert world.found_count(positions, radius=25.0) >= 3
    assert len(dispatcher.history) >= 3


def test_alerts_are_deduplicated():
    coord, _, dispatcher = _coordinator()
    coord.run(ticks=300)
    ids = [a.estimate_id for a in dispatcher.history]
    assert len(ids) == len(set(ids))  # no estimate alerted twice


def test_run_is_deterministic():
    c1, _, _ = _coordinator()
    c2, _, _ = _coordinator()
    r1 = c1.run(ticks=120)
    r2 = c2.run(ticks=120)
    assert [r.confirmed for r in r1] == [r.confirmed for r in r2]
