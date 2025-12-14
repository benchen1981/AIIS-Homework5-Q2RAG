"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Literal, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # OpenAI
    openai_api_key: str = Field("sk-placeholder", env="OPENAI_API_KEY")
    openai_org_id: Optional[str] = Field(None, env="OPENAI_ORG_ID")
    
    # Alternative LLM Providers
    llm_provider: str = Field("openrouter", env="LLM_PROVIDER")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    grok_api_key: Optional[str] = Field(None, env="GROK_API_KEY")
    openrouter_api_key: Optional[str] = Field(None, env="OPENROUTER_API_KEY")
    
    # Vector Database
    vector_db_type: Literal["chromadb", "pinecone"] = Field("chromadb", env="VECTOR_DB_TYPE")
    chromadb_path: str = Field("./chromadb_data", env="CHROMADB_PATH")
    pinecone_api_key: Optional[str] = Field(None, env="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(None, env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field("document-embeddings", env="PINECONE_INDEX_NAME")
    
    # File Upload
    upload_dir: str = Field("./uploads", env="UPLOAD_DIR")
    max_file_size_mb: int = Field(50, env="MAX_FILE_SIZE_MB")
    allowed_extensions: List[str] = Field(["pdf", "docx", "doc", "txt"], env="ALLOWED_EXTENSIONS")
    
    # Text Processing
    chunk_size: int = Field(1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(200, env="CHUNK_OVERLAP")
    min_chunk_size: int = Field(100, env="MIN_CHUNK_SIZE")
    
    # RAG Configuration
    default_top_k: int = Field(4, env="DEFAULT_TOP_K")
    similarity_threshold: float = Field(0.7, env="SIMILARITY_THRESHOLD")
    max_context_length: int = Field(4000, env="MAX_CONTEXT_LENGTH")
    
    # LLM Configuration
    llm_model: str = Field("gpt-4o-mini", env="LLM_MODEL")
    embedding_model: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")
    llm_temperature: float = Field(0.1, env="LLM_TEMPERATURE")
    max_tokens: int = Field(2000, env="MAX_TOKENS")
    
    # Alternative LLM Models
    google_model: str = Field("gemini-pro", env="GOOGLE_MODEL")
    grok_model: str = Field("grok-beta", env="GROK_MODEL")
    openrouter_model: str = Field("google/gemini-2.0-flash-exp:free", env="OPENROUTER_MODEL")
    
    # API Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_workers: int = Field(4, env="API_WORKERS")
    cors_origins: List[str] = Field(
        ["http://localhost:8501", "http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("./logs/app.log", env="LOG_FILE")
    
    # N8N Integration
    n8n_webhook_url: Optional[str] = Field(None, env="N8N_WEBHOOK_URL")
    n8n_api_key: Optional[str] = Field(None, env="N8N_API_KEY")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Feature Flags
    enable_batch_processing: bool = Field(True, env="ENABLE_BATCH_PROCESSING")
    enable_auto_extraction: bool = Field(True, env="ENABLE_AUTO_EXTRACTION")
    enable_query_logging: bool = Field(True, env="ENABLE_QUERY_LOGGING")
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    
    # Performance
    max_concurrent_uploads: int = Field(5, env="MAX_CONCURRENT_UPLOADS")
    processing_timeout_seconds: int = Field(300, env="PROCESSING_TIMEOUT_SECONDS")
    cache_ttl_seconds: int = Field(3600, env="CACHE_TTL_SECONDS")
    
    @validator("allowed_extensions", pre=True)
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
if settings.vector_db_type == "chromadb":
    os.makedirs(settings.chromadb_path, exist_ok=True)
