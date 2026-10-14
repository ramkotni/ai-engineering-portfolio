# 🎯 RAG & Agentic AI — Interview Q&A Guide

> Built from **Interview-Prep.xlsx** (all company sheets) and **Kalyan-Garu-Discussion.xlsx**.
> Every question is tagged with the **company / round** it was asked in, followed by a simple answer and an easy real-life example.
> Running project example used throughout: **Payment AI Platform** (investigates failed payments using incident reports, logs and policies).

**Note:** `Kalyan-Garu-Discussion.xlsx` has no content (only an empty sheet). The "Kalyan Garu Discussion" questions are in the *Infosys* sheet of the Interview-Prep file and are included below.

---

## 📑 Table of Contents

**Part 1 — RAG**
1. [RAG Fundamentals](#1-rag-fundamentals)
2. [Chunking Strategies](#2-chunking-strategies)
3. [Embeddings & Vector Databases](#3-embeddings--vector-databases)
4. [Retrieval, Search & Ranking](#4-retrieval-search--ranking)
5. [Prompts, Context & Temperature](#5-prompts-context--temperature)
6. [Hallucination Control](#6-hallucination-control)
7. [RAG Evaluation & Testing](#7-rag-evaluation--testing)
8. [RAG Optimization, Cost & Reliability](#8-rag-optimization-cost--reliability)

**Part 2 — Agentic AI**
1. [Agent Fundamentals (LangChain vs LangGraph)](#1-agent-fundamentals)
2. [State & Memory](#2-state--memory)
3. [Orchestration & Multi-Agent Patterns](#3-orchestration--multi-agent-patterns)
4. [Intent Classification & Routing](#4-intent-classification--routing)
5. [Tools & MCP](#5-tools--mcp)
6. [Observability & Evaluation of Agents](#6-observability--evaluation-of-agents)
7. [Deployment, Scaling & Agent Platform (Harness)](#7-deployment-scaling--agent-platform-harness)
8. [Security, PII & Guardrails](#8-security-pii--guardrails)
9. [Model Selection & Project Approach](#9-model-selection--project-approach)
10. [Design Principles & Python Engineering](#10-design-principles--python-engineering)
11. [Scenario / Case-Study Questions](#11-scenario--case-study-questions)

**Appendix** — [Company-wise index](#-company-wise-index) · [Cheat-sheet](#-one-line-cheat-sheet)

---
---

# 🟦 PART 1 — RAG (Retrieval-Augmented Generation)

---

## 1. RAG Fundamentals

### Q1. What is RAG and how does your RAG pipeline work?
**🏢 Company:** Gamestop (L1) · General notes (MyNotes)

**Answer:**
RAG = *Retrieve* relevant facts from your own data first, then let the LLM *Generate* an answer using only those facts.
It stops the LLM from guessing, because it gets the evidence in the prompt.

**Pipeline:**
```
Documents → Clean → Chunk → Embed → Store in Vector DB      (indexing, done once)

User question → Embed → Similarity search → Top-K chunks → Prompt + chunks → LLM → Answer + sources
```

**Easy example:** Open-book exam. The LLM is the student; the vector DB is the textbook. Instead of answering from memory (and maybe being wrong), the student first finds the right page, then writes the answer.

**Payment AI example:** *"Why did UPI payments fail yesterday?"* → retrieve 5 similar past incident reports → LLM reads them → answers *"Bank gateway timeout, similar to incident #231"* with the source.

---

### Q2. Why do we need chunking and embeddings? Why can't we just use a normal search tool?
**🏢 Company:** General RAG notes (Interview-Prep, RAG sheet)

**Answer:**
- **Normal search (BM25 / TF-IDF)** matches *exact words* (keyword).
- **Embeddings** match *meaning* (semantic).
- **Chunking** is needed because LLMs have a context limit and small focused chunks give more precise retrieval.

**Easy example:** User searches *"car"*. Keyword search misses documents that say *"automobile"* or *"vehicle"*. Embedding search finds all three because their meaning is close.

**Payment AI example:** User asks *"money not received"*. Documents say *"settlement delayed"*. Keyword search fails; semantic search succeeds.

> 💡 In production use **both** (hybrid search) — see [Section 4](#4-retrieval-search--ranking).

---

### Q3. When would you use RAG vs fine-tuning vs plain LLM?
**🏢 Company:** Virtusa (approach question)

| Need | Use | Why |
|---|---|---|
| Private / changing data (policies, incidents) | **RAG** | Update documents, no retraining |
| Change the *style / format / skill* of the model | **Fine-tuning** | Teaches behavior |
| General knowledge, no private data | **Plain LLM** | Simplest and cheapest |

**Easy example:** RAG = giving the employee a handbook. Fine-tuning = sending the employee to months of training. Plain LLM = asking a smart stranger.

---

### Q4. How do you fine-tune a model? (and when is it needed)
**🏢 Company:** Infosys / Virtusa (Kalyan Garu discussion)

**Answer (steps):**
1. Collect domain data (e.g., past support chats).
2. Clean and format it (prompt → ideal answer pairs).
3. Pick a base model (smaller if the task is narrow).
4. Train with a **low learning rate** (transfer learning) so existing knowledge isn't destroyed.
5. Evaluate with accuracy / precision / recall on a held-out test set.
6. Deploy and monitor.

**Easy example:** A doctor (base model) already knows medicine. Fine-tuning = a 3-month cardiology specialization — not re-teaching medicine from scratch.

> ⚠️ Say in the interview: *"I try prompting + RAG first. Fine-tune only if those can't reach the quality needed."*

---

## 2. Chunking Strategies

### Q5. What chunking strategies do you use for HTML, PDF and CSV? Explain in detail.
**🏢 Company:** Infosys (Kalyan Garu discussion) · General RAG notes

| File type | Strategy | Why |
|---|---|---|
| **CSV** | 1 row = 1 chunk (or group of rows by category); embed relevant columns only; keep column names with the value | Rows are naturally independent records |
| **HTML** | Split by tags (`<h1>`, `<h2>`, `<p>`, `<li>`); keep heading with its paragraph; store tag/URL as metadata | Structure already tells you the topic boundaries |
| **PDF** | Extract text → **Recursive character splitter**, chunk size 500–1000 tokens, overlap 100–200; handle tables and images separately | Layouts vary; overlap protects context |

**Easy example (CSV):** A row `Order 123 | Failed | Timeout | UPI` is converted to the sentence *"Order 123 failed with Timeout via UPI"* and then embedded. A bare row of numbers has no meaning for an embedding model.

**Easy example (PDF):** Cutting a book into pages. If a sentence is cut at the page edge, you lose meaning — so each new page repeats the last 2 lines of the previous page (= overlap).

**Code (recursive splitter):**
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_text(pdf_text)
```

**Code (CSV, row-wise):**
```python
import pandas as pd
for batch in pd.read_csv("payments.csv", chunksize=100):
    for _, row in batch.iterrows():
        text = f"Order {row.id} {row.status} reason {row.reason} via {row.channel}"
```

---

### Q6. What is recursive chunking and what other types exist?
**🏢 Company:** Infosys (Kalyan Garu discussion)

| Type | How it works | Best for |
|---|---|---|
| **Fixed-size** | Cut every N characters | Quick prototypes |
| **Recursive** | Try splitting on paragraph → sentence → word until it fits | Default choice for most text |
| **Semantic** | Split where the *meaning* changes (embedding similarity drops) | Long, topic-mixing docs |
| **Structure-based** | Split by headings / HTML tags / Markdown | Manuals, web pages |
| **Parent–child** | Search on small child chunks, return the bigger parent chunk | Need precision *and* context |
| **Row-based** | One row = one chunk | CSV / tables |

**Easy example (recursive):** Cutting a cake — first try to cut by layer (paragraph); if a piece is still too big, cut by slices (sentence); then by bites (word).

**Easy example (parent–child):** You search the *index* of a book (small, precise), but you read the *whole chapter* (big, full context).

---

### Q7. How do you implement semantic chunking?
**🏢 Company:** Infosys (Kalyan Garu discussion)

**Answer:**
1. Split the text into sentences.
2. Embed each sentence.
3. Compare each sentence with the next one (cosine similarity).
4. When similarity **drops sharply**, a new topic started → start a new chunk there.

```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

chunker = SemanticChunker(OpenAIEmbeddings())
chunks = chunker.split_text(long_text)
```

**Easy example:** A podcast transcript — chunk boundaries fall where the host changes the topic from "refund policy" to "chargebacks", not at an arbitrary 1000th character.

**Trade-off:** Better quality, but costs embedding calls at indexing time.

---

### Q8. How do you chunk documents that contain charts, images and tables inside PDFs?
**🏢 Company:** General RAG notes

**Answer:**
- **Text** → recursive splitter.
- **Tables** → keep the whole table as one chunk (or convert to Markdown); never split a table row from its header.
- **Charts / images** → use a vision model (or OCR) to generate a *text description / caption*, embed that, and keep a link to the original image in metadata.

**Easy example:** A bar chart can't be searched. So you write beside it: *"Chart: UPI failures rose from 2% to 6% in March"* — now it is searchable.

---

## 3. Embeddings & Vector Databases

### Q9. What is your understanding of Vector DBs?
**🏢 Company:** Insight Global (Sedgwick VP Round)

**Answer:**
A vector DB stores **embeddings** (lists of numbers that capture meaning) and finds the **nearest** ones to a query quickly using Approximate Nearest Neighbour (ANN) indexes (HNSW, IVF). It also stores **metadata** (source, date, access role) for filtering.

**Easy example:** A library arranged by *meaning* instead of alphabet. Books about similar topics sit on the same shelf, so asking for "healthy cooking" lands you next to "low-fat recipes".

---

### Q10. Why did you use Chroma in non-prod and FAISS in prod? Did you notice differences between their embeddings?
**🏢 Company:** Infosys (Kalyan Garu discussion)

**Answer:**
- **Embeddings are identical** — they come from the *embedding model*, not the DB. The DB only stores and searches them. Any difference you see is in search speed, filtering, persistence and scaling.
- **Chroma:** easy, persistent, metadata filtering built-in → great for dev / POC.
- **FAISS:** very fast in-memory ANN library, many index types → good for large scale and high throughput; you must manage metadata/persistence yourself.
- For managed production, also consider OpenSearch, pgvector, Pinecone.

**Easy example:** Same photos (embeddings), different albums (DBs). Chroma = a handy phone gallery, FAISS = a high-speed warehouse scanner.

---

### Q11. How do you decide which embedding model to use? How do you test its performance?
**🏢 Company:** Insight Global (Sedgwick VP Round) · Infosys (2nd round)

**Criteria:**
- Domain fit (general vs finance / code / multilingual)
- Dimension & cost (bigger vectors = more storage and slower)
- Max token length (must fit your chunk size)
- Latency, hosting (API vs local), data privacy

**How to test (practical):**
1. Build a **golden set**: 50–100 real questions + the correct chunk for each.
2. Run each candidate model, compute **Recall@K / Hit-rate / MRR**.
3. Pick the best score within cost/latency limits.

**Easy example:** Choosing a taxi service — you try 3 on the same route and compare *time, price and comfort*, then pick the best overall.

---

### Q12. What embedding models have you used / do you know?
**🏢 Company:** Infosys (Kalyan Garu discussion)

- **Word level:** Word2Vec, GloVe (one fixed vector per word)
- **Sentence level:** Sentence-BERT, Universal Sentence Encoder
- **Contextual:** BERT, ELMo
- **Modern API models:** OpenAI `text-embedding-3`, Amazon Titan Embeddings (Bedrock), Cohere embed
- **Open source / local:** `all-MiniLM-L6-v2`, BGE, Nomic (via Ollama)

**Easy example (contextual vs fixed):** The word *"bank"* — Word2Vec gives one vector; BERT gives different vectors for *river bank* and *money bank*.

---

## 4. Retrieval, Search & Ranking

### Q13. What is semantic search and hybrid search?
**🏢 Company:** Virtusa · TCS ("what type of search you use for retrieval")

- **Semantic search:** matches meaning using embeddings.
- **Keyword search (BM25):** matches exact words/IDs/codes.
- **Hybrid search:** combines both, e.g., `final_score = 0.4 × keyword + 0.6 × semantic`, then optionally **rerank**.

**Easy example:** Searching *"error E-4021"*. Semantic search may return random "payment error" docs; keyword search finds the exact code `E-4021`. Hybrid gets both the meaning and the exact code.

---

### Q14. On what basis do you rank the documents? What are the top ranking strategies?
**🏢 Company:** Infosys (Kalyan Garu discussion)

1. **Vector similarity** — cosine similarity / distance (for *distance*, **lower = closer**; for *similarity*, higher = closer).
2. **BM25 + semantic ensemble** with weights (e.g., 40/60).
3. **Metadata filtering** — only recent docs, only the user's allowed department.
4. **Multi-query retrieval** — LLM rewrites the question in 3 ways, retrieves for each, merges.
5. **Re-ranking** — a cross-encoder model re-scores the top 20 and keeps the best 5.
6. **Similarity threshold** — drop results below a minimum score.

**Easy example:** Hiring: first a quick resume keyword screen (retrieval), then a detailed interview of the top 20 (re-ranking), then pick the best 5.

---

### Q15. What is the confidence score? What if the LLM gives 2–3 different responses?
**🏢 Company:** Infosys (Kalyan Garu discussion)

**Answer:**
Confidence score = how sure the model/classifier is about its output (0–1). Sources: classifier probability, retrieval similarity score, or an LLM-judge score.

If you get 2–3 different responses:
- Compare their scores and pick the highest.
- **Self-consistency:** ask 3 times, pick the majority answer.
- Below a threshold → return *"I'm not sure"* or ask a clarification.

**Easy example:** Asking 3 doctors; if 2 say "flu" and 1 says "cold", you go with flu — and if all three disagree, you order more tests.

---

## 5. Prompts, Context & Temperature

### Q16. How do you limit the context size?
**🏢 Company:** General RAG notes

**Answer:**
Every model has a token limit (e.g., 40K / 100K / 200K). Total = **system prompt + history + retrieved context + question + answer space**. Rule of thumb: keep it **under ~50%** of the window — models ignore the middle of very long inputs.

**How:**
- Small chunks + only **Top-K** (3–5).
- Re-rank and drop low scores.
- Summarize old chat history.
- Metadata filters to remove irrelevant docs.
- Count tokens before sending (`tiktoken`).

**Easy example:** A suitcase with a weight limit — pack only essentials; the heavier it is, the more likely something important gets lost.

---

### Q17. How do you optimize your prompt?
**🏢 Company:** General RAG notes

1. **Clear role + task:** "You are a payment-support analyst."
2. **Ground it:** "Answer **only** from the context below."
3. **Fallback rule:** "If not in context, say *I don't know*."
4. **Output format:** JSON / bullets with sources.
5. **Break big prompts** into smaller steps (prompt chaining).
6. **Let the LLM rewrite/summarize** the user query before retrieval.
7. **Test and iterate** against a golden set.

**Example prompt:**
```
You are a payment incident analyst.
Use ONLY the context. If the answer is not in the context, reply "I don't know".
Return: root_cause, recommendation, confidence, sources.

Context: {context}
Question: {question}
```

---

### Q18. How do you determine / configure LLM temperature?
**🏢 Company:** Infosys (Kalyan Garu discussion) · General RAG notes

| Temperature | Behavior | Use for |
|---|---|---|
| **0 – 0.2** | Focused, repeatable | RAG, RCA, classification, extraction |
| **0.5** | Balanced | Summaries, explanations |
| **0.8 – 1.0** | Creative, varied | Brainstorming, marketing text |

**Easy example:** Temperature is a "creativity dial". A bank's chatbot should be a strict accountant (0), not a poet (1).

**How I decide:** start at 0 for factual flows → test on golden questions → raise only if answers feel robotic.

---

## 6. Hallucination Control

### Q19. What do you do if the LLM keeps giving hallucinated answers? (configuration)
**🏢 Company:** General RAG notes

**Answer:**
1. `temperature = 0`
2. Add **RAG** so answers are grounded in real documents.
3. Strict prompt: "only from context, else *I don't know*".
4. Ask for **citations**.
5. Add a **grounding / faithfulness check** on the output.
6. Collect failures → feedback loop.

**Easy example:** Don't let the student write from memory; give them the textbook and ask for the page number for every claim.

---

### Q20. You observe hallucination in a PRODUCTION system — what is your approach?
**🏢 Company:** Virtusa (09-28-2026 round) — asked **twice** (Q6 and Q10)

**Answer (step by step):**
1. **Contain** – don't panic-swap the model. Add a safe fallback / turn on stricter guardrail.
2. **Trace** the request through the whole pipeline: intent → retrieval → chunking → context → prompt → LLM → validation (use LangSmith / Langfuse).
3. **Find the failing layer**
   - Wrong docs retrieved? → fix chunking, embeddings, filters, rerank.
   - Right docs but wrong answer? → fix prompt / model / temperature.
   - No docs exist? → data gap.
4. **Add controls:** similarity threshold, metadata filter, grounding validation, "I don't know" fallback.
5. **Save the case** in a golden dataset → becomes a regression test.
6. **Fix, measure, then deploy** (compare metrics before/after).

> 🗣️ **One-line answer:** *"I don't blindly change the LLM; I trace the pipeline, find the failing layer, add a grounded fallback, turn the incident into an evaluation test, and deploy the measured fix."*

**Easy example:** A restaurant serves a wrong dish. You don't fire the chef immediately — you check: wrong order taken? wrong ingredients? wrong recipe? Fix that step and add a checklist.

---

## 7. RAG Evaluation & Testing

### Q21. Tell me about RAGAS — how do you implement it? How do you ensure agents give the right data?
**🏢 Company:** Insight Global (Sedgwick VP) · General Agent notes

**RAGAS metrics:**

| Metric | Question it answers |
|---|---|
| **Faithfulness** | Is the answer supported by the retrieved context? (anti-hallucination) |
| **Answer relevancy** | Does the answer actually address the question? |
| **Context precision** | Are the retrieved chunks mostly relevant? |
| **Context recall** | Did we retrieve *all* the needed information? |
| **Answer correctness** | Does it match the ground-truth answer? |

**Flow:** `question → retrieved chunks → LLM answer → (ground truth) → RAGAS scores`

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

result = evaluate(dataset, metrics=[faithfulness, answer_relevancy,
                                    context_precision, context_recall])
print(result)
```

**Easy example:** A teacher grading an open-book exam: *Did the student use the book?* (faithfulness) *Did they answer the question asked?* (relevancy) *Did they open the right page?* (context precision/recall).

---

### Q22. Difference between Precision and Recall (with an example)
**🏢 Company:** Insight Global (Sedgwick VP) — asked twice · MyNotes

- **Precision** = of what I *returned*, how much was *correct*?  `TP / (TP + FP)`
- **Recall** = of everything that *was correct*, how much did I *find*?  `TP / (TP + FN)`
- **F1** = balance of both.

**Worked example from the notes:**
> 100 total records. 10 belong to "Chiru". System pulls 20 records, of which 5 are Chiru's.
> - **Recall** = 5 / 10 = **50%** (found only half of Chiru's records)
> - **Precision** = 5 / 20 = **25%** (only a quarter of what it pulled was relevant)

**Easy example:** A fisherman's net. *Precision* = how much of the catch is the fish you wanted. *Recall* = how many of the fish in the lake you caught.

**In RAG:** high recall = retrieve all the evidence; high precision = no junk in the context.
**When to prefer which:** fraud/disease detection → high recall; spam filter → high precision.

---

### Q23. How do you test the AI application? (LLM-as-judge)
**🏢 Company:** Insight Global (Sedgwick VP)

1. Build a **golden dataset** (questions + expected answers + expected sources).
2. Test layers separately: retrieval (Recall@K), generation (faithfulness), end-to-end.
3. **LLM-as-judge:** a second LLM scores the answer on a rubric (correct? grounded? safe? complete?).
4. **Unit/integration tests** for tools and APIs.
5. Run in **CI/CD** on every change — fail the build if scores drop (regression test).
6. **Human review** for a sample.

**Easy example:** A school exam paper (golden set) + a teacher (LLM judge) who marks it automatically every time the syllabus (code) changes.

---

## 8. RAG Optimization, Cost & Reliability

### Q24. In what cases will you optimize RAG?
**🏢 Company:** Infosys (Kalyan Garu discussion) · General notes

- Very large document sets → slow / noisy retrieval
- Frequent repeated questions → add **caching**
- Poor answers → tune chunk size, overlap, hybrid search, rerank
- High cost/latency → smaller model, shorter context
- Multi-aspect questions → **multi-query retrieval**
- "Garbage in, garbage out" → clean and enrich the data first
- Multi-session users → better memory management

---

### Q25. Why is caching needed?
**🏢 Company:** General Agent notes

- **Saves cost** (no repeated LLM/embedding calls)
- **Faster** responses
- **Less load** on the LLM and rate limits

Types: exact-match cache (Redis), **semantic cache** (similar question → same answer), embedding cache, prompt cache.

**Easy example:** A tea stall that keeps the most-ordered tea ready instead of brewing from scratch every time.

---

### Q26. How do you do retries for LLM calls?
**🏢 Company:** Insight Global (Sedgwick VP)

1. Retry only on **transient errors** (timeout, 429 rate-limit, 5xx).
2. **Max retries** (e.g., 3).
3. **Exponential backoff + jitter:** wait 1s → 2s → 4s.
4. Log every attempt.
5. On context-limit error → shorten context / lower temperature; don't blindly retry.
6. After the last failure → graceful fallback message or cached answer.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def call_llm(prompt):
    return llm.invoke(prompt)
```

**Easy example:** Calling a busy friend — don't redial every second; wait a bit longer each time, and leave a message after 3 tries.

---

### Q27. How do you monitor cost and how many users use the application? How do you control user requests to avoid LLM cost?
**🏢 Company:** Infosys (Kalyan Garu discussion — Q1, Q20, Q22)

**Monitor:**
- Log **tokens in/out, model, user ID, agent** for every call (LangSmith / Langfuse / CloudWatch).
- Dashboards: cost per user, per agent, per day; active users; **budgets + alerts** (AWS Budgets / Cost Explorer).

**Control:**
- **Rate limit** per user, **token cap** per request.
- **Cache** repeated questions.
- **Route cheap model first** (Haiku for simple, Sonnet for hard).
- Shorter context (Top-K small), summarize history.
- Block irrelevant/abusive queries with an input guardrail.

**Easy example:** Like an electricity meter on each room — you see who uses the most, set limits, and use a low-power bulb for simple needs.

---

### Q28. Why didn't you automate payment-failure fixing? Why so many agents in your application?
**🏢 Company:** Infosys (Kalyan Garu discussion — Q14, Q15)

**Why not auto-fix:**
- Money movement is **high risk** — a wrong automatic action is costly and non-reversible.
- Compliance and audit require a **human approval** step.
- The AI gives **RCA + recommendation + confidence**, and an operator approves → *human-in-the-loop*.

**Why multiple agents:** *one agent = one responsibility* (intent, retrieval, RCA, recommendation, summary). Easier to test, change, scale and explain; smaller prompts → fewer errors.

**Easy example:** A hospital — the nurse (triage), the lab (retrieval), the doctor (RCA), the pharmacist (recommendation). One person doing all four is slower and riskier.

---
---

# 🟩 PART 2 — AGENTIC AI

---

## 1. Agent Fundamentals

### Q29. What is the difference between LangChain and LangGraph? Why do you need LangGraph when LangChain exists?
**🏢 Company:** Gamestop (L1) · MyNotes · Insight Global

| | **LangChain** | **LangGraph** |
|---|---|---|
| Flow | Mostly linear chains (A → B → C) | **Graph** with branches, loops, conditions |
| State | Passed along loosely | **Explicit shared state** |
| Best for | Simple RAG, prompt + tool calls | Multi-step, multi-agent, retry loops, human approval |
| Persistence | Limited | **Checkpointing** (resume after failure) |

> ✍️ *Correction to the notes:* LangGraph's "graph" is a **workflow/state graph** (nodes = steps, edges = flow), *not* a knowledge graph.

**Easy example:** LangChain = a **straight conveyor belt**. LangGraph = a **city road map with traffic signals** — it can branch ("if intent = RCA go left"), loop ("if answer is weak, retry") and pause for a human.

> 🗣️ *"LangGraph is the manager, the nodes are the workers, and state is the shared notebook that carries information between them."*

---

### Q30. Why do you need an agent for classification?
**🏢 Company:** Gamestop (L1)

**Answer:**
For simple fixed rules, you *don't* need an agent — keywords/regex or a small classifier is cheaper and faster. Use an LLM/agent when:
- User phrasing varies a lot ("pay failed", "money deducted but order not placed").
- The decision needs **context** or multiple intents in one question.
- You need a **confidence score** and a clean fallback.

**Practical design:** *Rules first → LLM for the ambiguous cases* (hybrid), saving cost.

**Easy example:** A receptionist who understands *"my head is killing me"* and sends you to the doctor, not to a security guard.

---

### Q31. Explain how you orchestrate with LangGraph and why do you maintain state?
**🏢 Company:** Insight Global (Sedgwick VP Round)

**Answer:**
I model the workflow as **nodes** (intent → retrieval → RCA → recommendation → final response). LangGraph controls **which node runs next** (edges / conditional edges). **State** holds what each step produced so the next step can use it.

**Easy example (Payment AI):**
```
Intent agent   → "RCA"                       (writes to state)
Search agent   → adds 5 similar incidents    (writes to state)
RCA agent      → "Gateway timeout"           (reads incidents, writes cause)
Recommend      → "Switch to backup gateway"  (reads cause)
```
State is the **shared notebook** passed between workers.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class S(TypedDict):
    question: str; intent: str; docs: list; rca: str; answer: str

g = StateGraph(S)
g.add_node("intent", intent_node)
g.add_node("search", search_node)
g.add_node("rca", rca_node)
g.set_entry_point("intent")
g.add_edge("intent", "search")
g.add_edge("search", "rca")
g.add_edge("rca", END)
app = g.compile()
```

---

### Q32. Why are you going for AI? (motivation)
**🏢 Company:** Infosys (Kalyan Garu) · Virtusa ("why are you looking for a job")

**Sample answer:** *"Repetitive investigation work — reading logs, incidents and policies — consumes hours. AI lets us automate retrieval and reasoning while humans make the final decision. I enjoy building systems that turn that knowledge into faster, explainable decisions, and I want to grow in production-grade agentic systems."*

---

## 2. State & Memory

### Q33. What is "state" in LangGraph?
**🏢 Company:** Infosys (Kalyan Garu discussion)

State = the **shared data object** that flows through the graph. Each node reads from it and returns updates.
- Keeps context within one run.
- With a **checkpointer** (SQLite / Postgres / Redis) it persists across turns and lets you resume or time-travel.
- Has an entry point and finish point.

**Easy example:** A relay race **baton** — every runner (node) takes it, adds something, passes it on.

---

### Q34. How many types of memory are there? Short-term vs long-term? Why is conversation history needed?
**🏢 Company:** General Agent notes (Q1, Q2, Q13)

| Memory | What it holds | Lifetime | Example |
|---|---|---|---|
| **Short-term** | Current conversation messages | One session / thread | "My name is Paolo" → "What's my name?" |
| **Long-term** | User facts & preferences across sessions | Persistent (DB / vector store) | "User A prefers Python" remembered next week |
| **LLM (parametric) memory** | Knowledge baked into model weights | Fixed at training | General world knowledge |

**Why history is needed:** LLMs are *stateless* — without history, *"What about Mars?"* has no meaning after *"What's Earth's mass?"*.

```python
# short-term: thread_id keeps this conversation
config = {"configurable": {"thread_id": "user-A-session-1"}}
# long-term: store per-user facts
store.put(("users", "user_a"), "favorite_language", {"value": "Python"})
```

**Easy example:** Short-term = sticky notes on your desk today. Long-term = your diary you can read next month.

---

## 3. Orchestration & Multi-Agent Patterns

### Q35. What orchestration patterns do you know? Supervisor vs peer-to-peer?
**🏢 Company:** Insight Global (Sedgwick VP Round) · General Agent notes

| Pattern | How it works | Control | Layman example |
|---|---|---|---|
| **Supervisor / Manager–worker** | Central agent decides who runs next | Centralized, predictable | Manager assigns tasks |
| **Peer-to-peer / Handoff** | Agents pass work directly to each other | Distributed | Employees coordinate directly |
| **Fan-out / Fan-in (parallel)** | Many agents run at once, results merged | Fast | 3 analysts research separately, one merges |
| **Choreography (event-based)** | Agents react to events, no central boss | Loosely coupled | Dancers following the music |
| **Agent–sub-agent (hierarchical)** | Agent breaks task into sub-tasks for sub-agents | Layered | Team lead → team members |
| **Workflow (fixed pipeline)** | Predefined steps | Most predictable | Assembly line |

> 🗣️ *"My Payment AI uses a supervisor/orchestrator pattern. LangGraph manages the workflow, each agent has one responsibility, shared state carries information, and the orchestrator controls routing."*

---

### Q36. What kind of LangGraph architecture have you used? Why so many agents?
**🏢 Company:** General Agent notes (Q17) · Infosys (Q15)

**Answer:**
Supervisor + sub-agents. A supervisor breaks the user task into a **task list** (step 1, step 2…), assigns each to a specialist agent, **manages the full context** and combines results. Large data goes to a **database** (not the prompt) to avoid blowing up the context window.

**Easy example:** A project manager splitting a wedding plan: catering, decoration, invitations — each specialist reports back to the manager.

---

### Q37. Design: *multi-agent AI app, running in parallel, with RAG, memory, guardrails, evaluation, CI/CD and a UI.*
**🏢 Company:** Insight Global (Alexandra round)

```
USER → React/Streamlit → API Gateway → Supervisor/Orchestrator
                                         ├── Research Agent (RAG)
                                         ├── Analyst Agent (numbers/SQL)
                                         └── Risk/Safety Agent (policy)
                                                 ↓
                                        Synthesizer Agent → Final Answer
```

**What interviewers look for & my answer:**

| Requirement | Solution |
|---|---|
| Parallel agents | LangGraph fan-out/fan-in |
| Company knowledge | RAG over vector DB with metadata filters |
| Memory | Short-term (thread) + long-term (store) |
| Safety | Input/output guardrails, PII masking, grounding check |
| Quality | RAGAS + LLM-as-judge in CI |
| Deployment | GitHub Actions → Docker → container service (ECS/EKS) |
| UI | React or Streamlit calling FastAPI |

**Opening pitch:** *"I'm building an AI-first financial-operations assistant: it investigates a failed transaction, retrieves evidence, does quantitative analysis, checks policies and gives an explainable recommendation with citations."*

---

## 4. Intent Classification & Routing

### Q38. How do you classify the intent / how do you decide which agent to call?
**🏢 Company:** MyNotes · Infosys (Kalyan Garu discussion Q5)

**Flow:**
```
Question → Intent → Confidence → Route → Agent → Tools/RAG → Grounding → Answer
Unknown  → Intent → UNKNOWN/Low confidence → Clarify or Safe fallback
```

**Steps:**
1. Define business intents: `SEARCH, RCA, RECOMMEND, TREND, SUMMARY, UNKNOWN`.
2. An **intent node** returns *one* intent + confidence.
3. **Validate** it's in the allowed list.
4. LangGraph **conditional edge** routes to the right agent.
5. Support **UNKNOWN** — ask a clarification, don't force a wrong agent.
6. Multi-intent question → split into tasks, run each, combine.
7. Validate the final answer against retrieved context.

**Classifier prompt:**
```
Classify the question into exactly ONE intent:
SEARCH, RCA, RECOMMEND, TREND, SUMMARY, UNKNOWN
- "why did..." → RCA        - "how to fix..." → RECOMMEND
- historical incidents → SEARCH   - patterns over time → TREND
- overview → SUMMARY        - ambiguous → UNKNOWN
Question: {question}
Return only the intent.
```

**Rule-based first pass (cheap):**
```python
RULES = {"RCA": ["why did", "root cause", "what caused"],
         "TREND": ["over time", "last month", "failure rate"],
         "SUMMARY": ["summary", "overview"],
         "RECOMMEND": ["how to fix", "prevent", "next steps"]}
```
> 💡 Use meaningful **phrases** ("why did") instead of single words ("fix") to avoid false matches.

**Easy example:** A hospital reception desk: chest pain → cardiology, fever → general, unclear → "please tell me more".

---

## 5. Tools & MCP

### Q39. What is MCP? What is its purpose and use case? What if I configure 50 MCP servers?
**🏢 Company:** General Agent notes (Q8, Q15) · TCS

**MCP (Model Context Protocol)** = a **standard way** for an AI agent/LLM to discover and call external **tools, resources and prompts** — like USB-C for AI.

- **Tools** – actions (query DB, create ticket)
- **Resources** – read-only data (files, DB schemas)
- **Prompts** – reusable prompt templates

**Easy example:** Instead of a different charger for every phone, one USB-C works everywhere. One MCP standard lets any agent use any tool.

**50 MCP servers problem:**
- The LLM gets **50 × N tool definitions** in the prompt → huge tokens, slow, and it **picks the wrong tool**.
- **Better approach:** load only the needed servers per agent, group tools by domain, **tool-registry + routing** (retrieve the top relevant tools), clear tool descriptions with input/output schema, and permissions per agent.

**TCS follow-up – "Only for DB connection you use MCP?"** No — MCP suits anything reusable: DB, files, APIs, SaaS tools. For a single internal function, a normal tool/function call is simpler.

---

### Q40. What is the purpose of a tool? How do you define one?
**🏢 Company:** General Agent notes

A tool = a function the LLM can ask the agent to run. Needs:
- **Name** and a **clear description** (LLM decides based on this)
- **Input schema** (typed params) and **output spec**
- Error handling and timeouts

```python
from langchain_core.tools import tool

@tool
def get_payment_status(order_id: str) -> str:
    """Return the current status of a payment given its order id."""
    return db.query(order_id)
```

**Easy example:** Giving a chef a labeled set of knives — the better the labels, the better the chef picks the right one.

---

### Q41. How do you implement a FastAPI service for your agent? How does your Python app get data?
**🏢 Company:** TCS ("Quantum World")

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Query(BaseModel):
    question: str
    session_id: str

@app.post("/ask")
async def ask(q: Query):
    result = graph.invoke({"question": q.question},
                          config={"configurable": {"thread_id": q.session_id}})
    return {"answer": result["answer"], "sources": result["sources"]}
```
- Data comes from **vector DB / RDS / S3 / APIs** through a repository/service layer (not hard-coded in the agent).
- Add auth, validation (Pydantic), async I/O, streaming, health endpoint, timeouts.

**Easy example:** FastAPI is the **front-desk counter** — users hand in a question, the agent in the back office does the work, and the counter returns the result.

---

### Q42. Where do you store data in AWS Bedrock / AWS?
**🏢 Company:** TCS ("Quantum World")

- **Raw documents:** S3
- **Vector embeddings:** Bedrock Knowledge Bases (backed by OpenSearch Serverless / Aurora pgvector) or your own vector DB
- **Structured data:** RDS / DynamoDB
- **Chat memory / sessions:** DynamoDB or Redis (ElastiCache)
- **Logs & metrics:** CloudWatch

---

## 6. Observability & Evaluation of Agents

### Q43. Have you done observability? What did you solve by looking at it? (LangSmith / Langfuse / CloudWatch)
**🏢 Company:** General Agent notes (Q9) · Infosys (Q12, 2nd round) · Insight Global

**What I trace:** every LLM call, tool call, retrieval step — with **latency, tokens, cost, errors, inputs/outputs**.

**Problems solved with it (examples):**
- Found one agent making 6 LLM calls per request → merged steps → **cut cost/latency**.
- Saw retrieval returning wrong docs → fixed chunking.
- Spotted a slow tool timing out → added retries/caching.

**Tools:** LangSmith, Langfuse (open-source), OpenTelemetry, AWS CloudWatch (metrics, logs, alarms, dashboards).

**CloudWatch usage:** custom metrics (token count, error rate), log groups with structured JSON logs, **alarms** on error rate / latency, dashboards, X-Ray for distributed traces.

**Easy example:** A flight's **black box + dashboard** — you can replay exactly what happened at each step.

---

### Q44. How do you ensure your agents provide the right data?
**🏢 Company:** General Agent notes (Q6)

- **Evals (RAGAS):** faithfulness, relevancy, context precision/recall.
- **Grounding check:** each claim must be supported by a retrieved chunk.
- **Citations** in every answer.
- **Golden dataset** + regression tests in CI.
- **Human-in-loop** for risky actions.
- **Monitoring** in production (thumbs-up/down, LLM-judge sampling).

---

## 7. Deployment, Scaling & Agent Platform (Harness)

### Q45. How do you scale your application? Do you run each agent independently? Explain deployment strategy.
**🏢 Company:** General Agent notes (Q11)

- Package as **Docker** containers; deploy on **Kubernetes (pods)** / ECS / Bedrock AgentCore.
- Each agent can be its **own service** (scales independently) or part of one graph service (simpler) — choose by load and team size.
- Auto-scale on CPU/requests/queue length; use **queues** (SQS) for long jobs.
- Cache + rate limiting + circuit breakers on LLM calls.
- Externalize state (Postgres/Redis) so any pod can serve any request.

**Easy example:** A restaurant opening more counters (pods) at lunch hour; the order-slip board (shared state) ensures any counter can continue any order.

---

### Q46. Explain end-to-end production deployment of an AI application.
**🏢 Company:** General RAG notes (Q19)

```
Code (GitHub) → CI: lint + tests + RAGAS eval gate
   → Build Docker image → Push to ECR
   → Deploy (Dev → QA → Prod) on ECS/EKS (IaC: Terraform)
   → Secrets Manager / IAM roles
   → API Gateway + Auth → App → LLM (Bedrock) + Vector DB
   → Observability (LangSmith/CloudWatch) + Alerts + Cost budgets
   → Feedback → new eval cases → improve
```
Add: blue-green/canary deploys, rollback, guardrails, PII masking, document-level access control.

---

### Q47. Client gave 60 use cases and wants to build 100 agents — how do you build an Agent Harness and monitor all agents?
**🏢 Company:** TCS (1st Round)

**Answer:** Don't build 100 separate apps. Build an **Agent Platform ("Harness")** — a common runtime so every agent team only defines *purpose, tools, instructions, model, data, output*.

**Harness components:** Agent Registry · Runtime · Orchestrator · Tool/MCP Registry · Prompt Registry · Memory · Guardrails · **Model Gateway** (Bedrock/Azure/local) · Evaluation · Observability · Security/RBAC · Cost management.

**Monitoring (3 levels):**
1. **Infrastructure** – health, uptime
2. **Operations** – latency, error rate, token cost
3. **AI quality** – correctness, groundedness, hallucination, safety, tool accuracy

**Tracing:** OpenTelemetry — every run emits a trace (agent ID, version, session ID, LLM/tool calls, tokens, cost, errors, guardrail events).
**Agent Control Tower:** dashboard → drill from agent → session → trace → individual call, with alerts on thresholds.
**Continuous improvement:** every production failure becomes an eval test case.

**Easy example:** An **airport control tower** — it doesn't fly the planes, but sees every flight, standard rules apply to all, and alerts when something is off.
Or: the harness is the **operating system** for your 100 apps — login, logging, retry, memory and monitoring are built once, not 100 times.

---

### Q48. What is "Harness" (as per your understanding)?
**🏢 Company:** Virtusa

Two meanings, say both:
1. **Agent harness** – the runtime/platform around an LLM (tools, memory, guardrails, evals, observability) that lets it act as a reliable agent (see Q47).
2. **Harness.io** – a CI/CD + AI-agent-observability platform.

Generally: "to harness" = to put tools and components together to extract the full power of AI.

---

### Q49. What is the significance of the `CLAUDE.md` file? Difference between Claude Code and Sonnet?
**🏢 Company:** Virtusa (09-28-2026 round + Virtusa round)

- **`CLAUDE.md`** = a project memory/instructions file that **Claude Code reads at the start of every session** — coding standards, architecture, commands, rules. It keeps behavior consistent without repeating yourself.
- **Claude Code vs Sonnet:** *Sonnet* is a **model** (the brain, by Anthropic). *Claude Code* is an **agentic coding tool/CLI** that uses a model like Sonnet to read your repo, edit files and run commands.

> ✍️ *Correction:* the spreadsheet's sample answer confuses Sonnet with DeepMind's TensorFlow library; in the AI-interview context, Sonnet = Anthropic's Claude model.

**Easy example:** Sonnet = a talented engineer's brain. Claude Code = that engineer sitting at your computer with a keyboard. `CLAUDE.md` = the onboarding note on their desk.

---

## 8. Security, PII & Guardrails

### Q50. How do you mask PII? What if PII is needed for the use case?
**🏢 Company:** General Agent notes (Q16)

- **Don't send PII to the model** – detect (Presidio / Bedrock Guardrails) and replace with tokens: `4111-xxxx` → `<CARD_1>`.
- Restore (de-tokenize) **only** in the final output if allowed.
- If PII is truly needed → **only the tool/backend** (not the LLM) accesses it, with role-based access, audit logs, and **Human-in-the-loop** approval.
- Encrypt at rest/in transit; never log raw PII.

**Easy example:** A bank teller shows you a masked card number `**** 1234`; the real number stays in the secure system.

---

### Q51. How do you handle credit-card payments?
**🏢 Company:** Virtusa (09-28-2026)

- Never store/process raw card data in the AI layer – use a **PCI-DSS compliant payment gateway** (Stripe, Razorpay, etc.) with **tokenization**.
- The app handles only tokens / last-4 digits.
- TLS everywhere, secrets in a vault, audit logging, least-privilege access, fraud checks.

**Easy example:** A hotel valet key — it opens the car door but never reveals your house keys.

---

### Q52. What errors do you see when unauthorized? How do you monitor and fix?
**🏢 Company:** Infosys (Kalyan Garu discussion Q27–28)

- **401 Unauthorized** – missing/expired token → refresh token, fix credentials.
- **403 Forbidden** – no permission → fix IAM role/RBAC.
- Also: expired API key, wrong region/model access in Bedrock, vector-DB document-level access denial.
- **Monitor:** CloudWatch metric filters + alarms on 401/403 counts, audit logs, alert on spikes (possible attack).
- **Fix:** least-privilege IAM, rotate secrets (Secrets Manager), token refresh logic, clear user-facing messages.

---

### Q53. How do you add document-level access control in RAG?
**🏢 Company:** Virtusa (project approach answer)

Store `allowed_roles` / `department` as **metadata** on each chunk; filter in the vector query with the caller's identity so users only retrieve what they're allowed to see.

**Easy example:** A library where the librarian only shows you the shelves your membership card permits.

---

## 9. Model Selection & Project Approach

### Q54. Which models have you used so far?
**🏢 Company:** General Agent notes (Q10)

Llama 3.2 (local, Ollama) · Amazon Bedrock → Claude Sonnet 4.0 and 4.5. Embeddings: Titan / open-source.

---

### Q55. Why did you choose Sonnet? How do you choose which model to use?
**🏢 Company:** Infosys (Kalyan Garu Q23) · Infosys 2nd round · Insight Global

| Requirement | Why it matters in Payment AI |
|---|---|
| Reasoning | Analyze multiple symptoms → RCA |
| Long context | Incident details, logs, reports |
| Instruction following | "Answer only from retrieved evidence" |
| Structured output | RCA + recommendation + confidence + sources |
| Quality vs cost vs latency | Strong reasoning without top-tier price |
| Bedrock integration | Enterprise-friendly access |

> 🗣️ *"I evaluated models on our actual use cases, not just benchmarks."*

**Selection method:** shortlist 2–3 → test on the golden set → compare **quality, latency, cost, context size, privacy** → pick; use a cheaper model for easy routes (model routing).

**Easy example:** Don't hire a surgeon to put on a bandage — match the model size to the task.

---

### Q56. How do you approach implementing an AI project end to end?
**🏢 Company:** Virtusa (09-28-2026)

```
Requirement → Data → Architecture → POC → Evaluation → Implementation
   → Security → Production deployment → Monitoring & continuous improvement
```
1. Understand the business problem, users, risk, latency, cost, success metrics.
2. Check data → decide RAG / agents / APIs / fine-tuning / plain LLM.
3. Build a small POC on real data; measure retrieval quality, accuracy, grounding, latency, cost.
4. Build ingestion, workflow, APIs, guardrails, authz.
5. Add PII protection, observability, eval datasets, CI/CD.
6. Deploy incrementally; improve with feedback.

---

### Q57. What did you discuss in the initial stages with the AI architect? Team size / duration / cloud?
**🏢 Company:** Infosys (Kalyan Garu discussion Q17–Q21)

Prepare your own facts for these; structure:
- **Discussed with architect:** use-case scope, data sources, RAG vs agent choice, vector DB, LLM choice (Bedrock/Sonnet), security, cost, deployment target.
- **Team size / role:** state clearly who you worked with and what *you* owned (design, build, deployment).
- **Duration:** phases (POC → pilot → prod).
- **Cloud:** AWS (Bedrock, S3, ECS/EKS, CloudWatch).

---

## 10. Design Principles & Python Engineering

### Q58. Explain SOLID principles (and how you applied them to AI)
**🏢 Company:** Insight Global (Sedgwick VP Round)

| Letter | Principle | Simple meaning | In AI project |
|---|---|---|---|
| **S** | Single Responsibility | One class = one job | One agent = one responsibility |
| **O** | Open/Closed | Extend without modifying | Add new file loader / retriever without changing core |
| **L** | Liskov Substitution | Child works wherever parent works | Any `LLMProvider` can replace another |
| **I** | Interface Segregation | Small focused interfaces | Don't force a retriever to implement `send_email()` |
| **D** | Dependency Inversion | Depend on abstractions | Swap Ollama ↔ Bedrock or Chroma ↔ FAISS without changing business logic |

**Easy example:** A power socket (interface): any device (implementation) with the right plug works without rewiring the house.

---

### Q59. Refactor `ClaimProcessor` that does validate + generate_pdf + send_email. How to support other databases (SQL Server → MongoDB / Postgres)?
**🏢 Company:** Insight Global (Sedgwick VP Round Q3, Q4)

**Problem:** one class doing many jobs (violates SRP) and hard-wired to SQL Server.

```python
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def save(self, data): ...
    @abstractmethod
    def get(self, id): ...

class SqlServerDatabase(Database): ...
class MongoDatabase(Database):
    def save(self, data): ...   # Mongo implementation
    def get(self, id): ...

class ClaimValidator:  def validate(self, claim): ...
class PdfGenerator:    def generate(self, claim): ...
class EmailSender:     def send(self, claim): ...

class ClaimProcessor:
    def __init__(self, db: Database, validator, pdf, mailer):
        self.db, self.validator, self.pdf, self.mailer = db, validator, pdf, mailer

    def process(self, claim):
        self.validator.validate(claim)
        self.db.save(claim)
        self.mailer.send(self.pdf.generate(claim))
```
Choose the DB through **config file + factory**; the processor never knows which DB it uses (**dependency injection**).

**Easy example:** A phone that accepts any SIM — the phone (processor) doesn't care about the carrier (database).

---

### Q60. In Python, how do you process millions of records?
**🏢 Company:** Infosys (2nd round)

1. **Push work to the database** if possible (SQL aggregation).
2. **Don't load everything** into memory – use chunks/streams.
3. Read only required columns, use efficient dtypes.
4. Batch writes.
5. CPU-heavy → `multiprocessing`; very large → **Spark** / orchestrated pipeline (Airflow, Glue).

```python
import pandas as pd
for chunk in pd.read_csv("large_file.csv", usecols=["id", "status"], chunksize=100_000):
    process(chunk)       # process → release → next 100,000
```
**Easy example:** Eating a big pizza slice by slice instead of trying to swallow it whole.

---

### Q61. Microservice patterns you used? Docker questions?
**🏢 Company:** Virtusa (09-28-2026) · TCS ("Quantum World")

**Microservice patterns:** API Gateway, Service Discovery, Circuit Breaker, Saga (distributed transactions), CQRS, Event-driven / Pub-Sub, Database-per-service, Retry + Backoff, Sidecar.

**Docker network types (3 main):** **bridge** (default, containers on one host), **host** (shares host network), **none** (no network). Others: overlay (multi-host), macvlan.

**Reduce Docker image size:** use slim/alpine base, **multi-stage builds**, `.dockerignore`, combine `RUN` layers, `--no-cache-dir` for pip, remove build tools.

---

### Q62. Data collection in Machine Learning? Predictive maintenance for a robot?
**🏢 Company:** Virtusa

- **Data collection steps:** define problem → identify sources (DB, APIs, sensors, logs) → ensure usable format → clean (missing values, noise) → augment → feed to model → keep collecting feedback.
- **Predictive maintenance (robot):** collect sensor data (vibration, temperature, current) → label past failures → features over time windows → model predicts *failure in the next N hours* → alert maintenance before breakdown.

**Easy example:** A car warns *"service engine in 500 km"* from sensor trends — before it breaks down.

---

## 11. Scenario / Case-Study Questions

### Q63. Use case: buy a shoe on Amazon, the price varies — how do you implement the Agent?
**🏢 Company:** Virtusa (09-28-2026)

```
User goal + target price → Agent loop:
  Tool 1: price_checker (scrape/API)  → get current price
  Tool 2: price_history               → is this a good deal?
  Decision: price <= target? → notify / (with approval) buy
  else → schedule re-check (cron/queue)
Guardrails: spending cap, human approval before purchase, rate limit, audit log.
```
**Easy example:** A personal shopper who keeps checking the shop and calls you when the price drops to your budget.

---

### Q64. Mainframe systems, no SMEs, no documents — how do you implement AI?
**🏢 Company:** Virtusa (09-28-2026)

1. **Discover**: use AI to read the COBOL/JCL code and **generate documentation** (code-to-knowledge).
2. Mine logs, DB schemas, batch jobs to learn behavior.
3. Build a **RAG knowledge base** from generated docs + code + tickets.
4. Validate with whoever still uses the system (business users/testers).
5. Start read-only (explain/assist), keep humans in the loop before any change.

**Easy example:** Reverse-engineering a recipe by tasting the dish and watching the kitchen — then writing the recipe book.

---

### Q65. We have lots of RFPs — what solution would you give to evaluate them? Review specification — what's your solution?
**🏢 Company:** Ovivo Water (Interviewer: Stephen Beck)

**Solution outline:**
1. **Ingest** RFPs/specs (PDF, Word) → parse tables and sections → chunk by headings → vector DB with metadata (client, date, section).
2. **Extraction agent:** pulls requirements, deadlines, compliance clauses into structured JSON.
3. **Matching agent:** compares requirements against company capabilities/past proposals (RAG).
4. **Risk/compliance agent:** flags risky or missing clauses.
5. **Scoring agent:** go/no-go score with reasons and citations.
6. **Human review** and export to a proposal draft.

**Easy example:** A smart assistant that reads a 200-page tender in minutes and hands the manager a one-page summary: *"We meet 42/50 requirements; 3 risks; recommend bid."*

---

### Q66. Payment AI — explain your project in 1 minute
**🏢 Company:** Insight Global / Infosys / Gamestop (project-explanation questions)

> *"I built an AI-first Payment Operations assistant. Ops teams spent hours investigating failed transactions across incident reports, policies and logs. My system classifies the user's intent, retrieves similar incidents and policies using RAG, an RCA agent identifies the root cause, a recommendation agent suggests next steps, and a final step checks the answer against the evidence before returning it with citations. LangGraph orchestrates the agents with shared state, Claude Sonnet on Bedrock provides reasoning, and everything is traced and evaluated with RAGAS and LangSmith. Risky fixes still need human approval."*

**What recommendations does it give (Gamestop Q4):** root cause, ranked fixes, similar past incidents, confidence score, and preventive actions.

---
---

# 🏢 Company-wise Index

| Company / Round | Topics asked |
|---|---|
| **Insight Global — Sedgwick VP Round** | LangGraph orchestration & state (Q31), supervisor vs peer-to-peer (Q35), refactor ClaimProcessor (Q59), DB swap (Q59), SOLID (Q58), precision/recall (Q22), RAGAS (Q21), embedding model choice (Q11), testing/LLM-as-judge (Q23), retries (Q26), vector DB (Q9) |
| **Insight Global — Alexandra** | Production multi-agent system design (Q37) |
| **Infosys (Kalyan Garu Discussion)** | Cost monitoring (Q27), why AI (Q32), chunking (Q5–Q8), state (Q33), intent (Q38), confidence score (Q15), ranking (Q14), Chroma vs FAISS (Q10), semantic/recursive chunking (Q6–Q7), Langfuse (Q43), why many agents (Q28), temperature (Q18), team/cloud (Q57), cost control (Q27), why Sonnet (Q55), optimize RAG (Q24), fine-tuning (Q4), embeddings (Q12), unauthorized errors (Q52), observability / CloudWatch / millions of records (Q43, Q60), choose model (Q55) |
| **Virtusa (Ravishankar)** | ML data collection (Q62), Harness (Q48), predictive maintenance (Q62), semantic & hybrid search (Q13), Claude Code vs Sonnet (Q49) |
| **Virtusa — 28-Sep-2026** | Amazon shoe agent (Q63), mainframe/no SME (Q64), CLAUDE.md (Q49), hallucination in prod (Q20), microservice patterns (Q61), credit card payments (Q51), approach to AI projects (Q56) |
| **Gamestop — L1** | LangGraph vs LangChain (Q29), why agent for classification (Q30), RAG pipeline (Q1), recommendations (Q66) |
| **TCS — 1st Round** | Agent Harness for 100 agents (Q47) |
| **TCS — Quantum World** | MCP (Q39), Docker networks & image size (Q61), retrieval search type (Q13), Bedrock data storage (Q42), data access (Q41), FastAPI for agents (Q41) |
| **Ovivo Water** | RFP evaluation solution (Q65) |
| **General Prep (RAG / Agent / MyNotes sheets)** | Chunking, hallucination, context size, prompt optimization, memory, caching, RAGAS, MCP, LangSmith, scaling, PII, LangGraph architecture, intent classification |

---

# 🧠 One-line Cheat-sheet

| Topic | Remember this |
|---|---|
| **RAG** | Open-book exam: *retrieve evidence → generate answer* |
| **Chunking** | Cut the book into pages with overlap so no sentence is cut in half |
| **Embedding** | Numbers that capture *meaning* |
| **Vector DB** | Library arranged by meaning |
| **Hybrid search** | Keyword (exact) + semantic (meaning) |
| **Re-ranking** | Second, more careful interview of the top candidates |
| **Hallucination fix** | Trace → find failing layer → fallback → golden test → measured fix |
| **Temperature** | Creativity dial: 0 for facts |
| **Precision vs Recall** | Quality of what you returned vs completeness of what you found |
| **RAGAS** | Faithfulness · Relevancy · Context precision · Context recall |
| **LangGraph** | Manager (graph) + workers (nodes) + notebook (state) |
| **Supervisor** | Manager assigns work; **Peer-to-peer** = employees coordinate directly |
| **Short vs long-term memory** | Sticky note today vs diary for next month |
| **MCP** | USB-C for AI tools |
| **Agent Harness** | Operating system for many agents; Control Tower to monitor them |
| **Observability** | Black box + dashboard (traces, tokens, cost, errors) |
| **PII** | Mask before the LLM; real data stays in the secure tool |
| **Retries** | Exponential backoff, max attempts, graceful fallback |
| **Intent flow** | Question → Intent → Confidence → Route → Agent → RAG → Grounding → Answer |
