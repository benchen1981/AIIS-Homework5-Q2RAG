"""
RAG Engine - Retrieval Augmented Generation for document Q&A
"""
from typing import List, Dict, Any, Tuple
from config import settings
from services.embedding_service import EmbeddingService
from services.llm_client import llm_client
import time


class RAGEngine:
    """RAG-based query engine for document Q&A"""
    
    def __init__(self):
        self.client = llm_client
        self.embedding_service = EmbeddingService()
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.max_tokens
    
    def query(
        self,
        query_text: str,
        top_k: int = None,
        filters: Dict = None,
        db: Any = None
    ) -> Dict[str, Any]:
        """
        Execute RAG query: retrieve relevant chunks and generate answer
        
        Args:
            query_text: User's question
            top_k: Number of chunks to retrieve
            filters: Optional metadata filters
            
        Returns:
            Dictionary with answer, sources, and timing info
        """
        start_time = time.time()
        
        # Step 1: Retrieve relevant chunks
        retrieval_start = time.time()
        sources = self.embedding_service.search_similar(
            query_text=query_text,
            top_k=top_k or settings.default_top_k,
            filter_metadata=filters
        )
        retrieval_time = int((time.time() - retrieval_start) * 1000)
        
        if not sources:
            return {
                'answer': "I couldn't find any relevant information to answer your question.",
                'sources': [],
                'retrieval_time_ms': retrieval_time,
                'llm_time_ms': 0,
                'total_time_ms': int((time.time() - start_time) * 1000)
            }
        
        # Step 2: Build context from sources
        context = self._build_context(sources)
        
        # Step 3: Generate answer using LLM
        llm_start = time.time()
        answer = self._generate_answer(query_text, context, sources)
        llm_time = int((time.time() - llm_start) * 1000)
        
        total_time = int((time.time() - start_time) * 1000)
        
        return {
            'answer': answer,
            'sources': self._format_sources(sources, db),
            'retrieval_time_ms': retrieval_time,
            'llm_time_ms': llm_time,
            'total_time_ms': total_time
        }
    
    def _build_context(self, sources: List[Dict]) -> str:
        """Build context string from retrieved sources"""
        context_parts = []
        
        for i, source in enumerate(sources):
            doc_id = source.get('document_id', 'unknown')
            chunk_idx = source.get('chunk_index', 0)
            text = source.get('text', '')
            score = source.get('score', 0)
            
            context_parts.append(
                f"[Source {i+1}] (Document: {doc_id}, Chunk: {chunk_idx}, Relevance: {score:.2f})\n{text}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Truncate if too long
        if len(context) > settings.max_context_length:
            context = context[:settings.max_context_length] + "\n...[truncated]"
        
        return context
    
    def _generate_answer(
        self,
        query: str,
        context: str,
        sources: List[Dict]
    ) -> str:
        """Generate answer using LLM with context"""
        
        system_prompt = """You are a helpful AI assistant for document search and Q&A.
Your task is to answer questions based ONLY on the provided context from documents.

Rules:
1. Answer based solely on the provided context
2. If the context doesn't contain enough information, say so clearly
3. Cite sources using [Source N] notation
4. Be concise and accurate
5. ALWAYS answer in Traditional Chinese (繁體中文), regardless of the input language, unless explicitly asked to translate.
6. Include specific details from the sources when relevant"""
        
        user_prompt = f"""Context from documents:
{context}

Question: {query}

Please provide a clear, accurate answer based on the context above. Cite your sources."""
        
        try:
            answer = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return answer
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def _format_sources(self, sources: List[Dict], db: Any = None) -> List[Dict]:
        """Format sources for response"""
        formatted = []
        
        # Cache for document filenames to avoid repeated DB queries
        doc_filename_cache = {}
        
        for source in sources:
            doc_id = source.get('document_id')
            filename = doc_id
            
            # Look up original filename if DB session is available
            if db and doc_id:
                if doc_id in doc_filename_cache:
                    filename = doc_filename_cache[doc_id]
                else:
                    try:
                        from models import Document
                        import uuid
                        doc_uuid = uuid.UUID(doc_id)
                        document = db.query(Document).filter(Document.id == doc_uuid).first()
                        if document:
                            filename = document.original_filename
                            doc_filename_cache[doc_id] = filename
                    except:
                        # Fallback to doc_id if any error occurs
                        pass
            
            formatted.append({
                'document_id': str(doc_id),           # Return original UUID
                'filename': filename,                 # Return resolved filename for display
                'chunk_index': source.get('chunk_index'),
                'text': source.get('text'),
                'score': round(source.get('score', 0), 3),
                'metadata': source.get('metadata', {})
            })
        
        return formatted
    
    def stream_query(
        self,
        query_text: str,
        top_k: int = None,
        filters: Dict = None
    ):
        """
        Stream RAG query response (for real-time UI updates)
        
        Yields chunks of the answer as they're generated
        """
        # Retrieve sources
        sources = self.embedding_service.search_similar(
            query_text=query_text,
            top_k=top_k or settings.default_top_k,
            filter_metadata=filters
        )
        
        if not sources:
            yield {
                'type': 'answer',
                'content': "I couldn't find any relevant information."
            }
            return
        
        # Yield sources first
        yield {
            'type': 'sources',
            'content': self._format_sources(sources)
        }
        
        # Build context
        context = self._build_context(sources)
        
        # Stream answer
        system_prompt = """You are a helpful AI assistant for document search and Q&A.
Answer questions based ONLY on the provided context from documents."""
        
        user_prompt = f"""Context:\n{context}\n\nQuestion: {query_text}\n\nAnswer:"""
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {
                        'type': 'answer_chunk',
                        'content': chunk.choices[0].delta.content
                    }
        
        except Exception as e:
            yield {
                'type': 'error',
                'content': str(e)
            }
