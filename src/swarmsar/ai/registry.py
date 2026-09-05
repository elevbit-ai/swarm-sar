"""Runtime registry that makes the AI layer hot-swappable and ensemblable.

Register any number of providers, pick an active one by name at runtime, or
fuse several with :meth:`ensemble`. This is what lets "diverse open AIs" plug
into the same swarm without code changes — each is just another registered
:class:`~swarmsar.ai.provider.AIProvider`.
"""

from __future__ import annotations

from collections import Counter

from .provider import AIProvider, Decision, SituationContext


class AIRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._active: str | None = None

    def register(self, provider: AIProvider, *, activate: bool = False) -> None:
        if not provider.name:
            raise ValueError("provider.name must be a non-empty string")
        self._providers[provider.name] = provider
        if activate or self._active is None:
            self._active = provider.name

    def unregister(self, name: str) -> None:
        self._providers.pop(name, None)
        if self._active == name:
            self._active = next(iter(self._providers), None)

    def names(self) -> list[str]:
        return list(self._providers)

    def get(self, name: str) -> AIProvider:
        return self._providers[name]

    @property
    def active(self) -> AIProvider:
        if self._active is None:
            raise RuntimeError("no AI provider registered")
        return self._providers[self._active]

    def use(self, name: str) -> None:
        if name not in self._providers:
            raise KeyError(f"unknown provider: {name!r}")
        self._active = name

    def decide(self, context: SituationContext) -> Decision:
        """Delegate to the active provider, falling back if it is unhealthy."""
        provider = self.active
        if not provider.health():
            for alt in self._providers.values():
                if alt.health():
                    provider = alt
                    break
        return provider.decide(context)

    def ensemble(self, context: SituationContext) -> Decision:
        """Combine all healthy providers by majority vote on escalations.

        Assignments are taken from the first healthy provider; escalations are
        accepted when at least half of the voting providers agree, which makes
        a single miscalibrated model unable to force an alert on its own.
        """
        healthy = [p for p in self._providers.values() if p.health()]
        if not healthy:
            raise RuntimeError("no healthy AI provider available")
        decisions = [p.decide(context) for p in healthy]

        votes: Counter[int] = Counter()
        for d in decisions:
            votes.update(set(d.escalate))
        quorum = (len(healthy) + 1) // 2
        escalate = sorted(eid for eid, n in votes.items() if n >= quorum)

        priority_rank: Counter[int] = Counter()
        for d in decisions:
            for rank, eid in enumerate(d.priorities):
                priority_rank[eid] += len(d.priorities) - rank
        priorities = [eid for eid, _ in priority_rank.most_common()]

        return Decision(
            assignments=decisions[0].assignments,
            priorities=priorities,
            escalate=escalate,
            rationale=f"ensemble of {len(healthy)}: {', '.join(p.name for p in healthy)}",
        )
