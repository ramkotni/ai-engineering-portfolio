# 00 - Preliminary Phase

## Architecture principles
| Area | Principle | Evidence |
|---|---|---|
| Business | **Information, not decisions.** No release/reject/quarantine/recall decisions and no medical or dosing advice | Disposition and medical guardrails |
| Business | Controlled documents stay authoritative: answers cite document IDs and sections; the DMS remains the system of record | Citations |
| Business | External partners see public content only | `logistics_partner` clearance public |
| Data | **Clearance before retrieval**: restricted text must never reach the prompt | Filter before ranking |
| Data | Figures are first-class content: extract, caption, index as `image` chunks, show source image | PyMuPDF + python-docx + `gemma3:4b` |
| Data | Structure is preserved (sections, whole tables, one chunk per CSV row) | Structure-aware chunking |
| Application | One workflow, versioned prompts per task (qa, summarize, search) | Prompt templates |
| Application | Exact lookups where IDs exist (`LOT-`) | Hybrid + exact lookup |
| Technology | Provider-neutral model layer; local fallback | Ollama / Bedrock |
| Technology | Electronic-record integrity: audit trail, versioned config, validated releases | GxP |
| Responsible AI | IDs and numbers in answers must exist in retrieved context | Output grounding |
| Responsible AI | Image captions are machine-generated and labelled as such | Provenance on `image` chunks |

## Governance and RACI
| Activity | Supply Chain Head (PO) | Enterprise Architect | AI Lead | QA / CSV Lead | Security | Regulatory Affairs |
|---|---|---|---|---|---|---|
| Scope | A | C | C | C | I | C |
| Architecture / ADRs | C | A | R | C | C | I |
| Classification policy | C | I | I | C | A | R |
| Validation (CSV) plan and release | C | I | R | A | C | C |
| Prompt/model change | C | I | A/R | C (impact assessment) | C | I |
| Partner access | R | I | I | C | A | C |
| Go-live | A | C | R | R | R | C |

**ARB:** fortnightly in build, monthly after GA. Any change to classification logic, guardrails, prompts or models is also an **impact assessment** by QA under change control (validated state must be preserved).

## Tailored ADM
Preliminary/A are light; B maps document-use processes and partner access; C separates data (ingestion, classification) from application (workflow); D is AWS; E/F plan MVP -> validated Phase 1 -> Phase 2 (DMS write-back is out of scope); G/H integrate with the QMS change control.

## Assumptions and open questions
- A-01 ~150 users; A-02 EU AI Act limited-risk classification (transparency); GxP applicability is a **QA determination**, not assumed final.
- Q: Does QA classify the assistant as GxP-relevant (answers used in deviation work)? It drives validation scope.
- Q: Who maintains document classification labels in the DMS?
