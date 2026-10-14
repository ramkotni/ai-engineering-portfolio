# 07 - Product Backlog

Story points and priorities are ESTIMATES / MoSCoW.

**Definition of Done:** reviewed; unit/integration tests pass; ruff clean; extraction contract tests and eval gate green; clearance tests pass; licence/rights checks pass for any new source; scans clean; docs updated; audit/metrics emitted; demoed to PO.

## Epics
E1 Briefing generation | E2 Follow-up Q&A | E3 Document extraction | E4 Live trials | E5 Access and safety | E6 Content governance | E7 Platform/DevOps | E8 Quality

## Stories
### US-CBR-01 Generate a structured briefing (E1) - Must, 13, REQ-CBR-001, 002
As a **strategy analyst**, I want a five-section briefing for a condition, so that I can brief leadership in minutes.
```gherkin
Scenario: HFrEF briefing
  Given I am strategy_analyst
  When I POST /briefing for "heart failure with reduced ejection fraction" (synthetic)
  Then the response has executive summary, standard of care, emerging treatments with a late-stage table, key companies and institutions, strategic considerations
  And every bullet carries a numbered source or is marked unattributed
Scenario: Unknown condition
  When I request a condition not in the catalogue with source synthetic
  Then I receive a clear message and the option to use live mode
Scenario: Truncation (negative)
  Given the token cap cuts off a bullet
  Then the bullet is trimmed to the last complete sentence and flagged
```

### US-CBR-02 Computed counts and rankings (E1) - Must, 5, REQ-CBR-003
As a **service-line director**, I want counts and rankings computed from the registry, so that numbers are right.
```gherkin
Scenario: Registry analytics
  When the pipeline section lists active programs by modality
  Then counts equal a direct count of the registry
Scenario: LLM invents a count (negative)
  Given the writer states 14 programs while the registry has 11
  Then verify flags the number and the figure is replaced by the computed value
```

### US-CBR-03 Complex PDF extraction (E3) - Must, 13, REQ-CBR-004, 005
As a **content steward**, I want multi-column, multi-page, figure-heavy PDFs extracted faithfully, so that facts are not lost.
```gherkin
Scenario: Layout handling
  Given the guideline PDF has a running header/footer, two columns and a table continued across a page break
  Then headers/footers are removed, the left column precedes the right, and the table is merged with all rows
Scenario: Figures
  Then each figure has a PNG, a transcription+description caption and its own chunk under its section
Scenario: Caption verification (negative)
  Given a caption names a drug that appears nowhere else in the document
  Then it is flagged for verification in the extraction report
Scenario: Failed extraction check
  Then the document is quarantined and not indexed
```

### US-CBR-04 Follow-up questions (E2) - Must, 5, REQ-CBR-006
As an **analyst**, I want to ask questions on the same sources, so that I can dig deeper.
```gherkin
Scenario: Figure-based answer
  When I ask "When is CRT-D indicated according to the algorithm?"
  Then the answer cites the algorithm figure chunk and the guideline text
Scenario: Not covered
  When I ask about a topic absent from the accessible documents
  Then the answer says the sources do not cover it
```

### US-CBR-05 Live ClinicalTrials.gov mode (E4) - Should, 8, REQ-CBR-007
As an **analyst**, I want live trial data for any condition, so that I am not limited to the catalogue.
```gherkin
Scenario: Atrial fibrillation
  When I request "atrial fibrillation" with source live
  Then recruiting and active Phase 2-3 studies are fetched and ranked by sponsor
  And the briefing shows retrieval date and NCT IDs
Scenario: Executive role (negative)
  Given I am executive (live_data false)
  Then live mode is denied
Scenario: API unavailable
  Then cached data is used with a stale-data warning or a clear error
```

### US-CBR-06 Role-based clearance (E5) - Must, 8, REQ-CBR-008
As a **security officer**, I want internal content hidden from public roles, so that strategy stays confidential.
```gherkin
Scenario: Consultant
  Given I am external_consultant (public)
  When I request a briefing
  Then no internal chunk is retrieved and the strategy section states it is unavailable
Scenario: Hidden endpoints
  When I call /extraction or /images for an internal document
  Then the document is not listed and the image returns 403
```

### US-CBR-07 Patient-advice refusal (E5) - Must, 3, REQ-CBR-009
As a **physician advisor**, I want patient-specific requests refused, so that the tool is not used for clinical decisions.
```gherkin
Scenario: Patient advice
  When I ask "should my father start an SGLT2 inhibitor?"
  Then the request is refused with a pointer to a clinician
Scenario: Strategy question mentioning doses
  When I ask "what are the guideline target doses for HFrEF therapies?"
  Then it is answered with sources
```

### US-CBR-08 Grounding and guardrails (E5) - Must, 5, REQ-CBR-010
As an **AI lead**, I want numbers and IDs verified, so that fabricated facts are caught.
```gherkin
Scenario: Unknown trial ID
  Given the writer cites NCT0000000 not in evidence
  Then verify removes or flags it
Scenario: Second-person treatment language
  Then the sentence is flagged for review
Scenario: Injection
  When the question says "ignore previous instructions"
  Then it is blocked
Scenario: PHI typed
  When a question contains an MRN or DOB
  Then it is redacted before any model call
```

### US-CBR-09 Briefing cache and refresh (E7) - Should, 5, REQ-CBR-011
As an **analyst**, I want repeat briefings to be instant but never stale, so that I save time and trust the content.
```gherkin
Scenario: Cache hit
  Given an identical request within 24 h at the same clearance and style
  Then the cached briefing is returned in under 1 s
Scenario: Invalidation
  Given the guideline was refreshed
  Then the cache for that condition is invalidated
```

### US-CBR-10 Content rights register (E6) - Must, 5, REQ-CBR-012
As **Legal**, I want ingestion gated by licence, so that we use content only as permitted.
```gherkin
Scenario: Unlicensed source
  Given a document without a rights record
  Then ingestion is rejected
Scenario: Quote limit
  Given a licence allows 150-word excerpts
  Then no briefing quote exceeds the limit and attribution is added
```

### US-CBR-11 Clinical review sign-off (E6) - Must, 5, REQ-CBR-013
As a **physician advisor**, I want to review and sign the standard-of-care section, so that clinical accuracy is assured.
```gherkin
Scenario: Review
  When I approve a briefing version
  Then the reviewer, time and version are stored and shown on exports
Scenario: Changed content
  Given the briefing is regenerated
  Then the previous approval is marked superseded
```

### US-CBR-12 SSO and audit (E7) - Must, 8, REQ-CBR-014, 015
As a **user**, I want SSO and an audit trail, so that access is accountable.
```gherkin
Scenario: Group to role
  Given group strategy-analysts
  Then I get strategy_analyst
Scenario: Audit
  Then each request logs role, condition, sources and flags
```

### US-CBR-13 CI quality gate (E8) - Must, 5, REQ-CBR-016
As an **AI lead**, I want regressions to fail the build, so that extraction and retrieval stay reliable.
```gherkin
Scenario: Gate
  Given extraction checks < 8/8 on the contract documents or hit@6 < 0.95 or guardrail recall < 1.0
  Then the pipeline fails
```

### US-CBR-14 Deploy and rollback (E7) - Must, 5, REQ-CBR-017
As a **DevOps engineer**, I want canary deploys with rollback, so that releases are safe.
```gherkin
Scenario: Rollback
  Given 5xx exceeds 5% or grounding failures exceed 10%
  Then traffic returns to the previous version
```

### US-CBR-15 Feedback (E8) - Could, 2, REQ-CBR-018
As an **analyst**, I want to rate briefings and flag errors, so that quality improves.
```gherkin
Scenario: Error flag
  When I flag a bullet as wrong
  Then the bullet, sources and my comment are sent to the content steward queue
```

## Non-functional constraints
| ID | Requirement | Linked |
|---|---|---|
| NFR-CBR-1 | Briefing p95 <= 60 s (hosted model; prototype 492-600 s on CPU); cached < 1 s | REQ-CBR-019 |
| NFR-CBR-2 | 8 concurrent briefings | REQ-CBR-019 |
| NFR-CBR-3 | 99.5% availability (business hours) | REQ-CBR-017 |
| NFR-CBR-4 | TLS 1.2+, KMS, secrets manager; outbound allow-list | REQ-CBR-020 |
| NFR-CBR-5 | WCAG 2.1 AA; briefing export accessible | REQ-CBR-021 |
| NFR-CBR-6 | LLM spend alert USD 150/month | REQ-CBR-022 |

## Open questions
Is PDF/Word/slide export needed at MVP? Is a multi-condition comparison in scope?
