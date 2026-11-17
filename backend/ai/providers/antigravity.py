"""
Google Antigravity Python SDK provider (V1 chat runtime, tools disabled).

Uses `google.antigravity.Agent` with `LocalAgentConfig` and explicit
`CapabilitiesConfig(enable_subagents=False, disabled_tools=list(BuiltinTools))`
per V1 Rule 8 (no autonomous task execution, MCP, RAG, or geospatial tools yet).
"""

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional

from backend.app.dependencies.config import settings
from backend.ai.config import DEFAULT_SYSTEM_PROMPT, PROVIDER_SPECS
from backend.ai.providers.base import (
    BaseAIProvider,
    ProviderAuthError,
    ProviderRequestError,
    ProviderUnavailableError,
    normalize_turns,
)

logger = logging.getLogger("geoharvest.ai.provider.antigravity")

try:
    from google.antigravity import Agent, CapabilitiesConfig, LocalAgentConfig, types as ag_types

    ANTIGRAVITY_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - surfaced explicitly when SDK isn't installed
    Agent = None  # type: ignore
    CapabilitiesConfig = None  # type: ignore
    LocalAgentConfig = None  # type: ignore
    ag_types = None  # type: ignore
    ANTIGRAVITY_SDK_AVAILABLE = False


class AntigravityProvider(BaseAIProvider):
    """Modular adapter around `google-antigravity` SDK `Agent` supporting real token streaming & cancellation."""

    provider_id = "antigravity"
    supports_streaming = True

    @staticmethod
    def _sdk_app_data_dir() -> str:
        path = settings.data_dir / "antigravity_sdk"
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    @staticmethod
    def _has_supported_auth(config: Dict[str, Any]) -> bool:
        if (config.get("_api_key") or "").strip():
            return True
        if (os.environ.get("ANTIGRAVITY_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip():
            return True
        vertex_project = (config.get("vertex_project") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
        adc_file = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
        if vertex_project and (adc_file or os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")):
            return True
        return False

    def _build_config(
        self,
        config: Dict[str, Any],
        model: Optional[str],
        system_instruction: str,
    ) -> Any:
        if not ANTIGRAVITY_SDK_AVAILABLE:
            raise ProviderUnavailableError(
                "The `google-antigravity` Python SDK is not installed in this runtime."
            )

        if not self._has_supported_auth(config):
            raise ProviderUnavailableError(
                "Antigravity SDK requires an API key (or Vertex AI project + ADC credentials). "
                "Open Settings / Connectors to configure Antigravity authentication."
            )

        api_key = (config.get("_api_key") or "").strip() or None
        vertex_project = (config.get("vertex_project") or "").strip() or None
        vertex_location = (config.get("vertex_location") or "").strip() or None
        use_vertex = bool(vertex_project and not api_key)

        kwargs: Dict[str, Any] = {
            "system_instructions": system_instruction,
            "capabilities": CapabilitiesConfig(
                enable_subagents=False,
                disabled_tools=list(ag_types.BuiltinTools),
            ),
            "app_data_dir": self._sdk_app_data_dir(),
        }
        target_model = (model or config.get("default_model") or "").strip()
        if target_model:
            kwargs["model"] = target_model
        if api_key:
            kwargs["api_key"] = api_key
        if use_vertex:
            kwargs["vertex"] = True
            kwargs["project"] = vertex_project
            if vertex_location:
                kwargs["location"] = vertex_location

        return LocalAgentConfig(**kwargs)

    @staticmethod
    def _compose_system_and_prompt(
        turns: List[Dict[str, str]],
        system_instruction: Optional[str],
    ) -> tuple[str, str]:
        base_sys = system_instruction or DEFAULT_SYSTEM_PROMPT
        if len(turns) <= 1:
            return base_sys, turns[-1]["content"]

        # Carry forward prior multi-turn context seamlessly when switching into Antigravity
        transcript_lines = []
        for t in turns[:-1]:
            speaker = "User" if t["role"] == "user" else "Assistant"
            transcript_lines.append(f"{speaker}: {t['content']}")
        combined_sys = (
            f"{base_sys}\n\n"
            "Prior conversation history for context:\n"
            + "\n".join(transcript_lines)
        )
        return combined_sys, turns[-1]["content"]

    async def list_models(self, config: Dict[str, Any]) -> List[str]:
        return list(PROVIDER_SPECS["antigravity"]["available_models"])

    async def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        if not ANTIGRAVITY_SDK_AVAILABLE:
            return {
                "ok": False,
                "provider": "antigravity",
                "message": "google-antigravity SDK package is not installed.",
            }
        if not self._has_supported_auth(config):
            return {
                "ok": False,
                "provider": "antigravity",
                "message": "Antigravity SDK needs an API key or Vertex AI ADC configuration.",
            }

        target_model = (config.get("default_model") or PROVIDER_SPECS["antigravity"]["default_model"]).strip()
        try:
            sdk_cfg = self._build_config(config, target_model, "Verify Antigravity SDK readiness.")
            # Verify Agent context initializes and cleanly tears down localharness runtime
            async with Agent(sdk_cfg) as agent:
                _ = agent.is_started
            return {
                "ok": True,
                "provider": "antigravity",
                "models": await self.list_models(config),
                "message": f"Antigravity SDK runtime verified (model={target_model}).",
            }
        except Exception as exc:
            return {
                "ok": False,
                "provider": "antigravity",
                "message": f"Antigravity SDK initialization check failed: {exc}",
            }

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        turns = normalize_turns(messages)
        if not turns:
            raise ProviderRequestError("Cannot send an empty conversation to Antigravity.")

        sys_prompt, latest_prompt = self._compose_system_and_prompt(turns, system_instruction)
        sdk_cfg = self._build_config(config, model, sys_prompt)

        response = None
        try:
            async with Agent(sdk_cfg) as agent:
                response = await agent.chat(latest_prompt)
                async for delta in response:
                    if delta:
                        yield delta
        except asyncio.CancelledError:
            if response is not None:
                try:
                    await response.cancel()
                except Exception:
                    pass
            raise
        except (ProviderUnavailableError, ProviderAuthError):
            raise
        except Exception as exc:
            err_msg = str(exc)
            if "401" in err_msg or "403" in err_msg or "API_KEY_INVALID" in err_msg or "API key" in err_msg.lower():
                raise ProviderAuthError(f"Antigravity authentication failed: {err_msg}") from exc
            raise ProviderRequestError(f"Antigravity runtime error: {err_msg}") from exc
