# AI-Powered Investor Intelligence Platform

<img width="1906" height="945" alt="RAGproject" src="https://github.com/user-attachments/assets/5024af81-e07e-47ed-a4ab-a40c439522f2" />

This repository contains the Python backend for an AI-powered Investor Intelligence Platform, including document ingestion, semantic search, KPI extraction (via Groq), Qdrant vector search, and PostgreSQL-based KPI storage. The whole stack runs free of cost: Groq's free-tier LLM API, a local on-disk Qdrant instance (no server/account needed), and local FastEmbed embeddings.

## Prerequisites

* Python 3.12+
* UV Package Manager

## Setup

### 1. Install UV

#### Windows

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### macOS/Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify installation:

```bash
uv --version
```

---

### 2. Create Virtual Environment

```bash
uv venv
```

---

### 3. Activate Virtual Environment

#### Windows

```bash
.venv\Scripts\activate
```

#### macOS/Linux

```bash
source .venv/bin/activate
```

---

### 4. Install Dependencies

```bash
uv pip install -r requirements.txt
```

---

### 5. Configure Environment Variables

Copy `.env.example` to `.env` and fill in the values (at minimum `GROQ_API_KEY` and your Postgres credentials — Qdrant works locally with no config).

---

### 6. Run the Application

```bash
python app.py
```

---

## Project Features

* Annual Report Upload & Processing
* KPI Extraction using Groq
* Qdrant Vector Search Integration
* Semantic Search & Retrieval
* RAG-based Chatbot
* PostgreSQL KPI Storage
* Investor Insights Dashboard
* Production-Grade Modular Architecture

---

## Technology Stack

### Backend

* FastAPI
* Python 3.12

### AI Services

* Groq (LLM)
* Qdrant (vector store — local on-disk by default, or a free Qdrant Cloud cluster)
* FastEmbed (local embeddings, no API key)

### Database

* PostgreSQL

### Package Management

* UV

---

## Notes

* Everything defaults to free/local: Qdrant runs on disk at `./qdrant_data` unless `QDRANT_URL` is set, and embeddings run locally via FastEmbed.
* Get a free Groq API key at [console.groq.com](https://console.groq.com).
* Verify that PostgreSQL is reachable from the application.
* Store secrets in environment variables and never commit `.env` files to source control.
