# 11 - Deployment, Operations, Phases G and H

## Deployment runbook (prod)
1. Change approved; eval + safety suites green; staging soak 24 h clean; EHS sign-off if safety behaviour changed.
2. Choose a window away from shift handovers; notify shift leads.
3. Snapshot OpenSearch; record prompt hash, model IDs, guardrail version, index fingerprint.
4. Run prod CD: canary 10% / 10 min, then 100%.
5. Smoke (automated and manual): one question per role; emergency banner appears first; unsafe request blocked; contractor limited to safety; `/metrics`; LLM-down degraded mode switch test (flag).
6. Watch dashboards 30 min; post release note.

### Go-live checklist
- [ ] EHS sign-off on safety red-team (0 unsafe outputs) and emergency drill
- [ ] Document-control sync verified: revisions current for 100 sampled documents
- [ ] Escalation contacts reviewed by each document owner
- [ ] SSO roles verified; contractor access tested
- [ ] Tablets tested on plant Wi-Fi in each area; MDM policy applied
- [ ] Pen test Critical/High closed
- [ ] Degraded mode (verbatim excerpts) tested
- [ ] On-call roster for 3 shifts; runbooks linked
- [ ] Cost alerts and Bedrock quota increase confirmed
- [ ] Supervisor training done (verify citations; permit-to-work unchanged)

## Release and rollback
Fortnightly; hotfix for guardrail/safety text. Rollback triggers: 5xx > 5% for 5 min; p95 > 30 s for 10 min; numeric-grounding failures > 10%; any answer to an emergency question without the banner; any unsafe-advice finding (Sev1). Rollback = previous ECS task set; prompt/model/guardrail = revert config tag; index = alias to previous snapshot.

## SLOs and alerts
| SLI | SLO | Alert |
|---|---|---|
| Availability (shift hours) | 99.9% | 2 failed probes / 3 min page |
| p95 `/ask` | <= 15 s | > 25 s warn; > 40 s page |
| Emergency banner latency | <= 1 s | > 2 s page |
| Emergency-without-banner probe | 0 | any page EHS + AI Lead |
| 5xx | < 1% | > 5% page |
| Unsafe-advice withheld events | trend | spike -> EHS review |
| Numeric-grounding failure rate | < 5% | > 10% warn; > 15% rollback |
| `no_answer` (escalation) rate | baseline | spike -> content gap review with owners |
| Source-access denials | baseline | spike -> Security |
| Index age (newest revision sync) | <= 2 h | > 6 h warn |
| Thumbs-down on safety | 0 unreviewed > 1 day | notify EHS |
| LLM cost/day | < USD 40 | > USD 60 |
Dashboards: service; safety and guardrails; content gaps and document freshness; AI quality; cost.

## Support (ITIL)
Incident: Sev1 (unsafe advice, emergency banner failure, outage on a shift): 15 min response, EHS notified; Sev2 1 h. Problem: review in 5 days; repeated `no_answer` topics become content problems with document owners. Change: Standard (document sync), Normal (prompt/model/role/router policy), Emergency (safety patch). On-call: 24x5/24x7 rota (A-05) with DevOps + AI lead; EHS on-call contact for safety incidents. Fallback for users when down: printed binders and phone tree remain authoritative.

## Phase G - governance
Compliance reviews at M2, M4, GA: safety-first policy intact, emergency handling deterministic, no execution paths to plant systems, source access enforced in code, audit complete. Deviations: ARB waiver + EHS concurrence.

## Phase H - change management
| Change | Request | Assessment | Approval |
|---|---|---|---|
| Prompt edit | PR + eval/LangSmith comparison | AI Lead; safety suite | AI Lead (EHS if safety source answers affected) |
| Model swap | RFC with eval incl. safety set | Eval + security | ARB + EHS |
| Router/guardrail rules, emergency text | PR to CODEOWNERS | Red-team rerun | EHS + AI Lead |
| Document revision | Document control | Automated sync + spot check | Document owner |
| Role/source mapping | Ticket | Security | Security + owners |
| Escalation contacts | Ticket | Owner | Document owner |
| New plant/language | Project | ADR | ARB |

## Drift and re-evaluation triggers
| Trigger | Action |
|---|---|
| Weekly golden-set drop > 2 pts or any safety regression | Investigate, freeze changes |
| Provider changes model behaviour/version | Full eval + safety suite before switching |
| Document set grows > 2x or new document type (diagrams, scans) | Re-run chunking/retrieval sweep; add to golden set |
| `no_answer` rate doubles for a source | Content gap review with owner |
| Rewrite rate rises | Vocabulary review (plant terms), add synonyms to rewrite prompt |
| Numeric-grounding failures rise | Prompt/model review; check table extraction |
| Quarterly | Refresh golden set with 20 real questions; 10% judge sample reviewed by owners/EHS |

## Open questions
Out-of-hours support model; whether deployment freezes apply during audits or turnarounds.
