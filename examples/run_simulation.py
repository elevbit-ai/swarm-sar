"""End-to-end search-and-rescue simulation.

Spawns a swarm over a search area seeded with hidden survivors, runs the full
mesh -> sense -> fuse -> decide -> alert -> act loop, and prints the survivors
the swarm located. Everything runs offline and deterministically.

Run from the repository root::

    python examples/run_simulation.py
"""

from __future__ import annotations

from swarmsar import (
    AIRegistry,
    AlertDispatcher,
    Drone,
    MissionConfig,
    SwarmCoordinator,
    Vec3,
)
from swarmsar.ai.providers import HeuristicProvider
from swarmsar.alerting.dispatcher import console_sink
from swarmsar.perception.simulated import SimulatedDetector
from swarmsar.sim import World
from swarmsar.swarm.formation import SearchArea


def build_swarm(n: int, area: SearchArea) -> list[Drone]:
    """Line the drones up along the south edge, ready to sweep north."""
    drones = []
    for i in range(n):
        x = area.min_x + (i + 1) * area.width / (n + 1)
        drones.append(
            Drone(
                id=f"uav-{i + 1:02d}",
                position=Vec3(x, area.min_y + 5.0, area.altitude),
            )
        )
    return drones


def main() -> None:
    world = World.random(n_survivors=6, width=400, height=300, seed=7)
    area = SearchArea(0, 0, 400, 300, altitude=30.0)

    ai = AIRegistry()
    ai.register(HeuristicProvider(), activate=True)

    dispatcher = AlertDispatcher()
    dispatcher.add_sink(console_sink)

    coordinator = SwarmCoordinator(
        drones=build_swarm(8, area),
        detector=SimulatedDetector(world, seed=7),
        area=area,
        ai=ai,
        dispatcher=dispatcher,
        config=MissionConfig(dt=0.5, gossip_hops=4),
    )

    print("SwarmSAR — search-and-rescue simulation")
    print(f"  survivors hidden in field: {len(world.survivors)}")
    print(f"  drones deployed:           {len(coordinator.drones)}")
    print(f"  active AI provider:        {ai.active.name}\n")

    def report(r):
        if r.tick % 20 == 0 or r.alerts:
            print(
                f"  t={r.sim_time:6.1f}s  live={r.live_drones}  "
                f"mesh-islands={r.mesh_components}  estimates={r.estimates}  "
                f"confirmed={r.confirmed}"
            )

    coordinator.run(ticks=400, on_tick=report)

    positions = [e.position for e in coordinator.detection_map.confirmed()]
    found = world.found_count(positions, radius=20.0)
    print("\n  --- mission summary ---")
    print(f"  confirmed survivor fixes: {len(positions)}")
    print(f"  true survivors located:   {found}/{len(world.survivors)}")
    print(f"  rescue alerts dispatched: {len(dispatcher.history)}")


if __name__ == "__main__":
    main()
