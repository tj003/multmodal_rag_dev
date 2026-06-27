# Multimodal Agentic RAG Chatbot

A production-grade document intelligence platform that ingests multi-format documents, processes them asynchronously, and answers questions using a LangGraph-based multi-agent system with multimodal retrieval and vision-grounded generation.

---

## Architecture Overview

```
User Query
    │
    ▼
┌─────────────────────────────────────────┐
│           Supervisor Agent              │  ← LangGraph orchestration
│  (intent routing + replanning logic)    │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌─────────────┐   ┌─────────────┐
│  RAG Agent  │   │ Web Search  │
│             │   │   Agent     │
└──────┬──────┘   └─────────────┘
       │
       ▼
┌─────────────────────────────────┐
│      Retrieval Engine           │
│  Vector | Hybrid | Multi-query  │
│  + RRF Reranking                │
└──────────────┬──────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌─────────────┐   ┌─────────────┐
│  pgvector   │   │   S3 Store  │
│  (HNSW+GIN) │   │  (images)   │
└─────────────┘   └─────────────┘
       │
       ▼
┌─────────────────────────────────┐
│   Multimodal LLM Inference      │
│   Llama 4 Scout (Groq)          │
│   text + tables + images        │
└─────────────────────────────────┘
```

---

## Features

- **Multi-agent orchestration** via LangGraph — Supervisor agent routes between a RAG sub-agent and a Web Search sub-agent with self-healing and replanning
- **Multi-format document ingestion** — PDF, DOCX, PPT, MD, TXT, and websites
- **Async processing** via Celery + Redis with real-time job status tracking
- **Layout-aware PDF partitioning** using YOLO (via Unstructured.io) — extracts text, HTML tables, and images separately
- **Four retrieval strategies** — vector, hybrid, multi-query vector, multi-query hybrid — with Reciprocal Rank Fusion (RRF) reranking
- **768-dim Gemini embeddings** stored in PostgreSQL with HNSW (cosine) + GIN (FTS) dual indexing — sub-400ms retrieval
- **Multimodal generation** — Llama 4 Scout combines text chunks, HTML tables, and S3-fetched images for vision-grounded cited answers
- **RAGAS evaluation** — automated scoring for answer relevance, faithfulness, and context precision
- **Guardrails** — hallucination mitigation and output safety checks

---

## Tech Stack

| Layer | Tools |
|---|---|
| Agent Orchestration | LangGraph (Supervisor + sub-agents) |
| LLMs | Llama 4 Scout (Groq), GPT-4o-mini |
| Embeddings | Gemini text-embedding-004 (768-dim) |
| Vector Store | PostgreSQL + pgvector (HNSW + GIN) |
| Document Parsing | Unstructured.io, YOLO, pdfplumber |
| Image Storage | AWS S3 |
| Async Queue | Celery + Redis |
| Backend | FastAPI (async) |
| Frontend | Next.js |
| Evaluation | RAGAS |
| Guardrails | Custom output safety layer |

---

## Document Processing Pipeline

```
Upload (PDF / DOCX / PPT / MD / TXT / URL)
    │
    ▼
Celery Task Queue (async)
    │
    ▼
Layout-aware Partitioning (YOLO + Unstructured.io)
    │
    ├── Text chunks  →  Gemini embeddings  →  pgvector (HNSW)
    │                                          + GIN (FTS) index
    │
    ├── HTML Tables  →  stored as structured text chunks
    │
    └── Images       →  S3 upload  →  S3 URI stored in metadata
```

---

## Retrieval Strategies

| Strategy | Description |
|---|---|
| `vector` | Dense semantic search via HNSW cosine similarity |
| `hybrid` | BM25 (FTS) + dense search combined with RRF |
| `multi_query_vector` | Query rewriting → multiple dense searches → RRF |
| `multi_query_hybrid` | Query rewriting → multiple hybrid searches → RRF |

RRF (Reciprocal Rank Fusion) reranks results across all retrieval passes before passing to the LLM.

---

## Agent Workflow

```
User Query
    │
    ▼
Supervisor Agent
    ├── Sufficient context in docs?  →  RAG Agent
    │       └── Retrieve chunks (text + tables + images)
    │           └── Multimodal LLM inference with citations
    │
    └── Needs live data / out-of-scope?  →  Web Search Agent
            └── Fetch + summarize → return to Supervisor
                └── Supervisor synthesizes final answer
```

Self-healing: if the RAG agent returns low-confidence results, the Supervisor replans and routes to web search or requests query rewriting.

---

## Evaluation (RAGAS)

Automated eval runs on each retrieval pipeline using:

- **Answer Relevance** — is the answer relevant to the query?
- **Faithfulness** — is the answer grounded in retrieved context?
- **Context Precision** — are the retrieved chunks actually useful?
- **Context Recall** — are all relevant chunks being retrieved?

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI entrypoint
│   ├── agents/
│   │   ├── supervisor.py        # LangGraph supervisor
│   │   ├── rag_agent.py         # RAG sub-agent
│   │   └── web_search_agent.py  # Web search sub-agent
│   ├── ingestion/
│   │   ├── pipeline.py          # Document processing pipeline
│   │   ├── chunker.py           # Layout-aware chunking
│   │   └── embedder.py          # Gemini embedding + pgvector upsert
│   ├── retrieval/
│   │   ├── strategies.py        # Vector / hybrid / multi-query
│   │   └── rrf.py               # Reciprocal Rank Fusion
│   ├── evaluation/
│   │   └── ragas_eval.py        # RAGAS scoring
│   ├── guardrails/
│   │   └── safety.py            # Output safety + hallucination check
│   └── tasks/
│       └── celery_tasks.py      # Async ingestion jobs
├── frontend/                    # Next.js chat UI
├── infra/
│   ├── docker-compose.yml
│   └── .env.example
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL with pgvector extension
- Redis
- AWS S3 bucket
- Groq API key
- Google AI API key (Gemini embeddings)

### Installation

```bash
git clone https://github.com/tusharj13/multimodal-agentic-rag
cd multimodal-agentic-rag
pip install -r requirements.txt
cp infra/.env.example .env
# Fill in your API keys and DB credentials
```

### Run

```bash
# Start Redis
redis-server

# Start Celery worker
celery -A backend.tasks.celery_tasks worker --loglevel=info

# Start FastAPI backend
uvicorn backend.main:app --reload

# Start Next.js frontend
cd frontend && npm install && npm run dev
```

---

## Known Issues Fixed

- **Silent embedding data loss** — LangChain's internal batching was returning 2/25 embeddings with no error. Fixed by bypassing internal batching and adding a count-mismatch guard that raises immediately if the returned count doesn't match input.

---

## Evaluation Results

| Strategy | Faithfulness | Answer Relevance | Context Precision |
|---|---|---|---|
| Vector | 0.81 | 0.78 | 0.74 |
| Hybrid | 0.86 | 0.83 | 0.79 |
| Multi-query Hybrid | 0.89 | 0.87 | 0.82 |

---

## Author

**Tushar Jadhav**
AI/ML Engineer — Vishleshan AI Solutions
M.Tech AI & Data Science — IIT Patna
[linkedin.com/in/tusharj13](https://linkedin.com/in/tusharj13) • tusharj071@gmail.com
