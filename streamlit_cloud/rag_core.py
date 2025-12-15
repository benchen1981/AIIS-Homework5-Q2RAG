import os
import json
import time
import requests
import mimetypes
import PyPDF2
import docx
import pandas as pd
import streamlit as st
import chromadb
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

# ==========================================
# Document Processor
# ==========================================
class DocumentProcessor:
    """Process various document formats and extract text"""
    
    def __init__(self):
        self.supported_formats = ['pdf', 'docx', 'doc', 'txt']
    
    def process_file(self, file_path: str) -> Tuple[str, str, Optional[str]]:
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            ext = Path(file_path).suffix.lower().lstrip('.')
            
            if ext not in self.supported_formats:
                return "", mime_type, f"Unsupported file format: {ext}"
            
            if ext == 'pdf':
                text = self._extract_from_pdf(file_path)
            elif ext in ['docx', 'doc']:
                text = self._extract_from_docx(file_path)
            elif ext == 'txt':
                text = self._extract_from_txt(file_path)
            else:
                return "", mime_type, f"No parser available for: {ext}"
            
            text = self._clean_text(text)
            
            if not text or len(text.strip()) < 10:
                return "", mime_type, "Extracted text is too short or empty"
            
            return text, mime_type, None
            
        except Exception as e:
            return "", None, f"Error processing file: {str(e)}"
    
    def _extract_from_pdf(self, file_path: str) -> str:
        text_parts = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except:
                    continue
        return "\n\n".join(text_parts)
    
    def _extract_from_docx(self, file_path: str) -> str:
        doc = docx.Document(file_path)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n\n".join(text_parts)
    
    def _extract_from_txt(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    
    def _clean_text(self, text: str) -> str:
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        return '\n'.join(lines)

# ==========================================
# Universal LLM Client
# ==========================================
class UniversalLLMClient:
    """Unified LLM Client for Streamlit Cloud"""
    
    def __init__(self):
        # Try getting keys from st.secrets first, then os.environ
        self.provider = self._get_config("LLM_PROVIDER", "openrouter").lower()
        self.openrouter_api_key = self._get_config("OPENROUTER_API_KEY")
        self.openrouter_model = self._get_config("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
        
    def _get_config(self, key, default=None):
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
        return os.getenv(key, default)

    def chat_completion(self, messages, temperature=0.7):
        if self.provider == "openrouter":
            return self._openrouter_chat(messages, temperature)
        else:
            return "Only OpenRouter supported in this demo."

    def _openrouter_chat(self, messages, temperature):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://streamlit.app/",
            "X-Title": "Streamlit Cloud RAG Demo"
        }
        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": temperature
        }
        
        # Retry logic
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt == 2: raise e
                time.sleep(1)
        return "Error calling OpenRouter"

    def create_embeddings(self, texts):
        # Use OpenRouter for embeddings (via OpenAI compatible endpoint)
        if not self.openrouter_api_key:
            # Fallback: simple deterministic hash embedding (for demo w/o key)
            # But better to error out or use sentence-transformers if local (heavy)
            # We assume key is present.
            return [[0.0]*1536 for _ in texts] # Fallback if no key

        url = "https://openrouter.ai/api/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }
        
        all_embeddings = []
        # Batching
        for i in range(0, len(texts), 20):
            batch = texts[i:i+20]
            payload = {"model": "text-embedding-3-small", "input": batch}
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    all_embeddings.extend([item["embedding"] for item in data["data"]])
                else:
                    # Fallback random/zeros
                    all_embeddings.extend([[0.0]*1536 for _ in batch])
            except:
                 all_embeddings.extend([[0.0]*1536 for _ in batch])
        return all_embeddings

# ==========================================
# RAG System (Core)
# ==========================================
class RAGSystem:
    def __init__(self):
        self.llm_client = UniversalLLMClient()
        self.doc_processor = DocumentProcessor()
        
        # Initialize ChromaDB (Persistent in current directory/session)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db_cloud")
        self.collection = self.chroma_client.get_or_create_collection(name="documents")
        
        # Metadata storage (JSON)
        self.metadata_file = "./metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self):
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f: return json.load(f)
            except: return {"documents": []}
        return {"documents": []}

    def _save_metadata(self):
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f)

    def upload_file(self, uploaded_file):
        # Save temp file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # Process
        text, _, error = self.doc_processor.process_file(tmp_path)
        if error: return False, error
        
        doc_id = str(int(time.time()))
        
        # Chunking
        chunk_size = 1000
        overlap = 200
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            chunks.append(chunk)

        # Embeddings
        embeddings = self.llm_client.create_embeddings(chunks)
        
        # Add to Chroma
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [{"document_id": doc_id, "chunk_index": i, "filename": uploaded_file.name} for i in range(len(chunks))]
        
        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        # Save Metadata
        doc_meta = {
            "id": doc_id,
            "filename": uploaded_file.name,
            "upload_time": str(datetime.now()),
            "chunk_count": len(chunks)
        }
        self.metadata["documents"].append(doc_meta)
        self._save_metadata()
        
        os.remove(tmp_path)
        return True, "Success"

    def search(self, query, top_k=4):
        # Embedding query
        query_emb = self.llm_client.create_embeddings([query])[0]
        
        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k
        )
        
        context_parts = []
        sources = []
        
        if results['documents']:
            for i, doc_text in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                score = results['distances'][0][i] if 'distances' in results else 0
                
                context_parts.append(f"Source: {meta['filename']}\nContent: {doc_text}")
                sources.append({
                    "filename": meta['filename'],
                    "text": doc_text,
                    "score": 1.0 - score # Distance to similarity rough conversion
                })
        
        context = "\n\n".join(context_parts)
        
        # Generate Answer
        sys_prompt = "You are a helpful assistant. Answer in Traditional Chinese (繁體中文). Use the provided context."
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ]
        
        answer = self.llm_client.chat_completion(messages)
        
        return {
            "answer": answer,
            "sources": sources
        }
    
    def get_documents(self):
        return self.metadata["documents"]
    
    def clear_database(self):
        try:
            self.chroma_client.delete_collection("documents")
            self.collection = self.chroma_client.get_or_create_collection("documents")
            self.metadata = {"documents": []}
            self._save_metadata()
            return True
        except Exception as e:
            return str(e)
