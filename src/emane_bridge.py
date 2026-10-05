"""
EMANE TDMA Physical Emulator Bridge & Profile Generator
Author: Garv Kaushik
Company: Vaan Megam Networks - IITM Research Park, Chennai

Part 2: Physical Emulator (EMANE Setup)
---------------------------------------
Converts the Distance-2 TDMA schedule matrix into native EMANE TDMA Radio Model
XML profiles (1ms slots, frame definitions, and NEM allocations).
Provides Docker environment configurations and event generation helpers.
"""

from __future__ import annotations
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Any


def generate_emane_tdma_xml(result: dict[str, Any], slot_duration_microsec: int = 1000, guard_time_microsec: int = 100) -> str:
    """
    Generate native EMANE TDMA Radio Model schedule XML.
    Each timeslot in the recurring frame is mapped to the nodes permitted to transmit.
    """
    spatial_reuse = result.get("spatial_reuse", {})
    num_slots = result.get("num_slots", 0)

    root = ET.Element("tdmaschedule")
    structure = ET.SubElement(root, "structure", {
        "frame": str(num_slots),
        "slotduration": str(slot_duration_microsec),
        "guardtime": str(guard_time_microsec)
    })

    multiframe = ET.SubElement(root, "multiframe", {"count": "1"})
    frame = ET.SubElement(multiframe, "frame", {"id": "0"})

    for slot_idx in range(num_slots):
        slot_str = str(slot_idx)
        members = spatial_reuse.get(slot_idx) or spatial_reuse.get(slot_str) or []
        # Convert Node_01 -> NEM ID 1
        nem_ids = []
        for m in sorted(members):
            clean_id = m.replace("Node_", "").lstrip("0") or "0"
            nem_ids.append(clean_id)
        
        slot_elem = ET.SubElement(frame, "slot", {
            "id": str(slot_idx),
            "nodes": ",".join(nem_ids) if nem_ids else "none"
        })

    rough_xml = ET.tostring(root, "utf-8")
    reparsed = minidom.parseString(rough_xml)
    return reparsed.toprettyxml(indent="  ")


def generate_emane_nem_xml(result: dict[str, Any], frequency_hz: int = 2400000000, bandwidth_hz: int = 20000000) -> str:
    """
    Generate EMANE NEM configuration XML template for the TDMA radio model.
    """
    root = ET.Element("nem", {"name": "tdma-nem"})
    
    transport = ET.SubElement(root, "transport", {"definition": "transvirtual.xml"})
    mac = ET.SubElement(root, "mac", {"definition": "tdmaeventschedulermac.xml"})
    ET.SubElement(mac, "param", {"name": "schedulefile", "value": "tdmaschedule.xml"})
    ET.SubElement(mac, "param", {"name": "pcrcurveuri", "value": "tdmabiterror.xml"})
    
    phy = ET.SubElement(root, "phy", {"definition": "emanephy.xml"})
    ET.SubElement(phy, "param", {"name": "defaultconnectivitymode", "value": "on"})
    ET.SubElement(phy, "param", {"name": "frequency", "value": str(frequency_hz)})
    ET.SubElement(phy, "param", {"name": "bandwidth", "value": str(bandwidth_hz)})

    rough_xml = ET.tostring(root, "utf-8")
    reparsed = minidom.parseString(rough_xml)
    return reparsed.toprettyxml(indent="  ")


def generate_docker_setup() -> str:
    """
    Instructions and Dockerfile recipe for running EMANE TDMA simulation.
    """
    return """# EMANE TDMA Simulation Container
# Vaan Megam Networks - Garv Kaushik
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \\
    build-essential \\
    git \\
    cmake \\
    libprotobuf-dev \\
    protobuf-compiler \\
    libxml2-dev \\
    libpcap-dev \\
    python3-protobuf \\
    python3-pip \\
    emane \\
    emane-model-tdma \\
    iproute2 \\
    iputils-ping \\
    iperf3 \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY tdmaschedule.xml /workspace/
COPY nem.xml /workspace/

CMD ["emane", "/workspace/platform.xml"]
"""
