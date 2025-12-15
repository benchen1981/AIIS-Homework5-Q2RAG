# Enterprise Document Intelligence Platform (RAG System)
## 5-Page Presentation Summary

---

### Phase 1: Project Overview
**Title**: Enterprise Document Intelligence Platform
**Goal**: Build a scalable, AI-powered system to manage, interact with, and extract intelligence from corporate documents (PDF, DOCX, TXT).

**Core Value Proposition**:
*   **Efficiency**: Replace manual document search with instant, semantic AI queries.
*   **Accuracy**: RAG (Retrieval-Augmented Generation) ensures answers are grounded in actual file content.
*   **Flexibility**: Supports both local enterprise deployment (Docker) and lightweight cloud demos (Streamlit Cloud).

**Technology Stack**:
*   **Frontend**: Streamlit (Python)
*   **Backend**: FastAPI (Python)
*   **AI Engine**: OpenRouter (Google Gemini Pro / GPT-4o-mini)
*   **Database**: PostgreSQL (Metadata) + ChromaDB (Vectors)

---

### Phase 2: System Architecture
**Hybrid Deployment Strategy**:

1.  **Microservices Architecture (Docker)**
    *   **Best for**: Enterprise, Scalability, Data Persistence.
    *   **Design**: Separate containers for UI, API, and Database.
    *   **Network**: Internal Docker network for secure communication.
    *   **Storage**: Persistent PostgreSQL volumes.

2.  **Monolithic Architecture (Streamlit Cloud)**
    *   **Best for**: Demos, Quick Access, Serverless.
    *   **Design**: Single "All-in-One" Python application.
    *   **Adaptation**: Replaced SQL DB with JSON Metadata; integrated RAG engine directly into the UI process.

**RAG Pipeline Flow**:
`Upload` → `Parser (PyPDF2/Docx)` → `Chunking (1000 chars)` → `Embedding (Text-Embedding-3)` → `Vector Store (Chroma)` → `Semantic Search` → `LLM Generation`

---

### Phase 3: Key Features
**1. 🔍 Intelligent RAG Search**
*   **Semantic Understanding**: Finds relevant content even without exact keyword matches.
*   **Source Citations**: Every answer includes "📚 Reference Source" with a direct link to the original file.
*   **Traditional Chinese**: Fully localized responses and UI.

**2. 📄 Smart Document Processing**
*   **Format Agnostic**: Handles PDF, Word, and Text files seamlessly.
*   **Duplicate Prevention**: Hashes files to prevent redundant uploads (Conflict Detection).

**3. ⚙️ Admin & Governance**
*   **System Dashboard**: Monitor total documents and vector chunks.
*   **Token Management**: Set daily usage limits to control API costs.
*   **API Health**: Real-time connection status monitoring.

---

### Phase 4: Technical Challenges & Solutions

| Challenge                 | Impact                                                | Solution                                                                                                     |
| ------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Docker Networking**     | Frontend couldn't reach Backend (Connection Refused). | Implemented Service Discovery using Docker aliases (`http://backend:8000`) instead of `localhost`.           |
| **API Rate Limits**       | Frequent queries caused `429 Too Many Requests`.      | Implemented **Exponential Backoff Retry** logic in the LLM Client to gracefully handle load.                 |
| **Cloud Incompatibility** | Streamlit Cloud doesn't support Docker/SQL.           | Refactored into a **Standalone Version** (`streamlit_cloud/`) with local file-based databases (SQLite/JSON). |
| **Data Hallucination**    | AI inventing facts.                                   | Enforced strict **System Prompting**: "Answer ONLY using the provided context."                              |

---

### Phase 5: Demo & Conclusion
**Validation Results**:
*   ✅ **Functionality**: All upload, search, and admin features validated.
*   ✅ **Performance**: Average query time < 2 seconds.
*   ✅ **Stability**: Successfully handled large PDFs > 50 pages.

**Project Deliverables**:
1.  **Source Code**: GitHub Repository with dual-mode support.
2.  **Documentation**: Comprehensive `README`, `debug.md`, and `prompt.md` logs.
3.  **Deployment**: Live Demo on Streamlit Cloud + `docker-compose.yml` for local run.

**Future Roadmap**:
*   Add **User Authentication** (Login/Signup).
*   Support **OCR** for scanned image PDFs.
*   Expand to **Multi-Modal** RAG (Images/Charts).
