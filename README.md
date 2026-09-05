<h1 align="center">SwarmSAR</h1>

<p align="center">
  <strong>Graph-coordinated drone swarm framework for search-and-rescue.</strong><br>
  Real-time mesh coordination · human-presence mapping · pluggable AI · rescue alerting.
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="Tests" src="https://img.shields.io/badge/tests-38%20passing-brightgreen">
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-orange">
</p>

<p align="center">
  <a href="https://elevbit-ai.github.io/swarm-sar/"><strong>Website</strong></a> ·
  <a href="https://elevbit-ai.github.io/swarm-sar/demo.html"><strong>Live demo</strong></a> ·
  <a href="https://github.com/elevbit-ai/swarm-sar/releases/tag/v0.1.0"><strong>Promo video</strong></a> ·
  <a href="dashboard/">Dashboard</a> ·
  <a href="RESPONSIBLE_USE.md">Responsible use</a>
</p>

---

SwarmSAR turns a fleet of drones into a **self-organising search team**. The
drones form a proximity graph and gossip what they see in real time, fuse their
sightings into one shared map of where people likely are, let a pluggable AI
layer decide where to look next, and hand confirmed locations to a rescue team.

It is built for one job: **finding people who need help, faster.** There is no
targeting or weapons functionality — see [Responsible use](RESPONSIBLE_USE.md).

## Why it exists

In a disaster the bottleneck is coverage: too much ground, too few responders,
too little time. A swarm can blanket an area in minutes, but only if the drones
coordinate without a fragile central controller and turn many noisy sightings
into a few trustworthy locations. SwarmSAR is a clean, hackable reference for
exactly that pipeline — runnable on a laptop today, structured to bridge to real
autopilots tomorrow.

## Features

- **Real-time graph mesh** — drones form an undirected proximity graph and
  gossip telemetry over it with bounded hops; the swarm keeps working even when
  it splits into disconnected islands.
- **Decentralised coverage control** — each drone computes its own velocity from
  local neighbours: anti-collision separation, coverage spreading, and a
  serpentine sweep. No global controller.
- **Human-presence mapping** — a `HumanDetector` interface (thermal/RGB/acoustic
  in the field) feeds an online fusion map that clusters detections and tracks a
  confidence-weighted estimate per suspected survivor.
- **Corroboration before belief** — an estimate is only *confirmed* once enough
  distinct drones agree, so a single false positive can't escalate.
- **Pluggable AI layer** — swap or **ensemble** decision engines at runtime
  (heuristic, on-board vision model, hosted LLM) through one registry. Diverse
  models plug in without touching flight logic.
- **Rescue alerting** — the one thing the pipeline "triggers" is a de-duplicated
  notification to human responders with the survivor's coordinates.
- **Deterministic simulator** — the whole loop runs offline and reproducibly, so
  examples and CI are stable.
- **Zero required dependencies** in the core; pure typed Python 3.10+.

## Architecture

```
                     ┌───────────────────────────────────────────────┐
                     │                SwarmCoordinator                │
                     │                (one tick loop)                 │
                     └───────────────────────────────────────────────┘
   ┌──────────┐  1  ┌──────────┐  2  ┌────────────┐  3  ┌──────────────┐
   │  Drones  │────▶│ GraphMesh│────▶│HumanDetector│────▶│ DetectionMap │
   │ (motion) │◀────│ (gossip) │     │ (per drone) │     │  (fusion)    │
   └──────────┘  6  └──────────┘     └────────────┘     └──────────────┘
        ▲  act                                                  │ 4
        │            ┌──────────────┐        ┌──────────────┐   ▼
        └────────────│  Coverage    │◀───────│  AIRegistry  │ decide
                     │  controller  │        │ (pluggable)  │
                     └──────────────┘        └──────────────┘
                                                     │ 5 escalate
                                                     ▼
                                             ┌──────────────┐
                                             │AlertDispatcher│──▶ rescue team
                                             └──────────────┘
```

Each tick: **1** rebuild mesh & gossip → **2/3** sense & fuse → **4** AI decides
re-tasking → **5** dispatch confirmed survivors → **6** fly.

## Install

```bash
git clone https://github.com/elevbit-ai/swarm-sar.git
cd swarm-sar
pip install -e ".[dev]"
```

## Quickstart

```bash
python examples/run_simulation.py
```

```text
SwarmSAR — search-and-rescue simulation
  survivors hidden in field: 6
  drones deployed:           8
  active AI provider:        heuristic

  t=  10.0s  live=8  mesh-islands=1  estimates=2  confirmed=0
  [RESCUE ALERT] Suspected survivor #3 confirmed at (past coords) — dispatch rescue team.
  ...
  --- mission summary ---
  confirmed survivor fixes: 5
  true survivors located:   5/6
  rescue alerts dispatched: 5
```

### In code

```python
from swarmsar import AIRegistry, AlertDispatcher, Drone, SwarmCoordinator, Vec3
from swarmsar.ai.providers import HeuristicProvider
from swarmsar.alerting.dispatcher import console_sink
from swarmsar.perception.simulated import SimulatedDetector
from swarmsar.sim import World
from swarmsar.swarm.formation import SearchArea

world = World.random(n_survivors=6, seed=7)
area = SearchArea(0, 0, 400, 300, altitude=30.0)

ai = AIRegistry()
ai.register(HeuristicProvider(), activate=True)

dispatcher = AlertDispatcher()
dispatcher.add_sink(console_sink)

coordinator = SwarmCoordinator(
    drones=[Drone(id=f"uav-{i}", position=Vec3(40 + i * 40, 5, 30)) for i in range(8)],
    detector=SimulatedDetector(world, seed=7),
    area=area,
    ai=ai,
    dispatcher=dispatcher,
)
coordinator.run(ticks=400)
```

## Plugging in your own AI

Implement one method and register it. Providers are interchangeable at runtime,
and several can be fused with `registry.ensemble(...)` so no single model can
force an escalation on its own.

```python
from swarmsar.ai.provider import AIProvider, Decision, SituationContext

class MyVisionProvider(AIProvider):
    name = "my-vision"

    def decide(self, ctx: SituationContext) -> Decision:
        ranked = sorted(ctx.estimates, key=lambda e: e.confidence, reverse=True)
        return Decision(
            priorities=[e.id for e in ranked],
            escalate=[e.id for e in ranked if e.confirmed],
            rationale="prioritised by my model",
        )

ai.register(MyVisionProvider(), activate=True)
```

A provider may only recommend **search-and-rescue** actions — where to look and
which survivor to prioritise. The coordinator exposes no action that could harm
a detected person.

## Plugging in a real sensor

Subclass `HumanDetector` and return `Detection`s in world coordinates; the rest
of the pipeline is unchanged.

```python
from swarmsar.perception.detector import Detection, HumanDetector

class ThermalDetector(HumanDetector):
    def detect(self, drone, now):
        # run your thermal person-detector on the live frame here
        return [Detection(source_drone=drone.id, position=..., confidence=0.87, timestamp=now)]
```

## Project layout

```
src/swarmsar/
├── core/         # Vec3, Drone, GraphMesh
├── swarm/        # coverage/formation control, SwarmCoordinator
├── perception/   # HumanDetector interface, simulated detector, fusion map
├── ai/           # AIProvider contract, runtime registry, bundled providers
├── alerting/     # rescue AlertDispatcher and sinks
├── geo/          # local ENU <-> WGS-84 conversion for real coordinates
├── autopilot/    # actuation backends: simulated + MAVLink/PX4 bridge
├── telemetry/    # DashboardRecorder — record a mission to JSON
└── sim/          # deterministic simulation world
dashboard/        # dependency-free web replay (mesh, coverage, alerts)
docs/             # project website (GitHub Pages)
examples/         # runnable simulation + dashboard recorder
tests/            # unit + integration tests (deterministic)
```

## Flying real hardware & real coordinates

Swap the in-process motion integrator for a MAVLink autopilot (PX4/ArduPilot,
real or SITL) without changing any swarm logic, and geolocate every alert:

```python
from swarmsar import LocalFrame, GeoPoint, AlertDispatcher
from swarmsar.autopilot import MavlinkActuator

frame = LocalFrame(GeoPoint(lat=-3.1190, lon=-60.0217, alt=92.0))
dispatcher = AlertDispatcher(frame=frame)          # alerts now carry lat/lon
actuator = MavlinkActuator("udpin:0.0.0.0:14540")  # pip install "swarmsar[mavlink]"
# SwarmCoordinator(..., dispatcher=dispatcher, actuator=actuator)
```

## Roadmap

- [x] MAVLink / PX4 bridge to replace the motion integrator on real hardware
- [x] Geographic (WGS-84) coordinates alongside the local ENU frame
- [x] Live web dashboard for mesh, coverage and the survivor map
- [ ] Reference vision provider (thermal person-detection)
- [ ] Webhook / radio alert sinks for field integration

## Testing

```bash
pytest        # unit + integration tests
ruff check .  # lint
```

## License

Released under the [MIT License](LICENSE). Please also read
[RESPONSIBLE_USE.md](RESPONSIBLE_USE.md).

## Author

Designed and developed by **Joaquim Pedro de Morais Filho**.
If you use SwarmSAR in research, see [CITATION.cff](CITATION.cff).
