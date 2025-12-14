"""
Embedding Service - handles text chunking and vector embeddings
"""
from typing import List, Dict, Any, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
from services.llm_client import llm_client
import uuid


class EmbeddingService:
    """Manage text chunking and vector embeddings"""
    
    def __init__(self):
        self.client = llm_client
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        
        # Initialize vector database
        if settings.vector_db_type == "chromadb":
            self.vector_db = chromadb.PersistentClient(
                path=settings.chromadb_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self.collection = self.vector_db.get_or_create_collection(
                name="document_chunks",
                metadata={"hnsw:space": "cosine"}
            )
        else:
            # Pinecone initialization would go here
            raise NotImplementedError("Pinecone support not yet implemented")
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Full document text
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        text_length = len(text)
        
        start = 0
        chunk_index = 0
        
        while start < text_length:
            # Calculate end position
            end = start + self.chunk_size
            
            # If not the last chunk, try to break at sentence boundary
            if end < text_length:
                # Look for sentence endings within the last 100 chars
                search_start = max(start, end - 100)
                sentence_endings = ['. ', '。', '! ', '！', '? ', '？', '\n\n']
                
                best_break = -1
                for ending in sentence_endings:
                    pos = text.rfind(ending, search_start, end)
                    if pos > best_break:
                        best_break = pos + len(ending)
                
                if best_break > start:
                    end = best_break
            
            # Extract chunk
            chunk_text = text[start:end].strip()
            
            # Only add if chunk is substantial
            if len(chunk_text) >= settings.min_chunk_size:
                chunk_metadata = {
                    "chunk_index": chunk_index,
                    "start_pos": start,
                    "end_pos": end,
                    **(metadata or {})
                }
                
                chunks.append({
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "metadata": chunk_metadata
                })
                
                chunk_index += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= text_length:
                break
        
        return chunks
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        return self.client.create_embeddings(texts)
    
    def store_chunks(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """
        Store chunks and embeddings in vector database
        
        Args:
            document_id: Document UUID
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        # Prepare data for ChromaDB
        ids = [f"{document_id}_{chunk['chunk_index']}" for chunk in chunks]
        documents = [chunk['chunk_text'] for chunk in chunks]
        metadatas = [
            {
                **chunk['metadata'],
                'document_id': str(document_id)
            }
            for chunk in chunks
        ]
        
        # Upsert to vector database
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    
    def search_similar(
        self,
        query_text: str,
        top_k: int = None,
        filter_metadata: Dict = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using semantic search
        
        Args:
            query_text: Query string
            top_k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of matching chunks with scores
        """
        top_k = top_k or settings.default_top_k
        
        # Create query embedding
        query_embedding = self.create_embeddings([query_text])[0]
        
        # Search in vector database
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )
        
        # Format results
        matches = []
        for i in range(len(results['ids'][0])):
            matches.append({
                'id': results['ids'][0][i],
                'document_id': results['metadatas'][0][i].get('document_id'),
                'chunk_index': results['metadatas'][0][i].get('chunk_index'),
                'text': results['documents'][0][i],
                'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                'metadata': results['metadatas'][0][i]
            })
        
        return matches
    
    def delete_document_chunks(self, document_id: str) -> None:
        """Delete all chunks for a document from vector database"""
        # Query for all chunks of this document
        results = self.collection.get(
            where={"document_id": str(document_id)}
        )
        
        if results['ids']:
            self.collection.delete(ids=results['ids'])
    
    def process_document(
        self,
        document_id: str,
        text: str,
        metadata: Dict = None
    ) -> Tuple[List[Dict], List[List[float]]]:
        """
        Complete pipeline: chunk text, create embeddings, and store
        
        Args:
            document_id: Document UUID
            text: Full document text
            metadata: Optional metadata
            
        Returns:
            Tuple of (chunks, embeddings)
        """
        # Chunk the text
        chunks = self.chunk_text(text, metadata)
        
        if not chunks:
            return [], []
        
        # Create embeddings
        chunk_texts = [chunk['chunk_text'] for chunk in chunks]
        embeddings = self.create_embeddings(chunk_texts)
        
        # Store in vector database
        self.store_chunks(document_id, chunks, embeddings)
        
        return chunks, embeddings
