"""Smoke test for all LLM backends."""
import os
import sys
import asyncio
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.llm.base import LLMGenConfig
from app.services.llm.backends.ollama_backend import OllamaBackend
from app.services.llm.backends.vllm_backend import VLLMBackend
from app.services.llm.backends.trtllm_backend import TRTLLMBackend


async def test_backend(backend_name: str):
    """Test a specific backend."""
    print(f"\n{'='*60}")
    print(f"Testing backend: {backend_name.upper()}")
    print(f"{'='*60}")
    
    # Get config from environment or use defaults
    base_url = os.getenv("LLM_BASE_URL", settings.LLM_BASE_URL)
    model_id = os.getenv("MODEL_ID", settings.MODEL_ID)
    timeout = settings.REQUEST_TIMEOUT_S
    
    try:
        # Create backend instance directly
        if backend_name == "ollama":
            backend = OllamaBackend(base_url, model_id, timeout)
        elif backend_name == "vllm":
            backend = VLLMBackend(base_url, model_id, timeout)
        elif backend_name == "trtllm":
            backend = TRTLLMBackend(base_url, model_id, timeout)
        else:
            print(f"❌ FAILED: Unknown backend {backend_name}")
            return False
        print(f"Backend initialized: {backend.name}")
        print(f"Base URL: {backend.base_url}")
        print(f"Model ID: {backend.model_id}")
        
        # Test prompt
        test_prompt = """Please output a valid JSON object with this structure:
{
  "test": "success",
  "backend": "test"
}

Output only the JSON, no additional text."""
        
        config = LLMGenConfig(temperature=0.2, max_tokens=200)
        
        print(f"\nSending test prompt...")
        start_time = time.time()
        result = await backend.generate(test_prompt, config)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if result.error:
            print(f"❌ FAILED")
            print(f"   Error: {result.error}")
            if "not configured" in result.error.lower() or "not set" in result.error.lower():
                print(f"   ⚠️  Backend not configured. Please set LLM_BASE_URL and MODEL_ID.")
            return False
        else:
            text = result.text.strip()
            text_len = len(text)
            print(f"✓ SUCCESS")
            print(f"   Latency: {latency_ms}ms")
            print(f"   Response length: {text_len} chars")
            print(f"   Response preview: {text[:200]}...")
            
            # Try to parse as JSON
            try:
                import json
                parsed = json.loads(text)
                print(f"   ✓ Valid JSON detected")
            except:
                print(f"   ⚠️  Response is not valid JSON (may be expected)")
            
            return True
    
    except Exception as e:
        print(f"❌ FAILED")
        print(f"   Exception: {str(e)}")
        if "not configured" in str(e).lower() or "not set" in str(e).lower():
            print(f"   ⚠️  Backend not configured. Please set LLM_BASE_URL and MODEL_ID.")
        return False
    
    finally:
        # Close backend session if exists
        if hasattr(backend, 'close'):
            try:
                await backend.close()
            except:
                pass


async def main():
    """Test all backends."""
    print("LLM Backend Smoke Test")
    print("="*60)
    
    backends = ["ollama", "vllm", "trtllm"]
    results = {}
    
    for backend_name in backends:
        success = await test_backend(backend_name)
        results[backend_name] = success
        await asyncio.sleep(1)  # Brief pause between tests
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for backend_name, success in results.items():
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"  {backend_name.upper():10} {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n✓ All backends passed!")
    else:
        print("\n⚠️  Some backends failed (may be due to configuration)")


if __name__ == "__main__":
    asyncio.run(main())
