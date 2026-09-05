import pytest

from swarmsar.ai.provider import AIProvider, Decision, SituationContext
from swarmsar.ai.registry import AIRegistry


class _Stub(AIProvider):
    def __init__(self, name, escalate, healthy=True):
        self.name = name
        self._escalate = escalate
        self._healthy = healthy

    def decide(self, context):
        return Decision(escalate=list(self._escalate), rationale=self.name)

    def health(self):
        return self._healthy


def _ctx():
    return SituationContext(tick=1, sim_time=1.0, telemetry={}, estimates=[], mesh_components=1)


def test_active_defaults_to_first_registered():
    reg = AIRegistry()
    reg.register(_Stub("a", [1]))
    reg.register(_Stub("b", [2]))
    assert reg.active.name == "a"


def test_use_switches_active():
    reg = AIRegistry()
    reg.register(_Stub("a", [1]))
    reg.register(_Stub("b", [2]))
    reg.use("b")
    assert reg.decide(_ctx()).escalate == [2]


def test_unknown_provider_raises():
    reg = AIRegistry()
    reg.register(_Stub("a", [1]))
    with pytest.raises(KeyError):
        reg.use("missing")


def test_unhealthy_active_falls_back_on_decide():
    reg = AIRegistry()
    reg.register(_Stub("a", [1], healthy=False), activate=True)
    reg.register(_Stub("b", [2], healthy=True))
    assert reg.decide(_ctx()).escalate == [2]


def test_ensemble_requires_quorum():
    reg = AIRegistry()
    reg.register(_Stub("a", [1, 2]))
    reg.register(_Stub("b", [1]))
    reg.register(_Stub("c", [1, 3]))
    # id 1 has 3 votes (quorum 2) -> escalated; 2 and 3 have 1 vote -> not.
    assert reg.ensemble(_ctx()).escalate == [1]
