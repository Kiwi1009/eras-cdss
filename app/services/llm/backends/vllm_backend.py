"""vLLM backend using OpenAI-compatible completions API."""
import aiohttp
import asyncio
import json
from typing import Optional
from app.services.llm.base import BaseLLMBackend, LLMGenConfig, LLMResult
from app.config import settings


class VLLMBackend(BaseLLMBackend):
    """vLLM backend using /v1/completions endpoint."""
    
    def __init__(self, base_url: str, model_id: str, timeout: int = 60):
        super().__init__("vllm", base_url, model_id, timeout)
        self.completions_path = settings.VLLM_COMPLETIONS_PATH
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
        """Generate using vLLM completions API."""
        if config is None:
            config = LLMGenConfig()
        
        url = f"{self.base_url}{self.completions_path}"
        
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "stream": False
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
                        text = data.get("choices", [{}])[0].get("text", "")
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
                            text = data.get("choices", [{}])[0].get("text", "")
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
            return LLMResult(text="", error=f"vLLM backend error: {str(e)}")
    
    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
