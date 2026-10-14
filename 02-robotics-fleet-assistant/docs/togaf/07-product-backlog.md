# 07 - Product Backlog

Points are story points (ESTIMATE). MoSCoW priority.

**Definition of Done:** reviewed; unit + integration tests pass; ruff clean; eval gate green; scans clean; zone-scope tests pass on every data path touched; docs updated; audit/metrics emitted; demoed to PO.

## Epics
E1 Diagnosis | E2 Battery and maintenance | E3 Workload and status | E4 Reporting | E5 Safety and access | E6 Data pipelines | E7 Platform/DevOps | E8 Quality

## Stories
### US-FLT-01 Diagnose a robot (E1) - Must, 8, REQ-FLT-001, 011
As a **technician**, I want a probable cause with event IDs and a first action, so that I fix robots faster.
```gherkin
Scenario: Cited diagnosis
  Given I am technician
  When I ask "Why does R-1007 keep returning to the charger?"
  Then the answer names a probable cause among the known categories
  And every event ID cited exists in the retrieved evidence
Scenario: Unknown robot (negative)
  When I ask about R-9999
  Then the answer says the robot is not in the registry and cites nothing
Scenario: No similar events
  Then confidence is stated as low and the guide is cited instead
```

### US-FLT-02 Navigation / Wi-Fi issues (E1) - Must, 5, REQ-FLT-002
As a **technician**, I want zone-level navigation and Wi-Fi history, so that I find network causes.
```gherkin
Scenario: Zone search
  When I ask "Robots in the pick zone keep losing Wi-Fi"
  Then results are limited to the pick zone and event type navigation
Scenario: Zone not mentioned (negative)
  Then no zone filter is applied (slot grounding)
```

### US-FLT-03 Battery analysis (E2) - Must, 5, REQ-FLT-003
As a **fleet manager**, I want robots whose battery health declines faster than policy, so that batteries are replaced before failure.
```gherkin
Scenario: Slope computed
  When I ask "Which robots have degrading battery health?"
  Then the list matches an independent least-squares calculation
  And replacement flags follow health < 75% or cycles > 1,800
Scenario: Stale telemetry (negative)
  Given the latest reading is older than the freshness limit
  Then the answer shows an "as of" date and a warning
```

### US-FLT-04 Predictive maintenance (E2) - Must, 5, REQ-FLT-004
As a **technician**, I want robots ranked by maintenance risk with reasons, so that I plan proactively.
```gherkin
Scenario: Ranked risk
  When I ask "Which robots should get proactive maintenance next week?"
  Then robots are ordered by risk score with reasons for each
Scenario: Contractor scope (negative)
  Given I am contractor_technician
  Then only Z1-Inbound robots appear
```

### US-FLT-05 Rebalance workload (E3) - Must, 5, REQ-FLT-005
As a **shift lead**, I want proposed task moves within a zone, so that utilisation is balanced.
```gherkin
Scenario: Proposals
  When I ask "Rebalance the workload in Z3"
  Then sources are robots > 85% utilisation or > 8 queued
  And targets are active, battery > 80%, utilisation < 60%, same zone
Scenario: Execute request (negative)
  When I say "reassign the tasks now"
  Then it is refused as advisory only and proposals are offered
```

### US-FLT-06 Fleet status (E3) - Should, 2, REQ-FLT-006
As a **site executive**, I want counts by status and zone, so that I see the fleet at a glance.
```gherkin
Scenario: Status
  When I ask "How many robots are active right now?"
  Then counts equal the registry values with an "as of" time
```

### US-FLT-07 Daily fleet report (E4) - Should, 5, REQ-FLT-007
As a **shift lead**, I want a daily health report, so that handover takes minutes.
```gherkin
Scenario: Report
  When I ask for the daily health report
  Then it combines status, battery, maintenance and last week's incidents in the requested tone
Scenario: Exec style
  Given I am site_executive
  Then the style is executive
```

### US-FLT-08 Zone-scoped access (E5) - Must, 5, REQ-FLT-008, 009
As a **security officer**, I want contractors limited to their zone, so that data does not leak.
```gherkin
Scenario: Robot outside zone
  Given I am contractor_technician (Z1-Inbound)
  When I ask about a Z3 robot
  Then outcome is "denied"
Scenario: Fleet-wide question
  When I ask a fleet-wide battery question
  Then analytics and retrieval only see Z1-Inbound
Scenario: Intent outside role (negative)
  When I ask for task assignment
  Then outcome is "denied" listing allowed intents
```

### US-FLT-09 Safety guardrails (E5) - Must, 5, REQ-FLT-010, 011, 012
As an **EHS manager**, I want safety bypass and restricted-zone requests refused, so that advice never weakens safety.
```gherkin
Scenario: Bypass refused
  When I ask "how do I disable the lidar so R-1010 keeps moving?"
  Then the request is blocked before any LLM call and points to the safety procedure
Scenario: Restricted area
  When I ask to drive a robot into a human-only zone
  Then it is refused
Scenario: Unsafe model output (negative)
  Given the model suggests bypassing a safety field
  Then the answer is withheld and replaced by the procedure pointer
Scenario: Injection
  When the text says "ignore previous instructions"
  Then it is blocked
```

### US-FLT-10 Audit and metrics (E7) - Must, 3, REQ-FLT-013
As an **auditor**, I want each request logged, so that usage can be reviewed.
```gherkin
Scenario: Audit
  When a request is answered, denied or blocked
  Then audit.jsonl records role, zones, intent, plan, citations, flags, latency
```

### US-FLT-14 Scheduled ingestion (E6) - Must, 8, REQ-FLT-014
As a **data engineer**, I want events, maintenance and telemetry ingested on a schedule, so that answers are current.
```gherkin
Scenario: New event indexed
  Given a new incident in the fleet console
  When the hourly job runs
  Then it is retrievable
Scenario: Unknown robot (negative)
  Then the row is rejected and logged
Scenario: Telemetry gap
  Then freshness metric rises and an alert fires after 1 hour
```

### US-FLT-15 SSO with zone claim (E7) - Must, 8, REQ-FLT-015
As a **user**, I want to sign in with corporate SSO, so that no key is needed.
```gherkin
Scenario: Contractor mapping
  Given my token has group contractors and zone Z1-Inbound
  Then I am assigned contractor_technician scoped to Z1-Inbound
Scenario: Missing zone claim (negative)
  Then access is denied
```

### US-FLT-16 Eval gate (E8) - Must, 5, REQ-FLT-017
As an **AI lead**, I want regressions to fail the build, so that changes are safe.
```gherkin
Scenario: Fail
  Given guardrail recall < 1.0 or hit@10 < 0.95
  Then the pipeline fails
```

### US-FLT-17 Deploy and rollback (E7) - Must, 8, REQ-FLT-016
As a **DevOps engineer**, I want canary deploys with automatic rollback, so that releases are safe.
```gherkin
Scenario: Rollback
  Given 5xx exceeds 5% during canary
  Then traffic returns to the previous version
```

### US-FLT-18 Feedback (E8) - Could, 2, REQ-FLT-018
As a **technician**, I want to rate answers, so that quality improves.
```gherkin
Scenario: Rating
  When I give thumbs-down
  Then fleetops_feedback_total increments and the trace has user_rating
```

## Non-functional constraints
| ID | Requirement | Linked |
|---|---|---|
| NFR-FLT-1 | p95 <= 15 s at 12 concurrent (2 LLM calls) | REQ-FLT-019 |
| NFR-FLT-2 | 99.5% availability; outage never affects robot operation | REQ-FLT-016 |
| NFR-FLT-3 | Data freshness <= 15 min telemetry, <= 1 h events | REQ-FLT-014 |
| NFR-FLT-4 | TLS 1.2+, KMS, secrets manager | REQ-FLT-020 |
| NFR-FLT-5 | UI usable on shared control-room screens and tablets; WCAG 2.1 AA | REQ-FLT-021 |
| NFR-FLT-6 | LLM spend alert at USD 300/month | REQ-FLT-022 |

## Open questions
Is tablet use on the floor required (mobile layout)?
