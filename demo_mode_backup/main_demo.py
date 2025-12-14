"""
Demo Mode - Simplified FastAPI Application without Database
In-memory storage for quick testing
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
import shutil
from datetime import datetime
from collections import defaultdict

# In-memory storage
documents_store: Dict[str, Dict] = {}
chunks_store: Dict[str, List[Dict]] = defaultdict(list)
query_logs: List[Dict] = []

# Initialize FastAPI app
app = FastAPI(
    title="Enterprise Document Intelligence Platform - DEMO MODE",
    description="Simplified demo without database",
    version="1.0.0-demo"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 4
    filters: Optional[dict] = None

class SearchResponse(BaseModel):
    answer: str
    sources: List[dict]
    retrieval_time_ms: int
    llm_time_ms: int
    total_time_ms: int

class DocumentListResponse(BaseModel):
    id: str
    filename: str
    document_type: Optional[str]
    status: str
    upload_date: str
    file_size_bytes: int

# Ensure upload directory exists
os.makedirs("./uploads", exist_ok=True)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Enterprise Document Intelligence Platform API - DEMO MODE",
        "version": "1.0.0-demo",
        "mode": "in-memory",
        "docs": "/docs",
        "note": "This is a demo version without database. Data will be lost on restart."
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mode": "demo",
        "timestamp": datetime.utcnow().isoformat(),
        "documents_count": len(documents_store)
    }

@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = None
):
    """Upload a document (demo mode - basic storage only)"""
    try:
        # Generate unique ID and filename
        doc_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{doc_id}{file_ext}"
        file_path = os.path.join("./uploads", unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        
        # Store in memory
        documents_store[doc_id] = {
            "id": doc_id,
            "filename": file.filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size_bytes": file_size,
            "document_type": document_type or "other",
            "status": "completed",  # Simplified - mark as completed immediately
            "upload_date": datetime.utcnow(),
            "processed_date": datetime.utcnow(),
            "metadata": {"demo_mode": True, "note": "Full processing requires database"}
        }
        
        return DocumentUploadResponse(
            id=doc_id,
            filename=file.filename,
            status="completed",
            message="Document uploaded successfully (demo mode - no AI processing)"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=List[DocumentListResponse])
async def list_documents(
    status: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List all documents"""
    docs = list(documents_store.values())
    
    # Apply filters
    if status:
        docs = [d for d in docs if d["status"] == status]
    if document_type:
        docs = [d for d in docs if d["document_type"] == document_type]
    
    # Sort by upload date (newest first)
    docs.sort(key=lambda x: x["upload_date"], reverse=True)
    
    # Apply pagination
    docs = docs[offset:offset + limit]
    
    return [
        DocumentListResponse(
            id=doc["id"],
            filename=doc["original_filename"],
            document_type=doc["document_type"],
            status=doc["status"],
            upload_date=doc["upload_date"].isoformat(),
            file_size_bytes=doc["file_size_bytes"]
        )
        for doc in docs
    ]

@app.get("/api/documents/{document_id}")
async def get_document(document_id: str):
    """Get document details"""
    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[document_id]
    return {
        "id": doc["id"],
        "filename": doc["original_filename"],
        "document_type": doc["document_type"],
        "status": doc["status"],
        "upload_date": doc["upload_date"].isoformat(),
        "processed_date": doc["processed_date"].isoformat() if doc.get("processed_date") else None,
        "file_size_bytes": doc["file_size_bytes"],
        "metadata": doc.get("metadata", {}),
        "chunk_count": len(chunks_store.get(document_id, []))
    }

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[document_id]
    
    # Delete file
    if os.path.exists(doc["file_path"]):
        os.remove(doc["file_path"])
    
    # Delete from memory
    del documents_store[document_id]
    if document_id in chunks_store:
        del chunks_store[document_id]
    
    return {"message": "Document deleted successfully"}

@app.post("/api/search/query", response_model=SearchResponse)
async def search_query(request: SearchRequest):
    """
    Demo search - returns mock response
    Note: Full RAG functionality requires database and OpenAI API
    """
    import time
    start_time = time.time()
    
    # Mock response for demo
    answer = f"""[DEMO MODE] This is a simulated response for your query: "{request.query}"

To enable full AI-powered search with:
- Real document text extraction
- Semantic vector search
- GPT-4 answer generation
- Source citations

Please set up PostgreSQL and configure your OpenAI API key, then restart with the full version.

Current demo capabilities:
✓ Document upload and storage
✓ Document listing and management
✗ AI text extraction (requires OpenAI API)
✗ Semantic search (requires vector database)
✗ RAG query answering (requires OpenAI API)"""
    
    sources = [
        {
            "document_id": "demo-doc-1",
            "chunk_index": 0,
            "text": "[Demo] This is a sample source chunk. Real sources would come from your uploaded documents.",
            "score": 0.95,
            "metadata": {"demo": True}
        }
    ]
    
    total_time = int((time.time() - start_time) * 1000)
    
    # Log query
    query_logs.append({
        "query": request.query,
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "demo"
    })
    
    return SearchResponse(
        answer=answer,
        sources=sources,
        retrieval_time_ms=10,
        llm_time_ms=total_time - 10,
        total_time_ms=total_time
    )

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "mode": "demo",
        "total_documents": len(documents_store),
        "completed_documents": len([d for d in documents_store.values() if d["status"] == "completed"]),
        "failed_documents": 0,
        "total_chunks": sum(len(chunks) for chunks in chunks_store.values()),
        "total_queries": len(query_logs),
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Demo mode - limited functionality"
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 Starting Enterprise Document Intelligence Platform")
    print("📍 Mode: DEMO (In-Memory Storage)")
    print("=" * 60)
    print("✅ No database required")
    print("✅ Quick testing and evaluation")
    print("⚠️  Data will be lost on restart")
    print("⚠️  AI features disabled (requires OpenAI API key)")
    print("=" * 60)
    print("🌐 Backend API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        "main_demo:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
