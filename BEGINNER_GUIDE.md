# Beginner's Guide to the AI-Powered Investor Intelligence Platform

Welcome! This guide explains the whole project from scratch — what it does, how the
pieces fit together, and how to run it yourself — assuming no prior knowledge of
RAG, vector search, or the specific libraries used here.

---

## 1. What Does This Project Do?

In plain English: you upload a company's **annual report (PDF)**, and the app:

1. Reads the PDF and converts it to text (Markdown).
2. Splits that text into small, meaningful chunks.
3. Turns each chunk into a list of numbers (an "embedding") that captures its meaning.
4. Stores those chunks + numbers in a searchable database (a "vector store").
5. Asks an AI model (Azure OpenAI / GPT) to read the most relevant chunks and pull out
   key financial numbers — Revenue, Net Income, Cash Flow, Risks, Growth Drivers, etc.
6. Saves those numbers into a regular SQL database.
7. Shows everything on a web **dashboard**, and lets you **chat** with the documents
   ("Why did revenue increase?").

This pattern — "search your own documents, then let an AI answer using only what it
found" — is called **RAG: Retrieval-Augmented Generation**. It's how you get an AI to
answer questions about *your* private documents instead of just general knowledge.

---

## 2. Key Concepts (Glossary for Beginners)

| Term | Meaning |
|---|---|
| **LLM** | Large Language Model — the AI (e.g., GPT-4o) that reads text and generates answers. |
| **Embedding** | A way to turn text into a list of numbers (a vector) so a computer can measure how "similar in meaning" two pieces of text are. |
| **Vector Store / Vector Search** | A database built to store embeddings and quickly find the ones most similar to a query. Here it's **Azure AI Search**. |
| **RAG (Retrieval-Augmented Generation)** | Retrieve relevant chunks of text first, then feed them to the LLM so it answers based on real data instead of guessing. |
| **Chunking** | Splitting a big document into smaller pieces, since LLMs and vector search work better on small, focused pieces of text. "Semantic chunking" splits based on meaning, not just fixed character counts. |
| **KPI** | Key Performance Indicator — a financial metric like Revenue or Net Income. |
| **Structured Output** | Instead of letting the AI reply in free-form text, you force it to reply in a JSON structure matching a schema (defined here with **Pydantic** models) so your code can safely use the values. |
| **FastAPI** | The Python web framework used to build the backend API and serve the dashboard. |
| **Docker / Container** | A way to package the app with everything it needs so it runs identically anywhere. |
| **Kubernetes (AKS)** | A system for running containers at scale in the cloud (Azure Kubernetes Service). |
| **PostgreSQL** | The relational (SQL) database used to store the final extracted KPI numbers. |

---

## 3. Technology Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn
- **AI:** Azure OpenAI (chat model + embedding model), LangChain (`langchain-openai`,
  `langchain-experimental` for semantic chunking)
- **Search / Vector DB:** Azure AI Search
- **Database:** PostgreSQL (via SQLAlchemy + psycopg2)
- **PDF Processing:** `pymupdf4llm` (PDF → Markdown)
- **Frontend:** Server-rendered HTML dashboard (Jinja2 templates + `static/style.css`)
- **Packaging:** `uv` (a fast Python package/dependency manager)
- **Deployment:** Docker → Azure Container Registry (ACR) → Azure Kubernetes Service (AKS)

---

## 4. Project Folder Structure

```
.
├── app.py                     # Main FastAPI app (dashboard UI + APIs) — run this to start the app
├── main.py                    # A second, smaller FastAPI app (API-only, no UI) — see note below
├── config/settings.yaml        # Non-secret config placeholders
├── data/
│   ├── raw_pdfs/               # Where you drop annual report PDFs
│   └── markdown/                # Auto-generated Markdown versions of the PDFs
├── ingestion/
│   ├── pdf_to_markdown.py      # Step 1: PDF -> Markdown
│   ├── semantic_chunker.py     # Step 2: Markdown -> semantic chunks
│   └── ingest_documents.py     # Orchestrates the full ingestion pipeline end-to-end
├── llm/
│   └── azure_openai.py         # Talks to Azure OpenAI; gets structured JSON answers
├── vectorstore/
│   ├── azure_ai_search.py      # Uploads chunks to Azure AI Search + retrieves them
│   └── create_index.py         # Creates the Azure AI Search index (schema)
├── rag/
│   ├── kpi_extractor_rag.py    # Step 3: retrieve context -> ask LLM -> extract KPIs
│   └── retrieval_debug.py      # CLI tool to manually test vector search queries
├── database/
│   ├── postgres_sql.py         # DB connection/engine + "create database if missing"
│   ├── create_table.py         # Creates the `financial_metrics` table
│   ├── save_metrics.py         # Saves extracted KPIs into PostgreSQL
│   └── metrics.py              # Reads the latest KPIs per company for the dashboard
├── routes/
│   ├── ingestion.py             # POST /api/upload — upload a PDF and run the full pipeline
│   ├── chat.py                  # POST /api/chat — RAG-based chatbot endpoint
│   ├── dashboard.py             # GET /api/metrics — used by main.py (API-only variant)
│   └── health.py                # GET /health — health check endpoint
├── templates/dashboard.html     # The dashboard's HTML page
├── static/style.css             # Dashboard styling
├── dockerfile                   # Container build instructions
├── k8s/                         # Kubernetes deployment + service manifests
├── requirements.txt              # Python dependencies
└── project_journey.md            # Development log/roadmap (phases of the project)
```

> **Note on `app.py` vs `main.py`:** There are two entry points. `app.py` is the real
> app — it serves the dashboard UI at `/`, wires up upload + chat routes, and creates
> the database/table/search-index on startup. `main.py` is a smaller, API-only
> FastAPI app (no UI, no startup DB setup) that only exposes `/health` and
> `/api/metrics`. When following this guide, **run `app.py`**.

---

## 5. How the Pieces Connect (End-to-End Flow)

```
                 ┌─────────────┐
  Upload PDF ──▶ │  PDF file    │ (data/raw_pdfs/2024_Apple.pdf)
                 └──────┬──────┘
                        │ pdf_to_markdown.py (PyMuPDF4LLM)
                        ▼
                 ┌─────────────┐
                 │ Markdown text│ (data/markdown/2024_Apple.md)
                 └──────┬──────┘
                        │ semantic_chunker.py (LangChain SemanticChunker)
                        ▼
                 ┌─────────────┐
                 │ Text chunks  │
                 └──────┬──────┘
                        │ azure_ai_search.py: embed each chunk + upload
                        ▼
                 ┌───────────────────┐
                 │ Azure AI Search    │  (vector store: content + embedding + company/year)
                 └──────┬─────────────┘
                        │ kpi_extractor_rag.py: retrieve relevant chunks for company/year
                        ▼
                 ┌───────────────────┐
                 │ Azure OpenAI (GPT) │  -> returns structured JSON (Revenue, Net Income, ...)
                 └──────┬─────────────┘
                        │ save_metrics.py
                        ▼
                 ┌───────────────────┐
                 │ PostgreSQL          │  (financial_metrics table)
                 └──────┬─────────────┘
                        │ metrics.py / dashboard route
                        ▼
                 ┌───────────────────┐
                 │ Dashboard (HTML)   │  <-- what you see in the browser
                 └───────────────────┘
```

Separately, the **chat** feature (`routes/chat.py`) skips the "extract KPIs" step: it
takes your question, searches Azure AI Search for relevant chunks, and asks GPT to
answer the question using only that retrieved context.

---

## 6. Walking Through Each Module

### 6.1 `ingestion/pdf_to_markdown.py`
Uses the `pymupdf4llm` library to turn a PDF's pages into clean Markdown text
(preserving headings/tables reasonably well, which helps the LLM later). Can convert
a single file or an entire folder of PDFs.

### 6.2 `ingestion/semantic_chunker.py`
Reads the Markdown and uses LangChain's `SemanticChunker`. Unlike naive chunking
(e.g., "every 500 characters"), this measures how similar consecutive sentences are
(using embeddings) and splits where the *topic* changes — so each chunk stays
coherent and self-contained.

### 6.3 `vectorstore/create_index.py`
Defines the schema of the Azure AI Search index: `id`, `company`, `year`,
`source_file`, `content` (searchable text), and `content_vector` (the 1536-dimension
embedding vector, matching OpenAI's `text-embedding-ada-002` model). This runs once
automatically on app startup (`app.py`'s `startup_event`).

### 6.4 `vectorstore/azure_ai_search.py`
Two things live here:
- `AzureAISearchVectorStore.upload_chunks(...)` — embeds each chunk and uploads it
  (content + vector + metadata) to the Azure index.
- `Retriever` — given a query (and optionally a company/year filter), searches the
  index and returns matching chunks as simple objects with `.page_content`.

### 6.5 `llm/azure_openai.py`
A thin wrapper around the Azure OpenAI SDK. `get_structured_completion(prompt,
response_model)` sends a prompt and asks the model to reply in the exact shape of a
given Pydantic model (structured output). If the deployed model doesn't support
strict structured outputs, it falls back to asking for plain JSON text and parsing it
manually.

### 6.6 `rag/kpi_extractor_rag.py`
The core RAG logic for KPI extraction:
1. `retrieve_context(...)` — pulls ~20 relevant chunks about financial statements,
   risks, and growth for a given company/year.
2. `build_extraction_prompt(...)` — builds a prompt asking the LLM to extract 8
   specific fields (Revenue, Net Income, Operating Income, Cash Flow, Total Assets,
   Total Liabilities, Risk Factors, Growth Drivers) **only** from that context.
3. `extract_financial_metrics(...)` — calls the LLM and returns the parsed
   `FinancialMetrics` model as a dictionary.

### 6.7 `ingestion/ingest_documents.py`
The orchestrator that chains everything above: PDF → Markdown → chunks → upload to
search → extract KPIs → save to PostgreSQL. It also guesses the `company` and `year`
from the PDF's filename (e.g., `2024_Apple.pdf` → company="Apple", year="2024" — so
**name your PDFs this way**).

### 6.8 `database/` folder
- `postgres_sql.py` — builds the DB connection string from environment variables and
  can create the target database if it doesn't exist yet.
- `create_table.py` — creates the `financial_metrics` table.
- `save_metrics.py` — inserts one row of extracted KPIs per ingested report.
- `metrics.py` — reads back the *latest* row per (company, year) for display.

### 6.9 `routes/` folder (the API)
- `POST /api/upload` — accepts a PDF file upload, saves it to `data/raw_pdfs/`, and
  runs the full ingestion pipeline synchronously.
- `POST /api/chat` — RAG chatbot: retrieves relevant chunks and asks GPT to answer.
- `GET /health` — simple health check (used by Kubernetes/monitoring).
- `GET /` (in `app.py`) — renders the dashboard with the latest KPIs per company.
- `GET /api/metrics` — returns the KPI data as JSON.

### 6.10 `templates/dashboard.html` + `static/style.css`
A server-rendered dashboard (via Jinja2) showing metrics per company/report, styled
with plain CSS — no separate frontend framework/build step required.

---

## 7. Environment Variables You Need

Create a `.env` file in the project root (never commit this file) with:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=<your-gpt-deployment-name>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<your-embedding-deployment-name>

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
AZURE_SEARCH_API_KEY=<your-key>
AZURE_SEARCH_INDEX_NAME=investor-intelligence

# PostgreSQL
POSTGRES_HOST=<your-db-host>
POSTGRES_PORT=5432
POSTGRES_USER=<your-db-user>
POSTGRES_PASSWORD=<your-db-password>
POSTGRES_DATABASE=investor_intelligence
```

`config/settings.yaml` shows the same fields but is just a non-secret reference —
actual secrets always come from `.env` / environment variables, never from that file.

---

## 8. Running the Project Locally (Step by Step)

### 8.1 Install `uv` (a fast Python package manager)

macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 8.2 Create and activate a virtual environment
```bash
uv venv
source .venv/bin/activate
```

### 8.3 Install dependencies
```bash
uv pip install -r requirements.txt
```

### 8.4 Set up your `.env` file
Copy the variables from Section 7 above and fill in your real Azure/PostgreSQL
credentials.

### 8.5 Run the app
```bash
python app.py
```
This starts the server at `http://localhost:8000`. On startup it will:
- Create the PostgreSQL database (if missing)
- Create the `financial_metrics` table (if missing)
- Create the Azure AI Search index (if missing)

Visit `http://localhost:8000/` in your browser to see the dashboard.

### 8.6 Upload a report and see it work
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@data/raw_pdfs/2024_Apple.pdf"
```
Or use the dashboard UI if it exposes an upload control. Name your PDF like
`2024_Apple.pdf` (year first) so the company/year get parsed correctly.

### 8.7 Ask a question via chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Why did revenue increase?", "company": "Apple", "year": 2024}'
```

### 8.8 Useful debugging script
Test raw vector search results without going through the LLM:
```bash
python -m rag.retrieval_debug "Apple revenue 2024"
```

---

## 9. Running Individual Pipeline Steps Manually

Each ingestion step can also be run/tested on its own:

```bash
# Convert all PDFs in data/raw_pdfs/ to markdown
python ingestion/pdf_to_markdown.py

# Try semantic chunking on one markdown file (edit the path inside the script first)
python ingestion/semantic_chunker.py

# Run the full pipeline over every PDF in data/raw_pdfs/
python ingestion/ingest_documents.py

# Manually extract KPIs for a company/year already indexed in Azure Search
python rag/kpi_extractor_rag.py
```

---

## 10. Deployment (Docker + Kubernetes)

- **`dockerfile`** builds a lightweight Python 3.12 image, installs dependencies with
  `uv`, copies the code, and runs `uvicorn app:app` on port 8000.
- **`k8s/deployment.yaml`** and **`k8s/service.yaml`** deploy that container image to
  Azure Kubernetes Service (AKS), pulling secrets from a Kubernetes Secret
  (`invint-secrets`) instead of a `.env` file.
- See [`CICD_Deployment_Guide.md`](CICD_Deployment_Guide.md) and
  [`deployment-Document.md`](deployment-Document.md) in the repo root for the full
  CI/CD pipeline and deployment walkthrough (build → push to ACR → deploy to AKS).

Basic local Docker test:
```bash
docker build -t investor-intelligence .
docker run --env-file .env -p 8000:8000 investor-intelligence
```

---

## 11. Project Status / Roadmap

See [`project_journey.md`](project_journey.md) for the phase-by-phase build log
(dataset prep → PDF conversion → chunking → Azure OpenAI → Azure Search → KPI
extraction → SQL storage → FastAPI → frontend → RAG pipeline → containerization →
AKS deployment). It's a useful map of *why* each module exists and in what order it
was built.

---

## 12. Common Beginner Questions

**Q: Why convert PDF to Markdown instead of just extracting raw text?**
Markdown preserves structure (headings, tables, lists) better than raw text
extraction, which helps both semantic chunking and the LLM understand context (e.g.,
knowing "Revenue" is a table row, not a random word).

**Q: Why chunk the document instead of feeding the whole PDF to GPT?**
LLMs have a limited context window and cost money per token. Chunking + retrieval
lets you fetch only the ~20 most relevant pieces of a potentially huge report instead
of sending the whole document every time.

**Q: What's the difference between the vector store (Azure AI Search) and PostgreSQL?**
Azure AI Search stores raw text chunks + embeddings for *semantic search* ("find text
similar to this question"). PostgreSQL stores the final, structured KPI numbers for
*fast, exact lookups* to power the dashboard (e.g., "give me Apple's 2024 revenue").

**Q: What does "structured output" actually protect against?**
Without it, the LLM might reply in prose ("Apple's revenue was about $391 billion...")
which is hard to parse reliably. Structured output forces a strict JSON shape
(defined by the `FinancialMetrics` Pydantic model) so the code can safely read
`metrics["revenue"]` every time.

**Q: I don't have Azure — can I test this?**
Azure OpenAI, Azure AI Search, and Azure PostgreSQL are all required as configured.
Without valid credentials for all three, the app will fail on startup or when
processing documents/chat requests.
