# Condition Briefing Assistant - TOGAF ADM Delivery Package

Planning and delivery package for taking the **Condition Briefing Assistant** prototype to a production service
for health-system strategy teams, structured by the TOGAF 10 ADM.

> **Basis.** Blank fields of `/prompt.md` are filled from this project's README, `docs/DESIGN.md`, extraction report
> and code. Anything not in the repo is an **ASSUMPTION** (`A-xx`); every estimated number is marked **ESTIMATE**
> with its formula. The prompt's "ask questions, pause per phase" steps were skipped by agreement; open questions
> close each file. Clinical content, companies, institutions and trials in the prototype are synthetic and **not
> clinical guidance**; numbers describe a hypothetical production roll-out. This is not legal advice.

## Project context (filled template)
| Field | Value |
|---|---|
| Application | Condition Briefing Assistant |
| Problem | Strategy teams spend days assembling the standard of care, pipeline and key players per condition from complex PDFs, internal briefs and registries; facts hide in multi-page tables and figures |
| AI type | LangGraph: guard -> resolve condition -> authorize -> gather trials -> **4 parallel deterministic section agents** (standard of care, pipeline, key players, strategy) -> **one writer LLM call** -> verify; plus follow-up RAG Q&A; layout-aware extraction of complex PDFs with vision-captioned figures; optional live ClinicalTrials.gov |
| Users / volume | ~40 strategy analysts, service-line directors, executives, physician advisors, external consultants (A-01). ESTIMATE 150 briefings/month (cached repeats excluded), 600 follow-up questions/month, peak 8 concurrent |
| Cloud | AWS target (Bedrock by configuration); prototype local Ollama |
| Stack | Python 3.12, LangGraph, pdfplumber, PyMuPDF, python-docx, BeautifulSoup, Chroma + BM25, httpx, FastAPI, Streamlit, LangSmith, RAGAS |
| Data | Clinical guidelines (PDF/HTML), internal strategy brief (Word), trial registry (CSV), ClinicalTrials.gov live. Classification: public / internal. **No patient data** (PHI redacted if entered) |
| Compliance | Copyright and licence terms of guideline publishers (A-02, critical), ClinicalTrials.gov terms of use, no patient-specific advice (CDS boundary, A-03), SOC 2, internal AI policy, GDPR for user data |
| Budget / timeline | ESTIMATE ~USD 0.40M build (people + 15% contingency), 5 months to GA |
| Integrations | Document repository / licensed content library, IdP/SSO, ClinicalTrials.gov API, BI/slide tools for export |

## Files
| # | File | Phase |
|---|---|---|
| 00 | [00-preliminary.md](00-preliminary.md) | Preliminary |
| 01 | [01-architecture-vision.md](01-architecture-vision.md) | A |
| 02 | [02-business-architecture.md](02-business-architecture.md) | B |
| 03 | [03-information-systems.md](03-information-systems.md) | C |
| 04 | [04-technology-architecture.md](04-technology-architecture.md) | D |
| 05 | [05-opportunities-solutions.md](05-opportunities-solutions.md) | E |
| 06 | [06-migration-planning.md](06-migration-planning.md) | F |
| 07 | [07-product-backlog.md](07-product-backlog.md) | Backlog |
| 08 | [08-functional-spec.md](08-functional-spec.md) | Functional spec |
| 09 | [09-test-strategy.md](09-test-strategy.md) | Tests |
| 10 | [10-cicd-mlops.md](10-cicd-mlops.md) | CI/CD, LLMOps |
| 11 | [11-deployment-operations.md](11-deployment-operations.md) | G, H |
| 12 | [12-requirements-summary.md](12-requirements-summary.md) | Requirements, ADRs, risks, summary |

ID scheme: `REQ-CBR-nnn`, `US-CBR-nn`, `TC-CBR-nn`, `ADR-CBR-nn`, `R-CBR-nn`.
