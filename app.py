"""
TDMA Schedule Planner & Optimizer — Web Dashboard
Author: Garv Kaushik
Company: Vaan Megam Networks, IITM Research Park, Chennai
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from scheduler import optimize, RADIO_RANGE_METERS

# ─────────────────────────────────────────────────────────────────────────────
# Default 16-node grid
# ─────────────────────────────────────────────────────────────────────────────
DEMO_COORDS = {
    "Node_01": [0.0, 0.0], "Node_02": [300.0, 0.0],
    "Node_03": [600.0, 0.0], "Node_04": [900.0, 0.0],
    "Node_05": [0.0, 300.0], "Node_06": [300.0, 300.0],
    "Node_07": [600.0, 300.0], "Node_08": [900.0, 300.0],
    "Node_09": [0.0, 600.0], "Node_10": [300.0, 600.0],
    "Node_11": [600.0, 600.0], "Node_12": [900.0, 600.0],
    "Node_13": [0.0, 900.0], "Node_14": [300.0, 900.0],
    "Node_15": [600.0, 900.0], "Node_16": [900.0, 900.0],
}

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/api/optimize", methods=["POST"])
def api_optimize():
    """
    POST /api/optimize
    Body: { "coords": {"Node_01":[x,y], ...}, "radio_range": 500 }
    """
    data = request.get_json(force=True, silent=True) or {}
    coords = data.get("coords", DEMO_COORDS)
    radio_range = float(data.get("radio_range", RADIO_RANGE_METERS))

    try:
        result = optimize(coords, radio_range=radio_range)
        # Make violations JSON-serialisable (tuples → lists)
        result["violations"] = [list(v) for v in result["violations"]]
        return jsonify({"status": "ok", "data": result})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@app.route("/api/demo", methods=["GET"])
def api_demo():
    """GET /api/demo — run optimizer with built-in demo coordinates."""
    result = optimize(DEMO_COORDS, radio_range=RADIO_RANGE_METERS)
    result["violations"] = [list(v) for v in result["violations"]]
    return jsonify({"status": "ok", "data": result})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "author": "Garv Kaushik",
                    "project": "TDMA Schedule Optimizer — Vaan Megam Networks"})


@app.route("/api/emane", methods=["POST", "GET"])
def api_emane():
    """
    POST/GET /api/emane — generate EMANE TDMA XML schedule & NEM profile.
    """
    from emane_bridge import generate_emane_tdma_xml, generate_emane_nem_xml, generate_docker_setup
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        coords = data.get("coords", DEMO_COORDS)
        radio_range = float(data.get("radio_range", RADIO_RANGE_METERS))
    else:
        coords = DEMO_COORDS
        radio_range = RADIO_RANGE_METERS

    try:
        res = optimize(coords, radio_range=radio_range)
        tdma_xml = generate_emane_tdma_xml(res)
        nem_xml = generate_emane_nem_xml(res)
        docker_setup = generate_docker_setup()
        return jsonify({
            "status": "ok",
            "tdma_xml": tdma_xml,
            "nem_xml": nem_xml,
            "dockerfile": docker_setup,
            "num_slots": res["num_slots"]
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400



if __name__ == "__main__":
    import socket

    def find_free_port(start=5050):
        for port in range(start, start + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No free port found")

    port = find_free_port()
    print(f"\n{'='*60}")
    print(f"  TDMA Schedule Optimizer Dashboard")
    print(f"  Author: Garv Kaushik | Vaan Megam Networks")
    print(f"  Running at: http://localhost:{port}")
    print(f"{'='*60}\n")
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
