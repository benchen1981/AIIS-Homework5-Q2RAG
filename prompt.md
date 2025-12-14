# Project Development Prompts & Architecture

## 1. Project Structure

```
AIIS-HW5/
├── .env                        # Environment variables (API Keys, Config)
├── docker-compose.yml          # Docker composition for Backend, Frontend, DB
├── backend/
│   ├── Dockerfile              # Backend image definition
│   ├── requirements.txt        # Python dependencies
│   ├── main.py                 # FastAPI application & endpoints
│   ├── models.py               # SQLAlchemy database models
│   ├── database.py             # Database connection setup
│   └── services/
│       ├── llm_client.py       # Unified LLM provider client (OpenRouter, Google, etc.)
│       ├── rag_engine.py       # RAG core logic (Query, Retrieval, Answer)
│       ├── document_processor.py # File reading and parsing
│       ├── embedding_service.py  # Vector embedding generation
│       └── ai_extractor.py     # Metadata extraction
├── frontend/
│   ├── Dockerfile              # Frontend image definition
│   └── app.py                  # Streamlit UI
├── data/                       # Persistent database storage (Docker volume)
└── ARCHIVE_*.md                # Development change logs
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
- This ensured the correct `OPENROUTER_API_KEY` and base URL were used instead of defaulting to OpenAI's servers.

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
- Modified `rag_engine.py` to fetch `original_filename` from the database using the UUID.
- Updated `_format_sources` to return both `document_id` and `filename`.
- Added new endpoint `GET /api/documents/{id}/content`.
- Frontend: Updated source display to show filename (`智慧建築...pdf`) and added `[📥 開啟檔案]` link.

### Phase 5: Admin Features & Token Limits
**User Request:**
> "Add Admin API, Token Limit, and System configuration."

**Prompt/Action:**
- Created `SystemConfig` model in `models.py`.
- Added `GET/POST /api/admin/config` endpoints.
- Frontend: Added "⚙️ 系統設定" tab in Admin page.
- Implemented UI for setting "Daily Token Limit" and visualizing usage.

### Phase 6: Robustness (Upload Check & Rate Limits)
**User Request:**
> "Prevent duplicate uploads" and "Fix 429 Too Many Requests"

**Prompt/Action:**
- Backend: Added check in `upload_document` for existing filename + size. Returns `409 Conflict`.
- Backend: Added retry logic (Exponential Backoff) in `llm_client.py` for OpenRouter 429 errors.
- Frontend: Increased upload timeout to 120s to prevent client-side timeouts.

---
**This log captures the iterative development process from basic containerization to a refined, robust RAG application.**
