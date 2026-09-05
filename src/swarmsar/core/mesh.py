"""Real-time graph mesh: who can talk to whom, and shared situational state.

Every tick the swarm rebuilds an undirected proximity graph — two drones are
adjacent when they are inside each other's communication range — and gossips
telemetry plus fresh detections across the edges. This is the "align with
other drones in real time, graph-style" layer: each node ends the tick with a
decayed view of the whole swarm without any central server.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .drone import Drone, Telemetry
from .vector import Vec3


@dataclass
class MeshLink:
    a: str
    b: str
    distance: float
    quality: float          # 0..1, degrades toward the edge of comm range


@dataclass
class GraphMesh:
    """An undirected, range-based communication graph over the live drones.

    The mesh owns no drones; it is rebuilt from their positions each tick via
    :meth:`rebuild`. It then exposes neighbour queries, connectivity checks and
    a bounded-hop gossip that spreads each drone's telemetry through the graph.
    """

    edges: dict[frozenset[str], MeshLink] = field(default_factory=dict)
    _adj: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _telemetry: dict[str, Telemetry] = field(default_factory=dict)

    def rebuild(self, drones: list[Drone], now: float) -> None:
        """Recompute edges from current positions; drop lost nodes."""
        self.edges.clear()
        self._adj = defaultdict(set)
        live = [d for d in drones if d.telemetry(now).is_healthy]
        for i, d1 in enumerate(live):
            self._telemetry[d1.id] = d1.telemetry(now)
            for d2 in live[i + 1:]:
                dist = d1.position.distance_to(d2.position)
                reach = min(d1.comm_range, d2.comm_range)
                if dist <= reach:
                    quality = 1.0 - (dist / reach) if reach > 0 else 1.0
                    link = MeshLink(d1.id, d2.id, dist, round(quality, 4))
                    self.edges[frozenset((d1.id, d2.id))] = link
                    self._adj[d1.id].add(d2.id)
                    self._adj[d2.id].add(d1.id)

    def neighbors(self, drone_id: str) -> set[str]:
        return set(self._adj.get(drone_id, set()))

    def degree(self, drone_id: str) -> int:
        return len(self._adj.get(drone_id, set()))

    def components(self) -> list[set[str]]:
        """Connected components — each is one island that can coordinate."""
        seen: set[str] = set()
        groups: list[set[str]] = []
        for node in self._telemetry:
            if node in seen:
                continue
            stack, group = [node], set()
            while stack:
                cur = stack.pop()
                if cur in group:
                    continue
                group.add(cur)
                stack.extend(self._adj.get(cur, set()) - group)
            seen |= group
            groups.append(group)
        return groups

    @property
    def is_connected(self) -> bool:
        return len(self.components()) <= 1

    def reachable_telemetry(self, drone_id: str, max_hops: int = 4) -> dict[str, Telemetry]:
        """Telemetry a drone can learn within ``max_hops`` of gossip.

        Models bounded flooding: a node knows itself immediately, its
        neighbours after one hop, and so on. Anything beyond the hop budget
        is invisible to that node this tick.
        """
        if drone_id not in self._telemetry:
            return {}
        visited = {drone_id}
        frontier = {drone_id}
        for _ in range(max_hops):
            nxt: set[str] = set()
            for node in frontier:
                nxt |= self._adj.get(node, set()) - visited
            if not nxt:
                break
            visited |= nxt
            frontier = nxt
        return {nid: self._telemetry[nid] for nid in visited if nid in self._telemetry}

    def swarm_centroid(self, ids: set[str] | None = None) -> Vec3:
        ids = ids or set(self._telemetry)
        known = [self._telemetry[i].position for i in ids if i in self._telemetry]
        if not known:
            return Vec3()
        total = Vec3()
        for p in known:
            total = total + p
        return total / len(known)
