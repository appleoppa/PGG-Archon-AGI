"""SE19 flow matching / link integration for PGG Archon agent orchestration.

Models bounded, local-only agent orchestration as a TTB + DAG flow network:

    pi*(tau | q) ∝ R_tilde(tau)^beta, where R_tilde(tau)=R(tau)+epsilon_min
    Flow(s -> a) ∝ Reward(trajectory through s -> a)

The implementation is intentionally bounded and deterministic: pure Python
computation with optional local JSON/SQLite persistence helpers only. It never
calls a provider, LLM, AGI/T5/ASI service, network endpoint, or changes system
configuration.

Boundary: local only; pure computation; optional local file/SQLite writes; no
network; no provider; no AGI/T5/ASI; no LLM calls; no system configuration
mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

SCHEMA = "PGGFlowMatching/v1"
BOUNDARY = (
    "PGGFlowMatching/v1; local only; pure computation; optional local JSON/SQLite; "
    "no network; no provider; no AGI/T5/ASI; no LLM calls; no system configuration mutation"
)
START_NODE = "__START__"
END_NODE = "__END__"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _stable_id(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


@dataclass
class FlowNode:
    """DAG node representing an orchestration state, agent, or tool step."""

    node_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    visits: int = 0
    terminal_reward_sum: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "metadata": self.metadata,
            "visits": self.visits,
            "terminal_reward_sum": round(self.terminal_reward_sum, 8),
        }


@dataclass
class FlowEdge:
    """Directed DAG edge with reward-derived weight and credit fields."""

    src: str
    dst: str
    action: str
    count: int = 0
    reward_sum: float = 0.0
    adjusted_reward_sum: float = 0.0
    policy_mass: float = 0.0
    flow: float = 0.0
    credit: float = 0.0
    trajectory_ids: list[str] = field(default_factory=list)

    @property
    def edge_id(self) -> str:
        return f"{self.src}::{self.action}::{self.dst}"

    @property
    def mean_reward(self) -> float:
        return self.reward_sum / self.count if self.count else 0.0

    @property
    def mean_adjusted_reward(self) -> float:
        return self.adjusted_reward_sum / self.count if self.count else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "src": self.src,
            "dst": self.dst,
            "action": self.action,
            "count": self.count,
            "reward_sum": round(self.reward_sum, 8),
            "adjusted_reward_sum": round(self.adjusted_reward_sum, 8),
            "mean_reward": round(self.mean_reward, 8),
            "mean_adjusted_reward": round(self.mean_adjusted_reward, 8),
            "policy_mass": round(self.policy_mass, 8),
            "flow": round(self.flow, 8),
            "credit": round(self.credit, 8),
            "trajectory_ids": list(self.trajectory_ids),
        }


@dataclass
class FlowGraph:
    """DAG structure for SE19 flow matching.

    Edges carry both empirical rewards and flow mass induced by trajectory reward:
    Flow(s -> a) is accumulated from trajectories that traverse the edge.
    """

    schema: str = SCHEMA
    nodes: Dict[str, FlowNode] = field(default_factory=dict)
    edges: Dict[str, FlowEdge] = field(default_factory=dict)
    outgoing: Dict[str, list[str]] = field(default_factory=dict)
    incoming: Dict[str, list[str]] = field(default_factory=dict)
    trajectories: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    skipped_edges: list[Dict[str, Any]] = field(default_factory=list)

    def add_node(self, node_id: str, metadata: Mapping[str, Any] | None = None) -> FlowNode:
        node_key = str(node_id)
        node = self.nodes.get(node_key)
        if node is None:
            node = FlowNode(node_id=node_key, metadata=dict(metadata or {}))
            self.nodes[node_key] = node
        elif metadata:
            node.metadata.update(dict(metadata))
        return node

    def add_edge(self, src: str, dst: str, action: str, *, strict_dag: bool = True) -> FlowEdge | None:
        src_key, dst_key, action_key = str(src), str(dst), str(action or f"{src}->{dst}")
        self.add_node(src_key)
        self.add_node(dst_key)
        if strict_dag and self._would_create_cycle(src_key, dst_key):
            self.skipped_edges.append({"src": src_key, "dst": dst_key, "action": action_key, "reason": "cycle_guard"})
            return None
        edge_id = f"{src_key}::{action_key}::{dst_key}"
        edge = self.edges.get(edge_id)
        if edge is None:
            edge = FlowEdge(src=src_key, dst=dst_key, action=action_key)
            self.edges[edge_id] = edge
            self.outgoing.setdefault(src_key, []).append(edge_id)
            self.incoming.setdefault(dst_key, []).append(edge_id)
            self.outgoing.setdefault(dst_key, [])
            self.incoming.setdefault(src_key, [])
        return edge

    def _would_create_cycle(self, src: str, dst: str) -> bool:
        if src == dst:
            return True
        stack = [dst]
        seen: set[str] = set()
        while stack:
            cur = stack.pop()
            if cur == src:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            for edge_id in self.outgoing.get(cur, []):
                stack.append(self.edges[edge_id].dst)
        return False

    def topological_order(self) -> list[str]:
        indegree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges.values():
            indegree[edge.dst] = indegree.get(edge.dst, 0) + 1
            indegree.setdefault(edge.src, 0)
        ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
        order: list[str] = []
        while ready:
            node_id = ready.pop(0)
            order.append(node_id)
            for edge_id in self.outgoing.get(node_id, []):
                dst = self.edges[edge_id].dst
                indegree[dst] -= 1
                if indegree[dst] == 0:
                    ready.append(dst)
                    ready.sort()
        if len(order) != len(indegree):
            raise ValueError("FlowGraph contains a cycle; DAG invariant violated")
        return order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "trajectory_count": len(self.trajectories),
            "nodes": {node_id: node.to_dict() for node_id, node in sorted(self.nodes.items())},
            "edges": {edge_id: edge.to_dict() for edge_id, edge in sorted(self.edges.items())},
            "trajectories": self.trajectories,
            "skipped_edges": self.skipped_edges,
            "boundary": BOUNDARY,
        }


class PGGFlowMatching:
    """SE19 bounded flow matching engine for agent orchestration.

    Public methods:
    - build_graph(trajectories): build TTB+DAG flow graph from trajectory samples.
    - compute_flow(node_id): report node flow and reward proportionality.
    - allocate_credit(): reverse transparent credit assignment over the DAG.
    - redundant_routing(): select multi-peak redundant paths to avoid collapse.
    """

    def __init__(
        self,
        *,
        beta: float = 1.0,
        epsilon_min: float = 1e-6,
        redundancy_k: int = 3,
        diversity_lambda: float = 0.35,
        discount: float = 0.95,
        max_paths: int = 128,
    ) -> None:
        self.beta = max(0.0, _safe_float(beta, 1.0))
        self.epsilon_min = max(1e-12, _safe_float(epsilon_min, 1e-6))
        self.redundancy_k = max(1, int(redundancy_k))
        self.diversity_lambda = max(0.0, _safe_float(diversity_lambda, 0.35))
        self.discount = max(0.0, min(1.0, _safe_float(discount, 0.95)))
        self.max_paths = max(1, int(max_paths))
        self.graph = FlowGraph()

    def build_graph(self, trajectories: Sequence[Mapping[str, Any]]) -> FlowGraph:
        """Build a DAG flow network from trajectory dictionaries.

        Supported trajectory forms:
        - {"nodes": [s0, s1, ...], "actions": [a0, ...], "reward": 1.0}
        - {"steps": [{"state": s0, "action": a0, "next_state": s1}, ...], "reward": 1.0}

        Flow mass follows pi*(tau|q) ∝ (reward + epsilon_min)^beta. Each edge on
        a trajectory receives that trajectory's normalized policy mass times its
        adjusted reward, making Flow(s->a) proportional to rewarding trajectories
        through that edge.
        """
        self.graph = FlowGraph()
        normalized = [self._normalize_trajectory(idx, raw) for idx, raw in enumerate(trajectories or [])]
        positive_weights = [self._trajectory_weight(item["reward"]) for item in normalized]
        total_weight = sum(positive_weights) or 1.0

        for item, weight in zip(normalized, positive_weights):
            policy_mass = weight / total_weight
            adjusted_reward = item["adjusted_reward"]
            traj_id = item["trajectory_id"]
            nodes = item["nodes"]
            actions = item["actions"]
            self.graph.trajectories[traj_id] = {
                "trajectory_id": traj_id,
                "nodes": nodes,
                "actions": actions,
                "reward": round(item["reward"], 8),
                "adjusted_reward": round(adjusted_reward, 8),
                "policy_mass": round(policy_mass, 8),
                "formula": "pi*(tau|q) proportional to R_tilde(tau)^beta",
            }
            for node_id in nodes:
                self.graph.add_node(node_id).visits += 1
            if nodes:
                self.graph.nodes[nodes[-1]].terminal_reward_sum += item["reward"]
            for src, dst, action in zip(nodes[:-1], nodes[1:], actions):
                edge = self.graph.add_edge(src, dst, action, strict_dag=True)
                if edge is None:
                    continue
                edge.count += 1
                edge.reward_sum += item["reward"]
                edge.adjusted_reward_sum += adjusted_reward
                edge.policy_mass += policy_mass
                edge.flow += policy_mass * adjusted_reward
                if traj_id not in edge.trajectory_ids:
                    edge.trajectory_ids.append(traj_id)
        self.graph.topological_order()  # validate DAG invariant
        return self.graph

    def compute_flow(self, node_id: str) -> Dict[str, Any]:
        """Compute node flow values and expose reward-flow proportionality."""
        node_key = str(node_id)
        if node_key not in self.graph.nodes:
            return {
                "schema": f"{SCHEMA}/compute_flow",
                "node_id": node_key,
                "exists": False,
                "incoming_flow": 0.0,
                "outgoing_flow": 0.0,
                "node_flow": 0.0,
                "boundary": BOUNDARY,
            }
        incoming_edges = [self.graph.edges[eid] for eid in self.graph.incoming.get(node_key, [])]
        outgoing_edges = [self.graph.edges[eid] for eid in self.graph.outgoing.get(node_key, [])]
        incoming_flow = sum(edge.flow for edge in incoming_edges)
        outgoing_flow = sum(edge.flow for edge in outgoing_edges)
        # For internal nodes the two should be close under flow conservation; for
        # source/sink nodes use the non-zero side.
        if incoming_edges and outgoing_edges:
            node_flow = (incoming_flow + outgoing_flow) / 2.0
        else:
            node_flow = incoming_flow or outgoing_flow
        traversed_reward = sum(edge.reward_sum for edge in incoming_edges + outgoing_edges)
        traversed_count = sum(edge.count for edge in incoming_edges + outgoing_edges)
        mean_reward = traversed_reward / traversed_count if traversed_count else 0.0
        return {
            "schema": f"{SCHEMA}/compute_flow",
            "node_id": node_key,
            "exists": True,
            "incoming_flow": round(incoming_flow, 8),
            "outgoing_flow": round(outgoing_flow, 8),
            "node_flow": round(node_flow, 8),
            "mean_reward_through_node": round(mean_reward, 8),
            "flow_reward_relation": "Flow(s->a) proportional to Reward(trajectory through s->a)",
            "incoming_edges": [edge.to_dict() for edge in incoming_edges],
            "outgoing_edges": [edge.to_dict() for edge in outgoing_edges],
            "boundary": BOUNDARY,
        }

    def allocate_credit(self) -> Dict[str, Any]:
        """Reverse transparent credit assignment over the DAG.

        Similar in spirit to a value network: terminal rewards seed leaf values,
        then each node receives a flow-weighted backed-up value from successors.
        Edge credit is its normalized contribution to the source node's value.
        """
        order = self.graph.topological_order()
        node_value = {node_id: 0.0 for node_id in self.graph.nodes}
        edge_credit: Dict[str, float] = {}

        for node_id in reversed(order):
            out_edges = [self.graph.edges[eid] for eid in self.graph.outgoing.get(node_id, [])]
            node = self.graph.nodes[node_id]
            if not out_edges:
                denom = max(1, node.visits)
                node_value[node_id] = node.terminal_reward_sum / denom
                continue
            total_flow = sum(max(edge.flow, 0.0) for edge in out_edges) or float(len(out_edges))
            backed_values = []
            for edge in out_edges:
                flow_weight = (edge.flow / total_flow) if total_flow else (1.0 / len(out_edges))
                q_value = edge.mean_adjusted_reward + self.discount * node_value.get(edge.dst, 0.0)
                contribution = flow_weight * q_value
                backed_values.append(contribution)
                edge_credit[edge.edge_id] = contribution
            node_value[node_id] = sum(backed_values)

        total_credit = sum(max(v, 0.0) for v in edge_credit.values()) or 1.0
        for edge_id, value in edge_credit.items():
            self.graph.edges[edge_id].credit = max(value, 0.0) / total_credit

        return {
            "schema": f"{SCHEMA}/credit",
            "node_values": {node_id: round(value, 8) for node_id, value in sorted(node_value.items())},
            "edge_credit": {
                edge_id: round(self.graph.edges[edge_id].credit, 8)
                for edge_id in sorted(self.graph.edges)
            },
            "method": "reverse_flow_weighted_value_backup",
            "discount": self.discount,
            "boundary": BOUNDARY,
        }

    def redundant_routing(
        self,
        start_node: str = START_NODE,
        end_node: str = END_NODE,
        *,
        k: int | None = None,
        temperature: float = 1.0,
    ) -> Dict[str, Any]:
        """Select multi-peak redundant routes and load shares.

        The selector scores candidate DAG paths by flow/reward, then greedily
        applies a diversity penalty so near-duplicate routes do not monopolize
        all load. This is a bounded redundancy strategy against policy collapse.
        """
        k = max(1, int(k or self.redundancy_k))
        temperature = max(1e-9, _safe_float(temperature, 1.0))
        paths = self._enumerate_paths(str(start_node), str(end_node), self.max_paths)
        scored = [self._score_path(path) for path in paths]
        scored.sort(key=lambda item: item["base_score"], reverse=True)

        selected: list[Dict[str, Any]] = []
        remaining = list(scored)
        while remaining and len(selected) < k:
            best_idx = 0
            best_score = -float("inf")
            for idx, candidate in enumerate(remaining):
                overlap = max((self._path_overlap(candidate["edge_ids"], chosen["edge_ids"]) for chosen in selected), default=0.0)
                diversified = candidate["base_score"] - self.diversity_lambda * overlap
                if diversified > best_score:
                    best_score = diversified
                    best_idx = idx
            chosen = remaining.pop(best_idx)
            chosen["diversified_score"] = round(best_score, 8)
            selected.append(chosen)

        if selected:
            max_score = max(item["diversified_score"] for item in selected)
            weights = [math.exp((item["diversified_score"] - max_score) / temperature) for item in selected]
            floor = 0.02 / len(selected)
            total = sum(weights) or 1.0
            shares = [(w / total) for w in weights]
            shares = [max(floor, share) for share in shares]
            renorm = sum(shares) or 1.0
            for item, share in zip(selected, shares):
                item["load_share"] = round(share / renorm, 8)
        top_share = max((item.get("load_share", 0.0) for item in selected), default=0.0)
        entropy = -sum(float(item.get("load_share", 0.0)) * math.log(max(float(item.get("load_share", 0.0)), 1e-12)) for item in selected)
        max_entropy = math.log(len(selected)) if selected else 0.0
        collapse_risk = bool(selected and (top_share > 0.75 or (max_entropy > 0 and entropy / max_entropy < 0.45)))

        return {
            "schema": f"{SCHEMA}/redundant_routing",
            "start_node": str(start_node),
            "end_node": str(end_node),
            "requested_k": k,
            "candidate_count": len(paths),
            "selected_paths": selected,
            "collapse_risk": collapse_risk,
            "top_load_share": round(top_share, 8),
            "entropy": round(entropy, 8),
            "strategy": "multi_peak_flow_reward_routing_with_diversity_penalty",
            "boundary": BOUNDARY,
        }

    def save_json(self, path: str | Path) -> Dict[str, Any]:
        """Persist current graph to a local JSON file only."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self.graph.to_dict()
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return {"schema": f"{SCHEMA}/save_json", "path": str(target), "bytes": target.stat().st_size, "boundary": BOUNDARY}

    def save_sqlite(self, path: str | Path) -> Dict[str, Any]:
        """Persist current graph to local SQLite only; no external services."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(target)) as con:
            con.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS nodes (node_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS edges (edge_id TEXT PRIMARY KEY, src TEXT, dst TEXT, action TEXT, payload TEXT NOT NULL)")
            con.execute("DELETE FROM metadata")
            con.execute("DELETE FROM nodes")
            con.execute("DELETE FROM edges")
            con.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("schema", SCHEMA))
            con.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("created_at", _now()))
            con.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("boundary", BOUNDARY))
            for node_id, node in self.graph.nodes.items():
                con.execute("INSERT INTO nodes(node_id, payload) VALUES (?, ?)", (node_id, json.dumps(node.to_dict(), ensure_ascii=False, sort_keys=True)))
            for edge_id, edge in self.graph.edges.items():
                con.execute(
                    "INSERT INTO edges(edge_id, src, dst, action, payload) VALUES (?, ?, ?, ?, ?)",
                    (edge_id, edge.src, edge.dst, edge.action, json.dumps(edge.to_dict(), ensure_ascii=False, sort_keys=True)),
                )
        return {"schema": f"{SCHEMA}/save_sqlite", "path": str(target), "boundary": BOUNDARY}

    def _normalize_trajectory(self, idx: int, raw: Mapping[str, Any]) -> Dict[str, Any]:
        item = dict(raw or {})
        reward = _safe_float(item.get("reward", item.get("score", 0.0)), 0.0)
        adjusted_reward = max(self.epsilon_min, reward + self.epsilon_min)
        trajectory_id = str(item.get("trajectory_id") or item.get("id") or _stable_id({"idx": idx, "raw": item}))

        if isinstance(item.get("steps"), Sequence) and not isinstance(item.get("steps"), (str, bytes, bytearray)):
            nodes, actions = self._nodes_actions_from_steps(item["steps"])
        else:
            nodes = [str(x) for x in item.get("nodes", [])]
            actions = [str(x) for x in item.get("actions", [])]
        if not nodes:
            nodes = [START_NODE, END_NODE]
        if len(nodes) == 1:
            nodes = [START_NODE, nodes[0], END_NODE]
        if nodes[0] != START_NODE:
            nodes = [START_NODE] + nodes
            actions = ["start"] + actions
        if nodes[-1] != END_NODE:
            nodes = nodes + [END_NODE]
            actions = actions + ["finish"]
        needed_actions = max(0, len(nodes) - 1)
        if len(actions) < needed_actions:
            actions = actions + [f"step_{i}" for i in range(len(actions), needed_actions)]
        if len(actions) > needed_actions:
            actions = actions[:needed_actions]
        return {
            "trajectory_id": trajectory_id,
            "nodes": nodes,
            "actions": actions,
            "reward": reward,
            "adjusted_reward": adjusted_reward,
        }

    def _nodes_actions_from_steps(self, steps: Sequence[Any]) -> tuple[list[str], list[str]]:
        nodes: list[str] = []
        actions: list[str] = []
        for idx, step in enumerate(steps):
            if not isinstance(step, Mapping):
                continue
            src = str(step.get("state") or step.get("src") or step.get("node") or f"step_{idx}")
            dst = str(step.get("next_state") or step.get("dst") or step.get("next") or f"step_{idx + 1}")
            action = str(step.get("action") or step.get("agent") or f"action_{idx}")
            if not nodes:
                nodes.append(src)
            if nodes[-1] != src:
                nodes.append(src)
            nodes.append(dst)
            actions.append(action)
        return nodes, actions

    def _trajectory_weight(self, reward: float) -> float:
        adjusted = max(self.epsilon_min, reward + self.epsilon_min)
        return adjusted ** self.beta

    def _enumerate_paths(self, start: str, end: str, limit: int) -> list[list[str]]:
        if start not in self.graph.nodes or end not in self.graph.nodes:
            return []
        paths: list[list[str]] = []
        stack: list[tuple[str, list[str], set[str]]] = [(start, [], {start})]
        while stack and len(paths) < limit:
            node_id, edge_path, seen = stack.pop()
            if node_id == end:
                paths.append(edge_path)
                continue
            edges = [self.graph.edges[eid] for eid in self.graph.outgoing.get(node_id, [])]
            edges.sort(key=lambda edge: (edge.flow, edge.mean_adjusted_reward), reverse=True)
            for edge in reversed(edges):
                if edge.dst in seen:
                    continue
                stack.append((edge.dst, edge_path + [edge.edge_id], seen | {edge.dst}))
        return paths

    def _score_path(self, edge_ids: Sequence[str]) -> Dict[str, Any]:
        if not edge_ids:
            return {"nodes": [], "edge_ids": [], "actions": [], "base_score": 0.0, "path_flow": 0.0, "mean_reward": 0.0}
        edges = [self.graph.edges[eid] for eid in edge_ids]
        nodes = [edges[0].src] + [edge.dst for edge in edges]
        actions = [edge.action for edge in edges]
        path_flow = min((edge.flow for edge in edges), default=0.0)
        mean_reward = sum(edge.mean_adjusted_reward for edge in edges) / len(edges)
        log_flow = sum(math.log(max(edge.flow, self.epsilon_min)) for edge in edges)
        base_score = log_flow + math.log(max(mean_reward, self.epsilon_min))
        return {
            "nodes": nodes,
            "edge_ids": list(edge_ids),
            "actions": actions,
            "base_score": round(base_score, 8),
            "path_flow": round(path_flow, 8),
            "mean_reward": round(mean_reward, 8),
        }

    @staticmethod
    def _path_overlap(a: Sequence[str], b: Sequence[str]) -> float:
        if not a or not b:
            return 0.0
        set_a, set_b = set(a), set(b)
        return len(set_a & set_b) / len(set_a | set_b)

    def report(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "created_at": _now(),
            "parameters": {
                "beta": self.beta,
                "epsilon_min": self.epsilon_min,
                "redundancy_k": self.redundancy_k,
                "diversity_lambda": self.diversity_lambda,
                "discount": self.discount,
                "max_paths": self.max_paths,
            },
            "graph": self.graph.to_dict(),
            "boundary": BOUNDARY,
        }


def _example_trajectories() -> list[Dict[str, Any]]:
    return [
        {
            "id": "tau_high_code_review",
            "nodes": ["query", "planner", "coder", "reviewer"],
            "actions": ["decompose", "implement", "verify"],
            "reward": 9.0,
        },
        {
            "id": "tau_high_research_code",
            "nodes": ["query", "researcher", "coder", "reviewer"],
            "actions": ["retrieve", "implement", "verify"],
            "reward": 8.2,
        },
        {
            "id": "tau_medium_direct",
            "nodes": ["query", "coder", "reviewer"],
            "actions": ["direct_implement", "verify"],
            "reward": 5.5,
        },
        {
            "id": "tau_alt_analysis",
            "steps": [
                {"state": "query", "action": "analyze", "next_state": "analyst"},
                {"state": "analyst", "action": "spec", "next_state": "coder"},
                {"state": "coder", "action": "verify", "next_state": "reviewer"},
            ],
            "reward": 7.1,
        },
    ]


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="SE19 PGG flow matching local-only verifier")
    parser.add_argument("--save-json", type=str, default="", help="optional local JSON output path")
    parser.add_argument("--save-sqlite", type=str, default="", help="optional local SQLite output path")
    args = parser.parse_args(argv)

    engine = PGGFlowMatching(beta=1.2, redundancy_k=3)
    graph = engine.build_graph(_example_trajectories())
    credit = engine.allocate_credit()
    output = {
        "schema": SCHEMA,
        "created_at": _now(),
        "boundary": BOUNDARY,
        "formula": {
            "policy": "pi*(tau|q) proportional to R_tilde(tau)^beta, R_tilde(tau)=R(tau)+epsilon_min",
            "flow": "Flow(s->a) proportional to Reward(trajectory through s->a)",
        },
        "graph_summary": {
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "trajectories": len(graph.trajectories),
            "skipped_edges": graph.skipped_edges,
        },
        "compute_flow_coder": engine.compute_flow("coder"),
        "credit": credit,
        "routing": engine.redundant_routing(START_NODE, END_NODE),
    }
    if args.save_json:
        output["save_json"] = engine.save_json(args.save_json)
    if args.save_sqlite:
        output["save_sqlite"] = engine.save_sqlite(args.save_sqlite)
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
