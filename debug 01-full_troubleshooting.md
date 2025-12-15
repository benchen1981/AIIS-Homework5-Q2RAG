# Debugging Log & Troubleshooting Report

This document records the critical issues encountered during the development of the Dockerized RAG system and their solutions.

## 1. Network & Connectivity Issues

### 🔴 Issue: Frontend Cannot Connect to Backend
**Error:** `ConnectionRefusedError: [Errno 111] Connection refused`
**Context:** Streamlit frontend running in Docker container trying to access `http://localhost:8000`.
**Root Cause:** inside a Docker container, `localhost` refers to the container itself, not the host machine.
**Solution:** 
- Changed `API_BASE_URL` in `app.py` from `http://localhost:8000` to `http://docdb_backend:8000` (internal service name).
- **Outcome:** Connection successful.

## 2. Authentication & API Key Errors

### 🔴 Issue: OpenAI API Key Validation Failed
**Error:** `openai.AuthenticationError: Incorrect API key provided: sk-placeholder...`
**Context:** When running RAG engine with OpenRouter key.
**Root Cause:** The `RAGEngine` was initializing a standard `OpenAI` client, defaulting to openai.com, ignoring the OpenRouter base URL.
**Solution:**
- Refactored `rag_engine.py` to use `UniversalLLMClient`.
- Explicitly mapped `${OPENROUTER_API_KEY}` in `docker-compose.yml`.
- **Outcome:** Correct verification against OpenRouter.

## 3. Rate Limiting (429 Errors)

### 🔴 Issue: OpenRouter Rate Limit Exceeded
**Error:** `requests.exceptions.HTTPError: 429 Client Error: Too Many Requests`
**Context:** Frequent RAG queries or embedding generation using free-tier models.
**Solution:**
- Implemented **Exponential Backoff Retry Logic** in `backend/services/llm_client.py`.
- Waits (1s, 2s, 4s) before giving up.
- **Outcome:** System handles transient rate limits gracefully.

## 4. Frontend & Display Bugs

### 🔴 Issue: JSON Key Error in Stats
**Error:** `KeyError: 'total_chunks'`
**Context:** The "System Stats" page crashed.
**Root Cause:** `total_chunks` field was accidentally removed from the API response during refactoring.
**Solution:** Added `total_chunks` back to `backend/main.py`.

### 🔴 Issue: Upload Timeout
**Error:** "上傳超時"
**Context:** Uploading PDF files larger than a few MBs.
**Root Cause:** Frontend HTTP client default timeout (30s) was too short for parsing+embedding.
**Solution:** Increased timeout to `120` seconds.

## 5. User Logic & Validation

### 🔴 Issue: Duplicate File Uploads
**Context:** Users could upload the same file multiple times.
**Solution:**
- Implemented pre-check in API for (Filename + Size).
- Returns `409 Conflict`.
- Frontend handles 409 error gracefully.

## 6. Streamlit Cloud Deployment

### 🔴 Issue: "API Not Connected" on Streamlit Cloud
**Error:** `requests.exceptions.ConnectionError` connecting to `http://backend:8000`.
**Context:** Deploying the Docker-based code to Streamlit Cloud.
**Root Cause:** **Architecture Mismatch**. Streamlit Cloud is a serverless environment that only runs the Python script (`app.py`). It does NOT run Docker Compose. Thus, the backend API container never starts, and `localhost` has no database.
**Solution:**
- **Re-architecture**: Created a **Standalone** version in `streamlit_cloud/`.
- **Monolithic Design**:
    - Merged `RAGEngine` logic directly into `app.py` imports (`rag_core.py`).
    - Replaced Postgres with local JSON metadata.
    - Used ChromaDB in persistent client mode.
- **Outcome:** Successfully deployed on `streamlit.app`.

---
**Summary:** The debugging process moved from Infrastructure (Docker) -> Auth -> Stability (Retries) -> Cloud Adaptation (Monolithic Refactor).
