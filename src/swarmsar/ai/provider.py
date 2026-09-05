"""The pluggable-AI contract.

The swarm hands each decision cycle to an :class:`AIProvider`, which returns a
:class:`Decision` — how to re-task the swarm and which survivors to escalate.
Providers are interchangeable at runtime (see :mod:`swarmsar.ai.registry`), so
a local heuristic, an on-board vision model, or a hosted LLM can be swapped in
or ensembled without touching the flight logic.

**Boundary.** A provider may only recommend *search and rescue* actions —
where to look, which survivor estimate to prioritise, whether to raise a
rescue alert. It has no authority to command anything that could harm a
detected person, and the coordinator exposes no such action for it to call.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..core.drone import Telemetry
from ..core.vector import Vec3
from ..perception.fusion import SurvivorEstimate


@dataclass(frozen=True)
class SituationContext:
    """Everything a provider is given to reason about, for one cycle."""

    tick: int
    sim_time: float
    telemetry: dict[str, Telemetry]
    estimates: list[SurvivorEstimate]
    mesh_components: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    """A provider's recommended re-tasking for this cycle.

    Attributes
    ----------
    assignments:
        Map of ``drone_id -> point`` to hold/investigate. Drones absent from
        the map keep searching under the coverage controller.
    priorities:
        Survivor-estimate ids ranked most-urgent first (for the rescue queue).
    escalate:
        Estimate ids the provider judges ready to alert a rescue team about.
    rationale:
        Short human-readable explanation, surfaced in logs and the dashboard.
    """

    assignments: dict[str, Vec3] = field(default_factory=dict)
    priorities: list[int] = field(default_factory=list)
    escalate: list[int] = field(default_factory=list)
    rationale: str = ""


class AIProvider(ABC):
    """Interface every decision engine implements."""

    #: Stable identifier used when registering/selecting the provider.
    name: str = "provider"

    @abstractmethod
    def decide(self, context: SituationContext) -> Decision:
        """Return a :class:`Decision` for the given situation."""
        raise NotImplementedError

    def health(self) -> bool:
        """Whether the provider is ready (e.g. model loaded, API reachable)."""
        return True
