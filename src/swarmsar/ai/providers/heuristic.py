"""A dependency-free reference provider.

``HeuristicProvider`` is a transparent baseline that models a sensible
search-and-rescue tactic:

* a lone sighting (seen by a single drone) is *pending* — it dispatches the
  nearest **other** free drone to take a second look, because confirmation
  requires independent corroboration;
* an estimate seen by enough drones with high enough belief is *escalated* to
  the rescue team.

It ships so the framework runs end-to-end offline, and it doubles as the
control arm when benchmarking a learned or hosted provider.
"""

from __future__ import annotations

from ...core.vector import Vec3
from ..provider import AIProvider, Decision, SituationContext


class HeuristicProvider(AIProvider):
    name = "heuristic"

    def __init__(
        self,
        escalate_confidence: float = 0.8,
        confirm_min_drones: int = 2,
        max_confirming: int = 4,
    ) -> None:
        self.escalate_confidence = escalate_confidence
        self.confirm_min_drones = confirm_min_drones
        self.max_confirming = max_confirming

    def decide(self, context: SituationContext) -> Decision:
        estimates = context.estimates

        # Priorities: strongest belief and best corroboration first.
        ranked = sorted(
            estimates,
            key=lambda e: (e.confidence, e.corroborated_by),
            reverse=True,
        )
        priorities = [e.id for e in ranked]

        # Pending = plausible but not yet independently corroborated. Send the
        # nearest *different* free drone to each, so a lone sighting becomes a
        # confirmed fix instead of being stranded on one drone's word.
        pending = sorted(
            (
                e
                for e in estimates
                if not e.confirmed and e.corroborated_by < self.confirm_min_drones
            ),
            key=lambda e: (e.confidence, e.observations),
            reverse=True,
        )
        assignments: dict[str, Vec3] = {}
        taken: set[str] = set()
        for est in pending[: self.max_confirming]:
            drone_id = self._nearest_free_drone(
                est.position, context, taken, exclude=est.contributors
            )
            if drone_id is not None:
                assignments[drone_id] = est.position
                taken.add(drone_id)

        escalate = [
            e.id
            for e in ranked
            if e.confidence >= self.escalate_confidence
            and e.corroborated_by >= self.confirm_min_drones
        ]
        rationale = (
            f"{len(estimates)} estimate(s); {len(pending)} pending corroboration; "
            f"{len(assignments)} drone(s) tasked to confirm; {len(escalate)} to escalate"
        )
        return Decision(
            assignments=assignments,
            priorities=priorities,
            escalate=escalate,
            rationale=rationale,
        )

    @staticmethod
    def _nearest_free_drone(
        point: Vec3,
        context: SituationContext,
        taken: set[str],
        exclude: set[str] | None = None,
    ) -> str | None:
        exclude = exclude or set()
        best_id, best_dist = None, float("inf")
        for tel in context.telemetry.values():
            if tel.drone_id in taken or tel.drone_id in exclude or not tel.is_healthy:
                continue
            d = tel.position.distance_to(point)
            if d < best_dist:
                best_id, best_dist = tel.drone_id, d
        return best_id
