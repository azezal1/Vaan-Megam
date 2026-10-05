#!/usr/bin/env python3
"""
TDMA Schedule Planner & Optimizer — CLI Interface
Author: Garv Kaushik
Usage:
  python3 cli.py --coords '{"Node_01":[0.0,0.0],...}'
  python3 cli.py --coords '{"Node_01":[0.0,0.0],...}' --range 500
  python3 cli.py --demo          # run with built-in 16-node demo grid
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from scheduler import optimize, RADIO_RANGE_METERS

# ─────────────────────────────────────────────────────────────────────────────
# Demo coordinates (4x4 grid, 300m spacing)
# ─────────────────────────────────────────────────────────────────────────────

DEMO_COORDS = {
    "Node_01": [0.0,    0.0],
    "Node_02": [300.0,  0.0],
    "Node_03": [600.0,  0.0],
    "Node_04": [900.0,  0.0],
    "Node_05": [0.0,    300.0],
    "Node_06": [300.0,  300.0],
    "Node_07": [600.0,  300.0],
    "Node_08": [900.0,  300.0],
    "Node_09": [0.0,    600.0],
    "Node_10": [300.0,  600.0],
    "Node_11": [600.0,  600.0],
    "Node_12": [900.0,  600.0],
    "Node_13": [0.0,    900.0],
    "Node_14": [300.0,  900.0],
    "Node_15": [600.0,  900.0],
    "Node_16": [900.0,  900.0],
}


# ─────────────────────────────────────────────────────────────────────────────
# Pretty-print helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bar(char: str = "=", width: int = 65) -> str:
    return char * width


def print_report(result: dict) -> None:
    gi = result["graph_info"]
    assignment = result["assignment"]
    node_order = result["node_order"]
    matrix = result["schedule_matrix"]
    violations = result["violations"]
    spatial_reuse = result["spatial_reuse"]
    num_slots = result["num_slots"]

    print()
    print(_bar("="))
    print("       TDMA TOPOLOGY OPTIMIZATION REPORT")
    print("       Author: Garv Kaushik | Vaan Megam Networks")
    print(_bar("="))
    print(f"  Total Nodes Processed   : {gi['num_nodes']}")
    print(f"  Configured Radio Range  : {gi['radio_range_m']} meters")
    print(f"  Network Links           : {gi['num_edges']}")
    print(f"  Conflict Pairs (d<=2)   : {gi['num_conflict_edges']}")
    print(f"  Optimized Frame Length  : {num_slots} unique timeslot(s)  [lower is better]")
    print(f"  Schedule Status         : {'CONFLICT-FREE ✓' if result['conflict_free'] else 'VIOLATIONS FOUND ✗'}")
    print(_bar("-"))

    # Node → Slot mapping
    print()
    print("  NODE -> SLOT ASSIGNMENTS:")
    for node in node_order:
        print(f"    {node}: Slot {assignment[node]}")

    # Spatial reuse groups
    print()
    print("  SPATIAL REUSE GROUPS (nodes sharing a slot safely):")
    for slot, members in spatial_reuse.items():
        print(f"    Slot {slot:02d}: {', '.join(sorted(members))}")

    # Schedule matrix
    print()
    print("  TDMA SCHEDULE MATRIX (Slot x Node — Boolean):")
    abbrev = [n.replace("Node_", "") for n in node_order]
    header = "Slot \\ Node | " + " | ".join(f"{a:>3}" for a in abbrev)
    print("  " + header)
    print("  " + _bar("-", len(header)))
    for s, row in enumerate(matrix):
        cells = " | ".join(f"  {v} " for v in row)
        print(f"   Slot {s:02d}   | {cells}")
    print("  " + _bar("-", len(header)))

    # Violations
    if violations:
        print()
        print("  ⚠  VIOLATIONS DETECTED:")
        for u, v, reason in violations:
            print(f"    {u} <-> {v}: {reason}")
    else:
        print()
        print("  Execution finalized cleanly. Schedule verified conflict-free. ✓")

    print()
    print(_bar("="))
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="TDMA Distance-2 Schedule Optimizer — Garv Kaushik / Vaan Megam Networks"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--coords",
        type=str,
        metavar="JSON",
        help='JSON string of node coordinates: \'{"Node_01":[0.0,0.0],...}\'',
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="Run with built-in 16-node 4x4 grid demo",
    )
    parser.add_argument(
        "--range",
        type=float,
        default=RADIO_RANGE_METERS,
        metavar="METERS",
        help=f"Radio transmission range in metres (default: {RADIO_RANGE_METERS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON result instead of formatted report",
    )

    args = parser.parse_args()

    # Load coordinates
    if args.demo:
        coords = DEMO_COORDS
        print(f"\n[DEMO MODE] Using 16-node 4x4 grid (300 m spacing)")
    else:
        try:
            coords = json.loads(args.coords)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON input — {e}", file=sys.stderr)
            sys.exit(1)

    # Run optimizer
    result = optimize(coords, radio_range=args.range)

    if args.json:
        # Serialise violations (tuples -> lists)
        result["violations"] = [list(v) for v in result["violations"]]
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
