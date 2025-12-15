# Project Development Prompts & Architecture

**Date**: 2025-12-15
**Developer**: Antigravity

## 1. Project Structure

```
AIIS-HW5/
├── .env                        
├── docker-compose.yml          
├── backend/
│   ├── Dockerfile              
│   ├── requirements.txt
│   ├── main.py                 
│   ├── models.py               
│   ├── database.py             
│   └── services/
│       ├── llm_client.py       
│       ├── rag_engine.py       
│       ├── document_processor.py 
│       ├── embedding_service.py  
│       └── ai_extractor.py     
├── frontend/
│   ├── Dockerfile              
│   └── app.py                  
├── streamlit_cloud/            # NEW: Standalone version for Cloud
│   ├── app.py
│   ├── rag_core.py
│   └── requirements.txt
└── openspec/changes/           # Archived logs
```

## 2. Development Interaction Log (Prompts)

### Phase 1: Docker Deployment & connectivity
**User Request:**
> "I cannot connect to the backend from the frontend in Docker."

**Prompt/Action:**
- Analyzed `docker-compose.yml` and `app.py`.
- Identified that `localhost` in Docker refers to the container itself, not the host.
- Updated `API_BASE_URL` to use the service name `http://docdb_backend:8000`.
- Ensured all environment variables (`OPENROUTER_API_KEY`, etc.) are passed from host `.env` to containers.

### Phase 2: RAG Optimization & Authorization
**User Request:**
> "API Key Error: Incorrect API key provided" and "401 Unauthorized"

**Prompt/Action:**
- Debugged `rag_engine.py` which was incorrectly initializing `OpenAI()` client directly.
- Refactored `rag_engine.py` to use the custom `UniversalLLMClient` (`llm_client.py`).
- This ensured the correct `OPENROUTER_API_KEY` and base URL were used.

### Phase 3: UI & Output Localization
**User Request:**
> "Fix newline characters in UI" and "Enforce Traditional Chinese responses"

**Prompt/Action:**
- Frontend: Replaced literal `\\n` strings with actual newlines in `app.py`.
- Backend: Updated the System Prompt in `rag_engine.py` to explicitly instruct the LLM: "ALWAYS answer in Traditional Chinese (繁體中文)".

### Phase 4: Displaying Original Filenames
**User Request:**
> "Search results show UUIDs (9ed4ab...). Change to original filenames and add open link."

**Prompt/Action:**
- Modified `rag_engine.py` to fetch `original_filename` from the database.
- Updated `_format_sources` to return both `document_id` and `filename`.
- Added new endpoint `GET /api/documents/{id}/content`.
- Frontend: Updated source display to show filename and added `[📥 開啟檔案]` link.

### Phase 5: Admin Features & Token Limits
**User Request:**
> "Add Admin API, Token Limit, and System configuration."

**Prompt/Action:**
- Created `SystemConfig` model in `models.py`.
- Added `GET/POST /api/admin/config` endpoints.
- Frontend: Added "⚙️ 系統設定" tab in Admin page.

### Phase 6: Robustness (Upload Check & Rate Limits)
**User Request:**
> "Prevent duplicate uploads" and "Fix 429 Too Many Requests"

**Prompt/Action:**
- Backend: Added check in `upload_document` for existing filename. Returns `409 Conflict`.
- Backend: Added retry logic (Exponential Backoff) in `llm_client.py`.

### Phase 7: Streamlit Cloud Adaptation (Final Phase)
**User Request:**
> "streamlit.app API Not Connected"

**Prompt/Action:**
- **Analysis**: Streamlit Cloud does not support Docker Compose/Microservices.
- **Action**: Created a **Standalone Version** in `streamlit_cloud/`.
    - Merged Backend logic into `rag_core.py`.
    - Switched from Postgres to JSON/In-Memory metadata.
    - Switched to local ChromaDB (PersistentClient).
    - Created simplified `app.py` for cloud deployment.
- **Result**: Users can deploy `streamlit_cloud/app.py` to Streamlit Cloud directly.

---
**This log captures the iterative development process from basic containerization to a refined RAG system and finally a Cloud-compatible hybrid architecture.**
