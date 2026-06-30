# 🧠 Multimodal Agentic RAG System

A production-grade document intelligence platform built with **LangGraph**-based agentic orchestration — featuring a **Supervisor Agent** coordinating a **RAG Agent** and a **Web Search Agent** for dynamic, context-aware retrieval and response generation.

---

## 🏗️ Architecture Overview

```
User Query
    │
    ▼
Supervisor Agent (LangGraph)
    ├── RAG Agent ──────────────► Vector DB (PostgreSQL pgvector)
    │        └── Retrieval Strategy Selection
    │                ├── Vector Search
    │                ├── Hybrid Search (Vector + FTS)
    │                ├── Multi-Query Vector
    │                └── Multi-Query Hybrid + RRF Re-ranking
    │
    └── Web Search Agent ───────► Real-time Web Results
                                        │
                                        ▼
                              Multimodal LLM Inference
                              (Groq LLaMA 4 Scout)
                                        │
                                        ▼
                              Cited, Grounded Response
```

---

## ✨ Key Features

### Agentic Orchestration
- **Supervisor Agent** dynamically routes queries to the appropriate subagent based on context
- **RAG Agent** handles document-grounded retrieval with multimodal context injection
- **Web Search Agent** handles real-time information needs beyond the document corpus
- Full multi-step reasoning with LangGraph state management

### Multimodal Document Ingestion
Supports **PDF, DOCX, PPT, MD, TXT, CSV, Excel, and websites** — with zero context loss across formats

| Format | Processing Strategy |
|--------|-------------------|
| PDF | Unstructured.io layout-aware element chunking + pdfplumber table extraction |
| DOCX / PPT | Unstructured.io element-based parsing |
| Images | Extracted and stored in S3, retrieved at inference time |
| Tables | HTML-preserved for structure-aware LLM injection |
| CSV / Excel | Tabular context preserved without flattening |
| Websites | ScrapingBee-powered web scraping pipeline |

### Retrieval Engine
- **768-dim Gemini embeddings** stored in PostgreSQL with dual indexing:
  - **HNSW index** (cosine similarity) for sub-400ms vector search
  - **GIN index** for full-text search (FTS)
- **4 configurable retrieval strategies:**
  1. Pure Vector Search
  2. Hybrid Search (Vector + BM25)
  3. Multi-Query Vector
  4. Multi-Query Hybrid with **Reciprocal Rank Fusion (RRF)** re-ranking
- Dual embedding support — **OpenAI** (cloud) or **local sentence-transformers** (zero latency, zero cost)

### Production-Grade Infrastructure
- **FastAPI** backend with async endpoints
- **Celery + Redis** for async document ingestion with real-time status tracking
- **Structured logging** via `structlog` for observability
- **RAGAS evaluation** integrated for hallucination measurement and retrieval quality scoring
- **Docker** containerized, scalable from day one

### LLM Inference
- **Groq LLaMA 4 Scout** for fast multimodal inference
- Structured prompt injection combining:
  - Text chunks
  - HTML tables
  - S3-fetched images
- Response includes **citations** grounded in source documents

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Agentic Framework | LangGraph, LangChain |
| LLM Inference | Groq (LLaMA 4 Scout) |
| Embeddings | Gemini / sentence-transformers (all-MiniLM-L6-v2) |
| Vector DB | PostgreSQL + pgvector (HNSW + GIN) |
| Document Processing | Unstructured.io, pdfplumber, YOLO |
| Storage | AWS S3 (images), PostgreSQL (vectors + metadata) |
| Async Processing | Celery + Redis |
| Backend | FastAPI (Python) |
| Frontend | Next.js + Clerk (auth) |
| Evaluation | RAGAS |
| Logging | structlog |
| Deployment | Docker, AWS ECS |

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Vector retrieval latency | < 400ms |
| Embedding dimensions | 768 |
| Supported file formats | 8+ |
| Retrieval strategies | 4 |
| Evaluation framework | RAGAS (faithfulness, relevancy, context precision) |

---

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.10+
PostgreSQL 15+ with pgvector extension
Redis
Docker (recommended)
```

### Environment Setup
```bash
git clone https://github.com/tj003/multmodal_rag_dev.git
cd multmodal_rag_dev
cp .env.example .env
# Fill in your API keys: Groq, Gemini, AWS, ScrapingBee
```

### Run with Docker
```bash
docker-compose up --build
```

### Run locally
```bash
pip install -r requirements.txt
# Start Celery worker
celery -A app.celery_app worker --loglevel=info
# Start FastAPI
uvicorn app.main:app --reload
```

---

## 📁 Project Structure

```
server/
├── src/
│   ├── agents/
│   │   ├── simple_agent/
│   │   │   └── agent.py                  # Base agent implementation
│   │   └── supervisor_agent/
│   │       └── agent.py                  # LangGraph Supervisor Agent (orchestrates RAG + Web Search)
│   ├── rag/
│   │   ├── ingestion/
│   │   │   ├── index.py                  # Ingestion pipeline entry point
│   │   │   └── utils.py                  # Unstructured.io + pdfplumber chunking
│   │   └── retrieval/
│   │       ├── index.py                  # Retrieval strategy selector
│   │       └── utils.py                  # RRF re-ranking + hybrid search utils
│   ├── routers/
│   │   ├── chats.py                      # Chat endpoints
│   │   ├── files.py                      # File upload + ingestion trigger
│   │   ├── projects.py                   # Project management
│   │   └── users.py                      # User endpoints
│   ├── services/
│   │   ├── awsS3.py                      # S3 image storage
│   │   ├── celery.py                     # Async task queue
│   │   ├── clerkAuth.py                  # Auth via Clerk
│   │   ├── llm.py                        # LLM inference (Groq LLaMA 4 Scout)
│   │   ├── supabase.py                   # PostgreSQL + pgvector client
│   │   └── webScrapper.py                # ScrapingBee web scraping
│   ├── config/
│   │   ├── index.py                      # Environment config
│   │   └── logging.py                    # structlog setup
│   ├── middleware/
│   │   └── logging_middleware.py         # Request/response logging
│   ├── models/
│   │   └── index.py                      # Pydantic models
│   └── server.py                         # FastAPI app entrypoint
├── evaluation/
│   ├── datasets/
│   │   └── ragas_evaluation_dataset.json # Evaluation dataset
│   ├── scripts/
│   │   ├── collect_data.py               # Data collection for eval
│   │   └── ragas_evaluation_script.py    # RAGAS metrics runner
│   └── ragas_experimentation.ipynb       # Evaluation experiments
├── supabase/
│   ├── migrations/
│   │   ├── 20260322183027_initial_schema.sql      # DB schema + pgvector setup
│   │   └── 20260429065908_chunk_search_functions.sql  # Hybrid search SQL functions
│   └── config.toml
├── notebooks/
│   └── simple_agent.ipynb                # Agent experimentation
├── logs/
│   ├── application.log
│   └── worker.log
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 🧪 Evaluation

RAGAS metrics tracked in production:

- **Faithfulness** — Are answers grounded in retrieved context?
- **Answer Relevancy** — Does the answer address the question?
- **Context Precision** — Is retrieved context relevant?
- **Context Recall** — Is all necessary context being retrieved?

---

## 🔑 Key Engineering Decisions

**1. Dual embedding support**
Supporting both OpenAI and local sentence-transformers without changing retrieval logic. Local embeddings reduced latency from 15s → 0.1s for India-based deployment.

**2. Element-based chunking over naive splitting**
Unstructured.io preserves document structure (headers, tables, figures) as discrete elements. This prevents context bleeding across sections that naive character splitting causes.

**3. HNSW + GIN dual indexing**
HNSW for approximate nearest neighbor vector search, GIN for lexical full-text search. Together they power hybrid retrieval without a separate search engine.

**4. RRF for multi-strategy re-ranking**
Reciprocal Rank Fusion combines rankings from multiple retrieval strategies without requiring score normalization — more robust than weighted sum approaches.

**5. Async ingestion with Celery**
Document processing is CPU and I/O intensive. Offloading to Celery workers keeps the API responsive and allows horizontal scaling of ingestion independently from inference.

---

## 📄 License

MIT License

---

*Built by [Tushar Jadhav](https://linkedin.com/in/tusharj13) — AI/ML Engineer*
