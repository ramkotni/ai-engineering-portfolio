# Robotics Fleet Assistant - Design Document

Portfolio prototype on synthetic data. Companion: [README](../README.md), [slides](Robotics_Fleet_Assistant.pptx).

## 1. Problem and goals
A warehouse runs a fleet of mobile robots across four zones. Failures (battery, sensor, motor, scanner, Wi-Fi,
navigation) look alike on the console, maintenance is calendar-based, workload is uneven, and daily reports
are compiled by hand. The assistant must diagnose, predict, rebalance and summarise - safely and with numbers
that come from data.

## 2. Architecture
```
CLI / FastAPI :8002 / Streamlit :8502 -> FleetAssistant.ask(question, role)
  -> LangGraph supervisor: guard_input -> intent_agent -> authorize (intents + zone scope) -> supervisor <-> agents
     -> compose -> guard_output
  -> ChromaDB (events: incidents + maintenance logs | knowledge: troubleshooting guide)
  -> pandas / numpy fleet analytics (status, battery slope, risk score, rebalancing)
  -> Ollama llama3.2 + nomic-embed-text; LangSmith; /metrics; audit log
```

### Why multi-agent
Seven workflows need different tools: semantic search (Fleet Search), causal diagnosis (Diagnostics), time-series
analysis (Battery), risk scoring + policy (Predictive Maintenance), optimisation (Task Optimization), aggregation
(Fleet Status) and audience-aware reporting (Ops Summary). A supervisor runs a fixed plan per intent:

| Intent | Plan |
|---|---|
| robot_diagnostics | Fleet Search -> Diagnostics |
| navigation_issues | Fleet Search (navigation / Wi-Fi filter) -> Diagnostics |
| battery_analysis | Battery |
| predictive_maintenance | Battery -> Maintenance |
| task_assignment | Fleet Status -> Task Optimization |
| fleet_status | Fleet Status |
| operational_summary | Fleet Status -> Battery -> Maintenance -> Summary |

**Only the final agent calls the LLM for narrative**; earlier agents return data. A daily report therefore costs
2 LLM calls (intent + summary) instead of 5.

## 3. Agents and deterministic analytics
| Agent | How | LLM |
|---|---|---|
| Intent | structured output: intent, robot ID, zone, event type; keyword fallback; slot grounding | 1 call |
| Fleet Search | hybrid retrieval with filters (robot ID, event type, caller's zones) + guide sections | none |
| Robot Diagnostics | robot record + similar incidents + guide -> probable cause among 6 categories with event IDs and first action | 1 call |
| Battery Analysis | least-squares slope of 30-day battery health per robot vs policy (replace < 75% or > 1,800 cycles; inspect if > 0.3%/day) | narrates |
| Predictive Maintenance | risk score = low health + cycles + PM age + battery decline + recent incidents, with reasons | narrates |
| Task Optimization | move tasks from robots > 85% utilisation or > 8 queued to healthy (> 80% battery, active) robots < 60% in the same zone | narrates |
| Fleet Status | status and utilisation per zone | none |
| Ops Summary | all outputs + last week's incidents, executive or operational tone | 1 call |

## 4. Data and RAG pipeline
| Source | Chunking | Metadata |
|---|---|---|
| `incidents.csv` (90) | one document per event (symptom, root cause, resolution, downtime) | event ID, robot, zone, model, firmware, event type, error code, severity |
| `maintenance_logs.csv` (60) | one document per action | robot, zone, action, part |
| `troubleshooting_guide.md` | structure-aware sections (700 chars); the error-code table is one `table` chunk | doc ID, section, content type |
| `robots.csv`, `battery_telemetry.csv` | not embedded - queried by pandas | - |

Numbers that must be exact (telemetry, utilisation, queue lengths) are **queried, not retrieved**: embedding
time series would make the LLM read numbers out of prose. Retrieval: `nomic-embed-text` -> ChromaDB (cosine),
hybrid vector + BM25 with RRF, metadata filters with list values (zone scope).

## 5. Roles and zone scope
| Role | Intents | Zones |
|---|---|---|
| technician | diagnostics, navigation, battery, predictive maintenance, fleet status | all |
| shift_lead | fleet status, task assignment, summary, diagnostics, navigation | all |
| fleet_manager | all | all |
| site_executive | summary, fleet status | all |
| contractor_technician | diagnostics, battery, navigation | Z1-Inbound |

Zone scope is row-level security applied in three places: `authorize` (robot outside zones -> denied),
retrieval filters, and analytics functions.

## 6. Guardrails
| Guardrail | Behaviour |
|---|---|
| Safety overrides (disable / bypass e-stop, lidar, bumpers, safety fields, collision avoidance) | refused |
| Restricted zones (drive robots into human-only / restricted areas) | refused |
| Action commands (dispatch, reassign, reboot, push firmware) | refused - advisory only; recommendations allowed |
| Prompt injection; emails / phones | blocked; redacted |
| Output: numbers, robot / event / maintenance IDs | must exist in the evidence or analytics |
| Output: unsafe advice | answer withheld, replaced with the safety procedure pointer |
| Slot grounding | robot IDs, zones, event types must appear in the question |

## 7. Evaluation
| Metric | Result |
|---|---|
| Intent accuracy (keyword fallback, 21 questions) | 90.5% (19/21) |
| Retrieval hit@k / MRR / precision@k (event type), k=6 -> k=10 | 1.0 / 1.0 / 0.976 -> 1.0 / 1.0 / 0.843 |
| Guardrail block precision / recall (14 cases) | 1.0 / 1.0 |
| Planted patterns: fast battery decline, top-risk robot, rebalancing targets | 3/3 robots, R-1007, R-1031 + R-1035 |
| RAGAS non-LLM context precision / recall, hybrid k=6 -> k=10 | 0.899 / 0.850 -> 0.855 / 1.000 |

### RAGAS-driven change
The sweep (vector / BM25 / hybrid x k = 3, 6, 10) showed k=10 raises context recall from 0.85 to 1.0
(F1 0.874 -> 0.922) at a small precision cost; vector-only k=10 was 0.005 higher, within noise, so hybrid was
kept for exact error codes. `search_top_k` was changed from 6 to 10 based on this.

## 8. Monitoring
LangSmith traces with role / channel tags and feedback; `/metrics` (`fleetops_requests_total{intent,role,outcome}`,
latency histogram, guardrail blocks, intent fallbacks, feedback); `/metrics/summary`; `logs/audit.jsonl`.

## 9. Tech stack
LangGraph 1.2, LangChain core 1.6, Ollama, ChromaDB 1.5, BM25, pandas / numpy, FastAPI, Streamlit, LangSmith,
RAGAS 0.4.3, pytest (25 tests).

## 10. Limitations and next steps
Synthetic data; static snapshot instead of live telemetry; rebalancing is greedy within a zone. Next: stream
fleet-console events, learn risk-score weights from outcomes, one-click approval of proposed moves by the shift lead.
