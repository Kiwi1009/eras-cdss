"""Base LLM backend interface."""
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional


class LLMGenConfig(BaseModel):
    """LLM generation configuration."""
    temperature: float = 0.2
    max_tokens: int = 900


class LLMResult(BaseModel):
    """LLM generation result."""
    text: str
    error: Optional[str] = None


class BaseLLMBackend(ABC):
    """Base class for LLM backends."""
    
    def __init__(self, name: str, base_url: str, model_id: str, timeout: int = 60):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.timeout = timeout
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        config: LLMGenConfig = None
    ) -> LLMResult:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            config: Generation configuration
            
        Returns:
            LLMResult with text or error
        """
        pass
