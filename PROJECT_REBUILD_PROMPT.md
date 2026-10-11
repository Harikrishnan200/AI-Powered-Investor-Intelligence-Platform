# Prompt: Build "Investor Intelligence" (free-of-cost RAG platform, FastAPI + React)

Copy everything below the line into Claude Code (or any coding agent) inside an empty folder.

---

## Role and goal

You are a senior engineer helping me build a portfolio project that I will put on my resume and explain line by line in interviews. Build an **AI-powered investor intelligence platform**: a user uploads company annual-report PDFs, the system extracts key financial KPIs, stores them, and lets the user chat with the reports (RAG).

**Hard constraints**

1. **Completely free of cost.** No Azure/AWS/OpenAI paid services. Use only:
   - LLM: **Groq API** (free tier, key in `GROQ_API_KEY`)
   - Vector DB: **Qdrant** (embedded local mode, `QdrantClient(path="./qdrant_data")`; optional `QDRANT_URL` for Qdrant Cloud free tier)
   - Embeddings: **FastEmbed** (`BAAI/bge-small-en-v1.5`, 384 dims, local CPU, no key)
   - Relational DB: **PostgreSQL** (local install or Docker)
   - Frontend: **React + Vite** (plain JavaScript, no TypeScript, no UI framework)
2. **Simple, readable, production-style code.** I must be able to explain every file. Prefer flat modules and plain functions over class hierarchies, factories, dependency-injection frameworks, or abstract base classes. No file over ~150 lines of logic. One responsibility per file. Short docstrings, almost no comments (only for non-obvious "why").
3. Python 3.12, FastAPI, SQLAlchemy (raw SQL via `text()` is fine), Pydantic v2.
4. Never commit secrets. Ship `.env.example`.

## What the product does

1. **Upload** a PDF (e.g. `2024_Apple.pdf`; filename convention `<year>_<company>.pdf`).
2. **Ingest pipeline:** PDF -> Markdown (`pymupdf4llm`) -> semantic chunks (`langchain_experimental.SemanticChunker` using the local embeddings) -> embed -> upsert into Qdrant with payload `{company, year, source_file, content}`.
3. **KPI extraction (RAG):** retrieve the most relevant chunks for that company+year, ask Groq (JSON mode) for exactly these keys: `Revenue, Net Income, Operating Income, Cash Flow from Operating Activities, Total Assets, Total Liabilities, Top Risk Factors, Top Growth Drivers`. Validate with a Pydantic model. Save to Postgres table `financial_metrics`.
4. **Dashboard (React):** KPI cards comparing companies (with proportional bars), a "qualitative deep-dive" panel (growth drivers / risk factors per selected company), upload dropzone with progress, and a collapsible **AI Analyst chat panel** with an optional company filter.
5. **Chat (RAG):** embed question -> Qdrant similarity search (optionally filtered by company+year) -> Groq answer grounded in retrieved context; say "not enough data" when context is insufficient.

## Architecture (keep exactly this simple)

```
investor-intelligence/
├── backend/
│   ├── main.py                 # FastAPI app, CORS, router registration, startup init
│   ├── config.py               # loads .env once; exposes settings (GROQ_MODEL, QDRANT_*, POSTGRES_*)
│   ├── routes/
│   │   ├── upload.py           # POST /api/upload
│   │   ├── chat.py             # POST /api/chat
│   │   └── metrics.py          # GET  /api/metrics, GET /api/health
│   ├── services/
│   │   ├── llm.py              # Groq client, chat(), extract_json()
│   │   ├── embeddings.py       # FastEmbed wrapper: embed_documents(), embed_query()
│   │   ├── vector_store.py     # Qdrant: ensure_collection(), add_chunks(), search()
│   │   ├── pdf_parser.py       # pdf -> markdown
│   │   ├── chunker.py          # markdown -> chunks
│   │   └── kpi_extractor.py    # retrieve context -> prompt -> validated KPIs
│   ├── db/
│   │   ├── database.py         # SQLAlchemy engine (sslmode from env, default "prefer")
│   │   └── metrics_repo.py     # create_table(), save_metrics(), get_latest_metrics()
│   ├── data/                   # raw_pdfs/, markdown/ (gitignored except samples)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
├── frontend/                   # Vite + React
│   └── src/
│       ├── App.jsx
│       ├── api.js              # all fetch calls in one file
│       ├── components/         # Sidebar, UploadCard, KpiCard, InsightsPanel, ChatPanel
│       └── styles.css
├── docker-compose.yml          # postgres + backend + frontend
├── .env.example
└── README.md
```

Rules: routes only handle HTTP (validate, call a service, return JSON). Services hold logic. No circular imports. No global mutable state except lazily loaded singletons (embedding model, Qdrant client).

## Backend details

**Postgres table `financial_metrics`:** `id SERIAL PK, company VARCHAR(100), year VARCHAR(10), revenue, net_income, operating_income, cash_flow, total_assets, total_liabilities, risk_factors, growth_drivers TEXT, created_at TIMESTAMP DEFAULT now()`. Add `UNIQUE (company, year)` and use `INSERT ... ON CONFLICT DO UPDATE` so re-uploading a report replaces old data instead of duplicating rows. `get_latest_metrics()` returns one row per company+year.

**API contract**
- `GET /api/health` -> `{"status":"healthy"}`
- `GET /api/metrics` -> list of rows (datetime fields must be JSON-safe; use `jsonable_encoder`)
- `POST /api/upload` (multipart `file`, PDF only, max ~25 MB) -> starts ingestion **in a FastAPI `BackgroundTasks`** and returns `{"status":"processing","file_name":...}` immediately; `GET /api/upload/status/{file_name}` returns `processing | done | failed` (simple in-memory dict is fine; mention its limits in README).
- `POST /api/chat` body `{question, company?, year?}` -> `{"answer": "..."}`

**Qdrant:** collection `investor-intelligence`, cosine distance, size 384. Filter with `FieldCondition` on `company` and `year` (year stored as string). Before adding chunks for a company+year, delete the existing points for it (same idempotency idea as the SQL upsert).

**Groq (learned the hard way — build these in from the start)**
- Default model is configurable via `GROQ_MODEL`. Model names get retired; on a 404 give a clear error telling the user to list models with `client.models.list()`. Suggested default: `openai/gpt-oss-120b` (verify it exists on your account).
- Free tier has a **~8000 tokens-per-minute cap**. Retrieve only `top_k=6` chunks and cap context at ~10,000 characters, for both chat and KPI extraction. Wrap Groq calls with a tiny retry on HTTP 429 (sleep, retry up to 3 times) and return a friendly error otherwise.
- JSON mode (`response_format={"type":"json_object"}`) does **not** enforce a schema. The prompt must list the exact JSON keys, and the Pydantic model must use aliases matching them. Missing values must be `null`.
- Model answers contain markdown (`**bold**`). The frontend must render it (see below).

**Robustness**
- Sanitize the uploaded filename (`Path(name).name`, allow only `.pdf`) to prevent path traversal.
- Parse company/year from the filename; reject with 400 if it does not match `^\d{4}_.+\.pdf$`.
- `risk_factors`/`growth_drivers` may be `null`, string, or list: normalize to newline-joined text before saving.
- Use parameterized SQL only. CORS: allow only the frontend origin from env.
- Log with the `logging` module (no bare `print`), one line per pipeline stage with timings.

## Frontend details (React + Vite, JS only)

- Layout: left sidebar (logo, upload dropzone + progress, stats), center dashboard, right collapsible chat panel. Dark theme, CSS variables: `--bg-primary:#0b0f19; --bg-secondary:#111827; --accent-blue:#0ea5e9; --accent-green:#10b981; --accent-amber:#f59e0b; --accent-red:#f43f5e; --accent-purple:#8b5cf6`. Plain CSS (one file or CSS modules), responsive.
- 6 KPI cards (Revenue, Net Income, Operating Income, Operating Cash Flow, Total Assets, Total Liabilities). Each lists companies with the value and a bar scaled to the max in that card. Parse values like `"$ 391,035"` and `"(1,200)"` (negative) safely.
- Insights panel: company `<select>`; shows growth drivers and risk factors as lists, with friendly empty states.
- Upload: drag-and-drop or click; validate PDF; call upload, then **poll the status endpoint** every 2s and show real progress states (Uploading -> Processing -> Done/Failed) instead of fake timers; refresh metrics when done; toast notifications.
- Chat: message list, typing indicator, Enter to send, company dropdown (sends `company` + `year`). Render bot text with a small safe markdown step: escape HTML first, then convert `**bold**`, `*italic*`, newlines. Never use `dangerouslySetInnerHTML` on raw model output.
- Use function components + hooks only (`useState`, `useEffect`). No Redux. State lives in `App.jsx` and is passed down as props. API base URL from `VITE_API_URL`.

## Deliverables and process

1. First reply with a short plan and the file list; wait for my "go".
2. Build backend first, run it, and verify each endpoint with curl. Then the frontend.
3. Include 6-10 focused tests (pytest): filename parsing, KPI JSON normalization, markdown-safe formatting (frontend), upsert idempotency, chat route with mocked Groq.
4. `docker-compose.yml` so `docker compose up` starts Postgres, backend, frontend. Qdrant stays embedded (volume-mounted `qdrant_data`).
5. README with: architecture diagram (mermaid), setup in 5 commands, env vars table, API table, limits of the free tier, and "how I would scale this".
6. `.gitignore` must cover `.env`, `.venv`, `node_modules`, `qdrant_data`, `__pycache__`, and generated data. Do not commit `__pycache__`.
7. Keep answers short. After each milestone tell me what to run and what I should see.

## Do NOT

- Do not add LangChain chains/agents, an ORM with models/migrations, Celery/Redis, auth, or TypeScript. Keep the surface area small enough to explain in 10 minutes.
- Do not leave dead config files or duplicate classes (the original project had a duplicated `Retriever` and an unused `settings.yaml`; avoid both).

---

# My notes (not part of the prompt)

## Suggestions I built into the prompt
- **Idempotent ingestion** (SQL `ON CONFLICT` + delete old Qdrant points): the original duplicated rows/chunks on re-upload.
- **Background ingestion + status polling**: the original blocked the upload request for minutes (local semantic chunking is slow) and the UI faked progress with timers.
- **Filename validation / path-traversal protection** on upload.
- **Rate-limit-aware Groq usage** (the biggest real-world issue on the free tier).
- **Tests, Docker Compose, logging, CORS** = the "production style" signals recruiters look for, without extra architecture.

## Optional upgrades (only if time allows)
- Hybrid retrieval (Qdrant dense + BM25 keyword) for better numeric-fact recall; several targeted queries per KPI instead of one broad query (fixes null KPIs for Tesla/Microsoft we saw).
- Show **source citations** (chunk text + page) under each chat answer.
- Streaming chat responses (SSE).
- Simple eval script: 10 known KPI values per sample report, print accuracy.

## Resume bullets (adjust numbers to your real results)
- Built a full-stack **RAG platform** (FastAPI, React, Qdrant, PostgreSQL) that ingests 10-K PDFs, extracts 8 financial KPIs with an LLM, and answers grounded questions with retrieved context.
- Designed an ingestion pipeline (PDF -> Markdown -> semantic chunking -> local embeddings -> vector store) running at **zero cost** using Groq, Qdrant and FastEmbed.
- Handled LLM production issues: token-rate limits, schema-less JSON output, idempotent re-ingestion, async processing with status polling.
- Containerized with Docker Compose; covered core logic with pytest.

## Interview talking points
- Why semantic chunking vs fixed-size; why cosine similarity; why filter by company/year payload.
- Why JSON mode needs pinned keys (no schema enforcement) and how you validate with Pydantic.
- Trade-offs of local embeddings (free, offline, slower) vs API embeddings.
- Known limits: in-memory job status, single-node embedded Qdrant, KPI misses when context is trimmed; and how you would fix each.
