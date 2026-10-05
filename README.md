# TDMA Schedule Planner & Optimizer

**Author:** Garv Kaushik  
**Company:** Vaan Megam Networks, IITM Research Park, Chennai  
**Role:** Wireless Developer Internship

---

## Problem Statement

Design a simulator for a **Schedule Planner and Optimizer for a TDMA network** — managing how radios communicate without collisions.

In a TDMA network, radios share the same frequency by taking turns in specific "time-slots." Radios within 500 m of each other interfere; distant ones can safely reuse the same slot (spatial reuse).

---

## Solution: Part 1 — The Network Brain (Python Engine)

### Algorithm: Distance-2 (Two-Hop) DSATUR Graph Colouring

**Pipeline:**

```
Node Coordinates (JSON)
        │
        ▼
1. Topology Graph (NetworkX)
   └─ Edges between nodes within 500 m
        │
        ▼
2. Distance-2 Conflict Graph (G²)
   └─ Edge if d(u,v) ≤ 2 hops
   └─ Captures: Direct-Link (d=1) + Hidden-Terminal (d=2)
        │
        ▼
3. DSATUR Heuristic Colouring
   └─ Assigns minimum slots greedily
   └─ Saturation-first selection → near-optimal
        │
        ▼
4. Slot Compaction (gap removal)
        │
        ▼
5. Conflict Verification
6. Slot × Node Schedule Matrix
```

### Interference Cases Handled

| Case | Pattern | Rule |
|------|---------|------|
| Direct Link (d=1) | A — B | A,B must have different slots |
| Hidden Terminal (d=2) | A — B — C | A,C must have different slots (interfere at B) |

### Spatial Reuse

Nodes ≥ 3 hops apart **safely share the same time slot**, maximising channel utilisation.

---

## Usage

### CLI

```bash
# Demo (16-node 4×4 grid)
python3 src/cli.py --demo

# Custom coordinates
python3 src/cli.py --coords '{"Node_01":[0.0,0.0],"Node_02":[300.0,0.0],...}'

# Custom radio range
python3 src/cli.py --demo --range 400

# JSON output
python3 src/cli.py --demo --json
```

### Web Dashboard

```bash
pip install -r requirements.txt
python3 app.py
# Open http://localhost:<port>
```

---

## File Structure

```
tdma_scheduler/
├── src/
│   ├── scheduler.py   # Core engine (topology, DSATUR, verification)
│   └── cli.py         # CLI interface
├── templates/
│   └── index.html     # Web dashboard
├── app.py             # Flask web server
├── requirements.txt
└── README.md
```

---

## Design Decisions

1. **DSATUR over simple greedy**: Saturation-based node selection consistently yields near-chromatic-number colouring for sparse wireless graphs.

2. **Squared graph (G²)**: Pre-computing the conflict graph decouples the interference model from the colouring algorithm, making it easy to extend.

3. **Slot compaction**: Ensures the frame length reported equals the chromatic number of G² — no wasted slots from index gaps.

4. **Verification pass**: Post-generation conflict check gives formal correctness guarantee independent of the colouring routine.

---

## References

- NetworkX Documentation — [networkx.org](https://networkx.org)
- EMANE TDMA BDCE Model — [emane.io/tdma-radio-model](https://emane.io/tdma-radio-model)
- Björn Halldórsson et al., "Distance-2 Graph Coloring in Wireless Networks"
