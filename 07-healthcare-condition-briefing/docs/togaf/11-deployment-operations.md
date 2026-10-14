# 11 - Deployment, Operations, Phases G and H

## Deployment runbook (prod)
1. Change record approved; CI/eval gates green; staging checks done; Legal/Clinical approvals if flagged.
2. Snapshot OpenSearch; record prompt versions, model IDs, extraction version, index alias.
3. If extraction rules changed: run re-extraction on all documents into a new index, run the contract tests and the 30-document acceptance set, then switch alias.
4. Run prod CD: canary 10% / 10 min, then 100%.
5. Smoke: cached briefing; one new synthetic briefing; live-mode briefing; follow-up; consultant clearance probe (0 internal chunks); patient-advice refusal; `/metrics`.
6. Watch dashboards 30 min; publish release note to analysts.

### Go-live checklist
- [ ] Rights register complete for all indexed sources; Legal sign-off on AI use and quote limits
- [ ] Clinical Advisor sign-off on templates and a 10-briefing sample
- [ ] Extraction acceptance >= 95% on 30 real documents; flagged captions reviewed
- [ ] SSO roles verified; consultant clearance tested end to end
- [ ] Pen test Critical/High closed; outbound allow-list verified
- [ ] Live-API contract test green; fallback behaviour tested
- [ ] Cost alerts configured; Bedrock quotas OK
- [ ] Support runbooks, training and "how to review a briefing" guide delivered
- [ ] Disclaimer text approved

## Release and rollback
Monthly releases; content releases (documents) any time through the ingestion gate. Rollback triggers: 5xx > 5% for 5 min; p95 briefing > 120 s for 10 min; grounding failures > 10%; any internal chunk served to a public role (Sev1); extraction regression found after switch. Rollback = previous ECS task set; prompts/models = revert config tag; index = previous alias; briefing cache flushed for affected conditions.

## SLOs and alerts
| SLI | SLO | Alert |
|---|---|---|
| Availability | 99.5% business hours | 2 failed probes / 5 min |
| Briefing p95 (uncached) | <= 60 s | > 90 s warn; > 120 s page |
| Cached briefing p95 | <= 1 s | > 3 s |
| 5xx | < 1% | > 5% page |
| Internal chunks to public | 0 | any -> Sev1 + rollback |
| Grounding failure rate | < 5% | > 10% |
| Unattributed bullets | <= 5% | > 10% weekly |
| Live-API error rate | < 2% | > 10% warn |
| Content freshness (per condition) | newest guideline <= 90 days since last check | stale -> steward |
| Extraction quarantine backlog | 0 > 7 days | any |
| Thumbs-down / error flags | < 10% | > 20% weekly |
| LLM cost/day | < USD 3 | > USD 8 |
Dashboards: service; content freshness and quarantine; AI quality (grounding, unattributed, flags); access (clearance probes); cost.

## Support (ITIL)
Incident: Sev1 (internal content exposed to public role, clinical-advice breach, outage during a board prep): 30 min response; Sev2 4 h. Problem: recurring extraction failures per publisher template grouped as problems; content gaps reviewed monthly. Change: Standard (content refresh), Normal (prompt/model/role/extraction rules/new source), Emergency (guardrail fix). On-call: business hours (A-06) with a named steward for content issues.

## Phase G - implementation governance
Reviews at M3, M4 and GA: clearance-before-retrieval honoured; rights register gating; disclaimers; no patient-specific features; audit complete; outbound network allow-list. Deviations need ARB waiver and Legal concurrence for licensing issues.

## Phase H - change management
| Change | Request | Assessment | Approval |
|---|---|---|---|
| Prompt edit | PR + LangSmith comparison | AI Lead, eval gate | AI Lead; Clinical Advisor if standard-of-care wording |
| Model swap | RFC (quality, cost, latency, licence terms for hosted processing) | Eval + sample review | ARB + Legal |
| New content source | Request | Licence check, extraction acceptance, classification | Legal + content steward |
| Extraction rule change | PR | Contract tests + acceptance set + re-extraction impact | AI Lead + QA |
| Role/clearance change | Ticket | Security | Security |
| Live-data configuration (phases, statuses) | Ticket | Analyst review of outputs | Product Owner |
| Architecture change | ADR | ARB | ARB |

## Drift and re-evaluation triggers
| Trigger | Action |
|---|---|
| Weekly golden-set drop > 2 pts | Investigate; freeze changes |
| New publisher layout or failed extraction check | Add to acceptance set; update loader; re-run affected documents |
| Guideline revision published | Re-ingest; invalidate briefing cache; notify analysts with a diff summary |
| ClinicalTrials.gov schema/API change | Adapter update; contract test |
| Model/provider version change | Full eval + clinical sample review |
| Caption verification flags rise | Vision model/prompt review |
| Unattributed bullet rate rises | Retrieval/prompt tuning |
| Quarterly | Refresh golden set; 10% judge sample review; clinical advisor re-rates 10 briefings; sponsor classification audit |

## Open questions
Who monitors guideline updates (steward vs automated feed)? SLA for clinical review turnaround.
