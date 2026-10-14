# 00 - Preliminary Phase

## Architecture principles
| Area | Principle | Evidence in the prototype |
|---|---|---|
| Business | **Strategy intelligence, not clinical advice.** No patient-specific guidance; briefings carry a disclaimer | Patient-specific requests refused ("should my father start an SGLT2 inhibitor?"); disclaimer always attached |
| Business | Every statement traceable to a numbered source; unattributed content is labelled | Citation backfill; "unattributed" marking |
| Business | Counts and rankings are computed, not guessed | Registry analytics (6/6 vs direct CSV count) |
| Business | Internal strategy content stays internal | Clearance before retrieval; external consultant sees public only |
| Data | Complex documents are first-class: layout-aware extraction of columns, tables across pages, figures | pdfplumber/PyMuPDF pipeline; extraction report 8/8 |
| Data | Machine-read figures are verified, not trusted | Caption verification flags drug names found nowhere else |
| Data | Licensed content is used only within its licence | Content-rights register (file 03) |
| Application | Fixed plan for every condition: parallel deterministic agents, one writer call | Cheaper, testable, consistent |
| Application | Evidence gathering uses no LLM; the LLM writes, code verifies | Section agents deterministic |
| Technology | Provider-neutral model layer; local fallback | Ollama / Bedrock by configuration |
| Responsible AI | Numbers and trial/document IDs in output must exist in evidence | Grounding check |
| Responsible AI | Live data is labelled with retrieval date and source | ClinicalTrials.gov mode |

## Governance and RACI
| Activity | CSO / Strategy Head (PO) | Enterprise Architect | AI Lead | Clinical Advisor | Legal / Licensing | Security |
|---|---|---|---|---|---|---|
| Scope and priorities | A | C | C | C | I | I |
| Architecture / ADRs | C | A | R | I | I | C |
| Content licensing and rights register | C | I | I | I | A | I |
| Clinical content review (standard-of-care section) | C | I | C | A/R | I | I |
| Clearance model | C | I | I | I | C | A |
| Prompt/model change | C | I | A/R | C | I | C |
| Go-live | A | C | R | R | R | R |

**ARB:** monthly in build and run; extra review for new content sources, live-data features, model changes. Legal holds a veto on ingesting a new licensed source; the Clinical Advisor must review the standard-of-care template and a sample per release.

## Tailored ADM
Light Preliminary/A. B: briefing preparation process and review workflow. C: content ingestion and rights register (data) plus workflow (application). D: AWS containers, batch ingestion. E/F: MVP (one service line, synthetic -> licensed content) -> Phase 2 (more conditions, export to slides, scheduled refresh) -> Target (watchlists, change alerts). G/H: content refresh and clinical review in change control.

## Assumptions and open questions
- A-01 ~40 users; A-02 guideline PDFs are licensed or openly reusable for internal summarisation (**must be confirmed per publisher**); A-03 the assistant stays outside FDA clinical decision support scope because it does not give patient-specific recommendations.
- Q: Which licensed sources (guidelines, market intelligence) are in scope and what do their licences allow (storage, summarisation by AI, redistribution)?
- Q: Who in Legal approves the live ClinicalTrials.gov use and attribution wording?
