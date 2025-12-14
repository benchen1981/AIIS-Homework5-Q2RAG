# Debugging Log & Troubleshooting Report

This document records the critical issues encountered during the development of the Dockerized RAG system and their solutions.

## 1. Network & Connectivity Issues

### 🔴 Issue: Frontend Cannot Connect to Backend
**Error:** `ConnectionRefusedError: [Errno 111] Connection refused`
**Context:** Streamlit frontend running in Docker container trying to access `http://localhost:8000`.
**Root Cause:** inside a Docker container, `localhost` refers to the container itself, not the host machine or other sibling containers.
**Solution:** 
- Docker Compose creates a default network where services are accessible by their service name.
- Changed `API_BASE_URL` in `app.py` from `http://localhost:8000` to `http://docdb_backend:8000` (internal) and kept `localhost` for browser-side links.
- **Outcome:** Connection successful.

## 2. Authentication & API Key Errors

### 🔴 Issue: OpenAI API Key Validation Failed
**Error:** `openai.AuthenticationError: Incorrect API key provided: sk-placeholder...`
**Context:** When running RAG queries using OpenRouter provider.
**Root Cause:** 
1. The `RAGEngine` was initializing a standard `OpenAI` client without passing the custom base URL and key for OpenRouter, causing it to default to `api.openai.com` with a placeholder key.
2. `OPENROUTER_API_KEY` was not effectively passed to the backend container.
**Solution:**
1. Unified the client: Modified `backend/services/rag_engine.py` to use the helper class `UniversalLLMClient` instead of direct instantiation.
2. Updated `docker-compose.yml` to explicitly map `${OPENROUTER_API_KEY}` from the host environment to the container.
- **Outcome:** RAG engine correctly routes requests to OpenRouter.

## 3. Rate Limiting (429 Errors)

### 🔴 Issue: OpenRouter Rate Limit Exceeded
**Error:** `requests.exceptions.HTTPError: 429 Client Error: Too Many Requests`
**Context:** Frequent RAG queries or embedding generation using free-tier models.
**Root Cause:** The application was making sequential requests too fast, hitting the provider's rate limit.
**Solution:**
- Implemented **Exponential Backoff Retry Logic** in `backend/services/llm_client.py`.
- If a 429 is received, the system waits (1s, 2s, 4s) before retrying up to 3 times.
- **Outcome:** System resilience improved significantly; transient errors are handled automatically.

## 4. Frontend & Display Bugs

### 🔴 Issue: JSON Key Error in Stats
**Error:** `KeyError: 'total_chunks'`
**Context:** The "System Stats" page crashed after modifying the backend API response structure.
**Root Cause:** In the process of adding "Token Usage" fields to `/api/stats`, the `total_chunks` field was accidentally removed from the return dictionary.
**Solution:**
- Added `total_chunks` back to the response dictionary in `backend/main.py`.
- **Outcome:** Stats page loads correctly.

### 🔴 Issue: Upload Timeout
**Error:** "上傳超時，請稍後再試"
**Context:** Uploading PDF files larger than a few MBs.
**Root Cause:** The frontend's HTTP client had a hardcoded `timeout=30` seconds. Backend processing (parsing + embedding) often takes longer.
**Solution:**
- Increased timeout to `120` seconds in `frontend/app.py`.
- **Outcome:** Uploads complete successfully.

## 5. User Logic & Validation

### 🔴 Issue: Duplicate File Uploads
**Context:** Users could upload the same file multiple times, creating redundant vector embeddings and cluttering the DB.
**Solution:**
- Implemented a pre-check in `POST /api/documents/upload`.
- Queries DB for existing document with same `original_filename` AND `file_size`.
- Returns `409 Conflict` if duplicate found.
- Frontend catches 409 and displays "Repeated Upload" warning.

---
**Summary:** The debugging process moved from infrastructure (Docker/Network) to Authentication, then to Runtime Stability (Rate limits/Timeouts), and finally to User Experience logic.
