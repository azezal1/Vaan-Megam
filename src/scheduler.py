"""
TDMA Schedule Planner & Optimizer
Author: Garv Kaushik
Company: Vaan Megam Networks - IITM Research Park, Chennai

Part 1: The Network Brain (Python Engine)
-----------------------------------------
Implements Distance-2 (Two-Hop) Graph Colouring to assign collision-free TDMA
time slots to a set of radio nodes.  Nodes within 500 m are considered adjacent.
Nodes that share a common neighbour (2-hop) also cannot use the same slot.
Spatial reuse is enabled: nodes >2 hops apart may share a slot safely.
"""

from __future__ import annotations

import json
import math
from typing import Any

import networkx as nx


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

RADIO_RANGE_METERS: float = 500.0


# ─────────────────────────────────────────────────────────────────────────────
# Topology Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_topology(coords: dict[str, list[float]],
                   radio_range: float = RADIO_RANGE_METERS) -> nx.Graph:
    """
    Build a NetworkX undirected graph from node coordinates.
    Two nodes are connected by an edge iff their Euclidean distance <= radio_range.
    """
    G = nx.Graph()
    nodes = list(coords.items())

    for name, (x, y) in nodes:
        G.add_node(name, pos=(x, y))

    for i in range(len(nodes)):
        n1, (x1, y1) = nodes[i]
        for j in range(i + 1, len(nodes)):
            n2, (x2, y2) = nodes[j]
            dist = math.hypot(x2 - x1, y2 - y1)
            if dist <= radio_range:
                G.add_edge(n1, n2, distance=round(dist, 2))

    return G


# ─────────────────────────────────────────────────────────────────────────────
# Distance-2 Conflict Graph
# ─────────────────────────────────────────────────────────────────────────────

def build_distance2_conflict_graph(G: nx.Graph) -> nx.Graph:
    """
    Build a conflict graph (squared graph G^2) where two nodes are connected
    iff they are within 2 hops in G (1-hop OR 2-hop).

    Cases handled:
      - Direct Link (d=1):   A -- B               -> A,B must differ
      - Hidden Terminal (d=2): A -- B -- C         -> A,C must differ (interfere at B)
    """
    C = nx.Graph()
    C.add_nodes_from(G.nodes())

    for u in G.nodes():
        # d=1 neighbours
        for v in G.neighbors(u):
            if u != v:
                C.add_edge(u, v)
        # d=2 neighbours via shared neighbour
        for w in G.neighbors(u):
            for v in G.neighbors(w):
                if v != u and not C.has_edge(u, v):
                    C.add_edge(u, v)

    return C


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic Graph Colouring (DSATUR)
# ─────────────────────────────────────────────────────────────────────────────

def dsatur_coloring(conflict_graph: nx.Graph) -> dict[str, int]:
    """
    DSATUR (Degree of SATURation) greedy graph-colouring heuristic.

    Selection priority:
      1. Highest saturation (# distinct colours already used by neighbours).
      2. Tie-break: highest uncoloured degree.

    Consistently outperforms simple greedy and produces near-optimal colouring
    for sparse wireless topologies.
    """
    nodes = list(conflict_graph.nodes())
    if not nodes:
        return {}

    colors: dict[str, int] = {}
    saturation: dict[str, set] = {n: set() for n in nodes}
    degree = dict(conflict_graph.degree())

    uncolored = set(nodes)

    while uncolored:
        node = max(
            uncolored,
            key=lambda n: (len(saturation[n]), degree[n])
        )
        neighbor_colors = {
            colors[nb]
            for nb in conflict_graph.neighbors(node)
            if nb in colors
        }
        slot = 0
        while slot in neighbor_colors:
            slot += 1

        colors[node] = slot

        for nb in conflict_graph.neighbors(node):
            if nb in uncolored:
                saturation[nb].add(slot)

        uncolored.remove(node)

    return colors


# ─────────────────────────────────────────────────────────────────────────────
# Slot Compaction
# ─────────────────────────────────────────────────────────────────────────────

def compact_slots(assignment: dict[str, int]) -> dict[str, int]:
    """Re-index slots to 0,1,2,... removing any gaps."""
    used = sorted(set(assignment.values()))
    remap = {old: new for new, old in enumerate(used)}
    return {node: remap[slot] for node, slot in assignment.items()}


# ─────────────────────────────────────────────────────────────────────────────
# Schedule Matrix
# ─────────────────────────────────────────────────────────────────────────────

def build_schedule_matrix(assignment: dict[str, int],
                          node_order: list[str]) -> list[list[int]]:
    """Build a Slot x Node binary matrix (1 = transmits in this slot)."""
    num_slots = max(assignment.values()) + 1
    matrix = [[0] * len(node_order) for _ in range(num_slots)]
    for col, node in enumerate(node_order):
        matrix[assignment[node]][col] = 1
    return matrix


# ─────────────────────────────────────────────────────────────────────────────
# Collision Verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_schedule(G: nx.Graph,
                    assignment: dict[str, int]) -> list[tuple[str, str, str]]:
    """
    Verify the schedule is conflict-free for d=1 and d=2 interference.
    Returns list of (node_a, node_b, reason) -- empty means no collisions.
    """
    violations = []

    # d=1 check
    for u, v in G.edges():
        if assignment.get(u) == assignment.get(v):
            violations.append((u, v, "Direct-Link collision (d=1)"))

    # d=2 check
    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            u, v = nodes[i], nodes[j]
            if G.has_edge(u, v):
                continue
            common = set(G.neighbors(u)) & set(G.neighbors(v))
            if common and assignment.get(u) == assignment.get(v):
                relay = list(common)[0]
                violations.append((u, v,
                    f"Hidden-Terminal collision (d=2) via {relay}"))

    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Spatial Reuse Analysis
# ─────────────────────────────────────────────────────────────────────────────

def compute_spatial_reuse(G: nx.Graph,
                          assignment: dict[str, int]) -> dict[int, list[str]]:
    """Group nodes sharing the same slot (demonstrating spatial reuse)."""
    slot_groups: dict[int, list[str]] = {}
    for node, slot in assignment.items():
        slot_groups.setdefault(slot, []).append(node)
    return dict(sorted(slot_groups.items()))


# ─────────────────────────────────────────────────────────────────────────────
# Main Optimizer Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def optimize(coords: dict[str, list[float]],
             radio_range: float = RADIO_RANGE_METERS) -> dict[str, Any]:
    """
    Full pipeline: coords -> topology -> conflict graph -> colouring -> schedule.

    Returns result dict with all schedule data.
    """
    G = build_topology(coords, radio_range)
    C = build_distance2_conflict_graph(G)
    raw_assignment = dsatur_coloring(C)
    assignment = compact_slots(raw_assignment)
    node_order = sorted(assignment.keys())
    matrix = build_schedule_matrix(assignment, node_order)
    violations = verify_schedule(G, assignment)
    spatial_reuse = compute_spatial_reuse(G, assignment)

    graph_info = {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "num_conflict_edges": C.number_of_edges(),
        "radio_range_m": radio_range,
        "edges": [
            {"source": u, "target": v, "distance_m": round(d["distance"], 2)}
            for u, v, d in G.edges(data=True)
        ],
        "positions": {n: list(G.nodes[n]["pos"]) for n in G.nodes()},
    }

    return {
        "graph_info": graph_info,
        "assignment": assignment,
        "node_order": node_order,
        "num_slots": max(assignment.values()) + 1 if assignment else 0,
        "schedule_matrix": matrix,
        "violations": violations,
        "spatial_reuse": spatial_reuse,
        "radio_range": radio_range,
        "conflict_free": len(violations) == 0,
    }
