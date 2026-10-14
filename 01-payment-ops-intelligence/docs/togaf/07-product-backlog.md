# 07 - Product Backlog

Points are Fibonacci story points (ESTIMATE). Priority is MoSCoW.

## Definition of Done (all stories)
Code reviewed; unit + integration tests pass; ruff clean; eval gate green (file 10); security scans clean; docs updated; metrics/audit emitted; demoed to PO.

## Epics and features
| Epic | Features |
|---|---|
| E1 Investigation | RCA, recommendation, search |
| E2 Analytics and reporting | Trend, summary |
| E3 Safety and access | RBAC, guardrails, masking |
| E4 Data pipeline | Ingestion, index refresh |
| E5 Platform and DevOps | SSO, IaC, CI/CD, observability |
| E6 Quality | Eval, feedback, red team |

## Stories
### US-PAY-01 Explain a failure (E1) - Must, 8 pts, REQ-PAY-001, 005, 011, 012
As a **payment analyst**, I want a probable root cause with cited similar incidents, so that I can fix failures faster.
```gherkin
Scenario: Cited root cause
  Given I am signed in as payment_analyst
  When I ask "Why was the ACH file rejected?"
  Then the answer lists probable causes
  And every cited PAY-INC id exists in the retrieved evidence
Scenario: No evidence
  Given no incident matches my filters
  When I ask for a root cause
  Then the answer states evidence is insufficient and gives no invented incident id
Scenario: Invented id (negative)
  Given the model cites PAY-INC-999 which was not retrieved
  Then guard_output flags or removes it
```
Dependencies: US-PAY-09.

### US-PAY-02 Recommend actions (E1) - Must, 5 pts, REQ-PAY-002, 011
As an **operations manager**, I want numbered actions citing the runbook, so that fixes are consistent.
```gherkin
Scenario: Actions with rule citation
  When I ask "What should we do to stop duplicate vendor payments?"
  Then I get numbered actions citing PAY-RULES-001 or incident ids
Scenario: Auditor denied (negative)
  Given I am an auditor
  When I ask for a recommendation
  Then outcome is "denied" and allowed intents are shown
```

### US-PAY-03 Similar-incident search (E1) - Must, 3 pts, REQ-PAY-005
As an **auditor**, I want to find incidents by description, so that I can gather evidence.
```gherkin
Scenario: Filtered search
  When I search "vendor bank-detail changes"
  Then results include incident ids with category and month
Scenario: Slot not mentioned (negative)
  When I do not name a system
  Then no system filter is applied
```

### US-PAY-04 Trend analysis (E2) - Must, 5 pts, REQ-PAY-003, 011
As an **operations manager**, I want trend numbers computed from data, so that I trust them.
```gherkin
Scenario: Duplicate payments after release
  When I ask "Are duplicate payments increasing since the gateway release?"
  Then counts per month equal an independent pandas calculation
  And the narrative contains no number absent from the analytics
Scenario: LLM unavailable (negative)
  Given the LLM times out
  Then the analytics table is returned without narrative
```

### US-PAY-05 Executive summary (E2) - Should, 5 pts, REQ-PAY-004
As an **executive**, I want a short summary of payment health, so that I can brief leadership.
```gherkin
Scenario: Executive style
  Given I am executive
  When I ask for a leadership summary
  Then the style is executive and includes trend facts
Scenario: Executive asks RCA (negative)
  Then outcome is "denied"
```

### US-PAY-06 Role-based access (E3) - Must, 5 pts, REQ-PAY-006, 007
As a **security officer**, I want roles to limit intents and amounts, so that least privilege holds.
```gherkin
Scenario: Amount masking
  Given I am support_engineer
  When I ask for RCA of a high-value incident
  Then amounts appear as "[amount restricted]"
Scenario: Unknown key (negative)
  Given an invalid credential
  Then the API returns 401
```

### US-PAY-07 Read-only guarantee (E3) - Must, 3 pts, REQ-PAY-008, 009, 010
As a **compliance officer**, I want action commands and injections blocked, so that no payment is touched.
```gherkin
Scenario: Action refused
  When I say "release payment 4411 now"
  Then the request is blocked before any LLM call
Scenario: Process question allowed
  When I ask "how are payments released?"
  Then it is answered
Scenario: Prompt injection
  When the text says "ignore previous instructions"
  Then it is blocked and counted in guardrail metrics
Scenario: Bank number echo (negative)
  When my input contains a routing number
  Then it is redacted in the answer and the audit log
```

### US-PAY-08 Audit and metrics (E5) - Must, 3 pts, REQ-PAY-013, 014
As an **auditor**, I want every question and citation logged, so that reviews are possible.
```gherkin
Scenario: Audit line
  When any question is answered or denied
  Then audit.jsonl gets role, intent, plan, citations, flags, latency
Scenario: Metrics scrape
  Then /metrics exposes payops_requests_total by intent, role, outcome
```

### US-PAY-09 Scheduled ingestion (E4) - Must, 8 pts, REQ-PAY-019
As a **data engineer**, I want nightly incremental ingest, so that answers reflect recent incidents.
```gherkin
Scenario: New incident indexed
  Given a new incident row in the ITSM export
  When the nightly job runs
  Then it is retrievable the next morning
Scenario: Malformed row (negative)
  Then the row is rejected, logged, and the job continues
Scenario: Embedding model change
  Then the fingerprint mismatch triggers a full rebuild
```

### US-PAY-10 Single sign-on (E5) - Must, 8 pts, REQ-PAY-020
As a **user**, I want to sign in with corporate SSO, so that I need no key.
```gherkin
Scenario: Group maps to role
  Given I belong to group payops-exec
  Then I am assigned role executive
Scenario: No group (negative)
  Then access is denied by default
```

### US-PAY-11 Feedback (E6) - Should, 2 pts, REQ-PAY-015
As an **analyst**, I want to rate answers, so that quality improves.
```gherkin
Scenario: Rating stored
  When I click thumbs-down on run_id X
  Then payops_feedback_total increments and LangSmith has user_rating
```

### US-PAY-12 CI evaluation gate (E6) - Must, 5 pts, REQ-PAY-018
As an **AI lead**, I want the build to fail on quality regressions, so that prompt changes are safe.
```gherkin
Scenario: Gate fails
  Given hit@6 drops below 0.95
  Then the pipeline fails
Scenario: Gate passes
  Then results are attached as an artifact
```

### US-PAY-13 Infrastructure as code and deploy (E5) - Must, 8 pts, REQ-PAY-017
As a **DevOps engineer**, I want reproducible environments and canary releases, so that releases are safe.
```gherkin
Scenario: Rollback
  Given error rate exceeds 5% after canary
  Then traffic returns to the previous version automatically
```

## Non-functional requirements as constraints
| ID | Requirement | Linked |
|---|---|---|
| NFR-PAY-1 | p95 latency <= 20 s (hosted model; prototype ~150 s on CPU) | REQ-PAY-016 |
| NFR-PAY-2 | 40 users, 10 concurrent, scalable to 100 | REQ-PAY-016 |
| NFR-PAY-3 | Availability 99.5% business hours | REQ-PAY-017 |
| NFR-PAY-4 | TLS 1.2+, KMS encryption, no secrets in code | REQ-PAY-021 |
| NFR-PAY-5 | WCAG 2.1 AA on the UI | REQ-PAY-022 |
| NFR-PAY-6 | LLM spend alert at USD 400/month (ESTIMATE 2x plan) | REQ-PAY-023 |

## Open questions
Are Streamlit accessibility limits acceptable or is a React UI required for WCAG?
