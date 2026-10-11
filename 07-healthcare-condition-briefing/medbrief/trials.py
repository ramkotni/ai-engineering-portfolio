"""Emerging treatments and key players from a trial registry.

Two interchangeable sources behind one function:
  synthetic  data/raw/pipeline_trials.csv (offline, default; fictional sponsors and sites)
  live       ClinicalTrials.gov API v2 - recruiting / active Phase 2-3 interventional studies (no API key)

Counts, rankings and timelines are computed here in code, never by the LLM: the model only narrates them.
"""

import csv
import logging
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass

import httpx

from medbrief.conditions import Condition
from medbrief.config import Settings, get_settings

log = logging.getLogger(__name__)
LATE_STAGE = ("Phase 3", "Pivotal", "Pragmatic RCT", "Phase 4")
PHASE_RANK = {"Phase 4": 6, "Phase 3": 5, "Pivotal": 5, "Phase 2/3": 4.5, "Pragmatic RCT": 4, "Phase 2": 3, "Phase 1/2": 2, "Phase 1": 1}
INACTIVE = ("Completed", "Terminated", "Withdrawn", "Suspended")
_CT_STATUS = {"RECRUITING": "Recruiting", "ACTIVE_NOT_RECRUITING": "Active, not recruiting", "NOT_YET_RECRUITING": "Not yet recruiting",
              "ENROLLING_BY_INVITATION": "Enrolling by invitation", "COMPLETED": "Completed"}
_CT_PHASE = {"PHASE1": "Phase 1", "PHASE2": "Phase 2", "PHASE3": "Phase 3", "PHASE4": "Phase 4", "EARLY_PHASE1": "Phase 1"}


@dataclass
class Trial:
    trial_id: str
    condition: str
    intervention: str
    mechanism: str
    modality: str
    phase: str
    status: str
    sponsor: str
    sponsor_type: str
    lead_institution: str
    enrollment: int
    start_date: str
    primary_completion: str
    primary_endpoint: str
    source: str
    url: str = ""

    @property
    def active(self) -> bool:
        return self.status not in INACTIVE

    def as_text(self) -> str:
        return (f"Trial {self.trial_id} ({self.source}): {self.intervention}; mechanism {self.mechanism}; modality {self.modality}; "
                f"{self.phase}; status {self.status}; sponsor {self.sponsor} ({self.sponsor_type}); lead site {self.lead_institution}; "
                f"enrollment {self.enrollment}; primary completion {self.primary_completion}; endpoint: {self.primary_endpoint}")


def synthetic_trials(cond: Condition, settings: Settings | None = None) -> list[Trial]:
    s = settings or get_settings()
    with open(s.data_dir / "pipeline_trials.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["condition"] == cond.registry_condition]
    return [Trial(**{**r, "enrollment": int(r["enrollment"])}, source="synthetic registry") for r in rows]


def live_trials(cond: Condition, settings: Settings | None = None) -> list[Trial]:
    s = settings or get_settings()
    params = {
        "query.cond": cond.live_query,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,NOT_YET_RECRUITING",
        "filter.advanced": "AREA[Phase](PHASE2 OR PHASE3)",
        "pageSize": s.live_max_trials,
        "fields": "NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName,LeadSponsorClass,InterventionName,InterventionType,"
                  "EnrollmentCount,PrimaryCompletionDate,StartDate,PrimaryOutcomeMeasure",
    }
    r = httpx.get(s.clinicaltrials_url, params=params, timeout=s.http_timeout)
    r.raise_for_status()
    out = []
    for study in r.json().get("studies", []):
        p = study.get("protocolSection", {})
        ident, status = p.get("identificationModule", {}), p.get("statusModule", {})
        sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
        design = p.get("designModule", {})
        interventions = [i for i in p.get("armsInterventionsModule", {}).get("interventions", []) if i.get("type") != "OTHER"
                         and "placebo" not in i.get("name", "").lower()]
        phases = [_CT_PHASE.get(x, x) for x in design.get("phases", [])]
        out.append(Trial(
            trial_id=ident.get("nctId", ""), condition=cond.name,
            intervention=", ".join(i.get("name", "") for i in interventions[:2]) or ident.get("briefTitle", ""),
            mechanism="see registry record", modality=(interventions[0].get("type", "").title() if interventions else "Other"),
            phase="Phase 2/3" if len(phases) > 1 else (phases[0] if phases else "N/A"),
            status=_CT_STATUS.get(status.get("overallStatus", ""), status.get("overallStatus", "")),
            sponsor=sponsor.get("name", ""), sponsor_type="Industry" if sponsor.get("class") == "INDUSTRY" else "Academic / other",
            # the first listed site is arbitrary in registry data - only non-industry lead sponsors count as institutions
            lead_institution="" if sponsor.get("class") == "INDUSTRY" else sponsor.get("name", ""),
            enrollment=int(design.get("enrollmentInfo", {}).get("count") or 0),
            start_date=status.get("startDateStruct", {}).get("date", ""),
            primary_completion=status.get("primaryCompletionDateStruct", {}).get("date", ""),
            primary_endpoint=(p.get("outcomesModule", {}).get("primaryOutcomes") or [{}])[0].get("measure", "")[:160],
            source="ClinicalTrials.gov", url=f"https://clinicaltrials.gov/study/{ident.get('nctId', '')}",
        ))
    return out


def get_trials(cond: Condition, source: str, settings: Settings | None = None) -> tuple[list[Trial], str]:
    """Returns (trials, source actually used). Live failures fall back to the synthetic registry when possible."""
    if source == "live":
        try:
            return live_trials(cond, settings), "ClinicalTrials.gov (live)"
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("ClinicalTrials.gov unavailable, using the synthetic registry: %s", exc)
            if not cond.registry_condition:
                return [], f"ClinicalTrials.gov unavailable ({type(exc).__name__})"
    return (synthetic_trials(cond, settings), "synthetic registry") if cond.registry_condition else ([], "none")


def pipeline_summary(trials: list[Trial]) -> dict:
    active = [t for t in trials if t.active]
    late = sorted([t for t in active if t.phase in LATE_STAGE], key=lambda t: (-PHASE_RANK.get(t.phase, 0), -t.enrollment))
    readouts: dict[str, list[str]] = defaultdict(list)
    for t in late:
        readouts[t.primary_completion[:4]].append(t.trial_id)
    return {
        "active_programs": len(active),
        "completed_programs": len(trials) - len(active),
        "by_phase": dict(Counter(t.phase for t in active).most_common()),
        "by_modality": dict(Counter(t.modality for t in active).most_common()),
        "by_mechanism": dict(Counter(t.mechanism for t in active).most_common()),
        "late_stage": [asdict(t) for t in late],
        "expected_readouts": dict(sorted(readouts.items())),
        "programs": [asdict(t) for t in sorted(active, key=lambda t: (-PHASE_RANK.get(t.phase, 0), t.trial_id))],
    }


def key_players(trials: list[Trial]) -> dict:
    """Companies = industry sponsors; institutions = lead sites and academic sponsors. Ranked by active programs,
    then by the most advanced phase."""
    active = [t for t in trials if t.active]

    def rank(groups: dict[str, list[Trial]]) -> list[dict]:
        rows = [{"name": name, "active_programs": len(ts), "most_advanced_phase": max((t.phase for t in ts), key=lambda p: PHASE_RANK.get(p, 0)),
                 "programs": sorted({t.trial_id for t in ts}), "modalities": sorted({t.modality for t in ts})} for name, ts in groups.items()]
        return sorted(rows, key=lambda r: (-r["active_programs"], -PHASE_RANK.get(r["most_advanced_phase"], 0), r["name"]))

    companies: dict[str, list[Trial]] = defaultdict(list)
    institutions: dict[str, list[Trial]] = defaultdict(list)
    for t in active:
        if t.sponsor_type == "Industry":
            companies[t.sponsor].append(t)
        else:
            institutions[t.sponsor].append(t)
        if t.lead_institution and t.lead_institution != t.sponsor:
            institutions[t.lead_institution].append(t)
    return {"companies": rank(companies), "institutions": rank(institutions)}


def evidence_text(summary: dict, players: dict, source: str, limit: int = 8) -> str:
    """Compact, numbered-friendly text the LLM narrates (all numbers computed above)."""
    lines = [f"Source: {source}. Active programs: {summary['active_programs']} (completed: {summary['completed_programs']}).",
             "By phase: " + ", ".join(f"{k} {v}" for k, v in summary["by_phase"].items()),
             "By modality: " + ", ".join(f"{k} {v}" for k, v in summary["by_modality"].items()),
             "Late-stage programs:"]
    lines += [f"- {t['trial_id']}: {t['intervention']} ({t['mechanism']}), {t['phase']}, {t['status']}, sponsor {t['sponsor']}, "
              f"primary completion {t['primary_completion']}" for t in summary["late_stage"][:limit]]
    lines.append("Expected late-stage readouts by year: " + "; ".join(f"{y}: {', '.join(ids)}" for y, ids in summary["expected_readouts"].items()))
    lines.append("Top companies: " + "; ".join(f"{c['name']} ({c['active_programs']} active, most advanced {c['most_advanced_phase']})"
                                                for c in players["companies"][:5]))
    lines.append("Top institutions: " + "; ".join(f"{i['name']} ({i['active_programs']} programs)" for i in players["institutions"][:5]))
    return "\n".join(lines)
