# TDMA Schedule Planner & Optimizer — Technical Documentation

**Author:** Garv Kaushik  
**Target Organization:** Vaan Megam Networks, IITM Research Park, Chennai  
**Project:** Centralized TDMA Network Brain (Part 1) & EMANE Physical Emulation Bridge (Part 2)  
**Status:** Completed & Conflict-Free Verified  

---

## 1. Executive Summary

In tactical and industrial Time Division Multiple Access (TDMA) wireless ad-hoc networks, radios share a common radio frequency channel by dividing time into recurring frames and synchronized discrete time-slots. Uncoordinated simultaneous transmissions cause catastrophic receiver collisions and packet drops. Conversely, assigning a separate time-slot to each radio yields an unnecessarily long frame, drastically diminishing overall network throughput and introducing latency.

This project delivers a complete, end-to-end TDMA Schedule Planner and Optimizer:
1. **Part 1 — The Network Brain (Python Engine):** A centralized graph-algorithmic optimization engine implementing **Distance-2 (Two-Hop) Graph Colouring** using the **DSATUR (Degree of Saturation)** heuristic. It eliminates both **Distance-1 (Direct Link)** collisions and **Distance-2 (Hidden Terminal)** collisions while maximizing **Spatial Reuse** for nodes separated by more than 2 hops.
2. **Part 2 — The Physical Emulator (EMANE Setup):** An automated integration bridge that transforms the generated schedule matrix into native **EMANE TDMA Radio Model XML profiles** (with 1 ms slot timing, frame structures, and NEM mappings), accompanied by a containerized Docker deployment specification.
3. **Interactive Visual Dashboard & CLI:** A clean, professional engineering workstation featuring real-time canvas topology rendering, interactive matrix inspection, node degree analytics, slot load distribution, and XML/JSON export facilities.

---

## 2. Problem Formulation & Theoretical Foundations

### 2.1 Network Topology as a Graph
Given a set of $N$ static radio nodes located in a 2D Euclidean coordinate space:
$$V = \{v_1, v_2, \dots, v_N\}, \quad \text{where } \text{pos}(v_i) = (x_i, y_i) \in \mathbb{R}^2$$

With an omnidirectional radio propagation range $R = 500.0\text{ meters}$, the physical RF communication topology is modeled as an undirected graph $G = (V, E)$, where an edge exists between two nodes if and only if their Euclidean distance does not exceed $R$:
$$E = \{(u, v) \in V \times V \mid u \ne v \text{ and } \| \text{pos}(u) - \text{pos}(v) \|_2 \le R\}$$

### 2.2 Collision Models in TDMA

#### Case A: Direct Link Interference (Distance-1)
When two nodes $u$ and $v$ are adjacent in $G$ ($(u, v) \in E$), one cannot transmit while the other is receiving, nor can both transmit simultaneously without mutual receiver saturation:
$$\text{slot}(u) \ne \text{slot}(v) \quad \forall (u, v) \in E$$

#### Case B: Hidden Terminal / Two-Hop Interference (Distance-2)
Consider three nodes $u, w, v$ such that $(u, w) \in E$ and $(w, v) \in E$, but $(u, v) \notin E$. Node $u$ and Node $v$ are "hidden" from each other. If both nodes transmit in the same time-slot, their signals collide at the intermediate receiver $w$, corrupting all incoming packets:
$$\text{dist}_G(u, v) = 2 \implies \text{slot}(u) \ne \text{slot}(v)$$

#### Case C: Spatial Reuse (Distance $\ge 3$)
If two nodes $u$ and $v$ satisfy $\text{dist}_G(u, v) \ge 3$, there is no intermediate node that can hear both $u$ and $v$ simultaneously. Therefore, both nodes can safely transmit in the exact same time-slot without interference:
$$\text{dist}_G(u, v) \ge 3 \implies \text{slot}(u) = \text{slot}(v) \text{ is permissible}$$

### 2.3 The Conflict Graph ($G^2$)
To unify Distance-1 and Distance-2 constraints into a single standard graph colouring problem, we construct the **square graph** $G^2 = (V, E_{conflict})$:
$$E_{conflict} = \{(u, v) \in V \times V \mid 1 \le \text{dist}_G(u, v) \le 2\}$$

A valid TDMA schedule is precisely a vertex colouring of $G^2$ such that no two adjacent vertices share the same colour:
$$\forall (u, v) \in E_{conflict}, \quad \text{colour}(u) \ne \text{colour}(v)$$

The chromatic number $\chi(G^2)$ defines the theoretical minimum number of time-slots required for a collision-free frame.

---

## 3. Algorithmic Design & Heuristics (Part 1: The Network Brain)

### 3.1 Computational Complexity & The DSATUR Heuristic
Finding the minimum vertex colouring $\chi(H)$ of an arbitrary graph $H = G^2$ is an **NP-hard** optimization problem. Simple greedy colouring algorithms are highly sensitive to initial vertex ordering and frequently produce sub-optimal frame lengths with severe colour fragmentation.

To achieve near-optimal results with deterministic efficiency, we implement **Brélaz’s DSATUR (Degree of Saturation)** algorithm:

```
Algorithm: Distance-2 DSATUR Scheduling
Input: Physical topology graph G = (V, E)
Output: Conflict-free slot assignment map A: V -> {0, 1, ..., k-1}

1. Construct conflict graph C = (V, E_conflict) where:
     (u, v) in E_conflict iff 1 <= dist_G(u, v) <= 2
2. For each v in V:
     saturation[v] = empty set
     degree[v] = degree of v in C
     assignment[v] = unassigned
3. uncolored = set of all V
4. while uncolored is not empty:
     a. Select node u in uncolored maximizing:
          primary: |saturation[u]|
          secondary (tie-break): degree[u]
     b. neighbor_colors = { assignment[w] for w in neighbors_C(u) if assigned }
     c. slot = smallest non-negative integer NOT in neighbor_colors
     d. assignment[u] = slot
     e. For each w in neighbors_C(u) & uncolored:
          saturation[w].add(slot)
     f. uncolored.remove(u)
5. Compact slots to consecutive range [0, k-1]
6. Return assignment
```

### 3.2 Verification Subsystem
To provide rigorous proof of correctness, every calculated schedule undergoes independent post-assignment verification:
1. **$d=1$ Sweep:** Iterates over every physical edge $(u, v) \in E$ to verify $\text{slot}(u) \ne \text{slot}(v)$.
2. **$d=2$ Sweep:** Iterates over all vertex pairs $(u, v)$ with common neighbours ($\Gamma(u) \cap \Gamma(v) \ne \emptyset$) to verify $\text{slot}(u) \ne \text{slot}(v)$.
Any violation triggers an explicit error identifying the conflicting node pair, the distance, and the relay.

---

## 4. Empirical Evaluation & Grid Topology Analysis

### 4.1 Benchmark Topology
The primary benchmark prescribed in the assignment is a **16-node 4x4 grid** with uniform 300 m spacing and a 500 m radio transmission range:

$$\text{Coordinates: } (x, y) \in \{0, 300, 600, 900\} \times \{0, 300, 600, 900\} \text{ (meters)}$$

- Euclidean distance to orthogonal neighbor: $300.0\text{ m} \le 500\text{ m}$ (direct link)
- Euclidean distance to diagonal neighbor: $\sqrt{300^2 + 300^2} \approx 424.26\text{ m} \le 500\text{ m}$ (direct link)
- Euclidean distance to 2-step orthogonal: $600.0\text{ m} > 500\text{ m}$ (hidden terminal via shared neighbor)

### 4.2 Benchmark Results

| Metric | Measured Value | Theoretical Significance |
| :--- | :--- | :--- |
| **Total Processed Nodes** | 16 | $4 \times 4$ uniform wireless grid |
| **Physical RF Links ($E$)** | 42 edges | High link density (grid + diagonals) |
| **Conflict Pairs ($E_{conflict}$)** | 90 edges | Direct links + two-hop hidden terminals |
| **Maximum Clique Size $\omega(G^2)$** | 9 vertices | $\chi(G^2) \ge \omega(G^2) = 9$ (Mathematical lower bound) |
| **Optimized Frame Length** | **9 slots** | **Strictly optimal** ($\chi(G^2) = 9$) |
| **Collision Verification** | **0 violations** | Verified 100% collision-free ($d=1$ and $d=2$) |
| **Spatial Reuse Efficiency** | 1.78 nodes/slot | 5 of 9 slots utilize spatial reuse |

### 4.3 Spatial Reuse Mapping

- **Corner Nodes (4-way reuse):** Node_01, Node_04, Node_13, Node_16 are mutually separated by at least 3 hops. They all share **Slot 8**.
- **Edge Pairs (2-way reuse):**
  - Slot 4: Node_09 & Node_12
  - Slot 5: Node_02 & Node_14
  - Slot 6: Node_03 & Node_15
  - Slot 7: Node_05 & Node_08
- **Interior Central Nodes (dedicated slots):**
  - Node_06 (Slot 1), Node_07 (Slot 3), Node_10 (Slot 0), Node_11 (Slot 2) form a dense core that conflicts with all surrounding rings.

---

## 5. Part 2: Physical Emulator (EMANE Integration Bridge)

### 5.1 Overview & Architecture
The Extendable Mobile Ad-hoc Network Emulator (EMANE) provides real-time link-layer and physical-layer emulation for distributed wireless nodes. In EMANE's native TDMA Radio Model (`tdmaeventschedulermac`), each virtual node (NEM — Network Emulation Module) is bound to specific timeslots in a synchronized repeating multiframe.

### 5.2 Generated EMANE TDMA Profile (`tdmaschedule.xml`)
The Python engine bridges into EMANE by generating valid XML schedule files:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tdmaschedule SYSTEM "tdmaschedule.dtd">
<tdmaschedule>
  <structure frame="9" slotduration="1000" guardtime="100"/>
  <multiframe count="1">
    <frame id="0">
      <slot id="0" nodes="10"/>
      <slot id="1" nodes="6"/>
      <slot id="2" nodes="11"/>
      <slot id="3" nodes="7"/>
      <slot id="4" nodes="9,12"/>
      <slot id="5" nodes="2,14"/>
      <slot id="6" nodes="3,15"/>
      <slot id="7" nodes="5,8"/>
      <slot id="8" nodes="1,4,13,16"/>
    </frame>
  </multiframe>
</tdmaschedule>
```

- `slotduration="1000"`: 1 millisecond timeslots.
- `guardtime="100"`: 100 microseconds guard interval to prevent inter-slot drift.
- `nodes="1,4,13,16"`: Spatial reuse realized in hardware emulation; NEMs 1, 4, 13, and 16 transmit simultaneously on the same carrier frequency without packet loss.

### 5.3 Containerized Emulation Deployment (Docker)
To allow seamless local execution without host dependency contamination, an EMANE container recipe is packaged:

```dockerfile
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential git cmake emane emane-model-tdma \
    python3-protobuf iproute2 iputils-ping iperf3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY tdmaschedule.xml /workspace/
COPY nem.xml /workspace/
COPY platform.xml /workspace/

CMD ["emane", "/workspace/platform.xml"]
```

---

## 6. Software Architecture & Components

```
tdma_scheduler/
├── app.py                  # Flask REST server & Web dashboard host
├── src/
│   ├── scheduler.py        # Core graph engine, DSATUR algorithm & verification
│   ├── cli.py              # CLI tool producing standardized reports & matrices
│   ├── emane_bridge.py     # EMANE XML profile generator & Docker setup
│   └── __init__.py
├── templates/
│   └── index.html          # Web dashboard (Canvas topology, tabs, analytics)
├── docs/
│   └── DOCUMENTATION.md    # Full project technical documentation
└── requirements.txt        # Dependencies: flask, flask-cors, networkx
```

### Key API Endpoints
- `POST /api/optimize`: Accepts custom coordinate JSON and radio range; returns schedule, graph stats, and verification.
- `GET /api/demo`: Returns optimized schedule for the default 16-node grid.
- `POST /api/emane`: Generates native EMANE TDMA XML, NEM definitions, and Docker recipes.
- `GET /api/health`: Health status and candidate attribution.

---

## 7. Instructions for Execution

### CLI Execution
```bash
# Run with default 16-node 4x4 grid demo
python3 src/cli.py --demo

# Run with custom coordinates JSON and custom radio range
python3 src/cli.py --coords '{"Node_01":[0.0,0.0], "Node_02":[300.0,0.0]}' --range 500

# Output machine-readable JSON
python3 src/cli.py --demo --json
```

### Web Dashboard
```bash
# Start Flask server on free port (default 5050)
python3 app.py
```
Open **`http://localhost:5050`** in any web browser to interact with the visual dashboard, explore the topology graph, inspect the conflict-free schedule matrix, examine network metrics, and export EMANE XML profiles.
