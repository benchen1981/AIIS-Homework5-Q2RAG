"""
FastAPI Main Application - Enterprise Document Intelligence Platform
"""
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
import uuid
import shutil
from datetime import datetime

from config import settings
from database import get_db, init_db
from models import Document, Chunk, QueryLog, SystemConfig
from services.document_processor import DocumentProcessor
from services.ai_extractor import AIExtractor
from services.embedding_service import EmbeddingService
from services.rag_engine import RAGEngine

# Initialize FastAPI app
app = FastAPI(
    title="Enterprise Document Intelligence Platform",
    description="AI-powered document management and RAG query system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
doc_processor = DocumentProcessor()
ai_extractor = AIExtractor()
embedding_service = EmbeddingService()
rag_engine = RAGEngine()


# Pydantic models for requests/responses
class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
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
    upload_date: datetime
    file_size_bytes: int


# Background task for document processing
async def process_document_task(
    document_id: str,
    file_path: str,
    db: Session
):
    """Background task to process uploaded document"""
    try:
        # Update status to processing
        doc = db.query(Document).filter(Document.id == document_id).first()
        doc.status = "processing"
        db.commit()
        
        # Step 1: Extract text
        full_text, mime_type, error = doc_processor.process_file(file_path)
        
        if error:
            doc.status = "failed"
            doc.error_message = error
            db.commit()
            return
        
        # Update document with text
        doc.full_text = full_text
        doc.mime_type = mime_type
        
        # Detect document type if not set
        if not doc.document_type:
            doc.document_type = doc_processor.detect_document_type(full_text, doc.filename)
        
        db.commit()
        
        # Step 2: Extract metadata using AI
        if settings.enable_auto_extraction:
            metadata, extract_error = ai_extractor.extract_metadata(
                full_text,
                doc.document_type
            )
            
            if not extract_error:
                doc.doc_metadata = metadata
                db.commit()
        
        # Step 3: Create chunks and embeddings
        chunks, embeddings = embedding_service.process_document(
            document_id=str(document_id),
            text=full_text,
            metadata={'document_type': doc.document_type}
        )
        
        # Step 4: Store chunks in database
        for chunk_data in chunks:
            chunk = Chunk(
                document_id=document_id,
                chunk_index=chunk_data['chunk_index'],
                chunk_text=chunk_data['chunk_text'],
                chunk_metadata=chunk_data['metadata']
            )
            db.add(chunk)
        
        # Mark as completed
        doc.status = "completed"
        doc.processed_date = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        # Handle errors
        doc = db.query(Document).filter(Document.id == document_id).first()
        doc.status = "failed"
        doc.error_message = str(e)
        doc.retry_count += 1
        db.commit()


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "企業文件智能平台 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload and process a document
    
    - **file**: Document file (PDF, DOCX, TXT)
    - **document_type**: Optional document type classification
    """
    try:
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset
        
        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum of {settings.max_file_size_mb}MB"
            )
            
        # Check for duplicate file
        existing_doc = db.query(Document).filter(
            Document.original_filename == file.filename,
            Document.file_size_bytes == file_size,
            Document.status != 'failed'
        ).first()

        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail=f"文件 '{file.filename}' 已存在，請勿重複上傳。"
            )
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.upload_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate file
        is_valid, error = doc_processor.validate_file(file_path)
        if not is_valid:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=error)
        
        # Create database record
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size_bytes=file_size,
            document_type=document_type,
            status="pending"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Schedule background processing
        background_tasks.add_task(
            process_document_task,
            str(document.id),
            file_path,
            db
        )
        
        return DocumentUploadResponse(
            id=str(document.id),
            filename=file.filename,
            status="pending",
            message="文件上傳成功，正在後台處理。"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents", response_model=List[DocumentListResponse])
async def list_documents(
    status: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List all documents with optional filters
    
    - **status**: Filter by status (pending, processing, completed, failed)
    - **document_type**: Filter by document type
    - **limit**: Maximum number of results
    - **offset**: Pagination offset
    """
    query = db.query(Document)
    
    if status:
        query = query.filter(Document.status == status)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    documents = query.order_by(Document.upload_date.desc()).offset(offset).limit(limit).all()
    
    return [
        DocumentListResponse(
            id=str(doc.id),
            filename=doc.original_filename,
            document_type=doc.document_type,
            status=doc.status,
            upload_date=doc.upload_date,
            file_size_bytes=doc.file_size_bytes
        )
        for doc in documents
    ]


@app.get("/api/documents/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific document"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的文件 ID 格式")
    
    document = db.query(Document).filter(Document.id == doc_uuid).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="找不到文件")
    
    return {
        "id": str(document.id),
        "filename": document.original_filename,
        "document_type": document.document_type,
        "status": document.status,
        "upload_date": document.upload_date.isoformat(),
        "processed_date": document.processed_date.isoformat() if document.processed_date else None,
        "file_size_bytes": document.file_size_bytes,
        "mime_type": document.mime_type,
        "metadata": document.doc_metadata,
        "error_message": document.error_message,
        "chunk_count": len(document.chunks)
    }


@app.get("/api/documents/{document_id}/content")
async def get_document_content(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Serve the raw content of a document"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的文件 ID 格式")
    
    document = db.query(Document).filter(Document.id == doc_uuid).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="找不到文件")
    
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="文件檔案已遺失")
        
    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.mime_type or "application/octet-stream"
    )


@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Delete a document and its associated data"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的文件 ID 格式")
    
    document = db.query(Document).filter(Document.id == doc_uuid).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="找不到文件")
    
    # Delete file
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete from vector database
    embedding_service.delete_document_chunks(str(document_id))
    
    # Delete from database (cascades to chunks)
    db.delete(document)
    db.commit()
    
    return {"message": "文件刪除成功"}


@app.post("/api/search/query", response_model=SearchResponse)
async def search_query(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Execute RAG-based semantic search query
    
    - **query**: Natural language question
    - **top_k**: Number of relevant chunks to retrieve (default: 4)
    - **filters**: Optional metadata filters
    """
    try:
        # Execute RAG query
        result = rag_engine.query(
            query_text=request.query,
            top_k=request.top_k,
            filters=request.filters,
            db=db
        )
        
        # Log query if enabled
        if settings.enable_query_logging:
            query_log = QueryLog(
                query_text=request.query,
                top_k=request.top_k or settings.default_top_k,
                filters=request.filters,
                answer_text=result['answer'],
                sources=result['sources'],
                retrieval_time_ms=result['retrieval_time_ms'],
                llm_time_ms=result['llm_time_ms'],
                total_time_ms=result['total_time_ms']
            )
            db.add(query_log)
            db.commit()
        
        return SearchResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    total_docs = db.query(Document).count()
    completed_docs = db.query(Document).filter(Document.status == "completed").count()
    failed_docs = db.query(Document).filter(Document.status == "failed").count()
    total_chunks = db.query(Chunk).count()
    total_queries = db.query(QueryLog).count()
    
    return {
        "total_documents": total_docs,
        "completed_documents": completed_docs,
        "failed_documents": failed_docs,
        "total_chunks": total_chunks,
        "total_queries": total_queries,
        "token_usage": {
            "total": total_queries * 500,  # Estimated fallback
            "limit": 100000,               # Default limit
            "remaining": 100000 - (total_queries * 500)
        },
        "timestamp": datetime.utcnow().isoformat()
    }


class SystemConfigRequest(BaseModel):
    key: str
    value: dict
    description: Optional[str] = None


@app.get("/api/admin/config")
async def get_system_config(db: Session = Depends(get_db)):
    """Get all system configurations"""
    configs = db.query(SystemConfig).all()
    return {cfg.key: cfg.value for cfg in configs}


@app.post("/api/admin/config")
async def update_system_config(
    config: SystemConfigRequest,
    db: Session = Depends(get_db)
):
    """Update system configuration"""
    from models import SystemConfig
    
    # Check if exists
    existing = db.query(SystemConfig).filter(SystemConfig.key == config.key).first()
    
    if existing:
        existing.value = config.value
        if config.description:
            existing.description = config.description
    else:
        new_config = SystemConfig(
            key=config.key,
            value=config.value,
            description=config.description
        )
        db.add(new_config)
    
    db.commit()
    return {"message": "Configuration updated successfully", "key": config.key}


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("✅ Database initialized")
    print(f"✅ API running on {settings.api_host}:{settings.api_port}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
