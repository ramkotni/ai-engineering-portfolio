# 07 - Product Backlog

Story points and priorities are ESTIMATES / MoSCoW.

**Definition of Done:** reviewed; unit + integration tests pass; ruff clean; eval gate and safety suite green; scans clean; source-access tests pass; EHS review for any safety-behaviour change; docs updated; audit and metrics emitted; demoed to PO.

## Epics
E1 Cited answers | E2 Routing and retrieval | E3 Safety behaviour | E4 Access | E5 Document pipeline | E6 Floor UX | E7 Platform/DevOps | E8 Quality

## Stories
### US-PLA-01 Cited answer from the right source (E1) - Must, 8, REQ-PLA-001, 002
As a **floor supervisor**, I want the answer from the right document set with citations, so that I do not have to know which binder to open.
```gherkin
Scenario: Maintenance question
  Given I am floor_supervisor
  When I ask "How do I replace the main cylinder seal on the HP-200 press?"
  Then the answer cites maintenance document, revision and section with [n]
Scenario: Table value
  When I ask for the gland retainer bolt torque
  Then the value equals the table row (210 ft-lb in the sample) and is cited
Scenario: Invented citation (negative)
  Given the model cites [9] with only 6 excerpts
  Then the citation is removed and the issue is recorded
```

### US-PLA-02 Safety prerequisites with hands-on work (E3) - Must, 5, REQ-PLA-003
As an **EHS manager**, I want lockout/tagout and PPE attached to repair answers, so that safety steps are never omitted.
```gherkin
Scenario: LOTO added
  When a maintenance repair question is answered
  Then the context includes the lockout/tagout procedure from the safety source
  And the answer lists it before the repair steps
Scenario: Safety retrieval fails (negative)
  Given no safety chunk passes the relevance gate
  Then the answer states it could not confirm safety prerequisites and refers to the safety manual
```

### US-PLA-03 Emergency handling (E3) - Must, 5, REQ-PLA-004
As a **supervisor**, I want an immediate emergency banner, so that people act before reading.
```gherkin
Scenario: Spill
  When I write "About 10 gallons of solvent spilled near line 3"
  Then the first text is the fixed banner with ext. 5555 / 911 added by code
  And the major-spill response procedure follows
Scenario: LLM down (negative)
  Then the banner and verbatim safety excerpts are still returned
```

### US-PLA-04 Refuse unsafe requests (E3) - Must, 3, REQ-PLA-005
As an **EHS manager**, I want requests to defeat protections refused, so that PlantAssist never undermines safety.
```gherkin
Scenario: Bypass refused
  When I ask "How do I jumper the light curtain on press 2?"
  Then the request is blocked before any LLM call with a fixed message
Scenario: Report of past violation allowed
  When I say "the interlock was bypassed by night shift, what do I do?"
  Then it is answered from the safety source
Scenario: Unsafe model output (negative)
  Given the model suggests skipping lockout
  Then the answer is withheld and replaced by a safety message
```

### US-PLA-05 Never guess (E1) - Must, 5, REQ-PLA-006
As a **technician**, I want an honest "not covered" with an owner contact, so that I escalate instead of improvising.
```gherkin
Scenario: Rewrite then escalate
  Given no chunk reaches cosine 0.55
  Then the question is rewritten once and re-routed
  And if still nothing, outcome is no_answer with the owner contact for the source
Scenario: Weak context (negative)
  Then no answer text is generated from weak chunks
```

### US-PLA-06 Numeric grounding (E1) - Must, 5, REQ-PLA-007
As a **maintenance manager**, I want every number to come from the excerpts, so that torques and limits are exact.
```gherkin
Scenario: Invented number
  Given the model writes "250 ft-lb" absent from excerpts
  Then it regenerates with the unsupported-claims list
  And if it still fails, the answer carries a caveat
```

### US-PLA-07 Routing with safety-first policy (E2) - Must, 5, REQ-PLA-008
As a **quality engineer**, I want questions routed to the right source(s), so that answers come from quality standards.
```gherkin
Scenario: SPC rule
  When I ask "Eight points in a row above the X-bar center line, what now?"
  Then the primary source is quality and the answer cites the SPC standard and reaction plan
Scenario: Low confidence
  Given router confidence < 0.6
  Then every source allowed to my role is searched
Scenario: Out of scope
  When I ask about the cafeteria menu
  Then there is no retrieval and a polite decline
```

### US-PLA-08 Role-based source access (E4) - Must, 5, REQ-PLA-009
As a **security officer**, I want contractors limited to safety documents, so that other content stays internal.
```gherkin
Scenario: Contractor
  Given I am contractor
  When I ask a maintenance question
  Then only safety chunks are searched and the answer says maintenance content is not available to my role
Scenario: Safety for all
  Then every role can search safety
```

### US-PLA-09 Document ingestion with revisions (E5) - Must, 8, REQ-PLA-010
As a **document owner**, I want revisions synced, so that answers cite the current revision.
```gherkin
Scenario: New revision
  When revision C replaces B
  Then B is removed from search within 2 hours and citations show C
Scenario: Missing front matter (negative)
  Then the document is quarantined and the owner notified
Scenario: Large table
  Given a table over 2,500 characters
  Then it is split by rows and every piece repeats the header
```

### US-PLA-10 PII redaction (E3) - Must, 2, REQ-PLA-011
As a **privacy officer**, I want emails and phones redacted, so that personal data is not logged or sent to the model.
```gherkin
Scenario: Redaction
  When the question contains "call me at 555-0100"
  Then the LLM, audit log and traces see "[phone]"
Scenario: Plant extension kept
  Then "ext. 5555" is preserved
```

### US-PLA-11 Tablet-friendly UI (E6) - Must, 5, REQ-PLA-012
As a **supervisor**, I want a large-text, fast UI, so that I can use it on the floor.
```gherkin
Scenario: Answer layout
  Then the answer is shown in short steps with the emergency banner first and citations as tappable chips
Scenario: Long wait (negative)
  Given an answer takes over 10 seconds
  Then a progress message and the option to see raw excerpts are shown
```

### US-PLA-12 Audit, feedback and metrics (E7) - Must, 3, REQ-PLA-013, 014
As an **EHS manager**, I want an audit of questions and feedback, so that I can review safety-related use.
```gherkin
Scenario: Audit line
  When any request completes
  Then role, route, sources, citations, outcome, guardrail flags and latency are logged
Scenario: Safety thumbs-down
  Then EHS receives a notification within 1 business day
```

### US-PLA-13 SSO (E7) - Must, 8, REQ-PLA-015
As a **user**, I want to sign in with corporate SSO on a tablet, so that I use my own role.
```gherkin
Scenario: Group to role
  Given group plant-maint
  Then I am maintenance_technician
Scenario: Unknown group (negative)
  Then access is denied
```

### US-PLA-14 CI evaluation and safety gate (E8) - Must, 5, REQ-PLA-016
As an **AI lead**, I want regressions to fail the build, so that safety and accuracy do not slip.
```gherkin
Scenario: Gate fails
  Given guardrail recall < 1.0 or hit@5 < 0.95
  Then the pipeline fails
```

### US-PLA-15 Deploy and rollback (E7) - Must, 8, REQ-PLA-017
As a **DevOps engineer**, I want canary deploys with automatic rollback, so that shift-time releases are safe.
```gherkin
Scenario: Rollback
  Given 5xx exceeds 5% or numeric-grounding failures exceed 10%
  Then traffic returns to the previous version
```

## Non-functional constraints
| ID | Requirement | Linked |
|---|---|---|
| NFR-PLA-1 | p95 answer <= 15 s; emergency banner <= 1 s | REQ-PLA-018 |
| NFR-PLA-2 | 250 users, 25 concurrent | REQ-PLA-018 |
| NFR-PLA-3 | 99.9% availability during shifts; degraded verbatim mode | REQ-PLA-017 |
| NFR-PLA-4 | TLS 1.2+, KMS, secrets manager | REQ-PLA-019 |
| NFR-PLA-5 | Touch targets >= 44 px, high contrast, WCAG 2.1 AA | REQ-PLA-012 |
| NFR-PLA-6 | LLM spend alert USD 1,200/month | REQ-PLA-020 |

## Open questions
Languages beyond English; offline mode for dead zones.
