"""Run a mission and record it to ``dashboard/run.json`` for the live viewer.

The dashboard at ``dashboard/index.html`` ships with an embedded run so it
works by double-click. Regenerate that run (and refresh the embedded copy) with::

    python examples/record_dashboard.py

It also demonstrates real-world coordinates: the rescue alerts are geolocated
by anchoring the local frame to an origin near Manaus, Brazil.
"""

from __future__ import annotations

import os

from swarmsar import (
    AIRegistry,
    AlertDispatcher,
    DashboardRecorder,
    Drone,
    GeoPoint,
    LocalFrame,
    MissionConfig,
    SwarmCoordinator,
    Vec3,
)
from swarmsar.ai.providers import HeuristicProvider
from swarmsar.perception.simulated import SimulatedDetector
from swarmsar.sim import World
from swarmsar.swarm.formation import SearchArea

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "dashboard", "run.json")


def main() -> None:
    world = World.random(n_survivors=6, width=400, height=300, seed=7)
    area = SearchArea(0, 0, 400, 300, altitude=30.0)

    ai = AIRegistry()
    ai.register(HeuristicProvider(), activate=True)

    # Anchor the search area to a real location so alerts carry lat/lon.
    frame = LocalFrame(GeoPoint(lat=-3.1190, lon=-60.0217, alt=92.0))
    dispatcher = AlertDispatcher(frame=frame)

    coordinator = SwarmCoordinator(
        drones=[
            Drone(id=f"uav-{i + 1:02d}", position=Vec3(40 + i * 42, 8, 30))
            for i in range(8)
        ],
        detector=SimulatedDetector(world, seed=7),
        area=area,
        ai=ai,
        dispatcher=dispatcher,
        config=MissionConfig(dt=0.5, gossip_hops=4),
    )

    recorder = DashboardRecorder(coordinator, world=world, every=2)
    coordinator.run(ticks=400, on_tick=recorder)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    recorder.save(OUT)
    print(f"wrote {recorder.frames.__len__()} frames -> {OUT}")
    for alert in dispatcher.history:
        g = alert.geo
        print(f"  alert #{alert.estimate_id}: {g.lat:.5f}, {g.lon:.5f}")


if __name__ == "__main__":
    main()
