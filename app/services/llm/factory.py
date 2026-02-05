"""LLM backend factory."""
from typing import Optional
from app.config import settings
from app.services.llm.base import BaseLLMBackend
from app.services.llm.backends.ollama_backend import OllamaBackend
from app.services.llm.backends.vllm_backend import VLLMBackend
from app.services.llm.backends.trtllm_backend import TRTLLMBackend


# Singleton instance（若 MODEL_ID 變更會重建）
_backend_instance: Optional[BaseLLMBackend] = None
_backend_model_id: Optional[str] = None


def get_llm_backend() -> BaseLLMBackend:
    """
    Get LLM backend instance (singleton).
    MODEL_ID 若為 llama2 會強制使用 gpt-oss:20b；若 MODEL_ID 變更會重建 backend。
    """
    global _backend_instance, _backend_model_id
    
    model_id = settings.MODEL_ID.strip()
    if model_id.lower() == "llama2":
        model_id = "gpt-oss:20b"
    
    if _backend_instance is not None and _backend_model_id == model_id:
        return _backend_instance
    
    _backend_instance = None
    _backend_model_id = model_id
    
    backend_name = settings.LLM_BACKEND.lower()
    base_url = settings.LLM_BASE_URL
    timeout = settings.REQUEST_TIMEOUT_S
    
    if backend_name == "ollama":
        _backend_instance = OllamaBackend(base_url, model_id, timeout)
    elif backend_name == "vllm":
        _backend_instance = VLLMBackend(base_url, model_id, timeout)
    elif backend_name == "trtllm":
        _backend_instance = TRTLLMBackend(base_url, model_id, timeout)
    else:
        raise ValueError(f"Unknown LLM backend: {backend_name}. Use: ollama, vllm, or trtllm")
    
    return _backend_instance
