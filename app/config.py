"""Configuration management using Pydantic Settings."""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # RAG Configuration
    RAG_ENABLED: bool = True
    RAG_STORE_ROOT: str = "data/rag_store"
    RAG_SOURCE_DIR: str = "data/rag_sources"
    RAG_EMB_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 50
    
    # LLM Configuration
    LLM_BACKEND: str = "ollama"  # ollama|vllm|trtllm
    LLM_BASE_URL: str = "http://localhost:11434"
    # 若出現 "model not found"，請在終端執行：ollama pull <MODEL_ID>
    MODEL_ID: str = "gpt-oss:20b"
    REQUEST_TIMEOUT_S: int = 60

    @field_validator("MODEL_ID", mode="before")
    @classmethod
    def force_gpt_oss_if_llama2(cls, v):
        """避免 .env 或環境變數殘留 llama2，一律改為 gpt-oss:20b"""
        if v is None:
            return "gpt-oss:20b"
        s = str(v).strip()
        if s.lower() == "llama2":
            return "gpt-oss:20b"
        return s
    
    # vLLM specific
    VLLM_COMPLETIONS_PATH: str = "/v1/completions"
    VLLM_CHAT_PATH: str = "/v1/chat/completions"
    
    # Trace Configuration
    TRACE_ENABLED: bool = True
    TRACE_ROOT: str = "logs/traces"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
