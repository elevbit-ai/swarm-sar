import json

from swarmsar import AIRegistry, AlertDispatcher, Drone, SwarmCoordinator, Vec3
from swarmsar.ai.providers import HeuristicProvider
from swarmsar.perception.simulated import SimulatedDetector
from swarmsar.sim import World
from swarmsar.swarm.formation import SearchArea
from swarmsar.telemetry import DashboardRecorder


def _coordinator():
    world = World.random(n_survivors=4, width=200, height=150, seed=1)
    area = SearchArea(0, 0, 200, 150, altitude=30.0)
    ai = AIRegistry()
    ai.register(HeuristicProvider())
    coord = SwarmCoordinator(
        drones=[Drone(id=f"uav-{i}", position=Vec3(30 + i * 30, 10, 30)) for i in range(4)],
        detector=SimulatedDetector(world, seed=1),
        area=area,
        ai=ai,
        dispatcher=AlertDispatcher(),
    )
    return coord, world


def test_recorder_captures_frames():
    coord, world = _coordinator()
    rec = DashboardRecorder(coord, world=world)
    coord.run(ticks=50, on_tick=rec)
    assert len(rec.frames) == 50
    assert all("drones" in f and "edges" in f for f in rec.frames)


def test_recorder_every_n():
    coord, world = _coordinator()
    rec = DashboardRecorder(coord, world=world, every=5)
    coord.run(ticks=50, on_tick=rec)
    assert len(rec.frames) == 10


def test_document_is_json_serialisable_with_header():
    coord, world = _coordinator()
    rec = DashboardRecorder(coord, world=world)
    coord.run(ticks=20, on_tick=rec)
    doc = json.loads(rec.to_json())
    assert doc["meta"]["drone_count"] == 4
    assert len(doc["meta"]["survivors"]) == 4
    assert doc["meta"]["frame_count"] == 20
