# 08 - Functional Specification

## Modules
| Module | Inputs | Processing | Outputs | Validations / errors |
|---|---|---|---|---|
| PDF loader | PDF | Remove repeating header/footer lines in top/bottom 8%; cut each page into strips around tables/images; in each strip, rows crossing the centre gutter are full width, others assigned to left/right column (left first); pdfplumber ruled tables to Markdown; merge a table whose header matches the previous one across pages; headings by font size; footnotes by small type; metadata from the document-ID line; PyMuPDF figures with positions | Markdown, images, extraction report | Check failures -> quarantine; unreadable page -> report + alert |
| Word / HTML loaders | DOCX, HTML | Ordered body walk, headings, tables, inline pictures / BeautifulSoup | Markdown, images | - |
| Vision | image | Prompt: transcribe text exactly then describe; cache by SHA-256; verification: drug names in caption not present elsewhere in the document are flagged | caption + flag | Failure -> "caption unavailable" |
| Chunker | Markdown | Section-bounded, tables whole (split by rows with header repeated), caption chunks, record chunks, contextual header | chunks + metadata | - |
| Guard input | request | Patient-specific advice detector, injection, PHI redaction, length | clean request or refusal | Refusal message with pointer to clinician |
| Resolve condition | text | Match condition catalogue (synonyms) or live mode for any condition | condition id | Unknown + synthetic -> message |
| Authorize | role, task, source | Task allowed? Live data allowed? Clearance level | proceed or denied | Denied lists allowed tasks |
| Gather trials | condition, source | Registry rows or ClinicalTrials.gov API v2 (recruiting/active, Phase 2-3, configurable) with retry and cache | program table, sponsors | API errors -> cached snapshot + warning |
| Standard-of-care agent | condition, clearance | Retrieve guideline text, tables, algorithm caption | evidence set | None -> section states no accessible guideline |
| Pipeline agent | programs | Counts by phase/modality/status; late-stage table; emerging therapies text | evidence + computed numbers | - |
| Key-players agent | programs | Rank sponsors and lead sites; classify company vs institution | ranked lists | - |
| Strategy agent | condition, clearance | Retrieve internal documents (cleared roles only) | evidence or "unavailable" | Public role -> unavailable |
| Writer | evidence, style | One call; style analyst/executive/clinical; bullet and token caps; cite `[n]` | JSON sections + Markdown | LLM failure -> facts-only briefing |
| Verify | draft, evidence | Number and ID grounding; citation backfill from best-matching evidence or mark *unattributed*; second-person language flag; truncation fix; disclaimer | final briefing + flags | - |
| Follow-up Q&A | question | retrieve (clearance/condition) -> grade -> answer -> verify | answer + citations | Not covered -> say so |
| Cache | request | Key (condition, clearance, style, content version), TTL 24 h | cached briefing | Invalidate on refresh |
| Observability | request | metrics, audit, LangSmith | - | Never fails request |

## Roles and permissions
| Role | briefing | qa | live data | internal docs | style |
|---|---|---|---|---|---|
| strategy_analyst | Y | Y | Y | Y | analyst |
| service_line_director | Y | Y | Y | Y | analyst |
| executive | Y | N | N | Y | executive |
| clinical_advisor | Y | Y | Y | Y | clinical |
| external_consultant | Y | Y | N | N | analyst |

## UI behavior
Tabs: **Briefing** (condition selector or free text; source toggle synthetic/live; style; progress; five sections with source chips; late-stage table; flags panel for unattributed/unverified items; disclaimer banner; approve/review button for clinical advisors), **Ask** (chat with citations), **Extraction** (side-by-side original page image vs extracted Markdown; flags), **Metrics** (admin). Download Markdown (Phase 2: Word/slide). Role/clearance badge always visible.

## AI behavior specification
| Aspect | Spec |
|---|---|
| Tone | Neutral, concise, third person; analyst style: bullets with numbers; executive style: <= 1 page, 5 bullets per section max; clinical style: guideline terminology preserved |
| Citations | `[n]` numbered sources list with document ID, version/date, page; trial rows cite NCT/program ID |
| Refusals | Patient-specific, dosing for an individual, diagnosis: "I can summarise guideline content and the landscape, not advise on individual care." |
| Confidence | Evidence missing for a section -> explicit statement, no filler; low retrieval score -> "sources do not cover" |
| Numbers | From analytics or evidence only; counts always computed |
| Fallback to human | Flagged bullets -> analyst; standard-of-care section -> clinical advisor sign-off before external use |
| Disclaimer | "Strategy summary of the cited sources; not clinical guidance" on every briefing and export |

## Open questions
Final template headings per audience; whether live-mode briefings need a legal disclaimer about data currency.
