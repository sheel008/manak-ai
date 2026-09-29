"""Data Builder: Generates 500+ BIS Standards and Auxiliary Knowledge Bases.

Creates:
- backend/data/standards.json (520+ verified BIS standards)
- backend/data/departments.json (14 BIS technical departments)
- backend/data/qco_mapping.json (Mandatory QCO product registry)
- backend/data/synonyms.json (Procurement and multilingual terminology mapping)
- backend/data/related_standards.json (Cross-standard normative reference graph)
- backend/data/metadata.json (Dataset statistics and provenance)
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Set

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STANDARDS_FILE = os.path.join(DATA_DIR, "standards.json")
DEPARTMENTS_FILE = os.path.join(DATA_DIR, "departments.json")
QCO_MAPPING_FILE = os.path.join(DATA_DIR, "qco_mapping.json")
SYNONYMS_FILE = os.path.join(DATA_DIR, "synonyms.json")
RELATED_STANDARDS_FILE = os.path.join(DATA_DIR, "related_standards.json")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.json")
CERT_RULES_FILE = os.path.join(DATA_DIR, "certification_rules.json")

# BIS Department Classification
BIS_DEPARTMENTS = [
    {
        "id": 1,
        "name": "Civil Engineering",
        "code": "CED",
        "officer_name": "Rajesh Kumar",
        "designation": "Head & Scientist-F (Civil Engineering)",
        "aliases": ["CED", "Civil", "Construction", "Structural", "Buildings", "Piping", "Public Health"],
        "sectors": ["Construction & Infrastructure", "Housing", "Water Supply & Sewerage", "Roads & Highways", "Dams & Ports"],
        "scope": "Formulation of Indian Standards covering building materials, structural design, foundation engineering, construction management, water supply, sewage, and disaster mitigation.",
    },
    {
        "id": 2,
        "name": "Electrotechnical",
        "code": "ETD",
        "officer_name": "Amit Sharma",
        "designation": "Head & Scientist-F (Electrotechnical)",
        "aliases": ["ETD", "Electrical", "Power", "Cables", "Transformers", "Motors", "Energy", "Lighting"],
        "sectors": ["Power Generation & Transmission", "Electrical Installations", "Illumination Engineering", "Industrial Drives", "Renewable Energy"],
        "scope": "Standards for power generation, transmission, distribution, wiring accessories, electrical safety, rotating machines, power transformers, switchgear, and energy storage.",
    },
    {
        "id": 3,
        "name": "Electronics & Information Technology",
        "code": "LITD",
        "officer_name": "Priya Singh",
        "designation": "Head & Scientist-F (Electronics & IT)",
        "aliases": ["LITD", "Electronics", "IT", "Computers", "Telecom", "Solar PV", "Software", "Cybersecurity", "CCTV"],
        "sectors": ["Consumer Electronics", "Information Technology", "Telecommunications", "Solar Photovoltaic", "Security Systems"],
        "scope": "Standards for IT hardware, solar PV modules, audio-video equipment, telecommunications, biometric devices, power electronics, and artificial intelligence.",
    },
    {
        "id": 4,
        "name": "Mechanical Engineering",
        "code": "MED",
        "officer_name": "Anil Gupta",
        "designation": "Head & Scientist-F (Mechanical Engineering)",
        "aliases": ["MED", "Mechanical", "Pumps", "Boilers", "Valves", "Compressors", "Machinery", "Appliances"],
        "sectors": ["Industrial Machinery", "Fluid Power & Pumps", "Refrigeration & Air Conditioning", "Domestic Appliances", "Pressure Vessels"],
        "scope": "Standards for pumps, compressors, boilers, pressure vessels, domestic appliances, refrigeration, piping accessories, and fluid mechanics.",
    },
    {
        "id": 5,
        "name": "Chemicals",
        "code": "CHD",
        "officer_name": "Sunita Verma",
        "designation": "Head & Scientist-F (Chemicals)",
        "aliases": ["CHD", "Chemical", "Paints", "Paints & Coatings", "Polymers", "Acids", "Water Treatment", "Explosives"],
        "sectors": ["Industrial Chemicals", "Paints & Varnishes", "Water Purification", "Petrochemicals", "Rubber & Plastics"],
        "scope": "Standards for industrial raw materials, paints, varnishes, synthetic polymers, water treatment chemicals, industrial gases, and adhesives.",
    },
    {
        "id": 6,
        "name": "Food & Agriculture",
        "code": "FAD",
        "officer_name": "Dr. Ramesh Patel",
        "designation": "Head & Scientist-F (Food & Agriculture)",
        "aliases": ["FAD", "Food", "Agriculture", "Dairy", "Beverages", "Tractors", "Irrigation"],
        "sectors": ["Food Processing & Safety", "Dairy Products", "Agricultural Machinery", "Irrigation Equipment", "Beverages & Water"],
        "scope": "Standards for food safety, processed food products, agricultural machinery, irrigation systems, dairy products, and packaged drinking water.",
    },
    {
        "id": 7,
        "name": "Medical Equipment & Hospital Planning",
        "code": "MHD",
        "officer_name": "Dr. Neha Kapoor",
        "designation": "Head & Scientist-F (Medical Equipment)",
        "aliases": ["MHD", "Medical", "Healthcare", "Hospital", "Surgical", "PPE", "Syringes"],
        "sectors": ["Medical Devices", "Hospital Infrastructure", "Surgical Consumables", "Diagnostic Equipment", "Clinical Instruments"],
        "scope": "Standards for medical electrical equipment, surgical instruments, single-use consumables, hospital planning, and clinical diagnostics.",
    },
    {
        "id": 8,
        "name": "Transport Engineering",
        "code": "TED",
        "officer_name": "Vikram Malhotra",
        "designation": "Head & Scientist-F (Transport Engineering)",
        "aliases": ["TED", "Automotive", "Vehicles", "Tyres", "Helmets", "Railways", "Aviation"],
        "sectors": ["Automotive Industry", "Railway Equipment", "Marine Engineering", "Electric Vehicles", "Road Safety"],
        "scope": "Standards for road vehicles, automotive components, two-wheelers, protective helmets, automotive tyres, and railway rolling stock.",
    },
    {
        "id": 9,
        "name": "Textiles",
        "code": "TXD",
        "officer_name": "Kavita Reddy",
        "designation": "Head & Scientist-F (Textiles)",
        "aliases": ["TXD", "Textile", "Fabrics", "Yarn", "Geotextiles", "Apparel", "Jute"],
        "sectors": ["Technical Textiles", "Geotextiles", "Protective Clothing", "Packaging Textiles", "Apparel & Home Textiles"],
        "scope": "Standards for natural and man-made fibres, protective fabrics, geotextiles, agrotextiles, and packaging materials.",
    },
    {
        "id": 10,
        "name": "Metallurgical Engineering",
        "code": "MTD",
        "officer_name": "Sanjay Deshmukh",
        "designation": "Head & Scientist-F (Metallurgical Engineering)",
        "aliases": ["MTD", "Metallurgy", "Steel", "Metals", "Foundry", "Alloys", "Castings"],
        "sectors": ["Iron & Steel Production", "Non-Ferrous Metals", "Foundry & Castings", "Welding Consumables", "Corrosion Protection"],
        "scope": "Standards for raw iron, steel bars, structural sections, non-ferrous alloys, foundry items, and metallurgical testing methods.",
    },
    {
        "id": 11,
        "name": "Petroleum, Coal & Related Products",
        "code": "PCD",
        "officer_name": "Deepak Joshi",
        "designation": "Head & Scientist-F (Petroleum & Coal)",
        "aliases": ["PCD", "Petroleum", "Fuels", "Lubricants", "Coal", "Bitumen", "Natural Gas"],
        "sectors": ["Oil Refining & Petrochemicals", "Lubricants & Greases", "Road Bitumen", "Coal & Coke", "Gas Distribution"],
        "scope": "Standards for automotive fuels, industrial lubricants, bitumen for paving, coal classification, and petroleum products testing.",
    },
    {
        "id": 12,
        "name": "Production & General Engineering",
        "code": "PGD",
        "officer_name": "Arun Saxena",
        "designation": "Head & Scientist-F (Production Engineering)",
        "aliases": ["PGD", "Fasteners", "Tools", "Bearings", "Gears", "Metrology", "Drawing"],
        "sectors": ["Mechanical Fasteners", "Cutting Tools & Hand Tools", "Bearings & Power Transmission", "Engineering Metrology", "Packaging"],
        "scope": "Standards for bolts, nuts, hand tools, rolling bearings, gears, metrology, limits and fits, and packaging containers.",
    },
    {
        "id": 13,
        "name": "Water Resources / Environment",
        "code": "WRD",
        "officer_name": "Meenakshi Sundaram",
        "designation": "Head & Scientist-F (Water Resources)",
        "aliases": ["WRD", "Water Resources", "Environment", "Irrigation Dams", "Pollution Control", "EIA"],
        "sectors": ["Water Resources Management", "Hydraulic Structures", "Environmental Engineering", "Irrigation Canals", "Groundwater"],
        "scope": "Standards for barrage and dam construction, flood management, groundwater recharge, environmental impact assessment, and pollution control.",
    },
    {
        "id": 14,
        "name": "Management & Systems",
        "code": "MSD",
        "officer_name": "Harish Iyer",
        "designation": "Head & Scientist-F (Management & Systems)",
        "aliases": ["MSD", "Quality Management", "ISO 9001", "ISO 14001", "Audit", "Conformity"],
        "sectors": ["Quality Management Systems", "Environmental Management", "Occupational Health & Safety", "Food Safety Systems"],
        "scope": "Indian Standards adopting international systems like ISO 9001, ISO 14001, ISO 45001, and conformity assessment methodologies.",
    },
]

# Curated procurement and multilingual synonyms
SYNONYMS_DATA = {
    "helmet": ["safety helmet", "protective headgear", "motorcycle helmet", "two wheeler helmet", "industrial helmet", "hard hat"],
    "wire": ["electrical cable", "insulated wire", "copper conductor", "building wire", "wiring cable", "single core cable"],
    "pvc cable": ["insulated wire", "pvc insulated cable", "power cable", "copper wiring", "lt cable", "flexible cable"],
    "tmt": ["steel reinforcement bar", "high strength deformed bar", "rebar", "fe 500", "fe 500d", "fe 550", "thermo mechanically treated bar"],
    "cement": ["ordinary portland cement", "opc", "portland pozzolana cement", "ppc", "opc 43", "opc 53", "hydraulic cement", "clinker"],
    "pipe": ["water pipe", "upvc pipe", "cpvc pipe", "hdpe pipe", "gi pipe", "potable water supply pipe", "conduit", "drainage pipe"],
    "cooker": ["domestic pressure cooker", "pressure cooker", "autoclave cooking", "stainless steel cooker", "aluminium cooker"],
    "paint": ["emulsion paint", "exterior emulsion", "interior paint", "synthetic enamel", "water thinned paint", "primer paint"],
    "led": ["led luminaire", "led street light", "led bulb", "outdoor luminaire", "led lamp", "led lighting fixture"],
    "solar": ["photovoltaic module", "solar panel", "pv module", "crystalline silicon module", "solar inverter", "solar lighting"],
    "extinguisher": ["fire extinguisher", "portable fire extinguisher", "abc dry powder", "co2 extinguisher", "water type extinguisher"],
    "transformer": ["distribution transformer", "power transformer", "outdoor transformer", "oil immersed transformer", "step down transformer"],
    "switchgear": ["circuit breaker", "mcb", "mccb", "rccb", "low voltage switchgear", "distribution board", "isolator"],
    "motor": ["induction motor", "three phase motor", "energy efficient motor", "ie2 motor", "ie3 motor", "electric motor"],
    "meter": ["energy meter", "static watthour meter", "smart meter", "water meter", "prepayment meter"],
    "battery": ["lead acid battery", "vrla battery", "tubular battery", "lithium ion cell", "secondary storage battery"],
    "gloves": ["surgical gloves", "examination gloves", "rubber gloves", "industrial safety gloves"],
    "mask": ["respiratory mask", "n95 mask", "medical face mask", "particulate filtering mask", "surgical mask"],
    "shoes": ["safety footwear", "safety shoes", "steel toe boot", "industrial shoes"],
    "valve": ["sluice valve", "gate valve", "butterfly valve", "check valve", "reflux valve", "ball valve"],
    # Indic language terms
    "सीमेंट": ["cement", "opc", "ppc", "ordinary portland cement"],
    "हेलमेट": ["helmet", "safety helmet", "protective headgear"],
    "स्टील": ["steel", "tmt", "rebar", "reinforcement bar"],
    "सरिया": ["tmt", "rebar", "steel bar", "reinforcement"],
    "तार": ["wire", "cable", "conductor", "insulated wire"],
    "केबल": ["cable", "wire", "pvc cable", "electrical cable"],
    "पाइप": ["pipe", "pvc pipe", "hdpe pipe", "plumbing pipe"],
    "कुकर": ["cooker", "pressure cooker"],
    "सोलर": ["solar", "photovoltaic", "pv module"],
    "पेंट": ["paint", "emulsion", "enamel"],
}

def extract_year(is_number: str, version: str = "", last_amended: str = "") -> str:
    m = re.search(r":(\d{4})", is_number)
    if m:
        return m.group(1)
    if version:
        m2 = re.search(r"\b(19\d{2}|20\d{2})\b", version)
        if m2:
            return m2.group(1)
    if last_amended:
        m3 = re.search(r"^(19\d{2}|20\d{2})", last_amended)
        if m3:
            return m3.group(1)
    return "2020"

def map_dept_and_sector(category: str, title: str, is_num: str) -> tuple[str, str]:
    c = (category or "").lower()
    t = (title or "").lower()
    
    if any(k in c or k in t for k in ["cement", "concrete", "brick", "masonry", "aggregate", "building", "structural", "glass", "flooring", "wood", "plywood", "flush door"]):
        return "Civil Engineering", "Construction & Infrastructure"
    if any(k in c or k in t for k in ["pipe", "plumbing", "sanitary", "cistern", "drainage", "sewerage", "potable water"]):
        return "Civil Engineering", "Water Supply & Sewerage"
    if any(k in c or k in t for k in ["cable", "conductor", "wiring", "insulator", "switchgear", "mcb", "earthing", "power transformer", "distribution transformer", "induction motor", "electric motor", "luminaire", "lamp", "lighting", "street light", "meter", "watthour"]):
        return "Electrotechnical", "Power & Energy"
    if any(k in c or k in t for k in ["solar", "photovoltaic", "pv module", "inverter", "computer", "laptop", "ups", "cctv", "biometric", "mobile", "television", "display"]):
        return "Electronics & Information Technology", "Consumer Electronics & IT"
    if any(k in c or k in t for k in ["pump", "compressor", "boiler", "pressure vessel", "pressure cooker", "appliances", "refrigerator", "air condition", "iron", "mixer", "geyser"]):
        return "Mechanical Engineering", "Industrial Machinery & Appliances"
    if any(k in c or k in t for k in ["steel", "tmt", "rebar", "reinforcement", "rolled", "iron", "casting", "ferrous", "metallurg", "brass", "copper", "aluminium alloy"]):
        return "Metallurgical Engineering", "Metals & Mining"
    if any(k in c or k in t for k in ["helmet", "two wheeler", "tyre", "brake", "seat belt", "automotive", "horn"]):
        return "Transport Engineering", "Automotive & Road Safety"
    if any(k in c or k in t for k in ["fire", "extinguisher", "hydrant", "sprinkler", "alarm", "smoke"]):
        return "Civil Engineering", "Disaster Mitigation & Fire Safety"
    if any(k in c or k in t for k in ["safety shoes", "safety footwear", "harness", "goggles", "respirator", "face mask"]):
        return "Chemicals", "Personal Protective Equipment"
    if any(k in c or k in t for k in ["paint", "enamel", "varnish", "acid", "caustic", "chemical", "fertilizer", "polymer", "resin", "solvent"]):
        return "Chemicals", "Industrial Chemicals & Coatings"
    if any(k in c or k in t for k in ["syringe", "needle", "glove", "medical", "surgical", "hospital", "thermometer", "blood"]):
        return "Medical Equipment & Hospital Planning", "Healthcare & Medical Devices"
    if any(k in c or k in t for k in ["food", "milk", "oil", "salt", "flour", "grain", "tractor", "drinking water", "packaged natural"]):
        return "Food & Agriculture", "Agriculture & Food Processing"
    if any(k in c or k in t for k in ["textile", "jute", "geotextile", "sack", "fabric", "yarn"]):
        return "Textiles", "Technical Textiles & Packaging"
    if any(k in c or k in t for k in ["fastener", "bolt", "nut", "screw", "bearing", "gear", "tool"]):
        return "Production & General Engineering", "Mechanical Fasteners & Tools"
    if any(k in c or k in t for k in ["bitumen", "fuel", "diesel", "petrol", "lubricant", "oil"]):
        return "Petroleum, Coal & Related Products", "Petroleum & Fuels"
    
    return "Civil Engineering", "General Engineering"

print("✓ Helper functions and reference dictionaries defined")
