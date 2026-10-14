# 00 - Preliminary Phase

## Architecture principles
| Area | Principle | Evidence in the prototype |
|---|---|---|
| Business | **Information, never a recommendation.** No buy/sell/hold, price targets, allocations, valuation judgements, or MNPI | Input refusals; output compliance filter removes advice bullets and lists them for Compliance |
| Business | Supervised by design: every briefing is attributable, archived and reviewable | Audit log with `GET /audit` for the compliance role |
| Business | Every figure traceable to a filing or a data feed with timestamp | Numeric grounding; data timestamps and "may be delayed" labelling |
| Data | Key figures come from structured data (XBRL, quotes), not from LLM text; computed in Python | Metrics computed (growth, margin, P/E); snapshot and key financials rendered from data |
| Data | Retrieval is always scoped to one ticker and, for briefing sections, one section group | 0 cross-company chunks |
| Data | Production market data must be licensed for the use | Yahoo chart API is a prototype source only (ADR-STB-03) |
| Application | Fixed plan: parallel data agents, one writer call, compliance review | Cheap, testable, consistent |
| Application | Structure is enforced in code (max 5 bullets, citations backfilled or marked unattributed) | Small models ignore format instructions |
| Technology | Provider-neutral models; polite, compliant external API use (SEC User-Agent, rate limits) | `SEC_USER_AGENT` required |
| Responsible AI | Numbers in text must exist in evidence; removed statements are visible to Compliance, not silently dropped | Compliance filter output |
| Responsible AI | Role-appropriate scope: associates see quotes only; trainees synthetic only | `roles.yaml` |

## Governance and RACI
| Activity | Head of Advisory (PO) | Enterprise Architect | AI Lead | Chief Compliance Officer | Legal/Vendor Mgmt | Security | Records Mgmt |
|---|---|---|---|---|---|---|---|
| Scope and priorities | A | C | C | C | I | I | I |
| Architecture / ADRs | C | A | R | C | C | C | I |
| Prohibited-language lexicon, refusal wording, disclaimer | I | I | R | **A** | C | I | I |
| Market-data and EDGAR terms | C | I | I | C | A | I | I |
| Retention and archive (books and records) | I | C | I | C | I | C | A |
| Prompt/model change | C | I | A/R | C (review) | I | C | I |
| Go-live | A | C | R | R | R | R | C |

**ARB:** fortnightly in build, monthly in run. Compliance holds a veto on member-facing language, lexicon and disclaimers; any change to the lexicon or prompts follows the firm's supervisory-procedure change process.

## Tailored ADM
Light Preliminary/A, heavy on compliance requirements. B maps advisor workflow, supervision and retention. C splits market data, filings and structured financials. D uses AWS containers with an immutable archive. E/F: MVP (briefing + quote for advisors) -> Phase 2 (CRM context, surveillance integration, more filings) -> Target (watchlists). G/H tie into the firm's supervisory procedures and change control.

## Assumptions and open questions
- A-01 ~450 users; A-02 the firm is an SEC/FINRA-regulated wealth manager (broker-dealer and/or RIA); applicable rules to be confirmed by Compliance.
- Q: Are AI-generated briefings treated as internal-only research aids (not client communications)? If shared with clients, FINRA/SEC communications rules apply (pre-approval, fair and balanced).
- Q: Which licensed market-data vendor does the firm already have?
