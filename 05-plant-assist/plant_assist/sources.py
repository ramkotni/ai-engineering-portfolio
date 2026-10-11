"""Registry of the knowledge sources the router can choose from.

Adding a new source (e.g. environmental permits) means adding one entry here and a
folder under data/docs/ -- the router prompt, schema and fallback are generated from it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeSource:
    name: str                 # routing label used by the LLM router
    display_name: str
    folder: str               # sub-folder of settings.docs_dir
    collection: str           # Chroma collection name
    description: str          # what the router is told about this source
    keywords: tuple[str, ...]  # used by the deterministic fallback router
    answer_guidance: str      # domain-specific rules for the answer generator
    escalation: str           # who to contact when the docs don't answer it


SOURCES: dict[str, KnowledgeSource] = {
    "safety": KnowledgeSource(
        name="safety",
        display_name="Safety Procedures",
        folder="safety",
        collection="safety_procedures",
        description=(
            "EHS safety procedures: lockout/tagout (LOTO), hazardous energy, PPE requirements, "
            "chemical handling, spills, SDS, fire, injuries, first aid, evacuation, emergency contacts, near misses."
        ),
        keywords=(
            "safety", "safe", "loto", "lockout", "tagout", "lock out", "ppe", "glove", "goggle", "glasses",
            "harness", "hearing", "spill", "chemical", "sds", "fire", "extinguisher", "injury", "injured",
            "first aid", "evacuat", "emergency", "near miss", "hazard", "burn", "eyewash", "arc flash",
        ),
        answer_guidance=(
            "State required PPE and hazard controls first. Never suggest skipping or shortening a safety step. "
            "Include emergency contact numbers when they appear in the excerpts."
        ),
        escalation="EHS Manager (ext. 4400); emergencies: ext. 5555",
    ),
    "maintenance": KnowledgeSource(
        name="maintenance",
        display_name="Maintenance Manuals",
        folder="maintenance",
        collection="maintenance_manuals",
        description=(
            "Equipment maintenance manuals for the HP-200 hydraulic press, VMC-500 CNC machining center, "
            "CV-3 conveyor and AC-75 air compressor: PM schedules, lubrication, oil, filters, seals, torque specs, "
            "part numbers, alarms and troubleshooting."
        ),
        keywords=(
            "maintenance", "maintain", "pm ", "repair", "replace", "filter", "oil", "lubric", "grease", "seal",
            "torque", "alarm", "troubleshoot", "spindle", "press", "hp-200", "vmc", "cnc", "conveyor", "cv-3",
            "belt", "compressor", "ac-75", "pump", "hydraulic", "accumulator", "warm-up", "backlash", "jam",
        ),
        answer_guidance=(
            "If the excerpts mention lockout/tagout or other safety prerequisites, list them before the steps. "
            "Quote intervals, specifications, torque values and part numbers exactly as written."
        ),
        escalation="Maintenance Planner (ext. 4410)",
    ),
    "quality": KnowledgeSource(
        name="quality",
        display_name="Quality Control Standards",
        folder="quality",
        collection="quality_standards",
        description=(
            "Quality control standards: first article inspection, sampling plans and AQL, in-process and final "
            "inspection, SPC control charts, Cpk/process capability, nonconforming product, NCR, MRB, CAPA/8D, "
            "gauge calibration and Gauge R&R."
        ),
        keywords=(
            "quality", "inspect", "inspection", "aql", "sample", "sampling", "spc", "control chart", "cpk",
            "capability", "nonconform", "ncr", "mrb", "capa", "8d", "defect", "reject", "scrap", "rework",
            "calibrat", "gauge", "gage", "r&r", "first article", "fai", "tolerance", "out of control",
        ),
        answer_guidance=(
            "Quote acceptance criteria, sample sizes and limits exactly. State the required disposition "
            "or escalation path for nonconforming product."
        ),
        escalation="Quality Engineer (ext. 4420)",
    ),
}

OUT_OF_SCOPE = "out_of_scope"
ROUTE_LABELS: tuple[str, ...] = (*SOURCES.keys(), OUT_OF_SCOPE)
