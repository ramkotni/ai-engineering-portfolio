# 11 - Deployment, Operations, Phases G and H

## Deployment runbook (prod)
1. Change record approved; CI gates, red-team and staging load/accessibility results attached; Compliance approval if wording changed.
2. Verify Bedrock quotas, guardrail version, KB sync status, claims-API health.
3. Deploy new AgentCore runtime version; endpoint alias at 5% (15 min) -> 25% (15 min) -> 100%.
4. Smoke and canary: policy question; own-claim question; other-member probe (must be identical to not-found); injection (blocked); handoff test; `/health` and `/ping`.
5. Monitor alarms 60 min; announce to member services.
6. Roll forward only after leakage probe and groundedness stay green for 24 h.

### Go-live checklist
- [ ] Privacy, Security and Compliance sign-off (HIPAA risk assessment updated)
- [ ] BAA covers each used service; Bedrock invocation logging configured; zero-retention terms confirmed
- [ ] Pen test Critical/High closed; authorization/enumeration tests passed
- [ ] Red-team 100% must-pass; Bedrock Guardrails active; known-gap cases >= 95%
- [ ] Denial templates and disclosures approved; reading level checked
- [ ] Identity from JWT verified; request-body `member_id` ignored
- [ ] Handoff path live in contact center; hours/phone fallback tested
- [ ] LangSmith configured with hidden inputs/outputs or self-hosted; PHI-in-trace test passed
- [ ] DR drill and Bedrock-outage fallback tested
- [ ] Member communications and customer-service training ready; support runbooks live
- [ ] Cost alerts, quotas, rate limits set

## Release and rollback
Bi-weekly for application and prompts; policy documents any time via ingest (content release). Rollback triggers: any confirmed cross-member disclosure (Sev1, immediate), 5xx > 2% for 5 min, p95 > 20 s for 10 min, groundedness < 90% for 30 min, guardrail bypass finding, handoff failure rate > 5%. Rollback = previous AgentCore runtime version (alias flip, < 5 min); guardrail/prompt = revert tag; KB = previous data-source version.

## SLOs and alerts
| SLI | SLO | Alert |
|---|---|---|
| Availability | 99.9% | Probe failures 2/3 min page |
| p95 turn latency | <= 12 s | > 20 s page |
| 5xx / tool errors | < 1% | > 2% page |
| **Cross-member disclosure** | 0 | any -> Sev1, auto rollback, Privacy notified |
| Leakage canary | pass every minute | 2 fails page |
| Grounded rate | >= 95% | < 90% 30 min page AI Lead |
| Escalation (handoff) rate | baseline (target 25-35%) | +/- 10 pts review |
| Guardrail block rate | baseline +/- 3 sigma | spike -> Security |
| `authz_denied` per member/hour | baseline | > 5 per member -> Security review |
| CSAT | >= 4.0 | < 3.7 weekly |
| Handoff delivery success | >= 99% | < 97% |
| LLM cost per conversation | <= USD 0.20 | > USD 0.30 |
| Bedrock throttling | < 0.5% | > 2% warn |
Dashboards: service health; privacy and security; AI quality and groundedness; business (containment, CSAT, handoff); cost.

## Support (ITIL)
Incident: Sev1 (PHI exposure, cross-member disclosure, outage, unsafe guidance): 15 min response, Privacy Officer paged, breach assessment per HIPAA timeline; Sev2 1 h; Sev3 next business day. Problem: weekly review of top failure themes (retrieval misses, critic rejections, handoff reasons); monthly policy-content gap review with benefits team. Change: Standard (document ingest, template typo fix with approval), Normal (prompt/model/guardrail/intent changes), Emergency (guardrail patch). On-call: 24x7 rota for platform and AI lead; privacy on-call for Sev1. Run book entries for Bedrock outage, claims API outage, quota throttling and KB sync failure.

## Phase G - implementation governance
Architecture and compliance reviews at M2, M3 (pre-sign-off) and GA: identity from token only; authorization in code on every tool; minimum-necessary PHI; no PHI in non-prod; audit complete; traces PHI-safe; HIPAA-eligible services only. Deviations require ARB waiver plus Privacy/Compliance concurrence.

## Phase H - change management
| Change | Request | Assessment | Approval |
|---|---|---|---|
| Prompt edit | PR + LangSmith experiment + eval | AI Lead; red-team subset | AI Lead; Compliance if member-facing wording |
| Model swap / version | RFC with cost, latency, quality, leakage tests | Eval + security | ARB + Privacy |
| Guardrail policy | PR to CODEOWNERS | Red-team incl. known gaps | Security + Compliance |
| Denial/appeal templates | Ticket by Compliance | Wording review, sample outputs | Compliance |
| Intent/tool addition (e.g. appeal drafting) | Epic with threat model | Authorization design, red-team | ARB + Privacy + Compliance |
| Plan documents | Content owner | Ingest report, spot check | Content owner |
| Architecture change | ADR | ARB | ARB |

## Drift and re-evaluation triggers
| Trigger | Action |
|---|---|
| Weekly golden-set metric drop > 2 pts | Investigate; freeze changes |
| Plan-year rollover or new plan/benefit design | Re-ingest; re-run golden set with new-year questions; compliance sample |
| New denial codes appear in claims data | Add templates and tests before enabling explanation for the code |
| Provider model/version change or deprecation | Full eval and red-team before switching |
| Retrieval relevance scores shift (embedding change) | Re-calibrate `RELEVANCE_THRESHOLD` with the eval report |
| Handoff reasons shift (more "not documented") | Content gap review |
| New attack patterns in blocked logs | Extend red-team set; update guardrail |
| Quarterly | Refresh golden set with 30 real (de-identified) questions; 10% judge sample reviewed; fairness comparison across plans |

## Open questions
Breach notification workflow ownership; out-of-hours handoff availability; retention for transcripts.
