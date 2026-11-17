"""
GeoHarvest AI V1 Configuration & Secure Provider Credential Store.

Exclusively manages the four V1 providers:
- gemini (Google Gemini API)
- claude (Anthropic Claude API)
- ollama (Local Ollama REST API)
- antigravity (Google Antigravity Python SDK)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.ai.config")

V1_PROVIDER_IDS: Tuple[str, ...] = ("gemini", "claude", "ollama", "antigravity")

DEFAULT_SYSTEM_PROMPT = (
    "You are GeoHarvest AI, a helpful scientific and geospatial research assistant. "
    "Provide clear, accurate, concise explanations and runnable code when helpful."
)

PROVIDER_SPECS: Dict[str, Dict[str, Any]] = {
    "gemini": {
        "id": "gemini",
        "name": "Google Gemini",
        "short_name": "Gemini",
        "requires_key": True,
        "supports_base_url": False,
        "supports_streaming": True,
        "allow_manual_model": True,
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.5-pro",
        "available_models": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "description": "Google Gemini API using an API key and streaming generateContent.",
    },
    "claude": {
        "id": "claude",
        "name": "Anthropic Claude",
        "short_name": "Claude",
        "requires_key": True,
        "supports_base_url": True,
        "supports_streaming": True,
        "allow_manual_model": True,
        "default_base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-7-sonnet-20250219",
        "available_models": [
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        "description": "Anthropic Claude Messages API with SSE streaming and manual model entry.",
    },
    "ollama": {
        "id": "ollama",
        "name": "Ollama (Local)",
        "short_name": "Ollama",
        "requires_key": False,
        "supports_base_url": True,
        "supports_streaming": True,
        "allow_manual_model": False,
        "default_base_url": "http://localhost:11434",
        "default_model": "",
        "available_models": [],
        "description": "Local Ollama API with automatic model discovery from /api/tags.",
    },
    "antigravity": {
        "id": "antigravity",
        "name": "Antigravity (SDK)",
        "short_name": "Antigravity",
        "requires_key": True,
        "supports_base_url": False,
        "supports_streaming": True,
        "allow_manual_model": True,
        "default_base_url": "",
        "default_model": "gemini-3.8-flash",
        "available_models": [
            "gemini-3.8-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
        ],
        "description": "Google Antigravity Python SDK (LocalAgentConfig chat runtime, V1 no-tools mode).",
    },
}


def mask_secret(secret: str) -> str:
    """Returns a redacted representation of an API key without exposing raw credentials."""
    clean = (secret or "").strip()
    if not clean:
        return ""
    if len(clean) >= 8:
        return f"{clean[:4]}...{clean[-4:]}"
    return "****"


class AIConfigStore:
    """Persists and resolves V1 AI provider credentials and defaults safely."""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path: Path = config_path or (settings.data_dir / "credentials" / "ai_providers.json")
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._active_provider: Optional[str] = None
        self._load()

    def _load(self) -> None:
        try:
            if self._config_path.exists():
                raw = json.loads(self._config_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    loaded = raw.get("providers") or {}
                    self._configs = {
                        pid: dict(loaded[pid])
                        for pid in V1_PROVIDER_IDS
                        if isinstance(loaded.get(pid), dict)
                    }
                    active = raw.get("active_provider")
                    if active == "antigravity":
                        ag_cfg = self._configs.get("antigravity") or {}
                        if not (ag_cfg.get("api_key") or ag_cfg.get("vertex_project")):
                            active = None
                    self._active_provider = active if active in V1_PROVIDER_IDS else None
        except Exception as exc:
            logger.warning(f"Could not read persisted AI config: {exc}")

        # Seed from environment variables when no explicit key is stored yet
        gemini_env = (settings.gemini_api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
        if gemini_env and not self._configs.get("gemini", {}).get("api_key"):
            self._configs.setdefault("gemini", {})["api_key"] = gemini_env

        claude_env = (settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        if claude_env and not self._configs.get("claude", {}).get("api_key"):
            self._configs.setdefault("claude", {})["api_key"] = claude_env

        ag_env = (os.environ.get("ANTIGRAVITY_API_KEY") or "").strip()
        if ag_env and not self._configs.get("antigravity", {}).get("api_key"):
            self._configs.setdefault("antigravity", {})["api_key"] = ag_env

    def _save(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "active_provider": self._active_provider,
                "providers": self._configs,
            }
            self._config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            try:
                os.chmod(self._config_path, 0o600)
            except OSError:
                pass
        except Exception as exc:
            logger.warning(f"Failed to persist AI config: {exc}")

    @staticmethod
    def validate_provider_id(provider_id: str) -> str:
        pid = (provider_id or "").lower().strip()
        if pid not in V1_PROVIDER_IDS:
            raise ValueError(
                f"Unsupported provider '{provider_id}'. Supported V1 providers: {', '.join(V1_PROVIDER_IDS)}."
            )
        return pid

    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        """Returns normalized config for a V1 provider, keeping `_api_key` internal."""
        pid = self.validate_provider_id(provider_id)
        spec = PROVIDER_SPECS[pid]
        saved = self._configs.get(pid) or {}

        api_key = (saved.get("api_key") or "").strip()
        if pid == "gemini" and not api_key:
            api_key = (settings.gemini_api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
        elif pid == "claude" and not api_key:
            api_key = (settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        elif pid == "antigravity" and not api_key:
            api_key = (os.environ.get("ANTIGRAVITY_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()

        env_base_url = os.environ.get("OLLAMA_BASE_URL", "") if pid == "ollama" else ""
        base_url = (
            (saved.get("base_url") if spec["supports_base_url"] else "")
            or env_base_url
            or spec["default_base_url"]
            or ""
        ).strip()
        raw_default = (saved.get("default_model") or "").strip()
        if pid == "antigravity" and raw_default == "antigravity-agent":
            raw_default = ""
        env_default_model = os.environ.get("OLLAMA_MODEL", "") if pid == "ollama" else ""
        default_model = (raw_default or env_default_model or spec["default_model"] or "").strip()
        custom_models = [
            m
            for m in (saved.get("custom_models") or [])
            if not (pid == "antigravity" and m == "antigravity-agent")
        ]
        discovered_models = list(saved.get("discovered_models") or [])

        if pid == "ollama":
            models = list(dict.fromkeys(discovered_models))
            if default_model not in models:
                default_model = models[0] if models else ""
        else:
            models = list(
                dict.fromkeys(
                    ([default_model] if default_model else [])
                    + custom_models
                    + list(spec["available_models"])
                )
            )

        vertex_project = (saved.get("vertex_project") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
        vertex_location = (saved.get("vertex_location") or os.environ.get("GOOGLE_CLOUD_LOCATION") or "").strip()
        adc_path = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()

        if pid == "ollama":
            configured = bool(base_url)
        elif pid == "antigravity":
            configured = bool(api_key or (vertex_project and (adc_path or os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"))))
        else:
            configured = bool(api_key)

        return {
            "id": pid,
            "name": spec["name"],
            "short_name": spec["short_name"],
            "description": spec["description"],
            "requires_key": spec["requires_key"],
            "supports_base_url": spec["supports_base_url"],
            "supports_streaming": spec["supports_streaming"],
            "allow_manual_model": spec["allow_manual_model"],
            "configured": configured,
            "has_api_key": bool(api_key),
            "masked_key": mask_secret(api_key),
            "base_url": base_url,
            "default_model": default_model,
            "available_models": models,
            "vertex_project": vertex_project,
            "vertex_location": vertex_location,
            "_api_key": api_key,
        }

    def update_provider(
        self,
        provider_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        vertex_project: Optional[str] = None,
        vertex_location: Optional[str] = None,
        set_active: bool = True,
    ) -> None:
        pid = self.validate_provider_id(provider_id)
        entry = dict(self._configs.get(pid) or {})

        if api_key is not None:
            clean = api_key.strip()
            if clean:
                entry["api_key"] = clean
            else:
                entry.pop("api_key", None)

        if base_url is not None and PROVIDER_SPECS[pid]["supports_base_url"]:
            clean_url = base_url.strip()
            if clean_url:
                entry["base_url"] = clean_url
            else:
                entry.pop("base_url", None)

        if default_model is not None:
            clean_model = default_model.strip()
            if clean_model:
                entry["default_model"] = clean_model
                custom = [m for m in (entry.get("custom_models") or []) if m != clean_model]
                custom.insert(0, clean_model)
                entry["custom_models"] = custom[:20]

        if pid == "antigravity":
            if vertex_project is not None:
                vp = vertex_project.strip()
                if vp:
                    entry["vertex_project"] = vp
                else:
                    entry.pop("vertex_project", None)
            if vertex_location is not None:
                vl = vertex_location.strip()
                if vl:
                    entry["vertex_location"] = vl
                else:
                    entry.pop("vertex_location", None)

        self._configs[pid] = entry
        if set_active:
            self._active_provider = pid
        self._save()

    def set_discovered_ollama_models(self, base_url: str, models: List[str]) -> None:
        entry = dict(self._configs.get("ollama") or {})
        clean_models = list(dict.fromkeys(m for m in models if m))
        entry["base_url"] = base_url.strip().rstrip("/")
        entry["discovered_models"] = clean_models
        entry.pop("custom_models", None)
        if entry.get("default_model") not in clean_models:
            entry["default_model"] = clean_models[0] if clean_models else ""
        self._configs["ollama"] = entry
        self._save()

    def get_active_provider(self) -> str:
        if self._active_provider in V1_PROVIDER_IDS:
            return self._active_provider
        for pid in ("gemini", "claude", "antigravity", "ollama"):
            if self.get_provider_config(pid)["configured"]:
                return pid
        return "gemini"

    def get_public_status(self) -> Dict[str, Any]:
        providers_map: Dict[str, Dict[str, Any]] = {}
        providers_list: List[Dict[str, Any]] = []
        for pid in V1_PROVIDER_IDS:
            cfg = self.get_provider_config(pid)
            public_cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
            providers_map[pid] = public_cfg
            providers_list.append(public_cfg)
        return {
            **providers_map,
            "providers": providers_list,
            "active_provider": self.get_active_provider(),
        }


ai_config = AIConfigStore()
