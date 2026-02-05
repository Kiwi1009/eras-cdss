"""Ollama backend using native /api/generate endpoint."""
import aiohttp
import json
from typing import Optional
from app.services.llm.base import BaseLLMBackend, LLMGenConfig, LLMResult
import asyncio


class OllamaBackend(BaseLLMBackend):
    """Ollama backend using /api/generate endpoint."""
    
    def __init__(self, base_url: str, model_id: str, timeout: int = 60):
        super().__init__("ollama", base_url, model_id, timeout)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def generate(
        self,
        prompt: str,
        config: LLMGenConfig = None
    ) -> LLMResult:
        """Generate using Ollama /api/generate endpoint."""
        if config is None:
            config = LLMGenConfig()
        
        url = f"{self.base_url}/api/generate"
        # 強制避免送出 llama2（改為 gpt-oss:20b），避免 404 model not found
        model = "gpt-oss:20b" if str(self.model_id).strip().lower() == "llama2" else self.model_id
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens
            }
        }
        
        session = await self._get_session()
        
        try:
            # First attempt
            try:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        text = data.get("response", "")
                        return LLMResult(text=text)
                    else:
                        error_text = await response.text()
                        return LLMResult(
                            text="",
                            error=f"HTTP {response.status}: {error_text}"
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # Retry once on network error
                try:
                    async with session.post(
                        url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            text = data.get("response", "")
                            return LLMResult(text=text)
                        else:
                            error_text = await response.text()
                            return LLMResult(
                                text="",
                                error=f"HTTP {response.status} (retry): {error_text}"
                            )
                except Exception as retry_e:
                    return LLMResult(
                        text="",
                        error=f"Network error (retry failed): {str(retry_e)}"
                    )
        except Exception as e:
            return LLMResult(text="", error=f"Ollama backend error: {str(e)}")
    
    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
