# 02 - Robotics Fleet Assistant

Multi-agent assistant for **warehouse robotics operations**: robot diagnostics, navigation and Wi-Fi issues,
battery analysis, predictive maintenance, task (workload) optimisation, fleet status and daily health reports.

> Portfolio prototype. Independent re-implementation of a robotics-operations assistant pattern on
> **synthetic data** - not employer code, systems or data.

| | |
|---|---|
| **Pattern** | Multi-agent (LangGraph supervisor) + RAG over incidents, maintenance logs and a troubleshooting guide + deterministic fleet analytics |
| **Agents** | Intent, Fleet Search, Robot Diagnostics, Battery Analysis, Predictive Maintenance, Task Optimization, Fleet Status, Operations Summary |
| **Models** | Ollama `llama3.2` + `nomic-embed-text`; Bedrock optional |
| **Test URLs** | API **http://localhost:8002/docs** - UI **http://localhost:8502** - metrics **http://localhost:8002/metrics** |
| **Docs** | [Design document](docs/DESIGN.md) - [Slides](docs/Robotics_Fleet_Assistant.pptx) |

## Business use case
| | |
|---|---|
| **Problem** | A warehouse runs 40 autonomous mobile robots across four zones (inbound, storage, pick, outbound). Failures look alike on the fleet console, maintenance is calendar-based instead of condition-based, workload is uneven across robots, and shift reports are compiled by hand. |
| **What the assistant does** | Diagnoses robot issues from incident history and the troubleshooting guide, finds batteries degrading faster than policy, ranks robots by maintenance risk, proposes workload moves and writes the daily fleet report. **Advisory only**: it never moves, reboots or reconfigures robots and refuses to help bypass safety systems. |
| **Value (pilot targets)** | Less unplanned robot downtime, batteries replaced before they fail, balanced utilisation, faster shift handover. Targets to measure in a pilot, not prototype results. |

## Who uses it
| User | Typical question | Role (`fleetops/roles.yaml`) | Demo API key |
|---|---|---|---|
| Robotics maintenance technician | "Why does R-1007 keep returning to the charger?" | `technician` - diagnostics, navigation, battery, maintenance, status | `tech-demo-key` |
| Floor shift lead | "Which robots should take work from overloaded ones?" | `shift_lead` - status, task assignment, summary, diagnostics | `lead-demo-key` |
| Fleet / robotics manager | "Which robots need maintenance next?" | `fleet_manager` - all workflows | `manager-demo-key` |
| Site leadership | "Give me today's fleet health summary" | `site_executive` - summary, status | `exec-demo-key` |
| Contract technician (inbound zone) | "Why does R-1005 keep stopping?" | `contractor_technician` - diagnostics, battery, navigation; **only Z1-Inbound robots** | `contractor-demo-key` |

Zone scope is row-level security: a contractor asking about a robot in another zone is denied, and retrieval
and analytics only see their zone.

## Tech stack
| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Orchestration | LangGraph 1.2 - supervisor + 8 agents with a fixed plan per intent; only the last agent narrates with the LLM |
| LLM framework | LangChain core 1.6, langchain-ollama 1.1 (structured output for intent and slots) |
| Models | Ollama 0.40: `llama3.2` (3B), `nomic-embed-text`; Amazon Bedrock by configuration |
| Retrieval | ChromaDB 1.5 (collections `events`, `knowledge`) + BM25 hybrid with RRF; zone / robot / event-type filters |
| Analytics | pandas 3.0 + numpy 2.5 (battery slope by least squares, risk score, rebalancing) - telemetry is queried, not embedded |
| API / UI | FastAPI 0.143 + Uvicorn 0.54 (REST, `X-API-Key` roles), Streamlit 1.65 |
| Evaluation | Labelled datasets + `eval/run_eval.py`, RAGAS 0.4.3, LangSmith experiments |
| Monitoring | LangSmith 0.14 tracing + feedback, Prometheus-format `/metrics`, JSONL audit log |
| Quality | pytest 9.1 (fake LLM, no model needed), ruff 0.17 |

## Workflows

| Intent | Agents (in order) | Example |
|---|---|---|
| Robot Diagnostics | Fleet Search -> Diagnostics | "Why does R-1007 keep returning to the charger?" |
| Navigation Issues | Fleet Search (navigation / Wi-Fi) -> Diagnostics | "Robots in the pick zone keep losing Wi-Fi" |
| Battery Analysis | Battery | "Which robots have degrading battery health?" |
| Predictive Maintenance | Battery -> Maintenance | "Which robots should get proactive maintenance next week?" |
| Task Assignment | Fleet Status -> Task Optimization | "Rebalance the workload in Z3" |
| Fleet Status | Fleet Status | "How many robots are active right now?" |
| Operational Summary | Fleet Status -> Battery -> Maintenance -> Summary | "Give me the daily health report" |

Only the last agent in a plan writes a narrative with the LLM; earlier agents return data (fewer LLM calls).

## Sample data (synthetic, committed)
`data/raw/` - regenerate with `python data/generate_data.py`:
`robots.csv` (40 robots, 4 zones), `incidents.csv` (90 events with error codes, root causes, resolutions),
`maintenance_logs.csv` (60), `battery_telemetry.csv` (30 days x 40 robots), `troubleshooting_guide.md`
(error-code table, battery policy, PM intervals, balancing rules).

Planted patterns: R-1007/R-1015/R-1023 lose battery health 0.6%/day; Wi-Fi drops cluster in Z3-Pick near
AP-07; navigation exceptions rise on firmware 4.8.0; Z3 is overloaded while R-1031/R-1035 are under-used.

## Run it
```powershell
cd 02-robotics-fleet-assistant
pip install -r requirements.txt            # or use the shared portfolio .venv
copy .env.example .env                     # never commit .env
python -m fleetops.ingest                  # 150 event docs + 5 guide chunks
uvicorn fleetops.api:app --port 8002       # http://localhost:8002/docs
streamlit run ui/streamlit_app.py --server.port 8502
python -m fleetops.cli ask "Why does R-1007 keep stopping?" --role technician --trace
```
```powershell
curl -X POST http://localhost:8002/ask -H "X-API-Key: tech-demo-key" -H "Content-Type: application/json" `
     -d '{"question": "Why does R-1007 keep returning to the charger?"}'
curl -X POST http://localhost:8002/ask -H "X-API-Key: lead-demo-key" -H "Content-Type: application/json" `
     -d '{"question": "Rebalance the workload in Z3"}'
curl http://localhost:8002/metrics
```

## Sample roles
| Role | Demo API key | Can run | Zones |
|---|---|---|---|
| `technician` | `tech-demo-key` | diagnostics, navigation, battery, predictive maintenance, fleet status | all |
| `shift_lead` | `lead-demo-key` | fleet status, task assignment, summary, diagnostics, navigation | all |
| `fleet_manager` | `manager-demo-key` | all | all |
| `site_executive` | `exec-demo-key` | summary, fleet status (executive style) | all |
| `contractor_technician` | `contractor-demo-key` | diagnostics, battery, navigation | **Z1-Inbound only** |

Zone scope is row-level security: retrieval filters and analytics only see the role's zones, and asking
about a robot outside them is denied.

## Guardrails
- **Safety overrides refused**: disabling / bypassing e-stops, lidar, bumpers, safety fields or collision avoidance; sending robots into restricted or human-only zones.
- **Advisory only**: commands to dispatch, reassign, reboot or push firmware are refused - the shift lead executes in the fleet console; "what should we reassign?" is answered.
- **Prompt injection** blocked; emails / phones redacted.
- **Output**: numbers must come from analytics/evidence; robot, event and maintenance IDs must exist in the evidence; answers suggesting safety bypasses are withheld.
- **Slot grounding**: robot IDs, zones and event types the LLM extracts must appear in the question.

## Chunking and RAG
- Incidents and maintenance logs: **one document per CSV row** (symptom, root cause, resolution together) with metadata (robot, zone, firmware, event type, error code) for filtered search.
- Troubleshooting guide: **structure-aware chunks** by section (700 chars); the error-code table is kept whole as one `table` chunk.
- `nomic-embed-text` -> ChromaDB (`events`, `knowledge`), hybrid vector + BM25 retrieval with metadata filters (robot ID, event type, zone scope).
- Numbers (battery slope, risk score, utilisation, task moves) come from pandas/numpy, never from the LLM.

## Tests, evaluation, RAGAS
```powershell
pytest -q                                    # 25 tests, no model needed
python -m eval.run_eval [--llm]              # intent, retrieval hit@k / MRR, guardrails, planted-pattern checks
python -m eval.ragas_eval --optimize         # RAGAS non-LLM context precision / recall + retrieval sweep
python -m eval.ragas_eval --llm 2            # + LLM-judged faithfulness / context recall
python -m eval.langsmith_eval                # LangSmith experiment (needs LANGSMITH_API_KEY)
```
CPU-only machines: create the capped judge once - `ollama create llama3.2-judge -f ../tools/ollama/Modelfile.judge`.

## Monitoring
LangSmith tracing + feedback (`LANGSMITH_TRACING=true`), Prometheus metrics at `/metrics`
(`fleetops_requests_total{intent,role,outcome}`, latency histogram, guardrail blocks, intent fallbacks),
JSON at `/metrics/summary`, UI "Metrics" tab, audit log `logs/audit.jsonl`.
