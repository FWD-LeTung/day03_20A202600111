import os
import time
import google.generativeai as genai
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def _resolve_model_name(self, requested: str) -> str:
        """
        Some API keys/regions don't expose the same model IDs (and this library uses v1beta).
        If the requested model isn't found, pick the best available generateContent model.
        """
        try:
            models = list(genai.list_models())
        except Exception:
            return requested

        def supports_generate_content(m: Any) -> bool:
            methods = getattr(m, "supported_generation_methods", None) or []
            return "generateContent" in methods

        available = [m for m in models if supports_generate_content(m)]
        if not available:
            return requested

        req = (requested or "").lower()

        # Prefer exact/endswith match first
        for m in available:
            name = str(getattr(m, "name", "") or "")
            if name.lower().endswith(req) or name.lower() == req:
                return name

        # Then prefer flash/pro style heuristics
        preferred_keywords = []
        if "flash" in req:
            preferred_keywords = ["flash"]
        elif "pro" in req:
            preferred_keywords = ["pro"]
        else:
            preferred_keywords = ["flash", "pro"]

        for kw in preferred_keywords:
            for m in available:
                name = str(getattr(m, "name", "") or "")
                if kw in name.lower():
                    return name

        return str(getattr(available[0], "name", requested))

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # In Gemini, system instruction is passed during model initialization or as a prefix
        # For simplicity in this lab, we'll prepend it if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        try:
            response = self.model.generate_content(full_prompt)
        except Exception as e:
            # Common case: 404 model not found. Try to resolve an available model and retry once.
            msg = str(e)
            if "models/" in msg and ("not found" in msg.lower() or "404" in msg):
                resolved = self._resolve_model_name(self.model_name)
                if resolved != self.model_name:
                    self.model_name = resolved.replace("models/", "")
                    self.model = genai.GenerativeModel(resolved)
                    response = self.model.generate_content(full_prompt)
                else:
                    raise
            else:
                raise

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Gemini usage data is in response.usage_metadata
        content = response.text
        usage = {
            "prompt_tokens": response.usage_metadata.prompt_token_count,
            "completion_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        response = self.model.generate_content(full_prompt, stream=True)
        for chunk in response:
            yield chunk.text
