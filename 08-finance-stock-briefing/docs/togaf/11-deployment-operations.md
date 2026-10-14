# 11 - Deployment, Operations, Phases G and H

## Deployment runbook (prod)
1. Change record approved; gates, red-team and archive drill attached; Compliance approval if lexicon/prompt/disclaimer changed.
2. Schedule outside 07:00-18:00 trading hours; announce to Advisory.
3. Snapshot OpenSearch; record prompt versions, lexicon version, model IDs, parser version, index alias.
4. Run prod CD: canary 10% / 10 min then 100%.
5. Smoke: quote; synthetic briefing; live briefing for a mega-cap; refusal ("should my client buy ..."); MNPI refusal; advisor gets 403 on `/audit`; archive object present and immutable; vendor and EDGAR connectivity.
6. Pre-warm top 500 tickers (index) before 06:30; watch dashboards at market open.

### Go-live checklist
- [ ] Compliance sign-off: lexicon, refusal wording, disclaimer, supervisory procedures updated
- [ ] Market-data licence and display/caching terms confirmed by Legal; entitlements tested
- [ ] EDGAR fair-access verified (User-Agent, shared rate limiter)
- [ ] Archive (Object Lock compliance mode) verified; restore drill passed; retention set
- [ ] Surveillance export working (or accepted exception)
- [ ] Pen test Critical/High closed; role scoping and `/audit` tests passed
- [ ] Red-team for advice/MNPI >= 99% blocked; output filter results reviewed
- [ ] Parser acceptance on 50 real filings >= 98%
- [ ] SSO groups verified; trainee/associate scope tested
- [ ] On-call, alerts, runbooks; cost and quota alerts
- [ ] Advisor training: verify citations, no client distribution unless approved

## Release and rollback
Fortnightly releases outside trading hours; hotfix for lexicon or filter issues. Rollback triggers: 5xx > 5% for 5 min; p95 > 60 s for 10 min; filter-collapse signal; any advice-language incident found in production (Sev1); archive write failure; wrong-company data. Rollback = previous ECS task set; prompt/lexicon/model = revert tag with change record; index = previous alias.

## SLOs and alerts
| SLI | SLO | Alert |
|---|---|---|
| Availability (trading hours) | 99.9% | 2 failed probes / 3 min page |
| Quote p95 | <= 1 s | > 2 s warn |
| Briefing p95 uncached | <= 45 s | > 60 s warn; > 90 s page |
| Cached briefing p95 | <= 1 s | > 3 s |
| 5xx | < 1% | > 5% page |
| Archive write success | 100% | any failure page |
| Advice leaks found in sampling | 0 | any -> Sev1 |
| Removed-statement rate | baseline +/- 3 sigma | drop to 0 for 1 h or spike -> AI Lead + Compliance |
| Refusal rate per user | baseline | >= 5 refusals/day/user -> Compliance |
| Numeric-grounding failures shown | < 2% | > 5% |
| Unattributed bullets | <= 5% | > 10% |
| Data freshness (quote as-of age) | <= 15 min delayed feed | > 30 min warn |
| EDGAR 429/403 | 0 | any warn |
| LLM cost/day | < USD 8 | > USD 15 |
Dashboards: service and trading-hours load; compliance (refusals, removals, audit queries); data feeds; AI quality; cost.

## Support (ITIL)
Incident: Sev1 (advice-language reaching clients, archive failure, wrong-company data, outage in trading hours): 15 min response, Compliance notified; Sev2 1 h. Problem: weekly review of removed statements and refusal patterns (lexicon improvements); monthly parser failure review. Change: Standard (data refresh, cache TTL), Normal (prompt/model/lexicon/role/vendor changes), Emergency (filter patch). On-call: market-hours rota (A-05) plus Compliance contact for Sev1.

## Phase G - implementation governance
Reviews at M3, M4 and GA: compliance filter always on; archive-before-display; licensed data only; ticker scope; role scoping; no client data in prompts (MVP); EDGAR fair access. Deviations need ARB waiver plus CCO concurrence.

## Phase H - change management
| Change | Request | Assessment | Approval |
|---|---|---|---|
| Prompt edit | PR + LangSmith comparison + red-team | AI Lead; Compliance sample review | AI Lead + Compliance |
| Lexicon / disclaimer / refusal catalog | Ticket by Compliance | Red-team rerun, false-positive review | Compliance (CCO) |
| Model swap | RFC with quality, cost, tone, advice-leak tests | Eval + security | ARB + Compliance |
| Market-data vendor change | Procurement | Legal terms, adapter tests | Legal + ARB |
| New data source (e.g. transcripts) | Epic | Licence, accuracy, advice-risk review | Legal + Compliance |
| Role change | Ticket | Security | Security + Compliance |
| Architecture change | ADR | ARB | ARB |

## Drift and re-evaluation triggers
| Trigger | Action |
|---|---|
| Weekly golden-set drop > 2 pts or any advice leak | Investigate; freeze changes |
| Filing format change or parser failure rate > 2% | Fix parser; re-run 50-filing set; re-parse cache |
| Model/provider change | Full eval + red-team + tone check before switching |
| Removed-statement categories shift | Update lexicon/classifier with Compliance |
| New regulatory guidance on AI communications | Compliance review of controls; update tests |
| Vendor/EDGAR schema change | Adapter update; contract tests |
| Market-regime events (earnings season, volatility) | Capacity check; pre-warm; stricter staleness warnings |
| Quarterly | Refresh adversarial sets; 10% judge sample review; fairness across cap sizes and sectors |

## Open questions
Out-of-hours support; whether supervisory sampling of AI briefings is a new procedure or part of existing communications review.
