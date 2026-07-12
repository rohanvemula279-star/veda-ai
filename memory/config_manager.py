"""
Configuration manager for Veda AI - Lite / Veda Echo.
Handles persistence, retrieval, and validation of API keys and provider endpoints.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from config/api_keys.json."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ConfigManager] Error reading {CONFIG_PATH}: {e}")
        return {}


def save_config(data: Dict[str, Any]) -> bool:
    """Save full configuration dict to config/api_keys.json."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[ConfigManager] Error saving {CONFIG_PATH}: {e}")
        return False


def save_api_keys(
    gemini_key: str = "",
    openrouter_key: str = "",
    seekai_key: str = "",
    seekai_url: str = "",
    seekai_model: str = "",
    **kwargs: Any,
) -> bool:
    """Update and persist API keys and provider endpoints."""
    cfg = load_config()
    if gemini_key:
        cfg["gemini_api_key"] = gemini_key.strip()
    if openrouter_key:
        cfg["openrouter_api_key"] = openrouter_key.strip()
    if seekai_key:
        cfg["seekai_api_key"] = seekai_key.strip()
    if seekai_url:
        cfg["seekai_api_url"] = seekai_url.strip()
    if seekai_model:
        cfg["seekai_model"] = seekai_model.strip()

    for k, v in kwargs.items():
        if v:
            cfg[k] = v

    return save_config(cfg)


def get_seekai_key() -> str:
    """Returns SeekAI API key, falling back to gemini_api_key if it starts with 'sk-'."""
    cfg = load_config()
    k = cfg.get("seekai_api_key", "").strip()
    if not k:
        g = cfg.get("gemini_api_key", "").strip()
        if g.startswith("sk-"):
            return g
    return k


def get_seekai_url() -> str:
    """Returns SeekAI endpoint URL."""
    cfg = load_config()
    return cfg.get("seekai_api_url", "https://seekai.cc/v1/chat/completions").strip()


def get_seekai_model() -> str:
    """Returns SeekAI primary model."""
    cfg = load_config()
    return cfg.get("seekai_model", "glm-5.3-flash").strip()


def get_openrouter_key() -> str:
    """Returns OpenRouter API key."""
    cfg = load_config()
    return cfg.get("openrouter_api_key", "").strip()


def get_gemini_key() -> str:
    """Returns Gemini API key."""
    cfg = load_config()
    return cfg.get("gemini_api_key", "").strip()


def is_configured() -> bool:
    """Returns True if any valid LLM provider key is available."""
    cfg = load_config()
    seekai = cfg.get("seekai_api_key", "").strip()
    gemini = cfg.get("gemini_api_key", "").strip()
    openrouter = cfg.get("openrouter_api_key", "").strip()
    return bool(seekai or gemini or openrouter)
