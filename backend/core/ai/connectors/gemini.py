"""
Google Gemini AI Connector for GeoHarvest (TAS v1.0 §4.1, §4.6, §9.1).

Connects to Google's Gemini models (e.g. Gemini 2.5 Flash, Gemini 1.5 Pro)
for natural language geospatial intent parsing, workflow reasoning, and tool calling.
"""

import logging
from typing import Dict, Any, List, Optional
from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.ai.gemini")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False


class GeminiConnector:
    """Interface to Google Gemini API with tool calling and structured reasoning."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.default_model = default_model or settings.gemini_default_model
        self._configured = False
        self._init_client()

    def _init_client(self):
        if self.api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self._configured = True
            except Exception as e:
                logger.error(f"Failed to configure Gemini client: {e}")
                self._configured = False
        else:
            self._configured = False

    def is_configured(self) -> bool:
        """Returns True if the connector is configured with a valid API key."""
        return bool(self._configured and self.api_key and GEMINI_AVAILABLE)

    def get_status(self) -> Dict[str, Any]:
        """Returns status metadata for the Gemini connector."""
        return {
            "configured": self.is_configured(),
            "default_model": self.default_model,
            "available_models": self.list_available_models(),
            "has_api_key": bool(self.api_key),
        }

    def list_available_models(self) -> List[str]:
        """Lists available Gemini models."""
        if not self.is_configured():
            return [
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ]
        try:
            models = []
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    models.append(m.name.replace("models/", ""))
            return models or ["gemini-2.5-flash", "gemini-1.5-pro"]
        except Exception as e:
            logger.warning(f"Failed to query live Gemini models: {e}")
            return ["gemini-2.5-flash", "gemini-1.5-pro"]

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        tools: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Generates a text or function-calling response using Gemini."""
        if not self.is_configured():
            raise RuntimeError(
                "Gemini connector is not configured. Please provide GEMINI_API_KEY in your environment or Settings."
            )

        target_model = model_name or self.default_model
        try:
            model = genai.GenerativeModel(
                model_name=target_model,
                system_instruction=system_instruction,
                tools=tools,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                )
            )

            response = await model.generate_content_async(prompt)

            tool_calls = []
            text_content = ""

            for part in response.candidates[0].content.parts:
                if part.function_call:
                    tool_calls.append({
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args)
                    })
                elif part.text:
                    text_content += part.text

            return {
                "provider": "gemini",
                "model": target_model,
                "text": text_content,
                "tool_calls": tool_calls,
                "finish_reason": str(response.candidates[0].finish_reason),
            }
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise RuntimeError(f"Gemini generation failed: {str(e)}")


gemini_connector = GeminiConnector()
