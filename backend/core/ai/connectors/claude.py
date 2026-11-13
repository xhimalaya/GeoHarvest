"""
Anthropic Claude AI Connector for GeoHarvest (TAS v1.0 §4.1, §4.6, §9.1).

Connects to Anthropic's Claude models (e.g. Claude 3.7 Sonnet, Claude 3.5 Sonnet, Claude 3 Opus)
for deep scientific reasoning, geospatial code generation, and Model Context Protocol tool execution.
"""

import logging
from typing import Dict, Any, List, Optional
from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.ai.claude")

try:
    import anthropic
    from anthropic import AsyncAnthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    anthropic = None
    AsyncAnthropic = None
    CLAUDE_AVAILABLE = False


class ClaudeConnector:
    """Interface to Anthropic Claude API with tool use and scientific reasoning."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.default_model = default_model or settings.claude_default_model
        self._client: Optional[Any] = None
        self._init_client()

    def _init_client(self):
        if self.api_key and CLAUDE_AVAILABLE:
            try:
                self._client = AsyncAnthropic(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self._client = None
        else:
            self._client = None

    def is_configured(self) -> bool:
        """Returns True if the Claude connector is active with a valid API key."""
        return bool(self._client and self.api_key and CLAUDE_AVAILABLE)

    def get_status(self) -> Dict[str, Any]:
        """Returns status metadata for the Claude connector."""
        return {
            "configured": self.is_configured(),
            "default_model": self.default_model,
            "available_models": self.list_available_models(),
            "has_api_key": bool(self.api_key),
        }

    def list_available_models(self) -> List[str]:
        """Lists standard Anthropic Claude models."""
        return [
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Generates a text or tool-calling response using Anthropic Claude."""
        if not self.is_configured():
            raise RuntimeError(
                "Claude connector is not configured. Please provide ANTHROPIC_API_KEY in your environment or Settings."
            )

        target_model = model_name or self.default_model
        try:
            kwargs: Dict[str, Any] = {
                "model": target_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_instruction:
                kwargs["system"] = system_instruction
            if tools:
                kwargs["tools"] = tools

            response = await self._client.messages.create(**kwargs)

            tool_calls = []
            text_content = ""

            for block in response.content:
                if block.type == "text":
                    text_content += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "name": block.name,
                        "args": block.input,
                        "id": block.id,
                    })

            return {
                "provider": "claude",
                "model": target_model,
                "text": text_content,
                "tool_calls": tool_calls,
                "stop_reason": str(response.stop_reason),
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }
            }
        except Exception as e:
            logger.error(f"Claude generation error: {e}")
            raise RuntimeError(f"Claude generation failed: {str(e)}")


claude_connector = ClaudeConnector()
