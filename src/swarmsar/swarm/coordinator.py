"""The mission coordinator: one tick wires the whole pipeline together.

Each :meth:`SwarmCoordinator.step` performs, in order:

1. **mesh** — rebuild the proximity graph and gossip telemetry;
2. **sense** — every healthy drone runs its :class:`HumanDetector`;
3. **fuse**  — detections are folded into the shared :class:`DetectionMap`;
4. **decide** — the active AI provider (or ensemble) re-tasks the swarm;
5. **alert** — confirmed + escalated survivors are dispatched to responders;
6. **act**  — the coverage controller turns knowledge into velocity commands
   and the drones integrate their motion.

The loop is deterministic given a seed, so examples and tests reproduce.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..ai.provider import SituationContext
from ..ai.registry import AIRegistry
from ..alerting.dispatcher import AlertDispatcher
from ..autopilot.actuator import Actuator, SimulatedActuator
from ..core.drone import Drone, DroneStatus
from ..core.mesh import GraphMesh
from ..perception.detector import HumanDetector
from ..perception.fusion import DetectionMap
from .formation import CoverageController, SearchArea


@dataclass
class MissionConfig:
    dt: float = 0.5                 # seconds per tick
    gossip_hops: int = 4
    use_ensemble: bool = False
    recall_battery: float = 0.15    # return-to-base threshold


@dataclass
class TickReport:
    tick: int
    sim_time: float
    live_drones: int
    mesh_components: int
    estimates: int
    confirmed: int
    alerts: int
    rationale: str = ""


@dataclass
class SwarmCoordinator:
    """Owns the drones and drives the search-and-rescue mission."""

    drones: list[Drone]
    detector: HumanDetector
    area: SearchArea
    ai: AIRegistry
    dispatcher: AlertDispatcher
    config: MissionConfig = field(default_factory=MissionConfig)
    mesh: GraphMesh = field(default_factory=GraphMesh)
    detection_map: DetectionMap = field(default_factory=DetectionMap)
    actuator: Actuator = field(default_factory=SimulatedActuator)
    tick: int = 0
    sim_time: float = 0.0
    _controller: CoverageController = field(init=False)

    def __post_init__(self) -> None:
        self._controller = CoverageController(self.area)
        for d in self.drones:
            if d.status is DroneStatus.IDLE:
                d.status = DroneStatus.SEARCHING

    # -- one simulation tick ----------------------------------------------

    def step(self) -> TickReport:
        self.sim_time += self.config.dt
        self.tick += 1

        # 1. mesh
        self.mesh.rebuild(self.drones, self.sim_time)

        # 2. sense + 3. fuse
        for drone in self._healthy():
            self.detection_map.ingest(self.detector.detect(drone, self.sim_time), self.sim_time)
        self.detection_map.decay(self.sim_time)

        # 4. decide
        context = SituationContext(
            tick=self.tick,
            sim_time=self.sim_time,
            telemetry={d.id: d.telemetry(self.sim_time) for d in self.drones},
            estimates=self.detection_map.estimates,
            mesh_components=len(self.mesh.components()),
        )
        decision = (
            self.ai.ensemble(context) if self.config.use_ensemble else self.ai.decide(context)
        )

        # 5. alert (only confirmed *and* escalated estimates reach responders)
        escalate = set(decision.escalate)
        alerts = 0
        by_id = {e.id: e for e in self.detection_map.estimates}
        for eid in escalate:
            est = by_id.get(eid)
            if est and self.dispatcher.dispatch(est, self.sim_time):
                alerts += 1

        # 6. act
        assigned = decision.assignments
        for drone in self._healthy():
            self._apply_status(drone, assigned)
            neighbors = self.mesh.reachable_telemetry(drone.id, self.config.gossip_hops)
            target = assigned.get(drone.id)
            desired = self._controller.command(drone, neighbors, target)
            self.actuator.apply(drone, desired, self.config.dt)

        return TickReport(
            tick=self.tick,
            sim_time=round(self.sim_time, 2),
            live_drones=len(self._healthy()),
            mesh_components=len(self.mesh.components()),
            estimates=len(self.detection_map.estimates),
            confirmed=len(self.detection_map.confirmed()),
            alerts=alerts,
            rationale=decision.rationale,
        )

    def run(self, ticks: int, on_tick=None) -> list[TickReport]:
        """Run ``ticks`` steps, optionally calling ``on_tick(report)`` each one."""
        reports = []
        for _ in range(ticks):
            report = self.step()
            reports.append(report)
            if on_tick is not None:
                on_tick(report)
        return reports

    # -- helpers -----------------------------------------------------------

    def _healthy(self) -> list[Drone]:
        return [d for d in self.drones if d.status is not DroneStatus.LOST]

    def _apply_status(self, drone: Drone, assigned: dict) -> None:
        if drone.battery <= self.config.recall_battery:
            drone.status = DroneStatus.RETURNING
        elif drone.id in assigned:
            drone.status = DroneStatus.TRACKING
        elif drone.status in (DroneStatus.TRACKING, DroneStatus.RETURNING):
            drone.status = DroneStatus.SEARCHING
